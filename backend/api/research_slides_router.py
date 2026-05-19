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
import logging
import re
from backend.middleware.rate_limiter import research_limiter
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

from backend.security.sandbox_hardening import SecurityGate
_injection_gate = SecurityGate()
router = APIRouter(prefix="/api/v1", tags=["research"])



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
    if not research_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit: max 3 research requests per minute")
    
    start = time.time()
    
    # ═══ PROMPT INJECTION GUARD ═══
    verdict = _injection_gate.full_prompt_analysis(body.topic)
    if not verdict.allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Request blocked by security filter: {verdict.reasons[0] if verdict.reasons else 'Injection detected'}"
        )
    
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
        
        synthesis_prompt = f"""You are an elite, world-class presentation designer and strategic researcher.
Your goal is to synthesize the provided research data into an outstanding, professional presentation that leaves a "wow" impression.

Topic: {body.topic}
Slides requested: {body.slide_count}
Requested Style: {body.style}

RESEARCH DATA:
{search_content if search_content else "No web research data available. Generate using your deep scientific/industry knowledge."}

ANALYZE TOPIC NATURE & LEVEL OF COMPLEXITY:
Identify the topic type to determine tone, terminology density, and text length:
1. **Scientific / Academic (Научный / Академический)**: Dense, precise, highly formal academic style. Bullet points must be detailed, analytical paragraphs of 2-3 sentences explaining complex mechanisms, theories, and studies.
2. **Technical / Engineering (Технический / Инженерный)**: Precise architecture, terms, system designs, parameters, and structural components.
3. **Business / Strategic (Бизнес / Стратегический)**: Analytical structure, emphasis on value propositions, strategic outcomes, business metrics (ROI, CAGR, LTV), market forces.
4. **Educational / Popular (Образовательный / Популярный)**: Clean, engaging explanations, structured definitions, analogies, and detailed examples.
5. **Creative / Pitch Deck (Творческий / Питч-дек)**: Compelling value declarations, powerful digital/financial metrics, high-impact quotes.

STRICT WRITING RULES:
1. **Language Adaptive Rule**: If the topic or research data is in Russian (or Cyrillic), you MUST generate all text (titles, body content, bullets, stats labels, and quotes) in impeccable, natural, professional Russian.
2. **No Placeholders**: Never use lazy terms, generic fillers ("point 1", "metric a", "etc.", "Lorem Ipsum"). Write domain-specific, informative, and deep content. Integrate real figures, names, years, and facts from the RESEARCH DATA.
3. **Bullet Formatting**: For slides with "bullets", every item MUST start with a key concept/title followed by a colon and a space, strictly in the format "Concept: Detailed explanation". Every bullet text MUST contain exactly one colon ":" separating the key concept title from the explanation (at least 20-40 words per bullet point, under 280 characters to fit visual boundaries).
   - Russian example: "Квантовая гравитация: Теория струн пытается объединить квантовую механику и общую теорию относительности в единую теоретическую модель, описывающую все фундаментальные взаимодействия."
4. **Stats Formatting**: Value must be a concrete, realistic metric (e.g., "99.9% Coherence", "$1.3T CAGR"). Label must be a descriptive summary.
5. **Quote Formatting**: Deep, historically or conceptually accurate quote with authentic or highly representative author.
6. **Structure Constraints**:
   - First slide MUST be type "title".
   - Last slide MUST be type "closing".
   - The array must contain EXACTLY {body.slide_count} slides.
   - Use varied slide types ("title", "content", "bullets", "stats", "quote", "closing") to ensure a dynamic presentation layout.
7. **NO REPETITIONS OR BOILERPLATES**: Do NOT repeat the same sentences, phrases, or verbal templates (such as "Это требует глубокого теоретического анализа..." or "Инновационные подходы...") across bullet points or slides. Every single bullet point must contain unique, highly informative, and scientifically accurate facts related to the topic.

Output EXACTLY {body.slide_count} slides as a JSON array. Do not include markdown formatting or wrapping around the JSON, return ONLY the raw valid JSON.

JSON Structure for each slide:
{{
  "type": "title|content|bullets|stats|quote|closing",
  "title": "Descriptive and professional title (max 200 chars)",
  "content": "Rich, detailed main text or context (max 1000 chars)",
  "bullets": [
    "Concept: Detailed 2-3 sentence explanation (20-40 words)",
    "Concept: Detailed 2-3 sentence explanation (20-40 words)"
  ],
  "stats": [
    {{
      "value": "99.9%",
      "label": "Detailed metric description (max 100 chars)"
    }}
  ]
}}

Return ONLY the JSON array, nothing else. Make the content extremely professional, academic, and deep."""

        llm_response = await router_instance.generate(
            messages=[{"role": "user", "content": synthesis_prompt}],
            task_hint="quality",
            temperature=0.4,
            max_tokens=4000,
        )
        
        raw_text = llm_response.get("text", "")
        
        # Auto-repair nested unescaped double quotes inside JSON string fields (like ""text"")
        import re
        raw_text = re.sub(r'":\s*""([^"]+)""', r'": "\1"', raw_text)
        raw_text = re.sub(r'":\s*"([^"]+)""\s*(,)?\s*\n', r'": "\1"\2\n', raw_text)
        
        # STEP 3: Parse and validate JSON
        from backend.utils.json_repair import repair_and_parse
        slides_raw, parse_err = repair_and_parse(raw_text)
        if slides_raw is None or not isinstance(slides_raw, list):
            logger.error(f"Failed to parse slides JSON: {parse_err}. Raw: {raw_text[:300]}")
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
