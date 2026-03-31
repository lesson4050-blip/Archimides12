# ARCHEMIDAS — Master Build Prompt for Google Antigravity
## Project: Autonomous AI Agent (Manus-class), Hybrid Model Architecture

---


---

## BRANDING — APPLY EVERYWHERE IN THE UI

**Logo file:** `logo.png` — will be provided in `/frontend/public/logo.png`
- Logo is black monoline on white background
- On dark backgrounds: apply CSS `filter: invert(1)` to make it white
- Display in top-left header, size: 32px height, auto width
- Never stretch or distort the logo

**Color scheme:**
- Background: `#0a0a0a` (near black)
- Surface/cards: `#111111`
- Accent: `#f59e0b` (amber)
- Text primary: `#ffffff`
- Text secondary: `#9ca3af`
- Error: `#ef4444`
- Success: `#22c55e`

**Typography:**
- UI font: Inter (Google Fonts)
- Terminal/code font: JetBrains Mono

**Name usage:**
- Product name: **Archimedes** (with capital A)
- Never write "Archemidas AI" — just "Archimedes"
- Tagline (optional, use in empty state): *"Give me a task. I'll figure out the rest."*

**Apply branding to:**
- Browser tab title: "Archimedes"
- Favicon: use logo.png
- Header: logo + name
- Loading states: amber spinner
- Plan phase indicators: amber for active, gray for pending, green for complete
- All primary buttons: amber background, black text

---

## CONTEXT & MISSION

You are building **Archemidas** — a fully autonomous, general-purpose AI agent that mirrors the architecture of Manus AI. Archemidas can receive a high-level natural language goal from a user and autonomously plan, execute, verify, and deliver results without human intervention in each step.

This is not a chatbot. This is not a code assistant. This is a complete agentic system where the LLM is the orchestrator that calls tools, runs shell commands, browses the web, reads/writes files, and delivers structured results — all inside an isolated Ubuntu sandbox.

## MODEL STRATEGY — THREE-TIER HYBRID

Archemidas uses three models. The `model_router.py` selects automatically based on task type.

| Tier | Model | Provider | Used For |
|---|---|---|---|
| **Primary** | `llama-3.3-70b-versatile` | Groq API | Fast agent loop iterations: shell decisions, file ops, short reasoning, retries |
| **Secondary** | `gemini-2.5-flash` | Google AI Studio | Planning, browser tasks, web research, final result generation, long context |
| **Fallback** | `deepseek-r1:14b` | Ollama (local) | When both APIs return 429 or are unavailable |

**Why this split:**
- Groq Llama 3.3 70B = 700+ tokens/sec, handles 80% of loop iterations cheaply and fast
- Gemini 2.5 Flash = best quality for planning + multimodal + long documents
- DeepSeek R1 14B local = zero cost, zero rate limits, always available as safety net

**APIs needed:** Groq API key (free tier) + Google AI Studio key + Ollama running locally

---

## TECHNICAL STACK — DO NOT DEVIATE

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI + asyncio |
| Frontend | Next.js 14 (App Router) + React + TailwindCSS |
| Real-time | WebSockets (FastAPI `websockets` library) |
| Sandbox | Docker (Ubuntu 22.04 linux/amd64 container) |
| Browser automation | Playwright + Chromium (headless, inside Docker) |
| Vector Memory | ChromaDB (local, persistent) |
| Short-term memory | In-memory conversation history + sliding window summarization |
| Search | Tavily Search API |
| Embeddings | `gemini-embedding-exp-03-07` (latest Google embedding model, replaces deprecated text-embedding-004) |
| Groq client | `groq` Python SDK (async) |
| Gemini client | `google-generativeai` Python SDK |
| Ollama client | `ollama` Python SDK (local HTTP) |
| Task queue | asyncio.Queue (in-process, no Redis needed for MVP) |
| Package manager | `uv` for Python dependencies |
| State persistence | SQLite via SQLAlchemy async |
| Container orchestration | `docker-py` SDK from backend |
| Config | `.env` file + Pydantic Settings |

---

## PROJECT STRUCTURE — CREATE EXACTLY THIS

```
archemidas/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Pydantic settings, env vars
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── core.py                # Main Agent Loop (THE BRAIN)
│   │   ├── planner.py             # Task decomposition into phases
│   │   ├── tool_registry.py       # All tools registered here
│   │   ├── thought_engine.py      # Thought block generation + streaming
│   │   └── error_recovery.py     # Retry logic, fallback strategies
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── plan_tool.py           # plan: update, advance
│   │   ├── message_tool.py        # message: info, ask, result
│   │   ├── shell_tool.py          # shell: exec, view, wait, send, kill
│   │   ├── file_tool.py           # file: read, write, append, edit, view
│   │   ├── match_tool.py          # match: glob, grep
│   │   ├── search_tool.py         # search: info, news, image, research
│   │   ├── browser_tool.py        # browser: navigate, click, type, extract, screenshot
│   │   ├── schedule_tool.py       # schedule: cron, interval
│   │   └── expose_tool.py         # expose: open sandbox port to public URL
│   ├── sandbox/
│   │   ├── __init__.py
│   │   ├── manager.py             # Docker container lifecycle manager
│   │   ├── executor.py            # Shell command execution with timeout/kill
│   │   └── filesystem.py          # File ops inside container via docker exec
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── context_manager.py     # Short-term: sliding window + summarization
│   │   └── vector_store.py        # Long-term: ChromaDB embeddings + retrieval
│   ├── models/
│   │   ├── __init__.py
│   │   ├── gemini_client.py       # Gemini API wrapper with function calling
│   │   └── model_router.py        # Routes tasks to Pro vs Flash based on complexity
│   ├── websocket/
│   │   ├── __init__.py
│   │   └── handler.py             # WebSocket connection handler + event streaming
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy models: Session, Task, Message, Artifact
│   │   └── crud.py                # DB operations
│   └── skills/
│       └── README.md              # Skills directory — agent reads SKILL.md files from here
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx               # Main chat + agent interface
│   │   └── globals.css
│   ├── components/
│   │   ├── ChatInterface.tsx       # User input + message history
│   │   ├── ThoughtBlock.tsx        # Collapsible internal monologue display
│   │   ├── ToolExecution.tsx       # Live tool call display with status
│   │   ├── PlanView.tsx            # Phase-based task plan visualization
│   │   ├── SandboxViewer.tsx       # Terminal output display (read-only stream)
│   │   └── ArtifactPanel.tsx       # Files, screenshots, results display
│   ├── lib/
│   │   └── websocket.ts            # WebSocket client with reconnect logic
│   └── package.json
├── docker/
│   ├── sandbox.Dockerfile         # Ubuntu 22.04 sandbox image
│   └── docker-compose.yml         # Full stack: backend + frontend + sandbox pool
├── .env.example
└── README.md
```

---

## STEP 1 — BUILD THE SANDBOX (Start Here)

Create `docker/sandbox.Dockerfile`:

```dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3.11 python3-pip python3.11-venv \
    nodejs npm \
    git curl wget zip unzip \
    chromium-browser \
    xvfb \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install playwright dependencies
RUN pip3 install playwright && playwright install chromium

# Create ubuntu user with passwordless sudo
RUN useradd -m ubuntu && echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Working directory
WORKDIR /home/ubuntu
USER ubuntu

CMD ["/bin/bash"]
```

Build this image first. Tag it `archemidas-sandbox:latest`.

---

## STEP 2 — MODEL CLIENTS + ROUTER (Three-Tier Hybrid)

### `backend/models/groq_client.py`
- Use `groq` Python SDK (`AsyncGroq`)
- Model: `llama-3.3-70b-versatile`
- Implement `generate_with_tools(messages, tools)` async
- Tools as OpenAI-compatible JSON schema (Groq uses same format)
- Retry on 429: exponential backoff 2s → 4s → 8s, max 3 attempts
- On 3rd failure: raise `RateLimitExceeded` so router falls back to next tier

### `backend/models/gemini_client.py`
- Use `google-generativeai` SDK
- Model: `gemini-2.5-flash` for planning/reasoning
- **Browser tasks:** standard `gemini-2.5-flash`. Browser execution uses Playwright exclusively.
- Implement `generate_with_tools(messages, tools)` async
- Tools as Gemini `FunctionDeclaration` format
- Support streaming responses
- Token counting: if context > 800k tokens, summarize oldest 40% before sending
- Retry on 429/503: same backoff. On failure: raise `RateLimitExceeded`

### `backend/models/ollama_client.py`
- Use `ollama` Python SDK (`http://localhost:11434`)
- Model: `deepseek-r1:14b`
- Convert tools to prompt-injected format (tool descriptions in system prompt)
- This is the last resort: local, always available, no rate limits, no cost
- No retry logic needed

### `backend/models/model_router.py`
Implement `ModelRouter` class with this exact routing logic:

```python
class ModelRouter:
    # Tasks that require Gemini's quality (long context, planning, research)
    GEMINI_FIRST_TASKS = {"plan", "browser", "search", "result", "summarize"}

    async def generate(self, messages, tools, task_hint: str = "default"):
        if task_hint in self.GEMINI_FIRST_TASKS:
            order = [self.gemini, self.ollama]       # Gemini → Ollama
        else:
            order = [self.groq, self.gemini, self.ollama]  # Groq → Gemini → Ollama

        for client in order:
            try:
                return await client.generate_with_tools(messages, tools)
            except RateLimitExceeded:
                continue  # try next tier
        raise AllModelsExhausted("All three model tiers failed")
```

**Unified response format** — ALL three clients normalize to this before returning:
```python
{
    "model_used": "groq|gemini|ollama",
    "thought": "...",
    "tool_call": {"name": "shell", "params": {...}},  # None if text reply
    "text": "...",
    "tokens_used": 1234
}
```

The agent loop ONLY works with this unified format. Never raw API responses.

---

## STEP 3 — THE AGENT LOOP (Most Critical Component)

In `backend/agent/core.py`, implement the `AgentLoop` class:

```python
class AgentLoop:
    """
    The core execution engine of Archemidas.
    Runs the Analyze → Think → Select Tool → Execute → Observe → Iterate cycle.
    """
    
    async def run(self, task: str, session_id: str) -> None:
        # 1. ANALYZE: Load context (system prompt + history + current plan)
        # 2. THINK: Call ModelRouter.generate(). Get thought block + tool call.
        # 3. SELECT TOOL: Parse the function call from LLM response
        # 4. EXECUTE: Call the tool with its parameters
        # 5. OBSERVE: Get tool result
        # 6. STREAM: Send thought + tool call + result to frontend via WebSocket
        # 7. ITERATE: Add observation to context. Loop until task complete or ask_user.
        # 8. DELIVER: When done, call message(type="result") with attachments
```

**Agent loop rules (MUST implement all):**
- Max iterations per task: 50 (configurable via env `AGENT_MAX_ITERATIONS`)
- On any tool error: retry up to 3 times with modified parameters before asking user
- Never call the same failing shell command twice without modification
- If iteration count > 30: call Flash to summarize conversation history to save tokens
- `thought` blocks stream to frontend character by character
- Every tool call must be logged: tool name, params, result, timestamp, iteration number
- Plan must be created in iteration 1 for any task with >2 steps

---

## STEP 4 — ALL TOOLS (Implement Every One)

### `shell_tool.py`
- Connect to a running Docker container via `docker exec`
- `exec`: Run command with configurable timeout (default 30s, max 300s)
- `view`: Show current terminal session output buffer
- `wait`: Sleep N seconds
- `send`: Send stdin to a running interactive process
- `kill`: Kill a process by PID or session name
- Each shell session has a unique string ID
- **Critical:** Always capture both stdout AND stderr. Always check exit code. Non-zero exit code = error, trigger retry logic.
- Wrap all commands in `timeout <N> bash -c "..."` to prevent hangs

### `file_tool.py`
- All operations run inside Docker container via `docker cp` and `docker exec`
- `read`: Read file content with optional line range
- `write`: Write content to file (creates parent dirs if needed)
- `append`: Append to file
- `edit`: Replace specific line ranges (takes `old_string` + `new_string`, like str_replace)
- `view`: Directory listing or file preview

### `browser_tool.py`
- Use Playwright running INSIDE the sandbox container
- Launch headless Chromium with `--no-sandbox` flag
- `navigate`: Go to URL, wait for load, return page title + extracted text
- `click`: Click element by CSS selector or text
- `type`: Type text into input field
- `extract`: Extract structured data from page (returns JSON)
- `screenshot`: Take screenshot, save to sandbox `/home/ubuntu/screenshots/`, return file path
- Sessions persist across calls using session ID

### `search_tool.py`
- Use Tavily API (env: `TAVILY_API_KEY`) — it returns clean, structured results
- Types: `info`, `news`, `research` (deep), `image`
- Return top 5 results with title, URL, snippet, published date
- After getting snippets, the agent loop should use `browser` to fetch full content for top 1-2 results

### `plan_tool.py`
- `update`: Create/replace the entire plan. Plan = list of phases. Each phase has `id`, `title`, `status` (pending/active/complete), `capabilities` list
- `advance`: Mark current phase complete, move to next
- Plan state stored in SQLite per session
- Plan broadcast to frontend via WebSocket on every update

### `message_tool.py`
- `info`: Non-blocking status update to user (streams immediately via WebSocket)
- `ask`: Blocking — agent pauses loop and waits for user response. Frontend shows input field. Resumes loop when user replies.
- `result`: Final delivery. Attach file paths from sandbox. Frontend shows download links.

### `expose_tool.py`
- Use `ngrok` or `localhost.run` inside sandbox to expose a port
- Return the public URL
- Store active tunnels per session, kill on session end

### `schedule_tool.py`
- Store cron/interval jobs in SQLite
- Use `asyncio` scheduled tasks (APScheduler library)
- One active scheduled job per session (enforce this)

---

## STEP 5 — MEMORY SYSTEM

### Short-term (`context_manager.py`):
- Maintain conversation history as list of `{"role": "user"|"model", "content": ...}` dicts
- When token count > 600k: call Flash model to summarize oldest 50% of history into 1 paragraph, replace those messages with the summary
- Always keep: system prompt, last 10 messages, current plan, current tool results

### Long-term (`vector_store.py`):
- ChromaDB collection per user
- Embed and store: task completions, learned facts, code snippets, error+solution pairs
- On each new task: retrieve top 5 similar past tasks from vector store, inject into context
- Embedding model: `gemini-embedding-exp-03-07` via Google AI SDK (text-embedding-004 is shut down as of Jan 2026)

---

## STEP 6 — THE SYSTEM PROMPT

The system prompt must be injected as the first message in every Gemini call. Generate it dynamically in `thought_engine.py`. It must include:

```
You are Archemidas — an autonomous AI agent. Your purpose: receive a high-level user goal and autonomously complete it using your tools.

IDENTITY:
- You are NOT a chatbot. You take actions, not just generate text.
- You work inside an isolated Ubuntu 22.04 Docker sandbox.
- Every action you take is visible to the user in real-time.

YOUR AGENT LOOP:
1. Analyze the task and current context
2. Think (generate a thought block explaining your reasoning)
3. Select the right tool
4. Execute the tool
5. Observe the result
6. Repeat until task is complete

MANDATORY RULES:
- ALWAYS create a plan (use plan tool) before executing multi-step tasks
- ALWAYS use message(type="info") to narrate what you are doing before doing it
- NEVER repeat a failed shell command without modification
- If a command hangs, use shell(action="kill") immediately
- If you are stuck after 3 retries, use message(type="ask") to ask the user
- ALWAYS check shell exit codes. Non-zero = error, do not ignore it.
- Save all important outputs to files in /home/ubuntu/workspace/
- When task is complete, use message(type="result") with attachments

TOOL SELECTION GUIDE:
- Need to run code or commands? → shell
- Need to read/write files? → file (not shell, to avoid escaping bugs)
- Need to find files? → match with glob
- Need to find text in files? → match with grep
- Need internet information? → search, then browser for full content
- Need to fill a web form or interact with UI? → browser
- Need to expose a web server you built? → expose
- Communicating with user? ONLY through message tool. Never raw text.

THOUGHT BLOCKS:
Before every tool call, output a thought block that explains:
- What you observed from the last action
- What you plan to do next and WHY
- What you expect to happen

SANDBOX ENVIRONMENT:
- OS: Ubuntu 22.04
- User: ubuntu (has passwordless sudo)
- Home: /home/ubuntu
- Pre-installed: python3.11, pip3, nodejs, npm, git, curl, wget, chromium
- Install anything you need with: sudo apt-get install -y <package> or pip3 install <package>
- Working directory for all projects: /home/ubuntu/workspace/

AVAILABLE SKILLS:
At the start of each session, scan /home/ubuntu/skills/ for SKILL.md files. 
Read any relevant SKILL.md before attempting tasks in that domain.
Follow SKILL.md instructions exactly — they contain proven workflows.
```

---

## STEP 7 — WEBSOCKET EVENT SCHEMA

All real-time events are JSON objects with this structure. Frontend handles each type differently:

```typescript
type AgentEvent = 
  | { type: "thought"; content: string; streaming: boolean }
  | { type: "tool_call"; tool: string; params: object; iteration: number }
  | { type: "tool_result"; tool: string; output: string; exit_code?: number; success: boolean }
  | { type: "plan_update"; phases: Phase[] }
  | { type: "message_info"; text: string }
  | { type: "message_ask"; text: string; suggested_action?: string }
  | { type: "message_result"; text: string; attachments: string[] }
  | { type: "agent_error"; message: string; iteration: number; retrying: boolean }
  | { type: "session_end"; reason: "complete" | "max_iterations" | "user_cancelled" }
```

---

## STEP 8 — FRONTEND

Build a dark-theme, professional UI in Next.js. Layout:

**Left panel (30%):** Plan phases — visual progress tracker, current phase highlighted
**Center panel (50%):** Main conversation — user messages + agent `message_info/ask/result` responses
**Right panel (20%):** Thought stream — live streaming thought blocks, collapsible per iteration

**Below center panel:** Terminal output area — shows real-time shell output as monospace text, scrollable

**Bottom:** Artifacts panel — shows files, screenshots produced by agent. Click to preview.

**Input box:** At bottom of center. Disabled while agent is running (except when `message_ask` received). Shows animated indicator "Archemidas is thinking..." while agent runs.

Use TailwindCSS. Dark background `#0a0a0a`. Accent color: deep amber `#f59e0b`. Monospace font for terminal/code: JetBrains Mono.

---


---

## STEP 8B — FOUR MISSING TOOLS (Manus parity)

### Tool: `slides` — Presentation Generation

Add `backend/tools/slides_tool.py`:
- Params: `slide_content_file_path`, `slide_count`, `theme`, `generate_mode` (html or pptx)
- Agent workflow MUST be:
  1. Gather content via `search` + `browser`
  2. Write structured Markdown to `/home/ubuntu/workspace/slides_content.md`
     (sections separated by `---`, each starting with `# Slide N: Title`)
  3. Call `slides` tool
  4. Tool generates Reveal.js HTML or .pptx
  5. Call `expose` to serve it, return public URL
- HTML mode: split Markdown by `---`, wrap in Reveal.js `<section>` tags, inject into CDN template
- PPTX mode: use `python-pptx` library
- Prefer HTML mode — zero extra dependencies

---

### Tool: `webdev_init_project` — Project Scaffolding

Add `backend/tools/webdev_tool.py`:
- Params: `name`, `title`, `description`, `scaffold`
- Scaffold types:

  `web-static`: create `/home/ubuntu/workspace/{name}/` with index.html, style.css, main.js

  `web-db-user`: run inside sandbox:
    npx create-next-app@latest {name} --typescript --tailwind --app --yes
    then install prisma + next-auth, init prisma schema with basic user model

  `mobile-app`: run inside sandbox:
    npx create-expo-app {name} --template blank-typescript

- After scaffolding: `message(type="info")` with project structure
- Then `expose` to serve preview URL
- RULE: agent must ALWAYS call this before writing any web project code

---

### Feature: noVNC Sandbox Desktop Streaming

Lets the user visually watch the agent work inside Ubuntu sandbox.

**Add `backend/sandbox/novnc.py`:**

Implement class `NoVNCManager` with methods:
- `start(container_id, port=6080)`: runs these inside the container via docker exec:
  - `Xvfb :99 -screen 0 1280x720x24 &`
  - `x11vnc -display :99 -nopw -forever -quiet &`
  - `websockify --web /opt/novnc 6080 localhost:5900 &`
  - Returns `http://localhost:{port}/vnc.html`
- `stop(container_id)`: kills all three processes

**Add to `sandbox.Dockerfile`:**
```
xvfb x11vnc websockify novnc openbox
```

**Frontend `SandboxViewer.tsx`:**
- Toggle button: "Watch Agent" / "Hide Desktop"
- When active: `<iframe src={novncUrl} />`
- "Take Control" button: sends `user_takeover` event via WebSocket
- On takeover: backend sets `human_in_control = True`, pauses agent loop
- "Return to Agent" button: resumes agent loop

**New WebSocket events:**
- `{ type: "novnc_ready", url: string }`
- `{ type: "novnc_stopped" }`
- `{ type: "user_takeover", active: boolean }`

**Trigger:** start noVNC automatically when agent calls `browser` tool for the first time in session.

---

## STEP 9 — ERROR HANDLING (NON-NEGOTIABLE)

This is what makes or breaks the agent. Implement ALL of these:

1. **Shell timeout:** Every `exec` call wrapped in `asyncio.wait_for(coroutine, timeout=N)`. On timeout → kill the process → log → retry with increased timeout or different approach.

2. **Docker connection errors:** If container is unreachable → try reconnect 3 times → if still failing → create new container → restore session.

3. **Gemini API errors:**
   - 429 (rate limit): exponential backoff (2s, 4s, 8s, max 3 retries)
   - 503 (overload): same
   - Context too long: trigger summarization immediately, retry
   - Invalid function call response: ask model to retry with explicit format reminder

4. **Browser crashes:** Playwright session auto-restart if page crashes. Never let a browser crash kill the agent loop.

5. **Max iterations reached:** Send `message(type="ask")` to user: "I've taken 50 steps on this task. Here's my progress so far: [summary]. Should I continue, take a different approach, or stop?"

6. **Unhandled exceptions in tools:** Catch ALL exceptions in tool execution. NEVER let a tool crash propagate to the agent loop. Always return `{"success": false, "error": "..."}` so the LLM can decide what to do.

---

## STEP 10 — SKILLS SYSTEM

Implement the skills system exactly as in Manus:

- Skills live in `backend/skills/` (mounted into sandbox at `/home/ubuntu/skills/`)
- Each skill is a directory with `SKILL.md` and optional helper scripts
- Agent scans skills directory at session start
- When a task matches a skill domain, agent reads that SKILL.md and follows its instructions
- Create 3 starter skills:
  - `web-research/SKILL.md` — instructions for deep web research tasks
  - `code-project/SKILL.md` — instructions for software development tasks
  - `data-analysis/SKILL.md` — instructions for CSV/data analysis tasks

---


---

## STEP 11 — UI/UX: REPLICATE MANUS INTERFACE EXACTLY

The interface has two main zones side by side. Study this carefully.

---

### OVERALL LAYOUT

```
┌─────────────────────────────────────────────────────────────────┐
│  [logo] Archimedes                              [New Task]  [⚙] │  ← Header (48px)
├───────────────────────┬─────────────────────────────────────────┤
│                       │                                         │
│   LEFT PANEL (35%)    │       RIGHT PANEL (65%)                 │
│                       │                                         │
│   Chat + Input        │   "Archimedes's Computer"               │
│                       │   (Agent workspace view)                │
│                       │                                         │
└───────────────────────┴─────────────────────────────────────────┘
```

---

### LEFT PANEL — Chat Interface

This is where the user talks to Archimedes.

**Empty state (no task yet):**
- Center the logo (large, 80px)
- Below logo: text "What can I help you with?"
- Below that: large textarea input, placeholder "Give me a task..."
- Below input: 3-4 example task chips the user can click:
  - "Research top Python frameworks"
  - "Build a landing page"
  - "Analyze this CSV file"
  - "Create a presentation about..."

**Active state (task running):**
- Top: scrollable message history
- Messages from user: right-aligned, amber background `#f59e0b`, black text
- Messages from Archimedes (`message_info`): left-aligned, surface card `#111111`, white text, small "ℹ" icon
- Messages asking user (`message_ask`): left-aligned, amber border, with action buttons below the text
- Final result (`message_result`): left-aligned, green border `#22c55e`, paperclip icon, downloadable file attachments listed below
- Bottom: input area — disabled with animated dots "Archimedes is working..." while agent runs. Active when `message_ask` received or task complete.
- Typing indicator when agent is mid-thought: three pulsing amber dots

---

### RIGHT PANEL — "Archimedes's Computer"

This is the signature feature. It's a tabbed panel showing everything the agent does in real-time.

**Tab bar at top of right panel (4 tabs):**
```
[📋 Plan]  [🧠 Thoughts]  [⚡ Actions]  [🖥 Desktop]
```

**Tab 1 — Plan:**
- Shows the task broken into phases
- Each phase is a card with: phase number, title, status badge
- Status badges: `Pending` (gray), `Active` (amber, pulsing dot), `Done` (green checkmark)
- Currently active phase is highlighted with amber left border
- Phases animate in one by one as agent creates the plan
- Example:
  ```
  ✅ Phase 1: Research frameworks
  🔄 Phase 2: Compare features        ← amber, pulsing
  ⏳ Phase 3: Write report
  ⏳ Phase 4: Format and deliver
  ```

**Tab 2 — Thoughts:**
- Shows agent's internal monologue streaming in real-time character by character
- Monospace font, slightly dimmed text `#9ca3af`
- Each thought block separated by thin divider line
- Iteration number shown: `[Iteration 7]`
- Scrolls automatically to bottom
- Example:
  ```
  [Iteration 3]
  I have the search results. FastAPI appears most popular
  for async workloads. I should now open the top 3 links
  to get deeper comparison data before writing the report...
  ```

**Tab 3 — Actions:**
- Shows every tool call in real-time as a card
- Card structure:
  ```
  ┌─────────────────────────────────┐
  │ 🔧 shell  [iter 4]    ✅ Done  │
  │ exec: pip install requests      │
  │ ─────────────────────────────── │
  │ > Successfully installed        │
  │   requests-2.31.0               │
  └─────────────────────────────────┘
  ```
- Tool icons: 🔧 shell, 📄 file, 🌐 browser, 🔍 search, 📋 plan, 💬 message
- Status: spinning amber circle while running → ✅ green when done → ❌ red if error
- Error cards show red border and the error text
- Output is monospace, max 8 lines shown, "Show more" toggle for longer output
- Cards stack newest at bottom, auto-scroll

**Tab 4 — Desktop:**
- Shows the noVNC stream of the Ubuntu sandbox
- Default: shows a message "Desktop view activates when agent opens a browser"
- When active: full `<iframe>` with the noVNC stream
- Bottom bar inside this tab:
  - Left: resolution indicator "1280×720"
  - Right: button "Take Control" (amber) / "Return to Agent" (gray when active)
- When user takes control: agent loop pauses, yellow banner appears at top of left panel: "You have control. Click 'Return to Agent' when done."

---

### ARTIFACTS PANEL

Below the right panel tabs — a collapsible drawer:

```
▼ Files & Outputs (3)
┌──────────────────────────────────────────────┐
│ 📄 comparison_report.md    [Preview] [⬇ Download] │
│ 🌐 presentation.html       [Open]    [⬇ Download] │
│ 📊 data_analysis.csv       [Preview] [⬇ Download] │
└──────────────────────────────────────────────┘
```

- Preview opens a modal/drawer with file content
- Images render inline as `<img>`
- Markdown renders as formatted HTML (use `react-markdown`)
- Code files render with syntax highlighting (use `highlight.js`)
- HTML files get an "Open in new tab" option

---

### HEADER

```
┌─────────────────────────────────────────────────────────┐
│  [logo 32px] Archimedes        [+ New Task]  [History] [⚙] │
└─────────────────────────────────────────────────────────┘
```

- Logo: white (CSS `filter: invert(1)`) on dark background
- "New Task" button: amber background, black text, rounded
- "History" button: shows past sessions in a left sidebar drawer
- Settings icon: opens modal with API key status indicators (green dot = connected, red = missing)

---

### LOADING & TRANSITION STATES

- **Page load:** Logo fades in, then tagline: *"Give me a task. I'll figure out the rest."*
- **Task start:** Left panel slides up, right panel fades in with Plan tab active
- **Agent thinking:** Amber pulsing dot next to "Archimedes is thinking..." in header
- **Task complete:** Green checkmark animation in header, result message appears with subtle glow
- **Error:** Red banner at top of right panel with error message and "Retry" button

---

### RESPONSIVE / MOBILE

On screens < 768px:
- Stack panels vertically: chat on top, computer view below
- Tab bar becomes horizontally scrollable
- Desktop tab hidden on mobile (noVNC not practical on phone)

---

### COMPONENT FILES TO CREATE

```
frontend/components/
├── Header.tsx
├── ChatPanel.tsx
│   ├── MessageList.tsx
│   ├── MessageBubble.tsx
│   ├── TaskInput.tsx
│   └── EmptyState.tsx
├── ComputerPanel.tsx
│   ├── PlanTab.tsx
│   ├── ThoughtsTab.tsx
│   ├── ActionsTab.tsx
│   │   └── ToolCallCard.tsx
│   └── DesktopTab.tsx
│       └── NoVNCViewer.tsx
└── ArtifactsDrawer.tsx
    └── FilePreviewModal.tsx
```

---

### ANIMATIONS (use Framer Motion)

- Plan phase cards: slide in from right with stagger (0.1s delay between each)
- Tool call cards: fade + slide up from bottom
- Thought text: typewriter effect (already streaming from WebSocket)
- Status badge transitions: smooth color change
- Artifacts drawer: smooth expand/collapse
- Message bubbles: fade in from bottom

Install: `npm install framer-motion react-markdown highlight.js`

---

## IMPLEMENTATION ORDER (Follow Exactly)

1. **docker/sandbox.Dockerfile** — build and test container starts
2. **backend/config.py** + **.env.example** — all env vars defined
3. **backend/models/gemini_client.py** — test Gemini function calling works
4. **backend/sandbox/manager.py + executor.py** — test shell commands run in container
5. **backend/tools/shell_tool.py + file_tool.py** — test file operations in sandbox
6. **backend/agent/core.py** — minimal agent loop, test with simple task
7. **backend/tools/** — all remaining tools
8. **backend/memory/** — context manager + vector store
9. **backend/websocket/handler.py** — real-time streaming
10. **backend/main.py** — FastAPI app wiring everything together
11. **frontend/** — UI components, wire to WebSocket
12. **docker/docker-compose.yml** — full stack

---

## ENVIRONMENT VARIABLES (.env.example)

```env
# === PRIMARY: Groq (fast iterations) ===
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# === SECONDARY: Google AI Studio (planning, browser, final results) ===
GOOGLE_API_KEY=your_google_ai_studio_key_here
GEMINI_MODEL=gemini-2.5-flash

# === FALLBACK: Ollama local (always available) ===
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:14b

# Search
TAVILY_API_KEY=your_key_here

# Sandbox
SANDBOX_IMAGE=archemidas-sandbox:latest
SANDBOX_MAX_CONTAINERS=5
SANDBOX_SHELL_TIMEOUT=60
SANDBOX_SHELL_MAX_TIMEOUT=300

# Agent
AGENT_MAX_ITERATIONS=50
AGENT_MAX_CONTEXT_TOKENS=800000

# DB
DATABASE_URL=sqlite+aiosqlite:///./archemidas.db

# Frontend
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## COMMON PITFALLS — AVOID ALL OF THESE

1. **Do NOT use `subprocess` directly** to run sandbox commands. Use `docker-py` SDK exclusively.
2. **Do NOT block the event loop.** All I/O must be `async`. Use `asyncio.run_in_executor` for any blocking calls.
3. **Do NOT store API keys in code.** Config only via env vars through Pydantic Settings.
4. **Do NOT parse tool results with regex.** Parse as JSON/dict. Use `.get()` with defaults.
5. **Do NOT assume Docker exec commands finish immediately.** Always use timeouts.
6. **Do NOT stream raw Gemini SDK objects to frontend.** Serialize to JSON events first.
7. **Do NOT create a new Docker container per tool call.** One container per session, reused.
8. **Do NOT hardcode model names.** Use config vars everywhere.

---

## DEFINITION OF DONE

Archemidas is complete when:
- [ ] User types "research the top 5 Python web frameworks and create a comparison report" and agent autonomously: creates plan, searches web, browses pages, writes a markdown report, delivers it as a file attachment
- [ ] User types "build a simple FastAPI hello world app and run it on port 8080" and agent: writes code, runs it in sandbox, exposes the port, returns public URL
- [ ] User types "read the file I uploaded and summarize it" and agent handles it correctly
- [ ] Shell timeout does NOT crash the agent — it retries or asks user
- [ ] Docker container restart does NOT lose the session

---

*Build Archemidas. Start with Step 1.*
