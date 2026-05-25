import asyncio
import logging

_logger = logging.getLogger("BackgroundTasks")

# ── ARCH-3: Back-pressure for fire-and-forget tasks ──
# Without a limit, safe_create_task() can spawn unlimited background tasks,
# causing memory leaks and event loop starvation.
_TASK_LIMIT = 64
_task_semaphore: asyncio.Semaphore | None = None
_active_tasks: set[asyncio.Task] = set()


def _get_semaphore() -> asyncio.Semaphore:
    """Lazy-init semaphore (must be created inside a running event loop)."""
    global _task_semaphore
    if _task_semaphore is None:
        _task_semaphore = asyncio.Semaphore(_TASK_LIMIT)
    return _task_semaphore


def get_active_task_count() -> int:
    """Return the number of currently active background tasks (for monitoring)."""
    # Clean up finished tasks
    _active_tasks.discard(None)
    finished = {t for t in _active_tasks if t.done()}
    _active_tasks.difference_update(finished)
    return len(_active_tasks)


def safe_create_task(coro, name=None):
    """
    Fire-and-forget task with back-pressure and exception handling.

    Back-pressure: At most _TASK_LIMIT concurrent background tasks.
    If the limit is reached, new tasks wait until a slot is free.
    This prevents unbounded task spawning from crashing the event loop.
    """
    async def _guarded():
        if coro is None:
            _logger.debug("safe_create_task received None — skipping")
            return
        sem = _get_semaphore()
        await sem.acquire()
        try:
            return await coro
        finally:
            sem.release()

    task = asyncio.create_task(_guarded(), name=name)
    _active_tasks.add(task)

    def _handle_task_result(t: asyncio.Task):
        _active_tasks.discard(t)
        try:
            t.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _logger.exception(
                f"Background task {t.get_name() if hasattr(t, 'get_name') else t} failed: {e}"
            )

    task.add_done_callback(_handle_task_result)
    return task
