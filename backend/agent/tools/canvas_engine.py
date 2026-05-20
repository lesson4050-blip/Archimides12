"""
Archimedes Canvas Engine — Presentation generation system.

Architecture:
- LLM generates structured JSON (not raw HTML)
- Frontend renders JSON into beautiful Tailwind/Framer Motion slides
- Puppeteer exports to PDF

Inspired by Kimi Slides / Gamma — HTML-native, not static images.
"""
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── JSON Schema for slides ──

SLIDE_LAYOUTS = [
    "hero",           # Big title, subtitle, optional background
    "split_content",  # Left text, right visual (code/image/chart)
    "bullet_list",    # Title + 3-7 bullet points with icons
    "data_grid",      # 2x2 or 3x3 grid of metrics/stats
    "quote",          # Large centered quote with attribution
    "timeline",       # Horizontal or vertical timeline
    "comparison",     # Side-by-side comparison table
    "code_showcase",  # Syntax-highlighted code + explanation
    "image_focus",    # Full-bleed image with overlay text
    "conclusion",     # Summary + call-to-action
]

SLIDE_SCHEMA = {
    "type": "object",
    "properties": {
        "layout_type": {
            "type": "string",
            "enum": SLIDE_LAYOUTS,
            "description": "Visual layout template"
        },
        "slide_number": {"type": "integer"},
        "content": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
                "body": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "icon": {"type": "string"},
                            "emphasis": {"type": "boolean"}
                        }
                    }
                },
                "code": {
                    "type": "object",
                    "properties": {
                        "language": {"type": "string"},
                        "content": {"type": "string"}
                    }
                },
                "metrics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "string"},
                            "delta": {"type": "string"},
                            "trend": {"type": "string", "enum": ["up", "down", "neutral"]}
                        }
                    }
                },
                "quote_text": {"type": "string"},
                "quote_author": {"type": "string"},
                "cta_text": {"type": "string"},
                "cta_url": {"type": "string"},
            }
        },
        "visual_config": {
            "type": "object",
            "properties": {
                "background": {
                    "type": "string",
                    "enum": [
                        "dark_gradient",   # Default Archimedes dark
                        "light_minimal",   # Clean white
                        "accent_purple",   # Purple gradient
                        "accent_blue",     # Blue gradient
                        "code_dark",       # VSCode-like dark
                        "image_overlay"    # Background image with overlay
                    ]
                },
                "animation": {
                    "type": "string",
                    "enum": ["fade", "slide_up", "slide_right", "scale", "none"]
                },
                "accent_color": {"type": "string"},
            }
        },
        "speaker_notes": {"type": "string"}
    },
    "required": ["layout_type", "content", "visual_config"]
}

PRESENTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "author": {"type": "string"},
        "theme": {
            "type": "string",
            "enum": ["archimedes_dark", "archimedes_light", "archimedes_minimal"]
        },
        "slides": {
            "type": "array",
            "items": SLIDE_SCHEMA,
            "minItems": 3,
            "maxItems": 30
        },
        "metadata": {
            "type": "object",
            "properties": {
                "created_at": {"type": "string"},
                "version": {"type": "string"},
                "export_formats": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["pdf", "pptx", "html"]}
                }
            }
        }
    },
    "required": ["title", "slides"]
}


GENERATION_PROMPT = """You are an elite, world-class presentation designer and strategic communicator for Archimedes AI.
Your goal is to create a presentation that leaves a "wow" impression, blending high-end visual layout choices with deep, analytical, and context-aware content.

ANALYZE TOPIC NATURE & LEVEL OF COMPLEXITY:
1. First, analyze the topic, audience, and instructions to determine the appropriate depth:
   - **Scientific / Academic (Научный / Академический)**: (e.g., Quantum physics, neural network architectures, biology, history, academic studies). Use dense, precise, academic style and terminology. Explain concepts deeply. Bullet points must be highly detailed paragraphs of 2-3 sentences. Every bullet point must have between 25 and 45 words.
   - **Technical / Engineering (Технический / Инженерный)**: (e.g., Code review, software design, infrastructure). Provide precise architecture terms, parameters, code snippets (layout_type="code_showcase").
   - **Business / Strategic (Бизнес / Стратегический)**: (e.g., Financial reporting, marketing strategy, startup deck). Focus on business metrics, impact, timelines, ROI, structured value propositions.
   - **Educational / Popular (Образовательный / Популярный)**: (e.g., Intro to astronomy, history for general audience). Clear, engaging explanations, rich analogies, structured definitions.
   - **Creative / Pitch Deck (Творческий / Питч-дек)**: Punchy, emotionally engaging copy, bold declarations, core stats, and inspiring quotes.

2. Language rule:
   - Respond in the language of the topic/key points. If the topic is in Russian (or cyrillic), output all slide titles, bodies, and metrics in perfect, natural, professional Russian.

STRICT RULES:
1. Output ONLY a valid JSON object instance matching the schema below.
   DO NOT output a schema definition (do not output "type": "object" or "properties" at the root level).
   Output the ACTUAL presentation object.
2. Use varied layout_types — never repeat the same layout 3 times in a row. Use the best fit layout for the slide content.
3. For hero slide: use layout_type="hero".
4. For data/metrics: use layout_type="data_grid".
5. For code: use layout_type="code_showcase".
6. Avoid superficial content. Forbid generic placeholders ("point 1", "point 2", "etc.", "Lorem Ipsum"). Write highly detailed and domain-specific text.
7. Title formatting: Every single slide in the presentation (including hero, bullet_list, data_grid, quote, code_showcase, etc.) MUST have a descriptive, non-empty, professional "title" inside the "content" object (max 10-12 words). For data_grid, quote, or other layouts, the title should summarize the theme of the metrics/quote.
8. Bullet list formatting (layout_type="bullet_list" / "split_content" / "timeline" / "comparison"):
   - For lists, every item MUST start with a bold key concept name followed by a colon and a space, strictly in the format "Concept: Detailed explanation".
   - Russian example: "М-теория: 11-мерная супергравитационная модель, которая объединяет пять различных суперструнных теорий в единый математический каркас, предложенный Эдвардом Виттеном в 1995 году."
   - Every bullet text MUST contain exactly one colon ":" separating the key concept title from its 20-40 word detailed explanation (at least 20-40 words per bullet point).
   - Max 6 items per slide. Never generate short, lazy, single-word or 3-word bullets.
9. Stats formatting (layout_type="data_grid"):
   - Value must be a concrete, realistic metric (e.g., "99.9% Coherence", "$1.3T CAGR").
   - Label must be a descriptive, professional summary of what the metric represents.
10. Quote formatting (layout_type="quote"):
    - Write deep, meaningful, historically/conceptually appropriate quotes with authentic or highly representative authors.
11. Every slide must have visual_config.background and visual_config.animation.
12. Use background="dark_gradient" for main slides, vary for emphasis slides.
13. Add highly professional speaker_notes to every slide (2-3 detailed sentences summarizing delivery advice or extra data).
14. NO REPETITIONS OR BOILERPLATES: Do NOT repeat the same sentences, phrases, or verbal templates (such as "Это требует глубокого теоретического анализа..." or "Инновационные подходы...") across bullet points or slides. Every single bullet point must contain unique, highly informative, and scientifically accurate facts related to the topic.

Expected Output JSON Instance Template:
{{
  "title": "Descriptive Presentation Title",
  "subtitle": "Analytical Subtitle",
  "author": "Author Name",
  "theme": "archimedes_dark",
  "slides": [
    {{
      "layout_type": "hero",
      "slide_number": 1,
      "content": {{
        "title": "Title of Slide",
        "subtitle": "Subtitle of Slide"
      }},
      "visual_config": {{
        "background": "dark_gradient",
        "animation": "fade"
      }},
      "speaker_notes": "Detailed speaker notes..."
    }},
    {{
      "layout_type": "bullet_list",
      "slide_number": 2,
      "content": {{
        "title": "Slide Title",
        "body": [
          {{
            "text": "Concept One: Detailed 2-3 sentence explanation with at least 20-40 words.",
            "icon": "star",
            "emphasis": true
          }},
          {{
            "text": "Concept Two: Another detailed explanation demonstrating that every single bullet item in the list must strictly follow this colon-separated pattern.",
            "icon": "circle",
            "emphasis": false
          }},
          {{
            "text": "Concept Three: Detailed explanation here as well, showing consistency across all elements of the body array.",
            "icon": "bolt",
            "emphasis": false
          }}
        ]
      }},
      "visual_config": {{
        "background": "dark_gradient",
        "animation": "slide_up"
      }},
      "speaker_notes": "Detailed notes..."
    }}
  ]
}}

Presentation Schema for slides:
{schema}

Topic: {topic}
Audience: {audience}
Slide count: {slide_count}
Key points to cover: {key_points}

Output ONLY the raw JSON object, no explanation, no markdown wrapping, no text outside the JSON."""



class CanvasEngine:
    """Generate Kimi-level presentations using structured JSON."""

    def __init__(self, router=None):
        self.router = router

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "canvas",
                "description": (
                    "Generate professional presentations in Archimedes Canvas format. "
                    "Actions: generate (create presentation JSON from topic), "
                    "export_pdf (render to PDF via Puppeteer), "
                    "add_slide (add a slide to existing presentation), "
                    "get_schema (return the JSON schema)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["generate", "export_pdf", "add_slide", "get_schema"]
                        },
                        "topic": {"type": "string"},
                        "audience": {"type": "string", "default": "general"},
                        "slide_count": {"type": "integer", "default": 10},
                        "key_points": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "presentation_json": {
                            "type": "object",
                            "description": "Existing presentation to modify"
                        },
                        "output_path": {"type": "string"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(
        self,
        action: str,
        topic: str = None,
        audience: str = "general",
        slide_count: int = 10,
        key_points: List[str] = None,
        presentation_json: Dict = None,
        output_path: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        
        if action == "get_schema":
            return {
                "success": True,
                "schema": PRESENTATION_SCHEMA,
                "layouts": SLIDE_LAYOUTS
            }
        
        elif action == "generate":
            if not topic:
                return {"success": False, "error": "topic required"}
            if not self.router:
                return {"success": False, "error": "No LLM router available"}
            
            prompt = GENERATION_PROMPT.format(
                schema=json.dumps(PRESENTATION_SCHEMA, indent=2),
                topic=topic,
                audience=audience,
                slide_count=slide_count,
                key_points=", ".join(key_points or []) or "auto-determine from topic"
            )
            
            try:
                response = await self.router.generate(
                    messages=[{"role": "user", "content": prompt}],
                    task_hint="quality",
                    max_tokens=4000
                )
                
                text = response.get("text", "")
                
                # Auto-repair nested unescaped double quotes inside JSON string fields (like ""text"")
                import re
                text = re.sub(r'":\s*""([^"]+)""', r'": "\1"', text)
                text = re.sub(r'":\s*"([^"]+)""\s*(,)?\s*\n', r'": "\1"\2\n', text)
                
                from backend.utils.json_repair import repair_and_parse
                presentation, parse_err = repair_and_parse(text)
                if presentation is None or not isinstance(presentation, dict):
                    return {
                        "success": False,
                        "error": f"LLM did not return valid JSON: {parse_err}",
                        "raw": text
                    }
                
                # Auto-repair presentation slide bullet formats and enrich short text
                if presentation and isinstance(presentation, dict) and "slides" in presentation:
                    for slide in presentation["slides"]:
                        layout = slide.get("layout_type")
                        content = slide.get("content", {})
                        if not content:
                            continue
                        
                        body = content.get("body")
                        if layout in ["bullet_list", "split_content", "timeline", "comparison"] and isinstance(body, list):
                            for item in body:
                                if not isinstance(item, dict):
                                    continue
                                item_text = item.get("text", "").strip()
                                if not item_text:
                                    continue
                                
                                words = item_text.split()
                                
                                colon_idx = item_text.find(":")
                                # A valid concept name should be short (max 40 characters)
                                if colon_idx == -1 or colon_idx > 40:
                                    # Extract first 2-3 words as concept name
                                    concept_words = []
                                    for w in words[:3]:
                                        clean_w = w.strip(".,;:!?\"'()«»-—")
                                        if clean_w:
                                            concept_words.append(clean_w)
                                    concept = " ".join(concept_words).capitalize()
                                    if not concept or len(concept) < 3:
                                        concept = "Важный тезис"
                                    
                                    # Clean up introductory words from the concept if any
                                    for intro in ["Другим", "Хотя", "Однако", "Поэтому", "Кроме", "Также"]:
                                        if concept.startswith(intro) and len(concept.split()) > 1:
                                            concept = concept[len(intro):].strip().capitalize()
                                            
                                    item_text = f"{concept}: {item_text}"
                                
                                item["text"] = item_text
                
                # Add Archimedes metadata
                from datetime import datetime, timezone
                presentation.setdefault("metadata", {})
                presentation["metadata"]["created_at"] = datetime.now(timezone.utc).isoformat()
                presentation["metadata"]["version"] = "1.0"
                presentation["metadata"]["engine"] = "archimedes_canvas"
                presentation["author"] = presentation.get("author", "Archimedes AI")
                
                # Save to file if output_path provided
                if output_path:
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(presentation, f, indent=2, ensure_ascii=False)
                
                return {
                    "success": True,
                    "output": f"Generated {len(presentation.get('slides', []))} slides",
                    "presentation": presentation,
                    "slide_count": len(presentation.get("slides", [])),
                }
                
            except Exception as e:
                logger.error(f"Canvas generation error: {e}")
                return {"success": False, "error": str(e)}
        
        elif action == "export_pdf":
            if not presentation_json:
                return {"success": False, "error": "presentation_json required"}
            
            output = output_path or "/tmp/archimedes_presentation.pdf"
            
            # Generate HTML from presentation JSON
            html = self._render_to_html(presentation_json)
            html_path = output.replace(".pdf", ".html")
            
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            
            # Use Puppeteer to export PDF
            try:
                from backend.tools.browser_tool import BrowserTool
                browser = BrowserTool()
                result = await browser.execute(
                    action="pdf",
                    url=f"file://{html_path}",
                    output_path=output,
                    format="A4",
                    landscape=True
                )
                if result.get("success"):
                    return {
                        "success": True,
                        "output": f"PDF exported: {output}",
                        "file_path": output
                    }
            except Exception as e:
                logger.warning(f"Puppeteer PDF failed: {e}")
            
            return {
                "success": True,
                "output": f"HTML presentation ready: {html_path}",
                "file_path": html_path,
                "note": "Install playwright for PDF export"
            }
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    def _render_to_html(self, presentation: Dict) -> str:
        """Render presentation JSON to standalone HTML."""
        slides_html = ""
        for i, slide in enumerate(presentation.get("slides", [])):
            slides_html += self._render_slide_html(slide, i)
        
        title = presentation.get("title", "Archimedes Presentation")
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
  * {{ font-family: 'Inter', sans-serif; box-sizing: border-box; }}
  .slide {{ width: 1280px; height: 720px; page-break-after: always; }}
  @media print {{ .slide {{ page-break-after: always; }} }}
</style>
</head>
<body class="bg-gray-900">
  <div class="archimedes-watermark text-xs text-gray-600 fixed top-2 right-2 z-50">
    Archimedes AI
  </div>
  {slides_html}
  <script>
    // Navigation
    let current = 0;
    const slides = document.querySelectorAll('.slide');
    slides.forEach((s, i) => s.style.display = i === 0 ? 'flex' : 'none');
    document.addEventListener('keydown', (e) => {{
      if (e.key === 'ArrowRight' && current < slides.length - 1) {{
        slides[current].style.display = 'none';
        current++;
        slides[current].style.display = 'flex';
      }}
      if (e.key === 'ArrowLeft' && current > 0) {{
        slides[current].style.display = 'none';
        current--;
        slides[current].style.display = 'flex';
      }}
    }});
  </script>
</body>
</html>"""
    
    def _render_slide_html(self, slide: Dict, index: int) -> str:
        """Render a single slide to HTML."""
        layout = slide.get("layout_type", "bullet_list")
        content = slide.get("content", {})
        config = slide.get("visual_config", {})
        
        bg_classes = {
            "dark_gradient": "bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900",
            "accent_purple": "bg-gradient-to-br from-purple-900 via-gray-900 to-purple-800",
            "accent_blue": "bg-gradient-to-br from-blue-900 via-gray-900 to-blue-800",
            "light_minimal": "bg-white",
            "code_dark": "bg-gray-950",
            "image_overlay": "bg-gray-900",
        }.get(config.get("background", "dark_gradient"), "bg-gradient-to-br from-gray-900 to-gray-800")
        
        title = content.get("title", "")
        subtitle = content.get("subtitle", "")
        body = content.get("body", [])
        
        title_html = f'<h1 class="text-5xl font-bold text-white mb-4">{title}</h1>' if title else ""
        subtitle_html = f'<p class="text-xl text-gray-300 mb-8">{subtitle}</p>' if subtitle else ""
        
        body_html = ""
        if body:
            items = "".join(
                f'<li class="flex items-start gap-3 text-lg text-gray-200 mb-3">'
                f'<span class="text-purple-400 mt-1">▸</span>'
                f'<span>{item.get("text", "")}</span></li>'
                for item in body
            )
            body_html = f'<ul class="space-y-2">{items}</ul>'
        
        # Slide number
        total = "?"
        num_html = (
            f'<div class="absolute bottom-6 right-8 text-gray-500 text-sm">'
            f'{index + 1}</div>'
        )
        
        # Archimedes logo watermark
        logo_html = (
            '<div class="absolute bottom-6 left-8 flex items-center gap-2">'
            '<div class="w-6 h-6 bg-purple-500 rounded-full opacity-70"></div>'
            '<span class="text-gray-500 text-xs">Archimedes AI</span></div>'
        )
        
        return (
            f'<div class="slide relative {bg_classes} '
            f'flex flex-col justify-center items-center p-16 overflow-hidden">'
            f'{logo_html}{num_html}'
            f'<div class="max-w-4xl w-full text-center">'
            f'{title_html}{subtitle_html}{body_html}'
            f'</div></div>\n'
        )
