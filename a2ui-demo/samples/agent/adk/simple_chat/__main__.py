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

import click
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2ui.extension.a2ui_extension import get_a2ui_agent_extension
from agent import SimpleChatAgent
from agent_executor import SimpleChatAgentExecutor
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware

load_dotenv()
# Also load from workspace root (A2UI/.env)
_load_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", ".env")
if os.path.exists(_load_path):
    load_dotenv(_load_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10004)
def main(host, port):
    try:
        if not os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "TRUE":
            if not os.getenv("GEMINI_API_KEY"):
                raise MissingAPIKeyError(
                    "GEMINI_API_KEY environment variable not set. "
                    "Add it to .env or set GOOGLE_GENAI_USE_VERTEXAI=TRUE."
                )

        capabilities = AgentCapabilities(
            streaming=True,
            extensions=[get_a2ui_agent_extension()],
        )

        base_url = f"http://{host}:{port}"
        agent_card = AgentCard(
            name="Simple Chat",
            description="A minimal chat assistant powered by Gemini.",
            url=base_url,
            version="1.0.0",
            default_input_modes=SimpleChatAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=SimpleChatAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[
                AgentSkill(
                    id="chat",
                    name="Chat",
                    description="General conversation and Q&A.",
                    tags=["chat", "assistant"],
                    examples=["Hello!", "What can you help me with?"],
                )
            ],
        )

        agent_executor = SimpleChatAgentExecutor()
        request_handler = DefaultRequestHandler(
            agent_executor=agent_executor,
            task_store=InMemoryTaskStore(),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler,
        )

        app = server.build()
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"http://localhost:\d+",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        import uvicorn
        uvicorn.run(app, host=host, port=port)
    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()
