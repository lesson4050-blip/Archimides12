# Archimedes Agent Benchmark Report

## Overview
- **Objective**: Systematic performance testing of Archimedes AI Agent across 10 tasks.
- **Environment**: Windows Host, Ubuntu Sandbox (Docker), Ollama (`gemma4:26b`).
- **Date**: 2026-04-04

## Task Results

| # | Task Category | Outcome | Notes |
|---|---------------|---------|-------|
| 1 | File Tool | ✅ SUCCESS | Basic file operations (writing/reading) performed correctly. |
| 2 | Shell Tool | ✅ SUCCESS | Fixed critical shell quoting bug in `executor.py`. |
| 3 | Search + File | ✅ SUCCESS | Internet search successful; markdown report generated. |
| 4 | Code Generation | ✅ SUCCESS | Fibonacci script generated and executed correctly. |
| 5 | HTML/CSS Calculator| ⚠️ PARTIAL | Logic confirmed, but hit model response truncation (fixed with `num_predict`). |
| 6 | Browser | ⚠️ FAILED | Playwright environment issues on Windows host sandbox. |
| 7 | Multi-step FastAPI | ⏳ PENDING | Environment stable; task requires solo execution. |
| 8 | Data Analysis | ⏳ PENDING | Depends on stable sequential execution. |
| 9 | Notes App | ⏳ PENDING | High complexity task for current VRAM constraints. |
| 10| Final Report | ⏳ PENDING | To be compiled after final task cycles. |

## Critical Fixes and Improvements

### 1. Shell Quoting Bug (`backend/sandbox/executor.py`)
- **Issue**: Commands were wrapped in `bash -c "..."`, leading to quoting errors when the command itself contained quotes.
- **Fix**: Refactored `exec_run` to use a list-based command representation: `["bash", "-c", command]`.
- **Status**: ✅ RESOLVED.

### 2. Ollama Tool Parsing (`backend/models/ollama_client.py`)
- **Issue**: Local model responses often contained trailing text or markdown that broke strict JSON parsing.
- **Fix**: Implemented robust JSON extraction and increased `num_predict` to 4096 to prevent Response Truncation.
- **Status**: ✅ RESOLVED.

### 3. Context Optimization (`backend/config.py`)
- **Issue**: Default 64k context caused extreme latency and OOM on 4GB VRAM hardware.
- **Fix**: Reduced `AGENT_MAX_CONTEXT_TOKENS` to 16,384 for stability.
- **Status**: ✅ RESOLVED.

## Recommendations
- **Hardware**: For gemma4:26b, at least 16GB-24GB VRAM is recommended. 4GB VRAM forces CPU inference, making multi-step tasks very slow.
- **Tools**: `BrowserTool` requires specific Playwright dependencies in the Docker image that might not be fully configured for the current Windows-WSL bridge.
