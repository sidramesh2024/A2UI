# Chainlit + Gemini Chat

A minimal chat application using [Chainlit](https://docs.chainlit.io/) for the UI and [Google Gemini](https://ai.google.dev/gemini-api) for the LLM. This example is designed for **comparison with the A2UI Simple Chat** (`samples/agent/adk/simple_chat`).

## Prerequisites

- Python 3.10+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Setup

1. Copy the environment file and add your API key:

   ```bash
   cp .env.example .env
   # Edit .env and set GEMINI_API_KEY=your_key
   ```

2. Install dependencies:

   ```bash
   uv sync
   # or: pip install -e .
   ```

## Run

```bash
chainlit run app.py -w
```

The `-w` flag enables auto-reload. The chat UI will be available at [http://localhost:8000](http://localhost:8000).

## Comparison with A2UI Simple Chat

| Aspect | Chainlit (this app) | A2UI Simple Chat |
|--------|---------------------|------------------|
| **Stack** | Python only (Chainlit + google-genai) | Python agent + TypeScript/Lit client |
| **UI** | Chainlit's built-in chat UI | Custom Lit shell with A2UI renderer |
| **Protocol** | Chainlit's WebSocket protocol | A2A over HTTP |
| **Lines of code** | ~90 (app.py) | Agent + executor + client + shell |
| **Conversation history** | In-memory via `cl.user_session` | ADK `InMemorySessionService` + `context_id` |
| **Streaming** | `msg.stream_token()` | A2A streaming + A2UI messages |

See `samples/agent/adk/simple_chat/HOW_IT_WORKS.md` for a detailed comparison table and when to choose each approach.
