# 🏛️ Archimedes

**Autonomous AI Agent — self-hosted, open-source alternative to Manus AI.**

Full-stack agentic platform with Docker sandbox, real-time browser control, Chromium-rendered presentations, multi-model LLM routing, and JWT authentication. Built for engineers who want full control over their AI infrastructure.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **🐳 Docker Sandbox** | Isolated Ubuntu container per session with persistent shell, noVNC desktop |
| **🧠 Multi-Model Router** | Ollama (local) → Groq → Gemini with automatic fallback |
| **🎨 Gamma-Level Slides** | Chromium-rendered PPTX with AI-generated images + Unsplash photos |
| **🔍 Web Browser** | Playwright-powered headful browser (scraping, screenshots, navigation) |
| **🔐 Auth System** | JWT + API Key dual authentication with role-based access |
| **📊 15+ Agent Tools** | Shell, files, search, browser, slides, voice, monitoring, triggers |
| **💬 Real-time UI** | Next.js + WebSocket with Manus-style split-view interface |
| **🧪 Self-Review** | Adversarial quality gate on agent outputs before delivery |
| **🗄️ PostgreSQL** | Production database with SQLite dev fallback |
| **📐 32K Context** | tiktoken-accurate sliding window with safe tool-chain preservation |

---

## 🏗️ Architecture

```
Archimedes/
├── backend/                    # Python FastAPI
│   ├── agent/                  # Agent core
│   │   ├── core.py             # Main agent loop (750+ lines)
│   │   ├── thought_engine.py   # System prompt + visual design directives
│   │   ├── self_review.py      # Adversarial self-review
│   │   ├── planner.py          # Task decomposition
│   │   ├── tool_registry.py    # Dynamic tool registration
│   │   ├── agent_profiles.py   # Agent personas
│   │   └── persona_mode.py     # Custom persona injection
│   ├── auth/                   # 🔐 Authentication
│   │   ├── jwt_handler.py      # JWT tokens + bcrypt + API keys
│   │   ├── dependencies.py     # FastAPI auth middleware
│   │   └── routes.py           # /register, /login, /me, /api-key
│   ├── models/                 # LLM clients
│   │   ├── model_router.py     # 3-tier failover routing
│   │   ├── ollama_client.py    # Gemma 4 26B (local, $0)
│   │   ├── groq_client.py      # Llama 3.3 70B (free tier)
│   │   └── gemini_client.py    # Gemini 2.5 Flash (free tier)
│   ├── tools/                  # 15 agent tools
│   │   ├── shell_tool.py       # Bash/command execution
│   │   ├── file_tool.py        # File CRUD operations
│   │   ├── browser_tool.py     # Playwright browser control
│   │   ├── search_tool.py      # Tavily web search
│   │   ├── slides_tool.py      # Chromium-rendered PPTX (1000+ lines)
│   │   ├── voice_tool.py       # TTS (gTTS) + STT (Whisper)
│   │   ├── monitor_tool.py     # URL change monitoring 24/7
│   │   ├── mirofish_tool.py    # Audience reaction analysis
│   │   ├── trigger_tool.py     # Conditional AND/OR triggers
│   │   ├── expose_tool.py      # Port tunneling (localhost.run)
│   │   ├── webdev_tool.py      # Web development assistant
│   │   ├── document_tool.py    # PDF processing
│   │   ├── schedule_tool.py    # Cron-like task scheduling
│   │   ├── plan_tool.py        # Plan management
│   │   └── message_tool.py     # Message formatting
│   ├── sandbox/                # Docker container lifecycle
│   │   ├── manager.py          # Session ↔ container mapping
│   │   ├── executor.py         # Command execution + persistent shell
│   │   ├── filesystem.py       # File I/O in sandbox
│   │   └── novnc.py            # VNC desktop streaming
│   ├── memory/                 # Context management
│   │   ├── context_manager.py  # 32K sliding window + tiktoken
│   │   └── vector_store.py     # ChromaDB long-term memory
│   ├── websocket/              # Real-time communication
│   │   └── handler.py          # WS connection manager + auth
│   ├── api/                    # REST API
│   │   └── routes.py           # CRUD endpoints + workspace
│   ├── db/                     # Database layer
│   │   ├── models.py           # SQLAlchemy ORM (User, Session, Task, etc.)
│   │   └── crud.py             # Async CRUD + PostgreSQL pool
│   ├── config.py               # All settings (.env driven)
│   └── main.py                 # FastAPI app entry point
├── frontend/                   # Next.js 14
│   ├── app/                    # App Router
│   ├── components/             # 17 React components
│   │   ├── ChatPanel.tsx       # Main chat interface
│   │   ├── ComputerPanel.tsx   # Code editor + terminal + browser
│   │   ├── AgentDashboard.tsx  # Agent status monitoring
│   │   ├── Sidebar.tsx         # Navigation + history
│   │   └── ...                 # 13 more components
│   └── lib/
│       └── websocket.ts        # WebSocket client
├── docker/
│   └── sandbox.Dockerfile      # Ubuntu 22.04 sandbox image
├── docker-compose.yml          # PostgreSQL 16 service
├── tests/                      # Test suite
├── requirements.txt            # Python dependencies
└── .env.example                # Configuration template
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Docker Desktop** (running)
- **Ollama** with `gemma4:26b` model

### 1. Configure

```bash
cp .env.example .env
# Edit .env — add your API keys (Groq, Google, Tavily)
```

### 2. Start PostgreSQL (optional)

```bash
docker-compose up -d
# If skipped — SQLite fallback is automatic
```

### 3. Build sandbox image

```bash
docker build -t cosmo-sandbox:latest -f docker/sandbox.Dockerfile .
```

### 4. Start backend

```bash
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 5. Start frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

---

## 🧠 LLM Models

| Priority | Model | Provider | Cost | Used For |
|:---:|---|---|:---:|---|
| 1 | Gemma 4 26B | Ollama (local) | **$0** | Primary — all tasks |
| 2 | Llama 3.3 70B | Groq (free tier) | $0 | Fast fallback |
| 3 | Gemini 2.5 Flash | Google AI Studio | $0 | Planning, research |

Total monthly cost: **$0**

---

## 🔐 Authentication

Auth is **disabled by default** (`AUTH_ENABLED=false`) for frictionless development.

To enable:

```env
AUTH_ENABLED=true
JWT_SECRET_KEY=your-secure-secret-here
```

### Auth Flow

```bash
# Register (first user = admin)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "secret"}'

# Login → JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@example.com&password=secret"

# Use token
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# Or use API key
curl http://localhost:8000/api/v1/auth/me \
  -H "X-API-Key: YOUR_API_KEY"
```

---

## 🎨 Presentation Engine

Chromium-rendered slides at Gamma/Kimi quality level:

- **8 layouts**: content, stat, quote, two_col, infographic, image_left, image_right, cta
- **5 themes**: dark, light, navy, aurora, corporate
- **AI images**: Pollinations.ai generation with Unsplash fallback
- **Split views**: Gamma-style image_left / image_right layouts
- **Real photos**: Unsplash integration with keyword search

---

## 🛠️ Agent Tools (15)

| Tool | Description |
|------|-------------|
| `shell` | Execute commands in sandbox |
| `file` | Read/write/list files |
| `browser` | Navigate, screenshot, scrape via Playwright |
| `search` | Web search via Tavily API |
| `slides` | Generate Gamma-level PPTX presentations |
| `voice` | Text-to-speech (gTTS) + speech recognition |
| `monitor` | 24/7 URL change detection |
| `mirofish` | Audience reaction analysis |
| `trigger` | Conditional AND/OR action triggers |
| `expose` | Share localhost via tunnel |
| `webdev` | Web development assistant |
| `document` | PDF text extraction |
| `schedule` | Cron-like task scheduling |
| `plan` | Task decomposition + tracking |
| `message` | Message formatting for user |

---

## ⚙️ Configuration

All settings are in `.env`. See [.env.example](.env.example) for the complete list.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Primary database |
| `DATABASE_URL_SQLITE` | `sqlite+aiosqlite:///...` | Dev fallback |
| `AUTH_ENABLED` | `false` | Enable JWT authentication |
| `AGENT_MAX_CONTEXT_TOKENS` | `32768` | Context window size |
| `SANDBOX_MAX_CONTAINERS` | `3` | Max concurrent sandboxes |
| `USE_MULTI_AGENT` | `false` | Multi-agent orchestration (coming soon) |

---

## 📋 Roadmap

- [x] Docker sandbox with persistent shell
- [x] Multi-model LLM routing (Ollama → Groq → Gemini)
- [x] 15 agent tools
- [x] Chromium-rendered presentations (Gamma/Kimi level)
- [x] AI image generation for slides
- [x] JWT + API Key authentication
- [x] PostgreSQL with connection pooling
- [x] 32K context window with tiktoken
- [ ] Multi-agent orchestration (Planner → Executor → Critic)
- [ ] MCP protocol integration
- [ ] CI/CD pipeline with >60% test coverage

---

## License

MIT
