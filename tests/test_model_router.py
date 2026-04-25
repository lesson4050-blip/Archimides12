"""
Tests for ModelRouter — fallback logic when providers raise RateLimitExceeded.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def router():
    from backend.models.model_router import ModelRouter
    r = ModelRouter.__new__(ModelRouter)
    r.groq = AsyncMock()
    r.groq.__class__ = type("GroqClient", (), {})
    r.gemini = AsyncMock()
    r.gemini.__class__ = type("GeminiClient", (), {})
    r.ollama = AsyncMock()
    r.ollama.__class__ = type("OllamaClient", (), {})
    return r


@pytest.mark.asyncio
async def test_default_routing_uses_groq_first(router):
    router.groq.generate_with_tools = AsyncMock(return_value={"text": "groq"})
    result = await router.generate(messages=[{"role": "user", "content": "hi"}])
    assert result["text"] == "groq"


@pytest.mark.asyncio
async def test_fallback_on_groq_rate_limit(router):
    from backend.models.groq_client import RateLimitExceeded as GroqRL
    router.groq.generate_with_tools = AsyncMock(side_effect=GroqRL("limit"))
    router.gemini.generate_with_tools = AsyncMock(return_value={"text": "gemini"})
    result = await router.generate(messages=[{"role": "user", "content": "hi"}])
    assert result["text"] == "gemini"


@pytest.mark.asyncio
async def test_fallback_through_all_tiers(router):
    from backend.models.groq_client import RateLimitExceeded as GroqRL
    from backend.models.gemini_client import RateLimitExceeded as GeminiRL
    router.groq.generate_with_tools = AsyncMock(side_effect=GroqRL("x"))
    router.gemini.generate_with_tools = AsyncMock(side_effect=GeminiRL("x"))
    router.ollama.generate_with_tools = AsyncMock(return_value={"text": "ollama"})
    result = await router.generate(messages=[{"role": "user", "content": "hi"}])
    assert result["text"] == "ollama"


@pytest.mark.asyncio
async def test_all_models_exhausted_raises(router):
    from backend.models.model_router import AllModelsExhausted
    from backend.models.groq_client import RateLimitExceeded as GroqRL
    router.groq.generate_with_tools = AsyncMock(side_effect=GroqRL("x"))
    router.gemini.generate_with_tools = AsyncMock(side_effect=Exception("down"))
    router.ollama.generate_with_tools = AsyncMock(side_effect=Exception("err"))
    with pytest.raises(AllModelsExhausted):
        await router.generate(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_quality_task_uses_local_first(router):
    router.ollama.generate_with_tools = AsyncMock(return_value={"text": "deep"})
    result = await router.generate(
        messages=[{"role": "user", "content": "plan"}], task_hint="think"
    )
    assert result["text"] == "deep"
    router.ollama.generate_with_tools.assert_awaited_once()
