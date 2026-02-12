# A2UI - Getting Started

A **protocol for agent-driven interfaces** that enables AI agents to generate rich, interactive UIs that render natively across web, mobile, and desktop—without executing arbitrary code.

Learn more: [https://a2ui.org/](https://a2ui.org/)

## Quick Start (5 Minutes)

This guide runs the **restaurant finder demo** with a Gemini-powered agent that generates dynamic UIs.

### Prerequisites

- **Node.js** (v18 or later) - [Download here](https://nodejs.org/)
- **Python 3.13+** (for the agent backend)
- **uv** (Python package manager) - `pip install uv` or [install from uv.toml](https://docs.astral.sh/uv/)
- **Gemini API key** - [Get one free from Google AI Studio](https://aistudio.google.com/apikey)

### Step 1: Set Your API Key

Create a `.env` file in the restaurant finder agent directory:

```bash
cd a2ui-demo/samples/agent/adk/restaurant_finder
cp .env.example .env
# Edit .env and add your Gemini API key: GEMINI_API_KEY=your_key_here
```

Or export it in your terminal:

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

### Step 2: Run the Demo

From the Lit samples directory:

```bash
cd a2ui-demo/samples/client/lit
npm install
npm run demo:restaurant
```

This will:
1. Install dependencies
2. Build the A2UI renderer
3. Start the restaurant finder agent (Python backend)
4. Launch the web app at **http://localhost:5173**

### Step 3: Try It Out

In the web app, try these prompts:
- **"Book a table for 2"** - Watch the agent generate a reservation form
- **"Find Italian restaurants near me"** - See dynamic search results
- **"What are your hours?"** - Experience different UI layouts for different intents

## Other Demos

| Demo | Command | Description |
|------|---------|-------------|
| Component Gallery | `npm run serve:shell -- --gallery` | See all A2UI components (no agent required) |
| Contact Lookup | `npm run demo:contact` | Contact lookup agent with search forms |
| All demos | `npm run demo:all` | Restaurant + Contact agents together |

## Project Structure

```
a2ui-demo/
├── samples/
│   ├── agent/adk/restaurant_finder/   # Python A2A agent
│   ├── client/lit/                    # Lit web client + demos
│   │   ├── shell/                     # Main app shell
│   │   ├── component_gallery/         # Component showcase
│   │   └── contact/                   # Contact lookup
│   └── agent/adk/contact_lookup/      # Contact lookup agent
├── renderers/
│   ├── lit/                           # Lit web renderer
│   └── web_core/                      # Shared web types
└── docs/                              # Full documentation
```

## How It Works

1. **You send a message** via the web UI
2. **The A2A agent** receives it and sends to Gemini
3. **Gemini generates** A2UI JSON messages (declarative UI structure)
4. **The agent streams** these messages to the web app
5. **The A2UI renderer** converts them into native web components
6. **You see the UI** rendered in your browser

## Troubleshooting

### Port Already in Use
The dev server will try the next available port. Check the terminal for the actual URL.

### API Key Issues
```bash
# Verify the key is set
echo $GEMINI_API_KEY

# For .env: ensure it's in samples/agent/adk/restaurant_finder/.env
```

### Python Dependencies
```bash
cd a2ui-demo/samples/agent/adk/restaurant_finder
uv sync
```

## Next Steps

- [Core Concepts](a2ui-demo/docs/concepts/overview.md) - Surfaces, components, data binding
- [Client Setup](a2ui-demo/docs/guides/client-setup.md) - Integrate A2UI into your app
- [Agent Development](a2ui-demo/docs/guides/agent-development.md) - Build agents that generate UIs
- [Protocol Reference](a2ui-demo/docs/reference/messages.md) - Technical specification
