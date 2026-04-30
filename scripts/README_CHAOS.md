# 🌀 Archimedes Failover Chaos Test

## Overview
This tool is designed to verify the **production resilience** of the Archimedes 12 platform. It simulates a mid-execution infrastructure failure by pausing the local Ollama container while the agent is processing a task.

The goal is to prove that the `ModelRouter` correctly detects the failure, applies the failover logic, and switches to cloud providers (Gemini/Groq) without interrupting the user session or losing data.

## Prerequisites
- Python 3.10+
- `websockets` and `httpx` installed (see `requirements.txt`)
- Docker running with the `archimedes-ollama` container active.

## Usage

### Basic Run
Runs a single chaos cycle against the local backend.
```bash
python scripts/chaos_engineer.py
```

### Dry Run
Simulates the timing and communication without actually pausing the Docker container.
```bash
python scripts/chaos_engineer.py --dry-run
```

### Stress Test (Multiple Cycles)
Runs 3 consecutive cycles to ensure consistent failover behavior.
```bash
python scripts/chaos_engineer.py --repeat 3
```

### Custom Container Name
If your Ollama container is named differently:
```bash
python scripts/chaos_engineer.py --container my-ollama-container
```

## How to Interpret Results

### ✅ PASS Criteria
- The agent receives at least one event (token, info, etc.) **after** the chaos injection.
- The task completes with a `message_result` OR a visible failover mention (e.g., "Gemini" or "Cloud").
- No `AllModelsExhausted` errors occur.

### ❌ FAIL Criteria
- **Agent Freeze**: Zero events arrive after Ollama is paused.
- **Critical Error**: The agent returns an `agent_error` stating it cannot reach any models.
- **WebSocket Drop**: The connection closes abruptly and doesn't recover.

## ⚠️ Warning
**DO NOT RUN THIS IN PRODUCTION.** This script intentionally pauses a core service. It is intended for CI/CD pipelines and development environments only.
