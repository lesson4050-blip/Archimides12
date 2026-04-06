# Archimedes Diagnostic Report
_Generated: 2026-04-04 14:27:20_

## Overall Summary

| Suite | Status |
|-------|--------|
| Configuration | ⚠️ WARN |
| Model Availability | ✅ PASS |
| Tool Audit | ⚠️ WARN |
| WebSocket | ✅ PASS |
| Agent Loop | ✅ PASS |
| Memory System | ⚠️ WARN |

**Total: 6 suites | ✅ 3 passed | ⚠️ 3 warnings | ❌ 0 failed**

---

## Detailed Results


## Suite 1 — Configuration
_Started at 14:25:30_

- ✅ **GROQ_API_KEY**: PASS — set (gsk_BP...)
- ✅ **GOOGLE_API_KEY**: PASS — set (AIzaSy...)
- ✅ **OLLAMA_BASE_URL**: PASS — set (http:/...)
- ✅ **TAVILY_API_KEY**: PASS — set (tvly-d...)
- ⚠️ **AGENT_MAX_CONTEXT_TOKENS**: WARN — value is 65536 — too high for local model, recommend 8192
- ✅ **AGENT_MAX_ITERATIONS**: PASS — 20

## Suite 2 — Model Availability
_Started at 14:25:30_

- ✅ **Groq API**: PASS — responded: 'OK' | model: llama-3.3-70b-versatile
- ✅ **Gemini API**: PASS — responded: 'OK' | model: gemini-2.5-flash
- ✅ **Ollama (local)**: PASS — responded: 'OK' | model: gemma4:26b

## Suite 3 — Tool Audit (real vs stub)
_Started at 14:26:23_

- ✅ **tool:shell**: PASS — looks real
- ✅ **tool:file**: PASS — looks real
- ✅ **tool:browser**: PASS — looks real
- ✅ **tool:search**: PASS — looks real
- ✅ **tool:expose**: PASS — looks real
- ✅ **tool:webdev**: PASS — looks real
- 🔶 **tool:slides**: STUB — contains stub signature: 'placeholder'
- 🔶 **tool:schedule**: STUB — contains stub signature: 'placeholder'
- ✅ **tool:video**: PASS — looks real
- ✅ **tool:audio**: PASS — looks real
- ✅ **tool:sheets**: PASS — looks real
- ✅ **tool:pdf**: PASS — looks real
- ✅ **tool:image_gen**: PASS — looks real
- ✅ **tool:github**: PASS — looks real
- ✅ **tool:email**: PASS — looks real

## Suite 4 — WebSocket Connection
_Started at 14:26:24_

- ✅ **WebSocket connect**: PASS — connected to ws://localhost:8001/ws/tester_session_ws
- ✅ **WebSocket response**: PASS — received: {"type":"session_ready","message":"Sandbox container is ready."}

## Suite 5 — Agent Loop (end-to-end)
_Started at 14:26:29_

  ⏳ Preparing sandbox session tester_session_001...
  📋 Task: Create a file at /home/ubuntu/workspace/tester_check.txt with content: 'Archimedes tester OK'

  🔧 tool_call: file | params: {'action': 'write', 'path': '/home/ubuntu/workspace/tester_c
  ✅ tool_result: file | output: 
  🔧 tool_call: message | params: {'action': 'result', 'content': 'File created successfully a
  ✅ tool_result: message | output: 
- ✅ **Agent made tool calls**: PASS — 2 tool calls made
- ✅ **Tool execution errors**: PASS — no errors
- ℹ️ **Total agent messages**: INFO — 5

## Suite 6 — Memory System
_Started at 14:27:19_

- ⚠️ **ContextManager.max_tokens**: WARN — still 65536 — apply Fix 1 from archimedes_fix_prompt.md
- ✅ **ContextManager add/get**: PASS — 2 messages stored and retrieved
- ✅ **VectorStore.embedding_model**: PASS — gemini-embedding-exp-03-07
- ⚠️ **VectorStore add/retrieve**: WARN — added but retrieved nothing — check embedding API