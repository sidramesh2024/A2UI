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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
from collections.abc import AsyncIterable
from typing import Any

from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

logger = logging.getLogger(__name__)

AGENT_INSTRUCTION = """You are a helpful, friendly chat assistant. Respond naturally and concisely to the user's messages.
Keep responses brief (1-3 paragraphs) unless the user asks for more detail."""


class SimpleChatAgent:
    """A minimal chat agent with no tools - just conversational responses."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, use_ui: bool = False):
        self.use_ui = use_ui
        self._agent = self._build_agent()
        self._user_id = "chat_user"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def get_processing_message(self) -> str:
        return "Thinking..."

    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for chat."""
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        return LlmAgent(
            model=Gemini(model=model),
            name="simple_chat_agent",
            description="A friendly chat assistant.",
            instruction=AGENT_INSTRUCTION,
            tools=[],  # No tools - pure chat
        )

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )

        current_message = types.Content(
            role="user", parts=[types.Part.from_text(text=query)]
        )
        final_response_content = None

        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session.id,
            new_message=current_message,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_content = "\n".join(
                        [p.text for p in event.content.parts if p.text]
                    )
                break
            else:
                yield {
                    "is_task_complete": False,
                    "updates": self.get_processing_message(),
                }

        if final_response_content:
            yield {
                "is_task_complete": True,
                "content": final_response_content.strip(),
            }
        else:
            yield {
                "is_task_complete": True,
                "content": "I'm sorry, I couldn't generate a response. Please try again.",
            }
