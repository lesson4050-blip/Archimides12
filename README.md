# Archimedes

Autonomous AI Agent — local, open-source alternative to Manus AI.

## Architecture

```
Archimedes/
├── backend/                 # Python FastAPI backend
│   ├── agent/               # Agent loop, profiles, skills
│   │   ├── core.py          # Main agent loop
│   │   ├── thought_engine.py # System prompt
│   │   ├── agent_profiles.py # Agent personas
│   │   ├── skills.py        # Self-evolution skill manager
│   │   └── tool_registry.py # Tool registration
│   ├── models/              # LLM clients
│   │   ├── model_router.py  # 3-tier routing (Groq → Gemini → Ollama)
│   │   ├── groq_client.py
│   │   ├── gemini_client.py
│   │   └── ollama_client.py
│   ├── tools/               # Agent tools
│   │   ├── shell_tool.py    # Bash execution
│   │   ├── file_tool.py     # File operations
│   │   ├── browser_tool.py  # Playwright browser
│   │   ├── search_tool.py   # Tavily search
│   │   ├── expose_tool.py   # Port tunneling
│   │   └── ...
│   ├── sandbox/             # Docker sandbox management
│   ├── memory/              # ChromaDB + context
│   ├── websocket/           # Real-time WebSocket
│   ├── api/                 # REST API routes
│   ├── db/                  # SQLite via SQLAlchemy
│   ├── tester/              # Diagnostic system
│   └── config.py            # Settings (reads .env)
├── frontend/                # Next.js 14 UI
│   ├── app/                 # Next.js App Router
│   ├── components/          # React components
│   └── lib/                 # WebSocket client
├── docker/                  # Docker configuration
│   ├── sandbox.Dockerfile   # Ubuntu sandbox image
│   └── docker-compose.yml
├── tests/                   # Test suite
├── run_tester.py            # Diagnostic runner
└── requirements.txt         # Python dependencies
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker Desktop (running)
- Ollama (running with gemma4:26b)

### Setup

**1. Clone and configure:**
```bash
cp .env.example .env
# Fill in your API keys in .env
```

**2. Build sandbox:**
```bash
docker build -t cosmo-sandbox:latest -f docker/sandbox.Dockerfile .
```

**3. Start backend:**
```bash
cd backend
pip install -r ../requirements.txt
python run.py
# Runs on http://localhost:8001
```

**4. Start frontend:**
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

**5. Run diagnostics:**
```bash
python run_tester.py
```

## Models

| Priority | Model | Provider | Used For |
|---|---|---|---|
| 1 | Llama 3.3 70B | Groq (free) | Fast iterations |
| 2 | Gemini 2.5 Flash | Google AI Studio (free) | Planning, research |
| 3 | Gemma 4 26B MoE | Ollama (local) | Fallback |

## Environment Variables

See `.env.example` for all required variables.

## License

MIT
