"""Benchmark API — trigger self-evaluation from frontend or CLI."""
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.post("/run")
async def run_benchmark(agent_session_id: str = "default") -> Dict[str, Any]:
    """
    Run quick internal benchmark on the agent.
    Returns scores across code generation, debugging, research, file ops.
    """
    try:
        from backend.websocket.handler import manager as ws_manager
        agent = ws_manager.agent_loops.get(agent_session_id)
        
        if not agent:
            return {"success": False, "error": "No active agent session"}
        
        from backend.benchmarks.runner import BenchmarkRunner
        runner = BenchmarkRunner(agent)
        results = await runner.run_quick_benchmark()
        
        return {"success": True, **results}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Return current agent performance metrics."""
    from backend.utils.metrics import metrics
    return {"success": True, "metrics": metrics.get_summary()}


@router.get("/history")
async def get_benchmark_history() -> Dict[str, Any]:
    """Return stored benchmark results."""
    try:
        import json, os
        history_path = "/tmp/archimedes_benchmark_history.json"
        if os.path.exists(history_path):
            with open(history_path) as f:
                history = json.load(f)
            return {"success": True, "history": history}
        return {"success": True, "history": []}
    except Exception as e:
        return {"success": False, "error": str(e)}
