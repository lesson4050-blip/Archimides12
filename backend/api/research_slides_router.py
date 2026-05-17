"""
Deep Research → Presentation Pipeline.
Researches a topic via SearchTool + LLM synthesis,
then generates structured slide data for cosmo_artist.

SECURITY:
- Input sanitized and length-capped
- Rate limited: 3 requests/minute per IP (expensive operation)
- Search results sanitized before LLM injection
- Output validated as proper JSON before returning
- No file system writes — purely in-memory pipeline
"""
import time
import json
import re
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["research"])

_research_rate: dict = {}
_RESEARCH_RPM = 3

# Allowed slide types whitelist
ALLOWED_SLIDE_TYPES = {
    "title", "content", "bullets", "image", "quote",
    "stats", "comparison", "timeline", "code", "closing"
}

class ResearchSlidesRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500)
    slide_count: int = Field(default=6, ge=3, le=12)
    style: str = Field(default="professional",
                       pattern="^(professional|minimal|creative|technical)$")

    @validator("topic")
    def sanitize_topic(cls, v):
        # Remove null bytes and excessive whitespace
        v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
        v = re.sub(r"\s+", " ", v).strip()
        if not v:
            raise ValueError("Topic cannot be empty after sanitization")
        return v

def _check_rate(client_ip: str) -> bool:
    now = time.time()
    window = now - 60
    history = [t for t in _research_rate.get(client_ip, []) if t > window]
    if len(history) >= _RESEARCH_RPM:
        return False
    history.append(now)
    _research_rate[client_ip] = history
    return True

def _sanitize_search_result(text: str, max_len: int = 3000) -> str:
    """Sanitize search results before injecting into LLM prompt."""
    if not text:
        return ""
    # Remove null bytes
    text = text.replace("\x00", "")
    # Cap length
    return text[:max_len]

def _validate_slide_json(slides_data: list) -> list:
    """
    Validate and sanitize generated slide JSON.
    Ensures only known slide types and reasonable field lengths.
    """
    validated = []
    for slide in slides_data[:12]:  # max 12 slides hard cap
        if not isinstance(slide, dict):
            continue
        
        slide_type = str(slide.get("type", "content"))
        if slide_type not in ALLOWED_SLIDE_TYPES:
            slide_type = "content"  # safe fallback
        
        validated.append({
            "type": slide_type,
            "title": str(slide.get("title", ""))[:200],
            "content": str(slide.get("content", ""))[:1000],
            "bullets": [
                str(b)[:300] for b in slide.get("bullets", [])[:8]
            ],
            "stats": [
                {
                    "value": str(s.get("value", ""))[:50],
                    "label": str(s.get("label", ""))[:100],
                }
                for s in slide.get("stats", [])[:4]
                if isinstance(s, dict)
            ],
        })
    return validated

@router.post("/research-to-slides")
async def research_to_slides(request: Request, body: ResearchSlidesRequest):
    """Research a topic and generate presentation slides."""
    
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: max {_RESEARCH_RPM} research requests per minute"
        )
    
    start = time.time()
    
    try:
        # STEP 1: Search for information
        from backend.tools.search_tool import SearchTool
        search = SearchTool()
        
        search_result = await search.execute(
            query=body.topic,
            search_depth="advanced",
            max_results=5,
        )
        
        raw_search_content = search_result.get("output", "") if search_result.get("success") else ""
        
        # SECURITY: sanitize search output before LLM injection
        search_content = _sanitize_search_result(raw_search_content)
        
        # STEP 2: LLM synthesizes research into slide structure
        from backend.models.model_router import ModelRouter
        router_instance = ModelRouter()
        
        synthesis_prompt = f"""You are a professional presentation designer.
Research topic: {body.topic}
Slides requested: {body.slide_count}
Style: {body.style}

RESEARCH DATA:
{search_content if search_content else "Generate from your knowledge."}

Generate EXACTLY {body.slide_count} slides as a JSON array.
Return ONLY valid JSON, no other text, no markdown.

Each slide must have this structure:
{{
  "type": "title|content|bullets|stats|quote|closing",
  "title": "Slide title (max 80 chars)",
  "content": "Main text (max 500 chars)",
  "bullets": ["point 1", "point 2"],
  "stats": [{{"value": "95%", "label": "description"}}]
}}

First slide must be type "title".
Last slide must be type "closing".
Make it informative and professional.
Return ONLY the JSON array, nothing else."""

        llm_response = await router_instance.generate(
            messages=[{"role": "user", "content": synthesis_prompt}],
            task_hint="quality",
            temperature=0.4,
            max_tokens=3000,
        )
        
        raw_text = llm_response.get("text", "")
        
        # STEP 3: Parse and validate JSON
        # Strip markdown code fences if present
        clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip()
        clean_text = clean_text.rstrip("`").strip()
        
        try:
            slides_raw = json.loads(clean_text)
            if not isinstance(slides_raw, list):
                raise ValueError("Expected JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse slides JSON: {e}. Raw: {raw_text[:200]}")
            raise HTTPException(
                status_code=422,
                detail="Failed to generate valid slide structure. Please try again."
            )
        
        # SECURITY: validate and sanitize all slide content
        slides = _validate_slide_json(slides_raw)
        
        if len(slides) < 2:
            raise HTTPException(
                status_code=422,
                detail="Generated too few slides. Please try again."
            )
        
        elapsed = round(time.time() - start, 2)
        
        return {
            "topic": body.topic[:200],
            "slide_count": len(slides),
            "style": body.style,
            "elapsed_seconds": elapsed,
            "slides": slides,
            "search_used": bool(search_content),
            "model": llm_response.get("model_used", "unknown"),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"research-to-slides failed: {e}")
        raise HTTPException(status_code=500, detail="Research pipeline failed")
