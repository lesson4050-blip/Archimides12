"""Tests for Archimedes Marp presentation engine."""
import os
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from backend.agent.tools.marp_engine import MarpEngine, MARP_THEME_CSS


def test_marp_engine_definition():
    engine = MarpEngine()
    definition = engine.get_definition()
    assert definition["type"] == "function"
    assert definition["function"]["name"] == "marp"
    assert "action" in definition["function"]["parameters"]["properties"]
    assert "topic" in definition["function"]["parameters"]["properties"]


def test_marp_engine_inject_theme_css():
    engine = MarpEngine()
    
    # Test case 1: Markdown without frontmatter
    md_no_fm = "# Hello World\nSome slide content."
    md_with_injected = engine._inject_theme_css(md_no_fm)
    assert "marp: true" in md_with_injected
    assert "theme: uncover" in md_with_injected
    assert "class: invert" in md_with_injected
    assert "style: |" in md_with_injected
    assert ".grid-2 {" in md_with_injected
    assert "# Hello World" in md_with_injected

    # Test case 2: Markdown with standard frontmatter but no style key
    md_fm_no_style = "---\nmarp: true\ntheme: uncover\n---\n# Slide 1"
    md_with_injected = engine._inject_theme_css(md_fm_no_style)
    assert "style: |" in md_with_injected
    assert ".card-purple {" in md_with_injected
    assert "# Slide 1" in md_with_injected

    # Test case 3: Markdown with existing style key
    md_fm_with_style = "---\nmarp: true\nstyle: |\n  section {\n    color: red;\n  }\n---\n# Slide 1"
    md_with_injected = engine._inject_theme_css(md_fm_with_style)
    assert "color: red;" in md_with_injected
    assert ".metric-value {" in md_with_injected


@pytest.mark.asyncio
async def test_marp_engine_generate_missing_topic():
    engine = MarpEngine()
    result = await engine.execute(action="generate")
    assert result["success"] is False
    assert "topic required" in result["error"]


@pytest.mark.asyncio
async def test_marp_engine_generate_success(mock_router):
    # Mocking the generate method on mock_router
    mock_router.generate = AsyncMock(return_value={
        "text": "```markdown\n---\nmarp: true\n---\n# Real Slide\n- Content\n```",
        "model_used": "mocked-llm"
    })
    
    engine = MarpEngine(router=mock_router)
    result = await engine.execute(
        action="generate",
        topic="AI Agents",
        audience="developers",
        slide_count=4,
        style="technical",
        research_data="Some context"
    )
    
    assert result["success"] is True
    assert "markdown" in result
    assert "Real Slide" in result["markdown"]
    assert "style: |" in result["markdown"]
    assert result["model_used"] == "mocked-llm"
    
    # Verify mock_router was called correctly
    mock_router.generate.assert_called_once()
    args, kwargs = mock_router.generate.call_args
    assert "messages" in kwargs
    assert "AI Agents" in kwargs["messages"][0]["content"]
    assert "developers" in kwargs["messages"][0]["content"]
    assert "Some context" in kwargs["messages"][0]["content"]


@pytest.mark.asyncio
async def test_marp_engine_compile_html_missing_markdown():
    engine = MarpEngine()
    result = await engine.execute(action="compile_html")
    assert result["success"] is False
    assert "markdown string required" in result["error"]


@pytest.mark.asyncio
async def test_marp_engine_compile_html_success():
    engine = MarpEngine()
    md = "---\nmarp: true\n---\n# Test Presentation\nThis is a compile test."
    
    result = await engine.execute(
        action="compile_html",
        markdown=md
    )
    
    # We test compilation for real since we have node and npx on the host
    assert result["success"] is True
    assert "html" in result
    assert "<!DOCTYPE html>" in result["html"]
    assert "Test Presentation" in result["html"]
    assert "This is a compile test." in result["html"]


@pytest.mark.asyncio
async def test_marp_engine_compile_pdf_success():
    engine = MarpEngine()
    md = "---\nmarp: true\n---\n# PDF Presentation\nPDF compile test."
    
    result = await engine.execute(
        action="compile_pdf",
        markdown=md
    )
    
    assert result["success"] is True
    assert "pdf_path" in result
    assert os.path.exists(result["pdf_path"])
    assert result["pdf_path"].endswith(".pdf")
    
    # Clean up the generated test PDF
    try:
        os.remove(result["pdf_path"])
    except Exception:
        pass


@pytest.mark.asyncio
async def test_marp_engine_invalid_action():
    engine = MarpEngine()
    result = await engine.execute(action="invalid_action")
    assert result["success"] is False
    assert "Unknown action" in result["error"]
