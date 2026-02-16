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

import json
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, Task, TaskState, TextPart, UnsupportedOperationError
from a2a.utils import new_agent_parts_message, new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from agent import SimpleChatAgent
from a2ui.extension.a2ui_extension import create_a2ui_part, try_activate_a2ui_extension

logger = logging.getLogger(__name__)


def _text_to_a2ui_messages(response_text: str) -> list[dict]:
    """Convert plain text response to A2UI messages (Card with text)."""
    # Escape for JSON - newlines become \n
    escaped = json.dumps(response_text)[1:-1]  # Remove outer quotes
    return [
        {
            "beginRendering": {
                "surfaceId": "chat",
                "root": "root-column",
                "styles": {"primaryColor": "#6366f1", "font": "system-ui"},
            }
        },
        {
            "surfaceUpdate": {
                "surfaceId": "chat",
                "components": [
                    {
                        "id": "root-column",
                        "component": {
                            "Column": {
                                "children": {"explicitList": ["response-card"]},
                                "distribution": "start",
                                "alignment": "stretch",
                            }
                        },
                    },
                    {
                        "id": "response-card",
                        "component": {
                            "Card": {
                                "child": "response-text",
                            }
                        },
                    },
                    {
                        "id": "response-text",
                        "component": {
                            "Text": {
                                "text": {"path": "/response"},
                                "usageHint": "body",
                            }
                        },
                    },
                ],
            }
        },
        {
            "dataModelUpdate": {
                "surfaceId": "chat",
                "contents": [
                    {"key": "response", "valueString": response_text},
                ],
            }
        },
    ]


class SimpleChatAgentExecutor(AgentExecutor):
    """Simple chat agent executor - converts text responses to A2UI when needed."""

    def __init__(self):
        self.ui_agent = SimpleChatAgent(use_ui=True)
        self.text_agent = SimpleChatAgent(use_ui=False)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        if not query or not str(query).strip():
            query = "Hello!"

        logger.info(f"--- SimpleChat: Processing message: '{query[:50]}...' ---")
        use_ui = try_activate_a2ui_extension(context)
        agent = self.ui_agent if use_ui else self.text_agent

        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        async for item in agent.stream(query, task.context_id):
            if not item["is_task_complete"]:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(item["updates"], task.context_id, task.id),
                )
                continue

            content = item["content"]
            final_parts = []

            if use_ui:
                a2ui_messages = _text_to_a2ui_messages(content)
                for msg in a2ui_messages:
                    final_parts.append(create_a2ui_part(msg))
            else:
                final_parts.append(Part(root=TextPart(text=content)))

            await updater.update_status(
                TaskState.input_required,
                new_agent_parts_message(final_parts, task.context_id, task.id),
                final=False,
            )
            break

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
