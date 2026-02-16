# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Chainlit + Gemini Chat Application

A minimal chat application using Chainlit for the UI and Google Gemini for the LLM.
This example is designed for comparison with the A2UI Simple Chat (samples/agent/adk/simple_chat).
"""

import asyncio
import os

import chainlit as cl
from dotenv import load_dotenv
from google import genai

load_dotenv()
# Also load from workspace root
_load_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env")
if os.path.exists(_load_path):
    load_dotenv(_load_path)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
SYSTEM_INSTRUCTION = """You are a helpful, friendly chat assistant. Respond naturally and concisely to the user's messages.
Keep responses brief (1-3 paragraphs) unless the user asks for more detail."""


def get_client() -> genai.Client:
    """Create a Gemini client. Uses GEMINI_API_KEY or Vertex AI if configured."""
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "TRUE":
        return genai.Client(vertexai=True)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable not set. "
            "Add it to .env or set GOOGLE_GENAI_USE_VERTEXAI=TRUE."
        )
    return genai.Client(api_key=api_key)


@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session with message history for multi-turn conversation."""
    cl.user_session.set("message_history", [])


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages: call Gemini and stream the response."""
    client = get_client()
    history = cl.user_session.get("message_history", [])

    # Build contents for Gemini (history + new message)
    # Use dict format for compatibility across google-genai versions
    contents = []
    for entry in history:
        role = "user" if entry["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": entry["content"]}]})
    contents.append({"role": "user", "parts": [{"text": message.content}]})

    # Create response message
    msg = cl.Message(content="")

    try:
        # Use sync generate_content - aio streaming has API quirks across google-genai versions.
        # Run in thread to avoid blocking the async Chainlit loop.
        def _generate() -> str:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                ),
            )
            return response.text or ""

        full_response = await asyncio.to_thread(_generate)
        await msg.stream_token(full_response)

        # Update message and persist history
        await msg.update()
        history.append({"role": "user", "content": message.content})
        history.append({"role": "assistant", "content": full_response})
        cl.user_session.set("message_history", history)

    except Exception as e:
        await cl.Message(content=f"Error: {e}").send()
