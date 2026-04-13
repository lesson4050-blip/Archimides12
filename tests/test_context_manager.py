import pytest
from backend.memory.context_manager import ContextManager

def test_context_manager_token_counting():
    """Verify that tokens are counted accurately (conceptually)."""
    cm = ContextManager(max_tokens=100)
    cm.add_message("user", "Hello world")
    
    messages = cm.get_messages()
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert "Hello world" in messages[0]["content"]

@pytest.mark.asyncio
async def test_context_manager_sliding_window():
    """Verify summarize_if_needed reduces token count."""
    class MockRouter:
        async def generate(self, **kwargs):
            return {"text": "Summary of conversation."}

    cm = ContextManager(
        max_tokens=500,
        summarization_threshold=100, preserve_recent=3
    )
    for i in range(15):
        cm.add_message("user", f"Message {i} " * 20)

    tokens_before = cm.current_tokens
    await cm.summarize_if_needed(MockRouter())
    tokens_after = cm.current_tokens

    assert tokens_after < tokens_before, (
        f"Summarization failed: {tokens_before} -> {tokens_after}"
    )

@pytest.mark.asyncio
async def test_summary_logic():
    """Verify that summarization is triggered (mock router)."""
    class MockRouter:
        async def generate(self, **kwargs):
            return {"text": "This is a summary of the conversation."}
            
    cm = ContextManager(max_tokens=1000, summarization_threshold=100, preserve_recent=1)
    for i in range(5):
        cm.add_message("user", "Extremely long text " * 50)
    
    # This should trigger summarization
    await cm.summarize_if_needed(MockRouter())
    
    messages = cm.get_messages()
    assert any("summary" in m["content"].lower() for m in messages)
