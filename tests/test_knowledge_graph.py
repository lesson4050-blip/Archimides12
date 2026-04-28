"""Tests for Knowledge Graph (test 1.15)."""
import os
import pytest
import aiosqlite
from unittest.mock import AsyncMock, MagicMock, patch

# Override DB_PATH before import
os.environ["KG_DB_PATH"] = "data/test_kg.db"

from backend.memory.knowledge_graph import (
    _init_db, add_entity, add_relation,
    query_related, format_graph_context,
)


@pytest.fixture(autouse=True)
async def clean_db():
    """Fresh DB for each test."""
    db_path = os.environ["KG_DB_PATH"]
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    await _init_db()
    yield
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass


@pytest.mark.asyncio
async def test_add_entity():
    eid = await add_entity("Python", entity_type="language")
    assert isinstance(eid, int)
    assert eid > 0


@pytest.mark.asyncio
async def test_add_relation_creates_entities():
    await add_relation("FastAPI", "uses", "Python", context="web framework")
    results = await query_related("FastAPI", depth=1)
    assert len(results) > 0
    assert any(r["to"] == "Python" for r in results)


@pytest.mark.asyncio
async def test_query_related_depth():
    await add_relation("A", "depends_on", "B")
    await add_relation("B", "depends_on", "C")
    results = await query_related("A", depth=2)
    entities = {r["to"] for r in results} | {r["from"] for r in results}
    assert "B" in entities


@pytest.mark.asyncio
async def test_query_related_empty():
    results = await query_related("nonexistent_entity_xyz")
    assert results == []


@pytest.mark.asyncio
async def test_format_graph_context():
    await add_relation("React", "uses", "JavaScript")
    ctx = await format_graph_context("React")
    assert "React" in ctx
    assert "JavaScript" in ctx


@pytest.mark.asyncio
async def test_format_graph_context_empty():
    ctx = await format_graph_context("nothing_here_xyz")
    assert ctx == ""
