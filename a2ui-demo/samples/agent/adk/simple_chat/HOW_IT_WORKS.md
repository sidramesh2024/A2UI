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

## How Session State Is Maintained

Session state is maintained at two layers: **A2A** (transport) and **ADK** (agent runtime).

### Layer 1: A2A Protocol (context_id, task_id)

The A2A protocol uses two identifiers for conversation threading:

| Identifier | Purpose |
|------------|---------|
| **context_id** | Groups multiple tasks into one logical conversation. The client sends this on follow-up messages to continue the same conversation. |
| **task_id** | Identifies a specific task (e.g. one request–response pair). Used when attaching a message to an existing task. |

**Flow:**
- **First message:** Client sends a message without `context_id`. The server creates a new task and returns a `context_id` in the response.
- **Follow-up messages:** Client includes the stored `context_id` in the next message. The server associates it with the existing context and can access prior conversation history.

The Lit shell's `A2UIClient` does not currently store or pass `context_id` between requests. Each `sendMessage()` call is independent. To enable true multi-turn with history, the client would need to:
1. Extract `context_id` from the task response.
2. Store it (e.g. in memory or `sessionStorage`).
3. Pass it in the `message.contextId` field on subsequent `sendMessage()` calls.

The Angular Rizzcharts sample does this—see `samples/client/angular/projects/rizzcharts/src/services/a2a_service.ts`.

### Layer 2: ADK Runner (InMemorySessionService)

**Location:** `agent.py` + `google.adk.sessions.InMemorySessionService`

The agent uses `task.context_id` as the **session_id** for the ADK Runner:

```python
async for item in agent.stream(query, task.context_id):  # session_id = task.context_id
```

The Runner's `InMemorySessionService` stores sessions keyed by:
- `app_name` (e.g. `"simple_chat_agent"`)
- `user_id` (e.g. `"chat_user"`)
- `session_id` (= `task.context_id` from A2A)

When `Runner.run_async()` is called, it:
1. Looks up or creates a session for that `session_id`.
2. Appends the new user message to the session's conversation history.
3. Sends the full history to Gemini so the LLM has context.
4. Stores the assistant's response in the session.

So **when the same `context_id` is reused**, the agent has access to the full conversation and Gemini receives prior turns. When each message gets a new `context_id` (as with the current Lit client), each request is a fresh session with no history.

### Storage and Lifetime

- **InMemoryTaskStore** (A2A): Stores tasks in process memory. Lost when the server restarts.
- **InMemorySessionService** (ADK): Stores sessions in process memory. Same process lifetime.
- **InMemoryMemoryService** (ADK): Optional long-term memory. Not used by Simple Chat.

For production, these would typically be replaced with persistent stores (e.g. Redis, database).

## Multi-Turn Conversation

For the chat app, the input form stays visible after each response (`config.key === "chat"`). The user can type again. With the current Lit client, each message is sent without `context_id`, so the agent treats each as a new conversation (no prior context). To enable conversation history, the client would need to persist and send `context_id` as described above.

## A2UI vs. Other Frameworks (Streamlit, Gradio, Chainlit)

This section compares A2UI with popular frameworks for building AI chat and agent UIs. The comparison focuses on running an application like Simple Chat.

| Dimension | A2UI | Streamlit | Gradio | Chainlit |
|-----------|------|-----------|--------|----------|
| **Architecture** | Decoupled: agent (Python) + client (JS/TS). Agent sends declarative JSON; client renders. | Monolithic: Python defines UI and logic in one process. | Monolithic: Python defines UI and logic. | Monolithic: Python defines chat UI and logic. |
| **Client stack** | Web (Lit, Angular, etc.). Agent is client-agnostic. | Python-only. Streamlit renders in the browser. | Python-only. Gradio renders in the browser. | Python-only. Chainlit renders in the browser. |
| **Security** | **Strong.** Agent sends JSON descriptions only. No executable code from agent. Client controls rendering. | **Moderate.** Server runs Python; UI is server-rendered. Risk if user input drives code paths. | **Moderate.** Similar to Streamlit. | **Moderate.** Similar to Streamlit. |
| **Customization** | **High.** Client owns layout, theming, branding. Multiple clients (Lit, Angular) can share same agent. | **Limited.** Theming and layout constrained by Streamlit's API. | **Moderate.** Custom components possible but within Gradio's model. | **Moderate.** Customizable within Chainlit's chat model. |
| **Deployment** | Agent and client can be deployed separately. Client can be static (CDN); agent scales independently. | Single server. Client is served by Python process. | Single server. Client is served by Python process. | Single server. Client is served by Python process. |
| **Learning curve** | **Steeper.** Requires understanding A2A, A2UI protocol, and a web client (Lit/TS). | **Low.** Pure Python. Quick to prototype. | **Low.** Pure Python. Quick to prototype. | **Low.** Pure Python. Chat-focused. |
| **Multi-client** | **Yes.** Same agent can serve Lit, Angular, mobile, or custom clients. | **No.** One UI per Streamlit app. | **No.** One UI per Gradio app. | **No.** One UI per Chainlit app. |
| **Protocol** | A2A (Agent-to-Agent) over HTTP. Standardized, interoperable. | Proprietary. Streamlit protocol. | Proprietary. Gradio API. | Proprietary. Chainlit protocol. |
| **State management** | Explicit: `context_id`, `session_id`. Client and agent coordinate. | Implicit. Streamlit reruns script on interaction; session state in Python. | Implicit. Gradio manages state. | Implicit. Chainlit manages chat state. |
| **Production scaling** | Agent can scale horizontally. Client is static assets. | Requires scaling the Python process. WebSocket connections. | Similar to Streamlit. | Similar to Streamlit. |

### Advantages of A2UI

- **Separation of concerns:** Agent logic is independent of UI. Change the client without changing the agent.
- **Security:** Declarative UI only—no code execution from the agent. Reduces injection risk.
- **Multi-client:** One agent can power web, mobile, or embedded clients.
- **Deployment flexibility:** Static client on CDN; agent behind load balancer. Good for high traffic.
- **Standard protocol:** A2A is an open protocol; agents can interoperate with different clients.

### Disadvantages of A2UI

- **Complexity:** More moving parts (agent, A2A server, client, A2UI renderer). Steeper learning curve.
- **Python-only UI:** Streamlit/Gradio/Chainlit let you build UIs entirely in Python. A2UI requires a web client (TypeScript/Lit, etc.).
- **Maturity:** Streamlit and Gradio have larger ecosystems and more examples.
- **Prototyping speed:** For quick demos, Streamlit/Gradio are faster to get running.

### When to Choose A2UI

- You need a custom, branded client or multiple clients (web, mobile).
- Security is important (agent must not send executable code).
- You want to scale the agent independently from the UI.
- You care about protocol interoperability (A2A, agent-to-agent).

### When to Choose Streamlit / Gradio / Chainlit

- You want to prototype quickly with minimal setup.
- Your team is Python-focused and prefers not to maintain a separate frontend.
- A single, standard chat UI is sufficient.
- You need a large ecosystem of components and examples.

### Chainlit Example in This Repo

A Chainlit + Gemini chat application is available at `samples/agent/chainlit/` for direct comparison. Run it with:

```bash
cd samples/agent/chainlit && uv sync && chainlit run app.py -w
```
