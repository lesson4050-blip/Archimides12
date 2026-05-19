import asyncio
import os
import sys
import json
from pathlib import Path

# Reconfigure stdout for UTF-8 in Windows environments
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass  # In some environments reconfigure might not exist or be disabled

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env
env_path = project_root / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

from backend.agent.tools.canvas_engine import CanvasEngine
from backend.models.model_router import ModelRouter

async def simulate_academic_presentation():
    print("=" * 60)
    print("SIMULATING COMPLEX SCIENTIFIC PRESENTATION GENERATION")
    print("=" * 60)
    
    router = ModelRouter()
    engine = CanvasEngine(router=router)
    
    topic = "Теория струн, М-теория и проблемы квантовой гравитации"
    audience = "Физики-теоретики и исследователи"
    slide_count = 6
    key_points = [
        "Объединение квантовой механики и общей теории относительности",
        "10-мерные суперструны и 11-мерная супергравитация",
        "Дуальности струн и возникновение М-теории (Эдвард Виттен, 1995)",
        "Голографический принцип и AdS/CFT соответствие",
        "Проблемы экспериментальной верификации на масштабах Планка"
    ]
    
    print(f"Topic: {topic}")
    print(f"Audience: {audience}")
    print("Generating slides using updated CanvasEngine...")
    
    result = await engine.execute(
        action="generate",
        topic=topic,
        audience=audience,
        slide_count=slide_count,
        key_points=key_points
    )
    
    if not result.get("success"):
        print(f"FAIL: {result.get('error')}")
        if "raw" in result:
            print("Raw response from LLM:")
            print(result["raw"])
        return False

    presentation = result["presentation"]
    print("SUCCESS! Generated presentation JSON structure.")
    print(f"Title: {presentation.get('title')}")
    print(f"Subtitle: {presentation.get('subtitle')}")
    
    slides = presentation.get("slides", [])
    print(f"Number of slides generated: {len(slides)}")
    
    # Audit quality of bullets and content density
    issues = []
    print("\n--- Slide Quality Audit ---")
    for i, slide in enumerate(slides):
        layout = slide.get("layout_type")
        content = slide.get("content", {})
        title = content.get("title", "")
        print(f"Slide {i+1} [{layout}]: '{title}'")
        
        # Check language
        # Quick Cyrillic check
        is_cyrillic = bool(any('а' <= char <= 'я' or 'А' <= char <= 'Я' for char in title))
        if not is_cyrillic and i > 0:
            issues.append(f"Slide {i+1} title is not in Russian: '{title}'")
            
        # Bullet points audit
        body_items = content.get("body", [])
        if layout in ["bullet_list", "split_content", "timeline", "comparison"] and body_items:
            for b_idx, item in enumerate(body_items):
                text = item.get("text", "")
                word_count = len(text.split())
                print(f"  Bullet {b_idx+1} ({word_count} words): '{text[:60]}...'")
                
                # Check for "Key: Explanation" format
                if ":" not in text:
                    issues.append(f"Slide {i+1} Bullet {b_idx+1} does not follow 'Key Concept: Explanation' format")
                
                # Check word count
                if word_count < 10:
                    issues.append(f"Slide {i+1} Bullet {b_idx+1} is too short ({word_count} words): '{text}'")
                    
        # Metric audit
        metrics = content.get("metrics", [])
        if layout == "data_grid" and metrics:
            for m_idx, m in enumerate(metrics):
                val = m.get("value", "")
                lbl = m.get("label", "")
                print(f"  Metric {m_idx+1}: {val} - {lbl}")
                if "point" in lbl.lower() or "metric" in lbl.lower() or not lbl:
                    issues.append(f"Slide {i+1} Metric {m_idx+1} has generic or empty label")

    print("\n" + "=" * 60)
    if issues:
        print("AUDIT ENCOUNTERED THE FOLLOWING QUALITY ISSUES:")
        for issue in issues:
            print(f"- [WARNING] {issue}")
    else:
        print("CONGRATULATIONS! ALL Slide Content Quality checks passed successfully!")
    print("=" * 60)
    
    # Save the output presentation JSON for inspection
    output_file = project_root / "tests" / "complex_presentation_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(presentation, f, indent=2, ensure_ascii=False)
    print(f"Saved generated presentation to {output_file}")
    return True

if __name__ == "__main__":
    asyncio.run(simulate_academic_presentation())
