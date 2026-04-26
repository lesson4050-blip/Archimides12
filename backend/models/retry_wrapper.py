"""
Adaptive Retry Wrapper for LLM calls.
Handles rate limits, transient errors, and timeouts
with exponential backoff and jitter.
"""
import asyncio
import logging
import random
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RetryConfig:
    def __init__(
        self,
        max_retries: int = 4,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter


DEFAULT_RETRY = RetryConfig()


async def with_retry(
    fn: Callable,
    *args,
    config: RetryConfig = DEFAULT_RETRY,
    fallback: Optional[Callable] = None,
    operation_name: str = "LLM call",
    **kwargs
) -> Any:
    """
    Execute fn with exponential backoff retry.
    
    Retries on:
    - RateLimitError (429)
    - ServiceUnavailableError (503)
    - asyncio.TimeoutError
    - ConnectionError
    
    Does NOT retry on:
    - AuthenticationError (401) — bad key, no point retrying
    - InvalidRequestError (400) — bad prompt format
    """
    RETRYABLE_PHRASES = [
        "rate limit", "429", "503", "overloaded",
        "timeout", "connection", "server error",
        "capacity", "try again"
    ]
    NON_RETRYABLE_PHRASES = [
        "401", "authentication", "invalid api key",
        "400", "invalid request", "context length"
    ]
    
    last_error = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await fn(*args, **kwargs)
            
        except asyncio.TimeoutError as e:
            last_error = e
            error_str = "timeout"
            
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            # Don't retry non-retryable errors
            if any(phrase in error_str for phrase in NON_RETRYABLE_PHRASES):
                logger.error(
                    f"{operation_name}: non-retryable error: {e}"
                )
                raise
            
            # Only retry if it looks retryable
            if not any(phrase in error_str for phrase in RETRYABLE_PHRASES):
                if attempt == 0:
                    # First attempt failed with unknown error — try once more
                    pass
                else:
                    raise
        
        if attempt >= config.max_retries:
            break
        
        # Exponential backoff with jitter
        delay = min(
            config.base_delay * (config.backoff_factor ** attempt),
            config.max_delay
        )
        if config.jitter:
            delay *= (0.5 + random.random() * 0.5)
        
        logger.warning(
            f"{operation_name}: attempt {attempt + 1}/{config.max_retries} "
            f"failed ({error_str[:60]}). Retrying in {delay:.1f}s..."
        )
        await asyncio.sleep(delay)
    
    # All retries exhausted
    if fallback:
        logger.warning(f"{operation_name}: all retries exhausted, using fallback")
        return await fallback(*args, **kwargs)
    
    logger.error(f"{operation_name}: all {config.max_retries} retries failed")
    raise last_error
