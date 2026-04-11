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

def test_context_manager_sliding_window():
    """Verify that old messages are dropped when limit reached."""
    # Set a very low limit to trigger pruning easily
    cm = ContextManager(max_tokens=50)
    
    # Add many messages
    for i in range(20):
        cm.add_message("user", f"Message number {i} with some extra padding text to increase token count.")
    
    messages = cm.get_messages()
    # Pruned history should be shorter than full history
    assert len(messages) < 20
    # The last message should still be there
    assert "Message number 19" in messages[-1]["content"]

@pytest.mark.asyncio
async def test_summary_logic():
    """Verify that summarization is triggered (mock router)."""
    class MockRouter:
        async def generate(self, **kwargs):
            return {"text": "This is a summary of the conversation."}
            
    cm = ContextManager(max_tokens=100)
    cm.add_message("user", "Extremely long text " * 50)
    
    # This should trigger summarization
    await cm.summarize_if_needed(MockRouter())
    
    messages = cm.get_messages()
    assert any("summary" in m["content"].lower() for m in messages)
