"""Tests for Archimedes Canvas presentation engine."""
import pytest
import json
from backend.agent.tools.canvas_engine import CanvasEngine, SLIDE_LAYOUTS


def test_canvas_get_schema():
    import asyncio
    engine = CanvasEngine()
    result = asyncio.run(engine.execute(action="get_schema"))
    assert result["success"] is True
    assert "schema" in result
    assert "layouts" in result
    assert len(result["layouts"]) >= 8

def test_canvas_schema_has_required_layouts():
    required = ["hero", "bullet_list", "data_grid", "quote", "conclusion"]
    for layout in required:
        assert layout in SLIDE_LAYOUTS

def test_slide_renderer_renders_html(tmp_path):
    engine = CanvasEngine()
    presentation = {
        "title": "Test Presentation",
        "slides": [
            {
                "layout_type": "hero",
                "content": {
                    "title": "Hello World",
                    "subtitle": "Test subtitle"
                },
                "visual_config": {
                    "background": "dark_gradient",
                    "animation": "fade"
                }
            },
            {
                "layout_type": "bullet_list",
                "content": {
                    "title": "Key Points",
                    "body": [
                        {"text": "Point one"},
                        {"text": "Point two"},
                    ]
                },
                "visual_config": {
                    "background": "accent_purple",
                    "animation": "slide_up"
                }
            }
        ]
    }
    html = engine._render_to_html(presentation)
    assert "Hello World" in html
    assert "Key Points" in html
    assert "Archimedes AI" in html
    assert "Point one" in html

def test_canvas_export_creates_html(tmp_path):
    import asyncio
    engine = CanvasEngine()
    output_path = str(tmp_path / "test.pdf")
    presentation = {
        "title": "Test",
        "slides": [{
            "layout_type": "hero",
            "content": {"title": "Test"},
            "visual_config": {"background": "dark_gradient", "animation": "fade"}
        }]
    }
    result = asyncio.run(engine.execute(
        action="export_pdf",
        presentation_json=presentation,
        output_path=output_path
    ))
    assert result["success"] is True
    assert "file_path" in result
