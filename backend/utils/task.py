import asyncio
import logging

def safe_create_task(coro, name=None):
    """
    Fire-and-forget task with global exception handling.
    Prevents silent failures when tasks crash.
    """
    task = asyncio.create_task(coro, name=name)
    
    def _handle_task_result(t: asyncio.Task):
        try:
            t.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.getLogger("BackgroundTasks").exception(
                f"Exception raised by task {t.get_name() if hasattr(t, 'get_name') else t}: {e}"
            )
            
    task.add_done_callback(_handle_task_result)
    return task
