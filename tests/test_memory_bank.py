"""Tests for Memory Bank (test 1.16)."""
import os
import pytest

os.environ["MEMORY_BANK_DB"] = "data/test_memory_bank.db"

from backend.memory.memory_bank import (
    _init_db, save_fact, get_relevant_facts, get_session_summary,
)


@pytest.fixture(autouse=True)
async def clean_db():
    db_path = os.environ["MEMORY_BANK_DB"]
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    await _init_db()
    yield
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass


@pytest.mark.asyncio
async def test_save_and_retrieve_fact():
    await save_fact("Python is great", session_id="s1", category="lang")
    facts = await get_relevant_facts(query="Python", limit=5)
    assert any("Python" in f for f in facts)


@pytest.mark.asyncio
async def test_get_relevant_facts_empty():
    facts = await get_relevant_facts(query="nonexistent_xyz_abc")
    assert facts == []


@pytest.mark.asyncio
async def test_get_relevant_facts_by_category():
    await save_fact("fact1", category="tech")
    await save_fact("fact2", category="science")
    facts = await get_relevant_facts(category="tech")
    assert len(facts) >= 1


@pytest.mark.asyncio
async def test_get_relevant_facts_no_query():
    await save_fact("important fact", importance=5)
    facts = await get_relevant_facts(limit=10)
    assert len(facts) >= 1


@pytest.mark.asyncio
async def test_get_session_summary():
    await save_fact("learned X", session_id="sess-abc", importance=3)
    await save_fact("learned Y", session_id="sess-abc", importance=1)
    summary = await get_session_summary("sess-abc")
    assert "learned X" in summary


@pytest.mark.asyncio
async def test_get_session_summary_empty():
    summary = await get_session_summary("nonexistent_session")
    assert summary == ""
