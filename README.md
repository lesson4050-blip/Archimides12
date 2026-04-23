# ⚡ Archimedes AI Agent

> **A production-grade, autonomous AI agent framework with self-correction, multi-agent swarm logic, and native MCP tool integration.**

[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)

---

## What is Archimedes?

Archimedes is a fully autonomous AI agent platform. It does not just answer questions — it plans, executes, debugs, and delivers results using real tools: browser automation, code execution, file management, web search, and presentation generation.

Through recent production hardening, Archimedes features robust quality gates, context isolation, and a multi-dimensional swarm synthesis engine to prevent task degradation and ensure high-reliability outputs.

---

## Architecture
User Request
│
▼
┌─────────────────────────────────────────┐
│          AgentOrchestrator              │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │ Planner  │→│ Executor │→│ Critic  │ │
│  └──────────┘ └──────────┘ └─────────┘ │
│         MicroAgent Swarm                │
│  Coder · Critic · Tester · Researcher   │
└─────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────┐
│              Tool Layer                 │
│  Browser · Shell · File · Search        │
│  COSMO Presentation · Image Gen         │
│  Native MCP Ecosystem Integration       │
└─────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────┐
│            Memory System                │
│  GraphRAG · Memory Bank · Vector Store  │
│  Self-Improvement (learns from errors)  │
└─────────────────────────────────────────┘

---

## Key Features

### 🧠 GraphRAG Memory
Builds a knowledge graph of everything the agent learns. Not just facts — relationships. "This auth module depends on that DB service, and the user prefers JWT because we discussed it 3 weeks ago."

### 🔌 Native MCP Tooling
Deep integration with the Model Context Protocol (MCP) allows Archimedes to securely access local file systems, databases, GitHub repositories, and execution environments natively.

### 🐝 Micro-Agent Swarm
Complex tasks spawn specialized agents that debate: Coder writes, Critic audits for vulnerabilities, Tester verifies. You get the synthesized best result, not the first attempt.

### 📈 Self-Improvement
Every error is stored with its fix. Next time the same pattern appears, the agent already knows the solution. It gets better with every task.

### 🧪 TDD Executor
Before showing you code, the agent writes tests, runs them in sandbox, reads failures, fixes, and verifies. You receive tested, working code.

### ⚡ COSMO Presentation
Built-in Gamma/Kimi-level presentation generator. Say "make a pitch deck" — get a professional PPTX in minutes.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, WebSockets |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Local Models | Gemma 4 26B via Ollama |
| Cloud Models | Groq (Llama 3.3 70B), Gemini 2.5 Flash |
| Memory | ChromaDB, SQLite (GraphRAG + Memory Bank) |
| Browser | Playwright (Chromium) |
| Sandbox | Docker |
| Presentations | COSMO Engine (Presenton, Apache 2.0) |
| MCP | stdio transport, 10+ catalog servers |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/lesson4050-blip/Archimides12.git
cd Archimides12

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install COSMO engine dependencies
pip install -r cosmo_engine_core/requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env: add GROQ_API_KEY, GOOGLE_API_KEY (optional)

# 5. Start Ollama with Gemma 4
ollama pull gemma4:26b

# 6. Run
python backend/run.py

# 7. Open
# http://localhost:3000
```

---

## Environment Variables

```env
# Required
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:26b
JWT_SECRET_KEY=your-secret-key-here

# Optional (enable cloud models)
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=AIza...
TAVILY_API_KEY=tvly-...
PEXELS_API_KEY=...        # For presentation images

# Optional (connectors)
GITHUB_TOKEN=ghp_...
SLACK_BOT_TOKEN=xoxb-...
NOTION_TOKEN=secret_...
```

---

## Connectors

Connect 10+ services so the agent can use them autonomously:

| Category | Services |
|----------|---------|
| Dev | GitHub, Vercel, Supabase |
| Communication | Gmail, Slack, Telegram |
| Productivity | Notion, Airtable, Google Drive |
| Finance | Stripe |
| AI | OpenAI, Groq, Gemini, ElevenLabs |

Access via **Settings → Connectors** in the UI.

---

## License

MIT License — free for personal and commercial use.

Presentation engine (COSMO) based on [Presenton](https://github.com/presenton/presenton) — Apache 2.0.

---

*Built with obsession. Beats the funded ones.*

---
