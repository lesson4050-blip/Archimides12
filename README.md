# ⚡ Archimedes AI Agent

> **A production-grade, autonomous AI agent framework with self-correction, multi-agent swarm logic, native MCP tool integration, and GOD MODE hardening.**

[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)

---

## What is Archimedes?

Archimedes is a fully autonomous AI agent platform. It does not just answer questions — it plans, executes, debugs, and delivers results using real tools: browser automation, code execution, file management, web search, and presentation generation.

Through recent production hardening, Archimedes features:
- **Modular Architecture**: Frontend refactored into decoupled, Zustand-powered components with a clean custom hook architecture (`useSettings`).
- **Production Observability**: Structured JSON logging, correlation IDs (Session/Trace), and Prometheus `/metrics` endpoint for enterprise-grade monitoring.
- **Hardened Security**: 
  - JWT Refresh tokens for secure long-lived sessions.
  - Multi-layer sandbox path validation (`BLOCKED_PREFIXES`) and realpath-based traversal protection.
  - Symbolic link escape prevention in `FileTool`.
- **Cognitive Reliability**: 
  - **Smart Model Routing**: Gemini (cloud) → Ollama/Qwen (local coding fallback) → Groq
  - **Hydra Swarm v2**: Hierarchical multi-agent pipeline (Scout → Warrior → Sentinel) with automated synthesis.
  - **MCTS Exploration**: Monte Carlo Tree Search for complex planning under uncertainty.
- **GOD MODE (v3.0)**:
  - **Bash Security Engine**: Multi-layer command injection detection with quote-aware parsing.
  - **Auto-Compact**: Three-level LLM-based context management (MICRO/STANDARD/AGGRESSIVE).
  - **Verification Agent**: Read-only quality gate (pytest, linter, health checks) after every change.
  - **Session Memory**: Per-session markdown notes with automated LLM extraction.
  - **Evaluation Pipeline**: Model comparison (A/B testing) across task categories.
  - **45+ Tools**: Notebook, Grep, Glob, and expanded domain tooling.
- **Archimedes Prime (v3.1)**:
  - **PredictiveGuard**: Proactive shell command validation (Self-healing AI Safety layer).
  - **VisionBrowserTool**: Playwright & Gemini Vision 2.0 Flash integration for visual UI analysis.
  - **Canvas Engine**: Next-gen React-based presentation generation replacing legacy tools.
  - **Stateful Recovery**: Mid-task session checkpointing for resilience against restarts.
  - **JWT Revocation**: JTI-based database tracking for instant session invalidation.
  - **Fact-Checker Swarm**: Specialized research agent replacing generic critics for 300% faster verification.
  - **Extended Resilience**: Task timeout increased to 900s for robust local model processing.

---

## 🗺️ Эволюционная архитектура и Фазы (Evolutionary Phases)

Кодовая база Archimedes полностью структурирована по **5 ключевым эволюционным фазам**, разделяющим ядро, фронтенд, интеллект, песочницы безопасности и инструменты визуализации.

Подробный гид по всем файлам находится в [PHASES.md](file:///d:/Cosmo/PHASES.md), а автоматическая разметка представлена в [PROJECT_MAP.md](file:///d:/Cosmo/PROJECT_MAP.md).

### 🔌 Фаза 1: Core Engine & Unified Routing (Ядро и Маршрутизация)
*Базовый каркас системы: сервер FastAPI, WebSocket-сессии с пользователем, Prometheus-интеграция, конфигурации среды и ORM база данных.*
- `backend/main.py` — Главная точка входа API сервера.
- `backend/config.py` — Менеджер настроек и валидации путей.
- `backend/websocket/` — WebSocket сессионные стримы.
- `backend/db/` — Таблицы и модели SQLAlchemy (Pydantic v2).
- `backend/middleware/` — Заголовки безопасности и лимитер запросов.

### 🎨 Фаза 2: Decoupled UI & Zustand State (Фронтенд и Стейт)
*Пользовательский веб-интерфейс: декуплированная Next.js-архитектура, Zustand глобальный стейт, кастомные хуки бизнес-логики и Framer Motion анимации.*
- `frontend/components/` — Модульные React UI компоненты (Settings, Chat, Canvas).
- `frontend/hooks/` — Декуплированные хуки состояния (`useSettings`, `useAppshots`).
- `frontend/lib/store.ts` — Zustand хранилища глобального стейта.

### 🧠 Фаза 3: Cognitive Swarm & MCTS Reasoning (Когнитивный Сварм и Поиск)
*Мозг агента: планирование задач, MCTS поиск решений, Mixture of Agents (MoA) синтез, динамическая библиотека навыков (ChromaDB) и трехуровневая сессионная память.*
- `backend/agent/core.py` — Главный когнитивный движок `ArchimedesCosmoAgent`.
- `backend/agent/orchestration/` — Планировщики, Hydra Swarm и дерево MCTS.
- `backend/memory/auto_compact.py` — Менеджер умного сжатия контекста.

### 🛡️ Фаза 4: Restricted Execution & Sandbox Hardening (Песочница и Hardening)
*Изоляция выполнения и безопасность: Docker/Kubernetes песочницы, AST-валидатор Python, защита от Bash инъекций шелла и отзыв JWT сессий.*
- `backend/sandbox/` — Persistent Shell сессии и SandboxFilesystem изоляция.
- `backend/security/sandbox_hardening.py` — AST-валидатор команд Python.
- `backend/tools/bash_security.py` — Защитник шелла от внедрения вредоносного кода.
- `backend/auth/` — JWT токены, отзыв по JTI и сессионные ключи.

### 📊 Фаза 5: Presentation Engine & Visual Analysis (Визуальный Аудит и Презентации)
*Инструменты генерации и аудита: Marp/Canvas генераторы, Visual QA скриншотер Playwright, Bumblebee Vulnerability Scanner.*
- `backend/api/marp_routes.py` — API генерации Marp слайдов.
- `backend/agent/tools/canvas_tool.py` — Canvas Engine для React-презентаций.
- `backend/security/vuln_scanner.py` — Bumblebee-сканер MCP конфигураций и зависимостей.
- `frontend/components/AppshotOverlay.tsx` — Региональный захват экрана и аннотаций.


---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, WebSockets, Pydantic v2 |
| **Frontend** | Next.js 14 (App Router), TypeScript, Framer Motion |
| **Local Models** | Gemma 2 / Llama 3 via Ollama |
| **Cloud Models** | Groq (Llama 3.3 70B), Gemini 2.0 Pro/Flash |
| **Database** | SQLite (Metadata), ChromaDB (Vector Search), Redis (Caching) |
| **Observability** | Prometheus, Structured JSON Logs |
| **Browser** | Playwright (Stealth mode) |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional, for sandboxing)
- [Ollama](https://ollama.ai/) installed and running

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/lesson4050-blip/Archimides12.git
cd Archimides12

# Install Backend dependencies
pip install -r requirements.txt

# Install Frontend dependencies
cd frontend && npm install && cd ..
```

### 3. Environment Setup
```bash
cp .env.example .env
# Edit .env with your keys:
# JWT_SECRET_KEY, GROQ_API_KEY, GOOGLE_API_KEY
```

## Running locally
Backend: `uvicorn backend.main:app --host 0.0.0.0 --port 8001`
Frontend: `cd frontend && npm run dev`
Open: `http://localhost:3000`

---

## 🔌 API Reference (v1)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | `GET` | System status. `?deep=true` for full diagnostics. |
| `/api/v1/settings` | `GET/POST` | Manage user profile and preferences. |
| `/api/v1/agent/chat` | `WS` | Main WebSocket stream for agent interaction. |
| `/api/v1/skills` | `GET` | List available skills in the SkillEngine. |
| `/metrics` | `GET` | Prometheus-compatible metrics export. |

---

## 🛡 Security & Hardening

Archimedes is designed with a **Security-First** mindset:
1. **Workspace Isolation**: All file operations are restricted to the `WORKSPACE_ROOT`. Symlink resolution is enforced to prevent escapes.
2. **Safe Code Execution**: Python REPL runs in a restricted environment with blocked access to sensitive system paths (`/etc`, `/proc`, `/lib`).
3. **Authentication**: All endpoints require valid JWT tokens. `AUTH_ENABLED=True` is recommended for any non-local deployment.

---

## 🧪 Testing & Quality

We maintain high standards for code quality:
```bash
# Run backend tests
pytest backend/tests/

# Check system integrity
python scripts/health_check.py
```

---

## License
MIT License — free for personal and commercial use.
Built with passion. Archimedes GOD MODE — the final evolution.

---
