"""
Marp Slides API Routes.
Exposes endpoints for generating and exporting premium Marp Markdown presentations.
"""
import os
import re
import time
import logging
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator

from backend.middleware.rate_limiter import research_limiter
from backend.security.sandbox_hardening import SecurityGate
from backend.agent.tools.marp_engine import MarpEngine
from backend.tools.search_tool import SearchTool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["marp"])
_injection_gate = SecurityGate()


class MarpSlidesRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500)
    slide_count: int = Field(default=6, ge=3, le=12)
    style: str = Field(default="professional", pattern="^(professional|minimal|creative|technical)$")

    @validator("topic")
    def sanitize_topic(cls, v):
        # Remove null bytes and excessive whitespace
        v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
        v = re.sub(r"\s+", " ", v).strip()
        if not v:
            raise ValueError("Topic cannot be empty after sanitization")
        return v


class MarpExportRequest(BaseModel):
    markdown: str = Field(..., min_length=10)


def _sanitize_search_result(text: str, max_len: int = 3000) -> str:
    """Sanitize search results before injecting into LLM prompt."""
    if not text:
        return ""
    text = text.replace("\x00", "")
    return text[:max_len]


@router.post("/research-to-marp")
async def research_to_marp(request: Request, body: MarpSlidesRequest):
    """Research a topic and generate a premium interactive Marp presentation."""
    client_ip = request.client.host if request.client else "unknown"
    if not research_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit: max 3 presentation requests per minute"
        )
    
    start_time = time.time()
    
    # ═══ PROMPT INJECTION GUARD ═══
    verdict = _injection_gate.full_prompt_analysis(body.topic)
    if not verdict.allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Request blocked by security filter: {verdict.reasons[0] if verdict.reasons else 'Injection detected'}"
        )
    
    try:
        # Step 1: Perform Web Research
        search = SearchTool()
        search_result = await search.execute(
            query=body.topic,
            search_depth="advanced",
            max_results=5
        )
        
        raw_search_content = search_result.get("output", "") if search_result.get("success") else ""
        search_content = _sanitize_search_result(raw_search_content)
        
        # Step 2: Initialize MarpEngine and generate slides markdown
        engine = MarpEngine()
        gen_result = await engine.execute(
            action="generate",
            topic=body.topic,
            slide_count=body.slide_count,
            style=body.style,
            research_data=search_content
        )
        
        if not gen_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Marp slide generation failed: {gen_result.get('error')}"
            )
        
        markdown_str = gen_result.get("markdown")
        
        # Step 3: Compile Markdown slides to standalone interactive HTML
        compile_result = await engine.execute(
            action="compile_html",
            markdown=markdown_str
        )
        
        if not compile_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Marp compilation to HTML failed: {compile_result.get('error')}"
            )
        
        html_str = compile_result.get("html")
        elapsed = round(time.time() - start_time, 2)
        
        return {
            "success": True,
            "topic": body.topic,
            "slide_count": body.slide_count,
            "style": body.style,
            "elapsed_seconds": elapsed,
            "markdown": markdown_str,
            "html": html_str,
            "search_used": bool(search_content),
            "model": gen_result.get("model_used", "unknown")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"research-to-marp failed: {e}")
        raise HTTPException(status_code=500, detail=f"Research presentation pipeline failed: {str(e)}")


@router.post("/export-marp-pdf")
async def export_marp_pdf(body: MarpExportRequest, background_tasks: BackgroundTasks):
    """Compile the provided Marp markdown and stream back a vector PDF."""
    try:
        engine = MarpEngine()
        compile_result = await engine.execute(
            action="compile_pdf",
            markdown=body.markdown
        )
        
        if not compile_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Marp compilation to PDF failed: {compile_result.get('error')}"
            )
        
        pdf_path = compile_result.get("pdf_path")
        
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(
                status_code=500,
                detail="Marp compiler failed to generate PDF file"
            )
        
        # Schedule the temporary PDF file to be deleted once sent
        background_tasks.add_task(os.remove, pdf_path)
        
        return FileResponse(
            path=pdf_path,
            filename="presentation.pdf",
            media_type="application/pdf"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"export-marp-pdf failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")
