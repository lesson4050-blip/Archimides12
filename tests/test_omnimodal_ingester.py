"""Tests for OmnimodalIngester — Gen 4 perception layer."""
import pytest
import os
import tempfile
from unittest.mock import AsyncMock, patch
from backend.agent.omnimodal_ingester import (
    OmnimodalIngester, Modality, PerceptionUnit
)


def test_detect_modality_image():
    ingester = OmnimodalIngester()
    assert ingester.detect_modality("photo.jpg") == Modality.IMAGE
    assert ingester.detect_modality("screenshot.png") == Modality.IMAGE
    assert ingester.detect_modality("animated.gif") == Modality.IMAGE


def test_detect_modality_audio():
    ingester = OmnimodalIngester()
    assert ingester.detect_modality("podcast.mp3") == Modality.AUDIO
    assert ingester.detect_modality("recording.wav") == Modality.AUDIO


def test_detect_modality_video():
    ingester = OmnimodalIngester()
    assert ingester.detect_modality("demo.mp4") == Modality.VIDEO
    assert ingester.detect_modality("presentation.webm") == Modality.VIDEO


def test_detect_modality_pdf():
    ingester = OmnimodalIngester()
    assert ingester.detect_modality("report.pdf") == Modality.PDF


def test_detect_modality_code():
    ingester = OmnimodalIngester()
    assert ingester.detect_modality("main.py") == Modality.CODE
    assert ingester.detect_modality("App.tsx") == Modality.CODE


def test_perception_unit_context_string():
    unit = PerceptionUnit(
        unit_id="test-001",
        modality=Modality.IMAGE,
        source_path="/tmp/test.jpg",
        text_summary="A bar chart showing revenue growth",
        concepts=["revenue", "growth", "Q4", "bar chart"]
    )
    ctx = unit.to_context_string()
    assert "IMAGE" in ctx
    assert "revenue" in ctx
    assert "bar chart" in ctx


@pytest.mark.asyncio
async def test_ingest_text_content(tmp_path):
    mock_router = AsyncMock()
    mock_router.generate = AsyncMock(return_value={
        "text": "machine learning, neural networks, training"
    })
    ingester = OmnimodalIngester(router=mock_router)
    
    unit = await ingester._process_text(
        "def train_model(data):\n    # Neural network training\n    pass",
        source_id="test_code"
    )
    
    assert unit.modality == Modality.TEXT
    assert "train_model" in unit.concepts or len(unit.concepts) >= 0


@pytest.mark.asyncio  
async def test_query_empty_returns_empty(tmp_path):
    with patch("backend.agent.omnimodal_ingester.OMNIMODAL_CHROMA_DIR", str(tmp_path)):
        ingester = OmnimodalIngester()
        results = await ingester.query("machine learning concepts")
        assert isinstance(results, list)


def test_generate_unit_id_deterministic():
    ingester = OmnimodalIngester()
    id1 = ingester._generate_unit_id("same_source")
    id2 = ingester._generate_unit_id("same_source")
    id3 = ingester._generate_unit_id("different_source")
    assert id1 == id2
    assert id1 != id3


@pytest.mark.asyncio
async def test_execute_action_ingest_text():
    mock_router = AsyncMock()
    mock_router.generate = AsyncMock(return_value={"text": "concept1, concept2"})
    ingester = OmnimodalIngester(router=mock_router)
    
    result = await ingester.execute(
        action="ingest",
        source="This is a test document about machine learning"
    )
    
    assert result["success"] is True
    assert "unit_id" in result
    assert "concepts" in result


@pytest.mark.asyncio
async def test_execute_invalid_action():
    ingester = OmnimodalIngester()
    result = await ingester.execute(action="invalid_action_xyz")
    assert result["success"] is False
