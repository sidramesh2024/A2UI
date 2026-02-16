# How Simple Chat Works: Agent–Frontend Interaction with A2UI

This document explains how the Simple Chat application uses the A2UI protocol to enable communication between a Python agent (backend) and a Lit-based web client (frontend).

## Overview

Simple Chat is a minimal A2UI demo: the user types a message, the agent (powered by Gemini) generates a response, and the frontend renders it as a styled UI component—all without the agent sending executable code. The agent sends **declarative JSON** that describes the UI; the client renders it using its own native components.

## Architecture

```
┌─────────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│   Web Client    │         │   A2A Server         │         │   Gemini API    │
│   (Lit Shell)   │         │   (Agent Executor)   │         │   (LLM)         │
└────────┬────────┘         └──────────┬───────────┘         └────────┬────────┘
         │                              │                               │
         │  1. User types "Hello"       │                               │
         │  2. POST (A2A + A2UI ext)    │                               │
         │─────────────────────────────>│                               │
         │                              │  3. Extract text, call agent  │
         │                              │  4. Agent calls Gemini        │
         │                              │──────────────────────────────>│
         │                              │  5. Gemini returns text       │
         │                              │<──────────────────────────────│
         │                              │  6. Convert text → A2UI JSON   │
         │  7. A2UI messages (JSON)     │                               │
         │<─────────────────────────────│                               │
         │  8. Render Card with text    │                               │
         │                              │                               │
```

## Protocols Involved

### 1. A2A (Agent-to-Agent)

[A2A](https://a2a.dev/) is the transport layer. It defines how messages are sent between clients and agents over HTTP. The client discovers the agent via `/.well-known/agent-card.json` and sends messages using the A2A message format.

### 2. A2UI Extension

A2UI extends A2A. The client signals support by sending:

```
X-A2A-Extensions: https://a2ui.org/a2a-extension/a2ui/v0.8
```

When this header is present, the agent returns UI descriptions as **A2UI messages** (JSON) instead of plain text. Each A2UI message describes a UI change: define a surface, add components, update data, etc.

## End-to-End Flow

### Step 1: User Sends a Message (Frontend)

**Location:** `samples/client/lit/shell/app.ts`

1. User types in the input and submits the form.
2. The shell calls `A2UIClient.send(message)` with the text (e.g. `"Hello!"`).
3. The client wraps it in an A2A message:
   - **Text input:** `parts: [{ kind: "text", text: "Hello!" }]`
   - **UI events (e.g. button clicks):** `parts: [{ kind: "data", data: { userAction: {...} }, mimeType: "application/json+a2ui" }]`
4. The request includes `X-A2A-Extensions: https://a2ui.org/a2a-extension/a2ui/v0.8` so the agent knows to return A2UI.

### Step 2: Agent Receives the Message (Backend)

**Location:** `samples/agent/adk/simple_chat/agent_executor.py`

1. The A2A server receives the message and routes it to `SimpleChatAgentExecutor.execute()`.
2. `try_activate_a2ui_extension(context)` checks for the A2UI extension → `use_ui = True`.
3. `context.get_user_input()` extracts the user's text from the message parts.
4. The executor calls `agent.stream(query, task.context_id)`.

### Step 3: Agent Calls Gemini (Backend)

**Location:** `samples/agent/adk/simple_chat/agent.py`

1. `SimpleChatAgent` uses Google ADK's `LlmAgent` with Gemini.
2. The agent has no tools—it only generates conversational text.
3. `Runner.run_async()` sends the user message to Gemini and streams the response.
4. The agent yields `{ "is_task_complete": True, "content": "Hi! How can I help you today?" }` (plain text).

### Step 4: Text → A2UI Conversion (Backend)

**Location:** `samples/agent/adk/simple_chat/agent_executor.py`

Because `use_ui` is true, the executor does **not** send raw text. Instead, it calls `_text_to_a2ui_messages(response_text)` to build A2UI messages:

```python
def _text_to_a2ui_messages(response_text: str) -> list[dict]:
    return [
        {"beginRendering": {"surfaceId": "chat", "root": "root-column", ...}},
        {"surfaceUpdate": {"surfaceId": "chat", "components": [...]}},
        {"dataModelUpdate": {"surfaceId": "chat", "contents": [{"key": "response", "valueString": response_text}]}}
    ]
```

Each message is wrapped in an A2A `DataPart` with `mimeType: "application/json+a2ui"` and sent back to the client.

### Step 5: Client Receives A2UI Messages (Frontend)

**Location:** `samples/client/lit/shell/client.ts`

1. The A2AClient receives the task response.
2. It extracts `data` parts with A2UI content from `result.status.message.parts`.
3. Returns an array of A2UI messages: `[{ beginRendering: {...} }, { surfaceUpdate: {...} }, { dataModelUpdate: {...} }]`.

### Step 6: Client Renders the UI (Frontend)

**Location:** `samples/client/lit/shell/app.ts` + `@a2ui/lit` renderer

1. The shell passes messages to `processor.processMessages(messages)`.
2. The A2UI processor (from `@a2ui/lit`) interprets each message:
   - **beginRendering:** Create a surface `"chat"` with root `"root-column"`.
   - **surfaceUpdate:** Define the component tree (Column → Card → Text).
   - **dataModelUpdate:** Set `/response` to the agent's text.
3. The Text component binds to `{"path": "/response"}` and displays the value.
4. The Lit renderer produces real DOM: a Card containing the response text.

## A2UI Message Format (Simple Chat)

For each response, the agent sends three A2UI messages:

### 1. beginRendering

Tells the client to create a rendering surface:

```json
{
  "beginRendering": {
    "surfaceId": "chat",
    "root": "root-column",
    "styles": { "primaryColor": "#6366f1", "font": "system-ui" }
  }
}
```

### 2. surfaceUpdate

Defines the component tree (adjacency list):

```json
{
  "surfaceUpdate": {
    "surfaceId": "chat",
    "components": [
      { "id": "root-column", "component": { "Column": { "children": { "explicitList": ["response-card"] } } } },
      { "id": "response-card", "component": { "Card": { "child": "response-text" } } },
      { "id": "response-text", "component": { "Text": { "text": { "path": "/response" }, "usageHint": "body" } } }
    ]
  }
}
```

### 3. dataModelUpdate

Populates the data model that components bind to:

```json
{
  "dataModelUpdate": {
    "surfaceId": "chat",
    "contents": [
      { "key": "response", "valueString": "Hi! How can I help you today?" }
    ]
  }
}
```

The Text component uses `"path": "/response"`, so it displays the value of `response` from the data model.

## Key Files

| File | Role |
|------|------|
| `agent.py` | LlmAgent + Gemini; produces plain text |
| `agent_executor.py` | Receives A2A messages, calls agent, converts text → A2UI |
| `__main__.py` | A2A server (Starlette/Uvicorn) on port 10004 |
| `shell/client.ts` | A2AClient; sends messages, receives A2UI parts |
| `shell/app.ts` | Shell UI; form, A2UI processor, surface rendering |
| `shell/configs/chat.ts` | Chat config (title, placeholder, serverUrl) |
| `@a2ui/lit` | A2UI renderer; turns JSON into Lit components |

## Security: Why Declarative UI?

A2UI sends **declarative descriptions**, not executable code. The agent can only use components from the client's catalog (e.g. `Text`, `Card`, `Column`). The client decides how to render them. This prevents UI injection attacks—the agent cannot run arbitrary JavaScript or inject malicious HTML.

## Multi-Turn Conversation

For the chat app, the input form stays visible after each response (`config.key === "chat"`). The user can type again. Each message creates a new A2A task; the agent uses `session_id` (from `task.context_id`) to maintain conversation history via the Runner's session service.
