import asyncio
import json
import logging
import os
import random
import subprocess
import time
import uuid
import argparse
from typing import List, Dict, Any, Optional
import httpx
import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("chaos-engineer")

# Configuration from environment
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
WS_URL = BACKEND_URL.replace("http://", "ws://") + "/ws"
OLLAMA_CONTAINER = os.environ.get("OLLAMA_CONTAINER_NAME", "archimedes-ollama")

class ChaosResult:
    def __init__(self):
        self.chaos_time = 0
        self.events_after_chaos = 0
        self.task_completed = False
        self.failover_detected = False
        self.errors = 0
        self.pass_score = False

async def check_health():
    """Initial health check of the system."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            health = await client.get(f"{BACKEND_URL}/api/health")
            models = await client.get(f"{BACKEND_URL}/api/health/models")
            
            if health.status_code != 200:
                raise Exception(f"Backend unhealthy: {health.status_code}")
            
            model_data = models.json()
            if model_data.get("ollama") != "healthy":
                logger.warning(f"Ollama is not healthy before test: {model_data.get('ollama')}")
                # We continue anyway to see if it heals
            
            return True
        except Exception as e:
            logger.error(f"Pre-chaos health check failed: {e}")
            return False

async def run_chaos_cycle(cycle_id: int, dry_run: bool = False) -> ChaosResult:
    result = ChaosResult()
    session_id = f"chaos-test-{cycle_id}-{uuid.uuid4().hex[:8]}"
    full_ws_url = f"{WS_URL}/{session_id}"
    
    logger.info(f"--- Starting Chaos Cycle #{cycle_id} | Session: {session_id} ---")
    
    if not await check_health():
        logger.error("Skipping cycle due to backend unreachability.")
        return result

    logger.info("✅ Pre-chaos health check passed")

    try:
        async with websockets.connect(full_ws_url) as ws:
            # 1. Send Task
            task_msg = {
                "task": "Write a Python function that calculates fibonacci(30) and explain it",
                "agent": "archimedes-cosmo",
                "mode": "fast"
            }
            await ws.send(json.dumps(task_msg))
            logger.info("✅ Task accepted, agent working...")

            start_time = time.time()
            chaos_injected = False
            
            # 2. Event loop
            while True:
                try:
                    # Wait for message with timeout to allow chaos injection logic
                    msg_text = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    event = json.loads(msg_text)
                    
                    if chaos_injected:
                        result.events_after_chaos += 1
                        # Detect Failover
                        content = str(event.get("text", "") or event.get("content", "")).lower()
                        if any(x in content for x in ["gemini", "groq", "anthropic", "cloud", "failover"]):
                            if not result.failover_detected:
                                logger.info("🎯 FAILOVER DETECTED in agent output!")
                                result.failover_detected = True
                        
                        if event.get("type") == "message_result":
                            result.task_completed = True
                            logger.info("🏁 Task completed after chaos!")
                            break
                            
                        if event.get("type") == "agent_error":
                            result.errors += 1
                            logger.error(f"❌ Agent Error: {event.get('error')}")
                            if "AllModelsExhausted" in str(event.get("error")):
                                break

                    # Check if it's time for chaos
                    elapsed = time.time() - start_time
                    if not chaos_injected and elapsed > random.uniform(2, 5):
                        logger.info(f"💥 INJECTING CHAOS: Pausing {OLLAMA_CONTAINER} at T+{elapsed:.2f}s")
                        if not dry_run:
                            try:
                                subprocess.run(["docker", "pause", OLLAMA_CONTAINER], check=True, capture_output=True)
                            except Exception as e:
                                logger.error(f"Failed to pause docker: {e}. Is Docker running? Are you using the right container name?")
                                return result
                        else:
                            logger.info("(Dry-run: skipping actual docker pause)")
                            
                        chaos_injected = True
                        result.chaos_time = elapsed

                    # Check for total timeout
                    if elapsed > 60: # Extended total limit for failover overhead
                        logger.warning("Cycle timeout reached.")
                        break

                except asyncio.TimeoutError:
                    # No message received in 1s, check if we should inject chaos if not done yet
                    elapsed = time.time() - start_time
                    if not chaos_injected and elapsed > 5:
                         # Force chaos if no events arrived yet (unlikely but possible)
                         chaos_injected = True
                         logger.info("💥 CHAOS (Forced): No events yet, but pausing Ollama...")
                         if not dry_run:
                             subprocess.run(["docker", "pause", OLLAMA_CONTAINER], capture_output=True)
                    
                    if elapsed > 60:
                        break
                    continue

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # 3. Restore
        if not dry_run:
            logger.info("♻️  Restoring Ollama...")
            subprocess.run(["docker", "unpause", OLLAMA_CONTAINER], capture_output=True)
        
    # Verdict Logic
    if result.events_after_chaos > 0 and result.errors == 0:
        result.pass_score = True

    return result

def print_report(results: List[ChaosResult]):
    if not results:
        return
    
    total = len(results)
    passed = sum(1 for r in results if r.pass_score)
    
    print("\n" + "═"*44)
    print("║     CHAOS ENGINEERING REPORT         ║")
    print("╠" + "═"*42 + "╣")
    
    for i, r in enumerate(results):
        print(f"║ CYCLE {i+1}: {'PASS' if r.pass_score else 'FAIL'} {'(Dry Run)' if r.chaos_time == 0 else ''}")
        print(f"║  Chaos at:     T+{r.chaos_time:.2f}s")
        print(f"║  Events after: {r.events_after_chaos}")
        print(f"║  Completed:    {'YES' if r.task_completed else 'NO'}")
        print(f"║  Failover:     {'YES' if r.failover_detected else 'NO'}")
        print(f"║  Errors:       {r.errors}")
        print("╠" + "─"*42 + "╣")
        
    print(f"║ FINAL SCORE:   {passed}/{total} ({ (passed/total)*100:.1f}%)")
    print(f"║ VERDICT:       {'🟢 PASS' if passed == total else '🔴 FAIL'}")
    print("╚" + "═"*42 + "╝\n")

async def main():
    parser = argparse.ArgumentParser(description="Archimedes Failover Chaos Test")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual docker pause")
    parser.add_argument("--repeat", type=int, default=1, help="Number of chaos cycles")
    parser.add_argument("--container", type=str, default=OLLAMA_CONTAINER, help="Ollama container name")
    args = parser.parse_args()

    global OLLAMA_CONTAINER
    OLLAMA_CONTAINER = args.container

    results = []
    for i in range(args.repeat):
        res = await run_chaos_cycle(i + 1, args.dry_run)
        results.append(res)
        if i < args.repeat - 1:
            await asyncio.sleep(5) # Cooldown between cycles

    print_report(results)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test aborted by user. Ensuring Ollama is unpaused...")
        subprocess.run(["docker", "unpause", OLLAMA_CONTAINER], capture_output=True)
