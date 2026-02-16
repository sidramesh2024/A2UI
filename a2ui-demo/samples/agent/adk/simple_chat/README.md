# Simple Chat Agent

A minimal A2UI chat application - a friendly assistant powered by Gemini with no tools.

## Setup

1. Copy `.env.example` to `.env`
2. Add your `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey)

## Run

```bash
uv run .
```

Runs on http://localhost:10004 by default.

## Use with the Shell

Start the shell with the chat app:

```bash
cd ../../client/lit
npm run demo:chat
```

Then open http://localhost:5173?app=chat
