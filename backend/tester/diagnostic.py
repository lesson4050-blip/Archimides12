"""
Archimedes Diagnostic System
Runs all test suites and produces a Markdown report.
"""

import asyncio
import websockets
import json
import os
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Fix for Windows terminal encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        pass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.config import settings

REPORT_LINES: List[str] = []
SUMMARY: Dict[str, str] = {}  # suite_name -> "PASS" | "FAIL" | "WARN"


def log(line: str = ""):
    print(line)
    REPORT_LINES.append(line)


def suite_header(name: str):
    log()
    log(f"## {name}")
    log(f"_Started at {datetime.now().strftime('%H:%M:%S')}_")
    log()


def result(label: str, status: str, detail: str = ""):
    icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "STUB": "🔶", "INFO": "ℹ️"}.get(status, "❓")
    line = f"- {icon} **{label}**: {status}"
    if detail:
        line += f" — {detail}"
    log(line)


# ─────────────────────────────────────────────
# SUITE 1: Configuration
# ─────────────────────────────────────────────
async def suite_config() -> str:
    suite_header("Suite 1 — Configuration")
    status = "PASS"

    checks = {
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "GOOGLE_API_KEY": settings.GOOGLE_API_KEY,
        "OLLAMA_BASE_URL": settings.OLLAMA_BASE_URL,
        "TAVILY_API_KEY": settings.TAVILY_API_KEY,
    }

    for key, val in checks.items():
        if not val or val.strip() == "":
            result(key, "FAIL", "not set in .env")
            status = "FAIL"
        else:
            masked = val[:6] + "..." if len(val) > 6 else "***"
            result(key, "PASS", f"set ({masked})")

    # Check context limits
    if settings.AGENT_MAX_CONTEXT_TOKENS > 32000:
        result("AGENT_MAX_CONTEXT_TOKENS", "WARN",
               f"value is {settings.AGENT_MAX_CONTEXT_TOKENS} — too high for local model, recommend 8192")
        if status == "PASS":
            status = "WARN"
    else:
        result("AGENT_MAX_CONTEXT_TOKENS", "PASS", str(settings.AGENT_MAX_CONTEXT_TOKENS))

    if settings.AGENT_MAX_ITERATIONS > 30:
        result("AGENT_MAX_ITERATIONS", "WARN",
               f"value is {settings.AGENT_MAX_ITERATIONS} — high, recommend 20")
        if status == "PASS":
            status = "WARN"
    else:
        result("AGENT_MAX_ITERATIONS", "PASS", str(settings.AGENT_MAX_ITERATIONS))

    return status


# ─────────────────────────────────────────────
# SUITE 2: Model Availability
# ─────────────────────────────────────────────
async def suite_models() -> str:
    suite_header("Suite 2 — Model Availability")
    status = "PASS"

    # Groq
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        resp = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": "Reply with one word: OK"}],
            max_tokens=5
        )
        reply = resp.choices[0].message.content.strip()
        result("Groq API", "PASS", f"responded: '{reply}' | model: {settings.GROQ_MODEL}")
    except Exception as e:
        result("Groq API", "FAIL", str(e)[:120])
        status = "FAIL"

    # Gemini
    try:
        from google import genai
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents="Reply with one word: OK"
        )
        reply = resp.text.strip()
        result("Gemini API", "PASS", f"responded: '{reply}' | model: {settings.GEMINI_MODEL}")
    except Exception as e:
        result("Gemini API", "FAIL", str(e)[:120])
        status = "FAIL"

    # Ollama
    try:
        import ollama
        client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
        resp = await client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": "Reply with one word: OK"}],
            options={"num_ctx": 512}
        )
        reply = resp.message.content.strip()[:50]
        result("Ollama (local)", "PASS", f"responded: '{reply}' | model: {settings.OLLAMA_MODEL}")
    except Exception as e:
        result("Ollama (local)", "WARN", f"not available: {str(e)[:100]} — this is OK if Groq/Gemini work")
        if status == "PASS":
            status = "WARN"

    return status


# ─────────────────────────────────────────────
# SUITE 3: Tool Audit (real vs stub)
# ─────────────────────────────────────────────
STUB_SIGNATURES = [
    "placeholder",
    "simulated",
    "not implemented",
    "todo",
    "dummy",
    "fake",
]

def is_stub(source: str) -> Tuple[bool, str]:
    source_lower = source.lower()
    for sig in STUB_SIGNATURES:
        if sig in source_lower:
            return True, sig
    return False, ""

async def suite_tools() -> str:
    suite_header("Suite 3 — Tool Audit (real vs stub)")
    import inspect
    status = "PASS"

    tools_to_check = []

    # Main tools
    try:
        from backend.sandbox.singleton import sandbox_manager
        from backend.tools.shell_tool import ShellTool
        from backend.tools.file_tool import FileTool
        from backend.tools.browser_tool import BrowserTool
        from backend.tools.search_tool import SearchTool
        from backend.tools.expose_tool import ExposeTool
        from backend.tools.webdev_tool import WebDevTool
        from backend.tools.slides_tool import SlidesTool
        from backend.tools.schedule_tool import ScheduleTool
        
        executor = sandbox_manager.executor
        filesystem = sandbox_manager.filesystem

        tools_to_check = [
            ("shell", ShellTool(executor)),
            ("file", FileTool(filesystem)),
            ("browser", BrowserTool(executor)),
            ("search", SearchTool()),
            ("expose", ExposeTool(executor)),
            ("webdev", WebDevTool(executor, filesystem)),
            ("slides", SlidesTool()),
            ("schedule", ScheduleTool()),
        ]
    except Exception as e:
        result("Tool import", "FAIL", str(e)[:150])
        return "FAIL"

    # Agent tools
    try:
        from backend.agent.tools.pdf_tool import PDFTool
        from backend.agent.tools.image_gen_tool import ImageGenTool
        from backend.agent.tools.github_tool import GithubTool
        from backend.agent.tools.email_tool import EmailTool
        # Check if utility_tools exists as expected
        try:
            from backend.agent.tools.utility_tools import VideoTool, AudioTool, SheetsTool
            tools_to_check += [
                ("video", VideoTool()),
                ("audio", AudioTool()),
                ("sheets", SheetsTool()),
            ]
        except ImportError:
            log("ℹ️ utility_tools not found, skipping video/audio/sheets check")

        tools_to_check += [
            ("pdf", PDFTool()),
            ("image_gen", ImageGenTool()),
            ("github", GithubTool()),
            ("email", EmailTool()),
        ]
    except Exception as e:
        result("Agent tool import", "WARN", str(e)[:150])

    for name, tool in tools_to_check:
        try:
            source = inspect.getsource(tool.__class__)
            stub, sig = is_stub(source)
            if stub:
                result(f"tool:{name}", "STUB", f"contains stub signature: '{sig}'")
                if status == "PASS":
                    status = "WARN"
            else:
                result(f"tool:{name}", "PASS", "looks real")
        except Exception as e:
            result(f"tool:{name}", "FAIL", f"cannot inspect: {e}")
            status = "FAIL"

    return status


# ─────────────────────────────────────────────
# SUITE 4: WebSocket Connection
# ─────────────────────────────────────────────
async def suite_websocket() -> str:
    suite_header("Suite 4 — WebSocket Connection")
    session_id = "tester_session_ws"
    ws_url = f"{settings.NEXT_PUBLIC_WS_URL}/{session_id}"

    try:
        async with websockets.connect(ws_url, open_timeout=5) as ws:
            result("WebSocket connect", "PASS", f"connected to {ws_url}")
            # Send a ping-style message
            await ws.send(json.dumps({"type": "ping"}))
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                result("WebSocket response", "PASS", f"received: {str(msg)[:80]}")
            except asyncio.TimeoutError:
                result("WebSocket response", "WARN", "no response in 5s — backend may not handle ping yet")
        return "PASS"
    except Exception as e:
        result("WebSocket connect", "FAIL", f"{str(e)[:150]}")
        log("> Make sure the backend is running: `python run.py` (port 8001)")
        return "FAIL"


# ─────────────────────────────────────────────
# SUITE 5: Agent Loop (end-to-end)
# ─────────────────────────────────────────────
async def suite_agent_loop() -> str:
    suite_header("Suite 5 — Agent Loop (end-to-end)")

    messages_received = []
    errors = []

    try:
        from backend.agent.core import AgentLoop
        from backend.sandbox.singleton import sandbox_manager

        session_id = "tester_session_001"
        
        # Ensure clean state: destroy if exists, then create
        log(f"  ⏳ Preparing sandbox session {session_id}...")
        try:
            await sandbox_manager.destroy_session(session_id)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Diagnostic check failed: {e}")
        await sandbox_manager.create_session(session_id)
        
        agent = AgentLoop(session_id=session_id)

        async def capture(msg: Dict[str, Any]):
            messages_received.append(msg)
            t = msg.get("type", "unknown")
            if t == "thought":
                log(f"  💭 thought: {msg.get('content', '')[:80]}")
            elif t == "tool_call":
                log(f"  🔧 tool_call: {msg.get('tool')} | params: {str(msg.get('params', {}))[:60]}")
            elif t == "tool_result":
                success = msg.get("success", True)
                icon = "✅" if success else "❌"
                log(f"  {icon} tool_result: {msg.get('tool')} | output: {str(msg.get('output', ''))[:60]}")
                if not success:
                    errors.append(f"tool {msg.get('tool')} failed: {msg.get('error', '')}")
            elif t == "agent_error":
                errors.append(msg.get("message", "unknown error"))
                log(f"  ❌ agent_error: {msg.get('message', '')[:100]}")

        test_task = "Create a file at /home/ubuntu/workspace/tester_check.txt with content: 'Archimedes tester OK'"

        log(f"  📋 Task: {test_task}")
        log()

        await asyncio.wait_for(
            agent.run(task=test_task, websocket_send=capture),
            timeout=120
        )

        types_seen = [m.get("type") for m in messages_received]

        if "tool_call" not in types_seen:
            result("Agent made tool calls", "FAIL", "no tool_call events received — agent may not be parsing model output")
            return "FAIL"
        else:
            result("Agent made tool calls", "PASS", f"{types_seen.count('tool_call')} tool calls made")

        if errors:
            result("Tool execution errors", "FAIL", f"{len(errors)} errors: {errors[0][:100]}")
            for e in errors[1:]:
                log(f"  - {e[:100]}")
            return "FAIL"
        else:
            result("Tool execution errors", "PASS", "no errors")

        result("Total agent messages", "INFO", str(len(messages_received)))
        return "PASS"

    except asyncio.TimeoutError:
        result("Agent loop timeout", "FAIL", "agent did not complete within 120 seconds")
        return "FAIL"
    except Exception as e:
        result("Agent loop crash", "FAIL", str(e)[:150])
        log(f"```\n{traceback.format_exc()[:500]}\n```")
        return "FAIL"


# ─────────────────────────────────────────────
# SUITE 6: Memory System
# ─────────────────────────────────────────────
async def suite_memory() -> str:
    suite_header("Suite 6 — Memory System")
    status = "PASS"

    # Context Manager
    try:
        from backend.memory.context_manager import ContextManager
        cm = ContextManager()

        if cm.max_tokens > 32000:
            result("ContextManager.max_tokens", "WARN",
                   f"still {cm.max_tokens} — apply Fix 1 from archimedes_fix_prompt.md")
            status = "WARN"
        else:
            result("ContextManager.max_tokens", "PASS", str(cm.max_tokens))

        cm.add_message("user", "test message")
        cm.add_message("assistant", "test reply")
        assert len(cm.get_messages()) == 2
        result("ContextManager add/get", "PASS", "2 messages stored and retrieved")
    except Exception as e:
        result("ContextManager", "FAIL", str(e)[:120])
        status = "FAIL"

    # Vector Store
    try:
        from backend.memory.vector_store import VectorStore
        vs = VectorStore(user_id="tester")

        if vs.embedding_model == "text-embedding-004":
            result("VectorStore.embedding_model", "WARN",
                   "using deprecated text-embedding-004 — apply Fix 5 from archimedes_fix_prompt.md")
            if status == "PASS":
                status = "WARN"
        else:
            result("VectorStore.embedding_model", "PASS", vs.embedding_model)

        # Try to add and retrieve a fact (requires Google API key)
        if settings.GOOGLE_API_KEY:
            await vs.add_fact("Tester diagnostic fact", {"source": "tester"})
            results = await vs.retrieve_similar("tester diagnostic", limit=1)
            if results:
                result("VectorStore add/retrieve", "PASS", f"retrieved: '{results[0]['document'][:50]}'")
            else:
                result("VectorStore add/retrieve", "WARN", "added but retrieved nothing — check embedding API")
                if status == "PASS":
                    status = "WARN"
        else:
            result("VectorStore add/retrieve", "WARN", "skipped — GOOGLE_API_KEY not set")

    except Exception as e:
        result("VectorStore", "FAIL", str(e)[:120])
        status = "FAIL"

    return status


# ─────────────────────────────────────────────
# REPORT WRITER
# ─────────────────────────────────────────────
def write_report():
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                               "archimedes_diagnostic_report.md")

    total = len(SUMMARY)
    passed = sum(1 for v in SUMMARY.values() if v == "PASS")
    warned = sum(1 for v in SUMMARY.values() if v == "WARN")
    failed = sum(1 for v in SUMMARY.values() if v == "FAIL")

    header = [
        "# Archimedes Diagnostic Report",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        "## Overall Summary",
        "",
        "| Suite | Status |",
        "|-------|--------|",
    ]
    for suite_name, suite_status in SUMMARY.items():
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(suite_status, "❓")
        header.append(f"| {suite_name} | {icon} {suite_status} |")

    header += [
        "",
        f"**Total: {total} suites | ✅ {passed} passed | ⚠️ {warned} warnings | ❌ {failed} failed**",
        "",
        "---",
        "",
        "## Detailed Results",
        "",
    ]

    full_report = "\n".join(header) + "\n" + "\n".join(REPORT_LINES)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(full_report)

    print()
    print(f"📄 Report saved to: {report_path}")
    return report_path


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
async def main():
    print("=" * 60)
    print("  ARCHIMEDES DIAGNOSTIC SYSTEM")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    suites = [
        ("Configuration", suite_config),
        ("Model Availability", suite_models),
        ("Tool Audit", suite_tools),
        ("WebSocket", suite_websocket),
        ("Agent Loop", suite_agent_loop),
        ("Memory System", suite_memory),
    ]

    for name, fn in suites:
        try:
            status = await fn()
        except Exception as e:
            log(f"\n❌ Suite '{name}' crashed: {e}")
            log(f"```\n{traceback.format_exc()[:400]}\n```")
            status = "FAIL"
        SUMMARY[name] = status

    write_report()

    print()
    print("=" * 60)
    for name, status in SUMMARY.items():
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(status, "❓")
        print(f"  {icon} {name}: {status}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
