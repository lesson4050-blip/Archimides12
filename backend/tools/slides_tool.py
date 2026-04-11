"""
SlidesTool v3 — Kimi/Gamma уровень качества.

Пайплайн:
1. Агент передаёт структуру слайдов с темой и ключевыми словами для фото
2. Для каждого слайда с фото — скачиваем реальное изображение через Unsplash/Pexels
3. Генерируем HTML с встроенными изображениями (base64) и богатыми CSS макетами  
4. Playwright (headless Chromium) рендерит каждый слайд как 1280×720 PNG
5. python-pptx собирает PNG в .pptx как изображения
6. Результат: визуально идентичен Kimi — реальные фото, градиенты, типографика
"""

import asyncio
import base64
import io
import json
import logging
import os
import re
import tempfile
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# ТЕМЫ
# ═══════════════════════════════════════════════════════

THEMES = {
    "dark": {
        "bg": "#0A0A0F",
        "bg2": "#13131F",
        "accent": "#7C6FFF",
        "accent2": "#B8B0FF",
        "text": "#FFFFFF",
        "text2": "#E2E8F0",
        "text3": "#94A3B8",
        "overlay": "rgba(10,10,15,0.72)",
        "card": "rgba(255,255,255,0.06)",
        "card_border": "rgba(124,111,255,0.25)",
        "grad1": "#7C6FFF",
        "grad2": "#B8B0FF",
        "font_h": "Syne",
        "font_b": "DM Sans",
    },
    "light": {
        "bg": "#F7F8FC",
        "bg2": "#EDEEF5",
        "accent": "#4F46E5",
        "accent2": "#818CF8",
        "text": "#0F0F1A",
        "text2": "#1E1E3A",
        "text3": "#6B7280",
        "overlay": "rgba(247,248,252,0.80)",
        "card": "rgba(79,70,229,0.07)",
        "card_border": "rgba(79,70,229,0.18)",
        "grad1": "#4F46E5",
        "grad2": "#818CF8",
        "font_h": "Playfair Display",
        "font_b": "Inter",
    },
    "navy": {
        "bg": "#020818",
        "bg2": "#060F2E",
        "accent": "#38BDF8",
        "accent2": "#7DD3FC",
        "text": "#FFFFFF",
        "text2": "#E0F2FE",
        "text3": "#7EC8E3",
        "overlay": "rgba(2,8,24,0.70)",
        "card": "rgba(56,189,248,0.08)",
        "card_border": "rgba(56,189,248,0.22)",
        "grad1": "#38BDF8",
        "grad2": "#7DD3FC",
        "font_h": "Space Grotesk",
        "font_b": "Outfit",
    },
    "aurora": {
        "bg": "#080414",
        "bg2": "#110820",
        "accent": "#F472B6",
        "accent2": "#FBCFE8",
        "text": "#FFFFFF",
        "text2": "#FAE8FF",
        "text3": "#C084FC",
        "overlay": "rgba(8,4,20,0.68)",
        "card": "rgba(244,114,182,0.09)",
        "card_border": "rgba(244,114,182,0.22)",
        "grad1": "#F472B6",
        "grad2": "#C084FC",
        "font_h": "Fraunces",
        "font_b": "Figtree",
    },
    "corporate": {
        "bg": "#F0F4FF",
        "bg2": "#E4EBFF",
        "accent": "#1D4ED8",
        "accent2": "#3B82F6",
        "text": "#0B1437",
        "text2": "#1E3A5F",
        "text3": "#4B6A9B",
        "overlay": "rgba(240,244,255,0.82)",
        "card": "rgba(29,78,216,0.07)",
        "card_border": "rgba(29,78,216,0.15)",
        "grad1": "#1D4ED8",
        "grad2": "#3B82F6",
        "font_h": "IBM Plex Sans",
        "font_b": "IBM Plex Sans",
    },
}


# ═══════════════════════════════════════════════════════
# ЗАГРУЗКА ФОТОГРАФИЙ
# ═══════════════════════════════════════════════════════

async def _fetch_photo_base64(keywords: str, executor, session_id: str) -> Optional[str]:
    """
    Скачать фото через Unsplash Source (без API ключа).
    Возвращает base64 строку или None если не удалось.
    """
    if not keywords:
        return None

    # Unsplash Source — редирект на реальное фото без API ключа
    query = keywords.replace(" ", "+").replace(",", "")
    url = f"https://source.unsplash.com/1280x720/?{query}"

    # Скачать через curl внутри контейнера (там есть интернет)
    tmp_path = f"/tmp/slide_photo_{abs(hash(keywords))}.jpg"
    cmd = f'curl -sL --max-time 15 -o {tmp_path} "{url}" && echo "OK" || echo "FAIL"'
    result = await executor.run_command(session_id, cmd, timeout=20)

    if not result.get("success"):
        return None

    # Проверить что файл скачался и не пустой
    check = await executor.run_command(
        session_id, f"wc -c < {tmp_path} 2>/dev/null || echo 0", timeout=5
    )
    out_str = check.get("output", "0")
    nums = [int(s) for s in out_str.split() if s.isdigit()]
    size = nums[-1] if nums else 0
    if size < 5000:  # меньше 5KB — плохой файл
        return None

    # Прочитать как base64
    b64_result = await executor.run_command(
        session_id, f"base64 -w 0 {tmp_path}", timeout=10
    )
    if not b64_result.get("success"):
        return None

    b64 = b64_result.get("output", "").strip()
    # Cleanup
    await executor.run_command(session_id, f"rm -f {tmp_path}", timeout=5)

    return b64 if b64 else None


async def _generate_ai_image_base64(prompt: str, executor, session_id: str) -> Optional[str]:
    """
    Генерировать AI-изображение через Pollinations.ai и вернуть base64.
    Используется как приоритетный источник изображений (вместо Unsplash).
    """
    if not prompt:
        return None

    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&model=flux&nologo=true"

    tmp_path = f"/tmp/ai_slide_{abs(hash(prompt)) % 999999}.png"
    cmd = f'curl -sL --max-time 30 -o {tmp_path} "{url}" && echo "OK" || echo "FAIL"'
    result = await executor.run_command(session_id, cmd, timeout=35)

    if not result.get("success"):
        logger.warning(f"AI image generation failed for prompt: {prompt[:50]}")
        return None

    # Проверить что файл скачался и не пустой
    check = await executor.run_command(
        session_id, f"wc -c < {tmp_path} 2>/dev/null || echo 0", timeout=5
    )
    out_str = check.get("output", "0")
    nums = [int(s) for s in out_str.split() if s.isdigit()]
    size = nums[-1] if nums else 0
    if size < 5000:  # меньше 5KB — плохой файл
        logger.warning(f"AI image too small ({size} bytes) for: {prompt[:50]}")
        return None

    # Прочитать как base64
    b64_result = await executor.run_command(
        session_id, f"base64 -w 0 {tmp_path}", timeout=15
    )
    if not b64_result.get("success"):
        return None

    b64 = b64_result.get("output", "").strip()
    # Cleanup
    await executor.run_command(session_id, f"rm -f {tmp_path}", timeout=5)

    logger.info(f"AI image generated successfully for: {prompt[:50]}")
    return b64 if b64 else None


# ═══════════════════════════════════════════════════════
# HTML ГЕНЕРАТОР
# ═══════════════════════════════════════════════════════

def _css(t: dict) -> str:
    fh = t["font_h"].replace(" ", "+")
    fb = t["font_b"].replace(" ", "+")
    fonts_url = (
        f"https://fonts.googleapis.com/css2?"
        f"family={fh}:wght@400;600;700;900&"
        f"family={fb}:wght@300;400;500;600&display=swap"
    )

    return f"""
@import url('{fonts_url}');

*{{margin:0;padding:0;box-sizing:border-box}}

body{{background:#000;font-family:'{t["font_b"]}',sans-serif;color:{t["text"]}}}

/* ── BASE SLIDE ── */
.slide{{
    width:1280px;height:720px;
    position:relative;overflow:hidden;
    display:flex;flex-direction:column;
    background:{t["bg"]};
}}

.slide-bg{{
    position:absolute;inset:0;
    background-size:cover;background-position:center;
    z-index:0;
}}

.slide-overlay{{
    position:absolute;inset:0;
    background:{t["overlay"]};
    z-index:1;
}}

.slide-content-wrap{{
    position:relative;z-index:2;
    width:100%;height:100%;
    display:flex;flex-direction:column;
}}

/* Декор: цветовые blobs */
.blob{{
    position:absolute;border-radius:50%;
    filter:blur(80px);pointer-events:none;z-index:0;
}}
.blob-1{{
    width:500px;height:500px;
    background:{t["grad1"]};opacity:0.08;
    top:-150px;right:-100px;
}}
.blob-2{{
    width:350px;height:350px;
    background:{t["grad2"]};opacity:0.05;
    bottom:-100px;left:-80px;
}}

/* Верхняя полоска */
.accent-stripe{{
    position:absolute;top:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,{t["grad1"]},{t["grad2"]});
    z-index:10;
}}

/* Бренд и номер */
.brand{{
    position:absolute;bottom:24px;left:48px;z-index:10;
    font-family:'{t["font_h"]}';font-size:11px;font-weight:700;
    letter-spacing:3px;text-transform:uppercase;
    background:linear-gradient(135deg,{t["grad1"]},{t["grad2"]});
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}}
.slide-num{{
    position:absolute;bottom:24px;right:48px;z-index:10;
    font-family:'{t["font_b"]}';font-size:11px;
    color:{t["text3"]};letter-spacing:2px;
}}

/* Разделитель */
.divider{{
    width:56px;height:3px;border-radius:2px;
    background:linear-gradient(90deg,{t["grad1"]},{t["grad2"]});
    margin:16px 0;
}}

/* ── TITLE SLIDE ── */
.title-wrap{{
    flex:1;display:flex;flex-direction:column;
    justify-content:center;padding:80px 96px;
}}
.title-eyebrow{{
    font-family:'{t["font_b"]}';font-size:12px;font-weight:600;
    letter-spacing:5px;text-transform:uppercase;
    color:{t["accent"]};margin-bottom:20px;
}}
.title-h1{{
    font-family:'{t["font_h"]}';font-size:74px;font-weight:900;
    line-height:1.0;color:{t["text"]};
    max-width:820px;margin-bottom:0;
}}
.title-sub{{
    font-family:'{t["font_b"]}';font-size:22px;font-weight:300;
    color:{t["text3"]};max-width:620px;line-height:1.5;margin-top:8px;
}}

/* ── CONTENT SLIDE (photo bg) ── */
.content-wrap{{
    flex:1;display:flex;flex-direction:column;
    padding:56px 72px 60px;
}}
.content-h2{{
    font-family:'{t["font_h"]}';font-size:44px;font-weight:700;
    line-height:1.1;color:{t["text"]};margin-bottom:4px;
}}
.content-body{{
    font-family:'{t["font_b"]}';font-size:19px;font-weight:300;
    color:{t["text2"]};line-height:1.6;margin-top:16px;margin-bottom:24px;
    max-width:780px;
}}

/* Bullet cards */
.bullets{{display:flex;flex-direction:column;gap:10px;margin-top:4px;}}
.bullet{{
    display:flex;align-items:center;gap:14px;
    background:{t["card"]};border:1px solid {t["card_border"]};
    border-radius:10px;padding:13px 18px;
    backdrop-filter:blur(8px);
}}
.bullet-dot{{
    width:7px;height:7px;border-radius:50%;flex-shrink:0;
    background:linear-gradient(135deg,{t["grad1"]},{t["grad2"]});
}}
.bullet-text{{
    font-family:'{t["font_b"]}';font-size:16px;font-weight:400;
    color:{t["text2"]};line-height:1.35;
}}

/* ── STAT SLIDE ── */
.stat-wrap{{
    flex:1;display:flex;flex-direction:column;
    padding:52px 72px;
}}
.stat-grid{{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:20px;margin-top:28px;flex:1;
}}
.stat-card{{
    background:{t["card"]};border:1px solid {t["card_border"]};
    border-radius:14px;padding:32px 24px;
    display:flex;flex-direction:column;align-items:center;
    text-align:center;backdrop-filter:blur(10px);
}}
.stat-value{{
    font-family:'{t["font_h"]}';font-size:58px;font-weight:900;
    line-height:1;
    background:linear-gradient(135deg,{t["grad1"]},{t["grad2"]});
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
    margin-bottom:10px;
}}
.stat-label{{
    font-family:'{t["font_b"]}';font-size:14px;font-weight:500;
    color:{t["text3"]};letter-spacing:0.3px;
}}

/* ── QUOTE SLIDE ── */
.quote-wrap{{
    flex:1;display:flex;flex-direction:column;
    justify-content:center;align-items:center;
    padding:80px 120px;text-align:center;
}}
.quote-mark{{
    font-family:'{t["font_h"]}';font-size:100px;font-weight:900;
    line-height:0.6;
    background:linear-gradient(135deg,{t["grad1"]},{t["grad2"]});
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
    opacity:0.6;margin-bottom:12px;
}}
.quote-text{{
    font-family:'{t["font_h"]}';font-size:34px;font-weight:400;
    font-style:italic;color:{t["text"]};
    line-height:1.45;max-width:900px;margin-bottom:28px;
}}
.quote-author{{
    font-family:'{t["font_b"]}';font-size:15px;font-weight:500;
    letter-spacing:3px;text-transform:uppercase;color:{t["accent"]};
}}

/* ── TWO-COL SLIDE ── */
.twocol-wrap{{
    flex:1;display:flex;flex-direction:column;
    padding:52px 72px;
}}
.twocol-grid{{
    display:grid;grid-template-columns:1fr 1fr;
    gap:24px;flex:1;margin-top:28px;
}}
.col-card{{
    background:{t["card"]};border:1px solid {t["card_border"]};
    border-radius:14px;padding:28px 28px;
    backdrop-filter:blur(10px);
}}
.col-card-title{{
    font-family:'{t["font_h"]}';font-size:22px;font-weight:700;
    color:{t["accent"]};margin-bottom:12px;
}}
.col-card-body{{
    font-family:'{t["font_b"]}';font-size:15px;font-weight:400;
    color:{t["text2"]};line-height:1.6;
}}

/* ── INFOGRAPHIC (text-heavy, no photo) ── */
.info-wrap{{
    flex:1;display:grid;
    grid-template-columns:1fr 1fr;
    gap:0;
}}
.info-left{{
    padding:56px 48px 56px 72px;
    border-right:1px solid {t["card_border"]};
    display:flex;flex-direction:column;justify-content:center;
}}
.info-right{{
    padding:56px 72px 56px 48px;
    display:flex;flex-direction:column;gap:14px;
    justify-content:center;
}}
.info-h2{{
    font-family:'{t["font_h"]}';font-size:42px;font-weight:700;
    line-height:1.1;color:{t["text"]};
}}
.info-body{{
    font-family:'{t["font_b"]}';font-size:17px;font-weight:300;
    color:{t["text2"]};line-height:1.65;margin-top:16px;
}}
.info-tag{{
    background:{t["card"]};border:1px solid {t["card_border"]};
    border-radius:8px;padding:10px 14px;
    font-family:'{t["font_b"]}';font-size:14px;color:{t["text2"]};
    display:flex;align-items:center;gap:10px;
}}
.info-tag-dot{{
    width:6px;height:6px;border-radius:50%;flex-shrink:0;
    background:linear-gradient(135deg,{t["grad1"]},{t["grad2"]});
}}

/* ── CTA SLIDE ── */
.cta-wrap{{
    flex:1;display:flex;flex-direction:column;
    justify-content:center;align-items:center;
    text-align:center;padding:80px;
}}
.cta-eyebrow{{
    font-family:'{t["font_b"]}';font-size:12px;font-weight:600;
    letter-spacing:5px;text-transform:uppercase;
    color:{t["accent"]};margin-bottom:20px;
}}
.cta-h1{{
    font-family:'{t["font_h"]}';font-size:62px;font-weight:900;
    line-height:1.1;color:{t["text"]};
    max-width:800px;margin-bottom:36px;
}}
.cta-btn{{
    display:inline-block;
    background:linear-gradient(135deg,{t["grad1"]},{t["grad2"]});
    color:#fff;font-family:'{t["font_b"]}';font-size:18px;font-weight:600;
    padding:18px 52px;border-radius:50px;letter-spacing:0.5px;
}}

/* ── IMAGE-LEFT SLIDE ── */
.imgleft-wrap{{
    flex:1;display:grid;
    grid-template-columns:1fr 1fr;
    gap:0;
}}
.imgleft-photo{{
    background-size:cover;background-position:center;
    border-right:1px solid {t["card_border"]};
    position:relative;
}}
.imgleft-photo-overlay{{
    position:absolute;inset:0;
    background:linear-gradient(90deg,transparent 60%,{t["bg"]} 100%);
}}
.imgleft-content{{
    padding:56px 48px 56px 42px;
    display:flex;flex-direction:column;justify-content:center;
}}
.imgleft-h2{{
    font-family:'{t["font_h"]}';font-size:38px;font-weight:700;
    line-height:1.1;color:{t["text"]};margin-bottom:6px;
}}
.imgleft-body{{
    font-family:'{t["font_b"]}';font-size:17px;font-weight:300;
    color:{t["text2"]};line-height:1.6;margin-top:14px;
}}

/* ── IMAGE-RIGHT SLIDE ── */
.imgright-wrap{{
    flex:1;display:grid;
    grid-template-columns:1fr 1fr;
    gap:0;
}}
.imgright-content{{
    padding:56px 42px 56px 72px;
    display:flex;flex-direction:column;justify-content:center;
}}
.imgright-h2{{
    font-family:'{t["font_h"]}';font-size:38px;font-weight:700;
    line-height:1.1;color:{t["text"]};margin-bottom:6px;
}}
.imgright-body{{
    font-family:'{t["font_b"]}';font-size:17px;font-weight:300;
    color:{t["text2"]};line-height:1.6;margin-top:14px;
}}
.imgright-photo{{
    background-size:cover;background-position:center;
    border-left:1px solid {t["card_border"]};
    position:relative;
}}
.imgright-photo-overlay{{
    position:absolute;inset:0;
    background:linear-gradient(270deg,transparent 60%,{t["bg"]} 100%);
}}
"""


def _bg_style(photo_b64: Optional[str]) -> str:
    """Стиль фона: фото или пустой"""
    if photo_b64:
        return f'style="background-image:url(\'data:image/jpeg;base64,{photo_b64}\')"'
    return ""


def _slide_html(idx: int, total: int, s: dict, t: dict,
                photo_b64: Optional[str]) -> str:
    """Генерировать HTML одного слайда."""
    layout = s.get("layout", "content")
    title = s.get("title", "")
    num_str = f"{idx:02d} / {total:02d}"
    has_photo = bool(photo_b64)

    # Фоновые слои
    bg_el = ""
    overlay_el = ""
    if has_photo:
        bg_el = f'<div class="slide-bg" {_bg_style(photo_b64)}></div>'
        overlay_el = '<div class="slide-overlay"></div>'

    blobs = "" if has_photo else '<div class="blob blob-1"></div><div class="blob blob-2"></div>'

    # ── Контент по типу слайда ──

    if layout == "title":
        subtitle = s.get("subtitle", "")
        eyebrow = s.get("eyebrow", "Presentation")
        inner = f"""
        <div class="title-wrap">
            <div class="title-eyebrow">{eyebrow}</div>
            <h1 class="title-h1">{title}</h1>
            <div class="divider"></div>
            <p class="title-sub">{subtitle}</p>
        </div>"""

    elif layout == "stat":
        stats = s.get("stats", [])
        body = s.get("content", "")
        stat_cards = "".join([
            f'<div class="stat-card">'
            f'<div class="stat-value">{st.get("value","")}</div>'
            f'<div class="stat-label">{st.get("label","")}</div>'
            f'</div>'
            for st in stats[:4]
        ])
        inner = f"""
        <div class="stat-wrap">
            <h2 class="content-h2">{title}</h2>
            <div class="divider"></div>
            {f'<p class="content-body">{body}</p>' if body else ''}
            <div class="stat-grid">{stat_cards}</div>
        </div>"""

    elif layout == "quote":
        quote = s.get("quote", "")
        author = s.get("quote_author", "")
        inner = f"""
        <div class="quote-wrap">
            <div class="quote-mark">"</div>
            <p class="quote-text">{quote}</p>
            {f'<div class="quote-author">— {author}</div>' if author else ''}
        </div>"""

    elif layout == "two_col":
        cl = s.get("col_left", {})
        cr = s.get("col_right", {})
        inner = f"""
        <div class="twocol-wrap">
            <h2 class="content-h2">{title}</h2>
            <div class="divider"></div>
            <div class="twocol-grid">
                <div class="col-card">
                    <div class="col-card-title">{cl.get("title","")}</div>
                    <div class="col-card-body">{cl.get("content","")}</div>
                </div>
                <div class="col-card">
                    <div class="col-card-title">{cr.get("title","")}</div>
                    <div class="col-card-body">{cr.get("content","")}</div>
                </div>
            </div>
        </div>"""

    elif layout == "infographic":
        body = s.get("content", "")
        tags = s.get("tags", [])
        tag_html = "".join([
            f'<div class="info-tag"><div class="info-tag-dot"></div>{tag}</div>'
            for tag in tags[:8]
        ])
        inner = f"""
        <div class="info-wrap">
            <div class="info-left">
                <h2 class="info-h2">{title}</h2>
                <div class="divider"></div>
                <p class="info-body">{body}</p>
            </div>
            <div class="info-right">{tag_html}</div>
        </div>"""

    elif layout == "image_left":
        body = s.get("content", "")
        bullets = s.get("bullet_points", [])
        bullet_html = ""
        if bullets:
            cards = "".join([
                f'<div class="bullet">'
                f'<div class="bullet-dot"></div>'
                f'<div class="bullet-text">{b}</div>'
                f'</div>'
                for b in bullets[:4]
            ])
            bullet_html = f'<div class="bullets">{cards}</div>'
        # Для image_left фото встраивается как inline-блок слева
        photo_style = ""
        if has_photo:
            photo_style = f'style="background-image:url(\'data:image/jpeg;base64,{photo_b64}\')"'
            # Не использовать фоновый фото-слой, фото внутри сетки
            bg_el = ""
            overlay_el = ""
        inner = f"""
        <div class="imgleft-wrap">
            <div class="imgleft-photo" {photo_style}>
                <div class="imgleft-photo-overlay"></div>
            </div>
            <div class="imgleft-content">
                <h2 class="imgleft-h2">{title}</h2>
                <div class="divider"></div>
                {f'<p class="imgleft-body">{body}</p>' if body else ''}
                {bullet_html}
            </div>
        </div>"""

    elif layout == "image_right":
        body = s.get("content", "")
        bullets = s.get("bullet_points", [])
        bullet_html = ""
        if bullets:
            cards = "".join([
                f'<div class="bullet">'
                f'<div class="bullet-dot"></div>'
                f'<div class="bullet-text">{b}</div>'
                f'</div>'
                for b in bullets[:4]
            ])
            bullet_html = f'<div class="bullets">{cards}</div>'
        photo_style = ""
        if has_photo:
            photo_style = f'style="background-image:url(\'data:image/jpeg;base64,{photo_b64}\')"'
            bg_el = ""
            overlay_el = ""
        inner = f"""
        <div class="imgright-wrap">
            <div class="imgright-content">
                <h2 class="imgright-h2">{title}</h2>
                <div class="divider"></div>
                {f'<p class="imgright-body">{body}</p>' if body else ''}
                {bullet_html}
            </div>
            <div class="imgright-photo" {photo_style}>
                <div class="imgright-photo-overlay"></div>
            </div>
        </div>"""

    elif layout == "cta":
        cta_text = s.get("cta", "Get Started")
        eyebrow = s.get("eyebrow", "What's Next")
        inner = f"""
        <div class="cta-wrap">
            <div class="cta-eyebrow">{eyebrow}</div>
            <h1 class="cta-h1">{title}</h1>
            <div class="cta-btn">{cta_text}</div>
        </div>"""

    else:  # content (default)
        body = s.get("content", "")
        bullets = s.get("bullet_points", [])
        bullet_html = ""
        if bullets:
            cards = "".join([
                f'<div class="bullet">'
                f'<div class="bullet-dot"></div>'
                f'<div class="bullet-text">{b}</div>'
                f'</div>'
                for b in bullets[:6]
            ])
            bullet_html = f'<div class="bullets">{cards}</div>'
        inner = f"""
        <div class="content-wrap">
            <h2 class="content-h2">{title}</h2>
            <div class="divider"></div>
            {f'<p class="content-body">{body}</p>' if body else ''}
            {bullet_html}
        </div>"""

    return f"""
<div class="slide" id="slide-{idx}">
    {bg_el}
    {overlay_el}
    {blobs}
    <div class="accent-stripe"></div>
    <div class="slide-content-wrap">{inner}</div>
    <div class="brand">Archimedes</div>
    <div class="slide-num">{num_str}</div>
</div>"""


def _build_html(title: str, slides_data: list, t: dict,
                photos: dict) -> str:
    """Собрать полный HTML документ со всеми слайдами."""
    total = len(slides_data) + 1

    # Title slide
    title_slide_data = {
        "layout": "title",
        "title": title,
        "subtitle": "Generated by Archimedes",
        "eyebrow": "Presentation",
        "photo_keywords": slides_data[0].get("photo_keywords", "") if slides_data else "",
    }
    title_photo = photos.get(0)

    all_slides = [_slide_html(1, total, title_slide_data, t, title_photo)]

    for i, s in enumerate(slides_data, 1):
        photo = photos.get(i)
        all_slides.append(_slide_html(i + 1, total, s, t, photo))

    slides_html = "\n".join(all_slides)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1280">
<style>
{_css(t)}
</style>
</head>
<body>
{slides_html}
</body>
</html>"""


# ═══════════════════════════════════════════════════════
# PLAYWRIGHT СКРИПТ (запускается внутри контейнера)
# ═══════════════════════════════════════════════════════

PLAYWRIGHT_SCRIPT = r"""
import asyncio, sys, os, json
from playwright.async_api import async_playwright

async def run(html_path, out_dir, n):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox','--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--font-render-hinting=none',
            ]
        )
        ctx = await browser.new_context(viewport={"width":1280,"height":720})
        page = await ctx.new_page()
        await page.goto(f"file://{html_path}", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)  # ждём шрифты

        shots = []
        for i in range(1, n+1):
            el = await page.query_selector(f"#slide-{i}")
            if el:
                path = os.path.join(out_dir, f"slide_{i:03d}.png")
                await el.screenshot(path=path, type="png")
                shots.append(path)

        await browser.close()
        print(json.dumps({"ok": True, "count": len(shots)}))

html_path, out_dir, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
asyncio.run(run(html_path, out_dir, n))
"""


# ═══════════════════════════════════════════════════════
# SLIDES TOOL
# ═══════════════════════════════════════════════════════

class SlidesTool:

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "slides",
                "description": (
                    "Create Kimi/Gamma-level PowerPoint presentations. "
                    "Uses real Chromium rendering with AI-generated images (Pollinations.ai) "
                    "and/or real photos from Unsplash. "
                    "ALWAYS use theme='dark' unless user says otherwise. "
                    "Use image_prompt for AI-generated imagery (PRIORITY) or photo_keywords for Unsplash photos. "
                    "Alternate visual and infographic slides for best rhythm. "
                    "Layouts: content, stat, quote, two_col, infographic, image_left, image_right, cta, title."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "filename": {"type": "string", "default": "presentation.pptx"},
                        "theme": {
                            "type": "string",
                            "enum": ["dark", "light", "navy", "aurora", "corporate"],
                            "default": "dark"
                        },
                        "slides": {
                            "type": "array",
                            "description": "Slide list. DO NOT include title slide — it's auto-generated.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "layout": {
                                        "type": "string",
                                        "enum": ["content","stat","quote","two_col","infographic","image_left","image_right","cta"],
                                        "default": "content",
                                        "description": (
                                            "content: title+body+bullets (6 max). "
                                            "stat: big numbers grid, needs stats:[{value,label}]. "
                                            "quote: full-slide quote+author. "
                                            "two_col: side-by-side cards, needs col_left/col_right. "
                                            "infographic: left=text, right=tags list — use for NO-photo slides. "
                                            "image_left: image takes left 50%, text+bullets on right — Gamma-style split. "
                                            "image_right: text+bullets on left, image takes right 50% — Gamma-style split. "
                                            "cta: final call-to-action."
                                        )
                                    },
                                    "image_prompt": {
                                        "type": "string",
                                        "description": (
                                            "AI image generation prompt (Pollinations.ai). PRIORITY over photo_keywords. "
                                            "Use for custom illustrations when you want precise control. "
                                            "English only. Be very detailed about style, colors, composition. "
                                            "Example: 'A minimalist illustration of a neural network, "
                                            "glowing blue and purple, abstract, high-tech, dark background'. "
                                            "Best for: image_left, image_right, content, stat, cta layouts."
                                        )
                                    },
                                    "photo_keywords": {
                                        "type": "string",
                                        "description": (
                                            "Keywords for Unsplash photo background. Fallback if image_prompt is not set. "
                                            "Use for: content, stat, quote, two_col, cta slides. "
                                            "SKIP for infographic layout (it looks better without photo). "
                                            "Examples: 'artificial intelligence network', "
                                            "'space galaxy nasa', 'city technology future', "
                                            "'abstract data visualization'"
                                        )
                                    },
                                    "content": {"type": "string"},
                                    "bullet_points": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Max 6 bullets. Each under 12 words."
                                    },
                                    "stats": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "value": {"type": "string"},
                                                "label": {"type": "string"}
                                            }
                                        }
                                    },
                                    "quote": {"type": "string"},
                                    "quote_author": {"type": "string"},
                                    "col_left": {
                                        "type": "object",
                                        "properties": {
                                            "title": {"type": "string"},
                                            "content": {"type": "string"}
                                        }
                                    },
                                    "col_right": {
                                        "type": "object",
                                        "properties": {
                                            "title": {"type": "string"},
                                            "content": {"type": "string"}
                                        }
                                    },
                                    "tags": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "For infographic layout. List of tags/facts."
                                    },
                                    "eyebrow": {"type": "string"},
                                    "cta": {"type": "string"}
                                },
                                "required": ["title", "layout"]
                            }
                        }
                    },
                    "required": ["title", "slides"]
                }
            }
        }

    async def execute(
        self,
        session_id: str,
        title: str,
        slides: list,
        filename: str = "presentation.pptx",
        theme: str = "dark",
        **kwargs
    ) -> Dict[str, Any]:

        try:
            from backend.sandbox.singleton import sandbox_manager
            executor = sandbox_manager.executor
            t = THEMES.get(theme, THEMES["dark"])
            total_slides = len(slides) + 1  # +1 title

            # ── 1. Скачать фотографии / сгенерировать AI-изображения параллельно ──
            photo_tasks = {}
            photo_sources = {}  # Трекинг: 'ai' или 'unsplash'

            # Фото для title slide (берём image_prompt или keywords первого слайда)
            title_ai = slides[0].get("image_prompt", "") if slides else ""
            title_kw = slides[0].get("photo_keywords", "") if slides else ""
            if title_ai:
                photo_tasks[0] = _generate_ai_image_base64(title_ai, executor, session_id)
                photo_sources[0] = "ai"
            elif title_kw:
                photo_tasks[0] = _fetch_photo_base64(title_kw, executor, session_id)
                photo_sources[0] = "unsplash"

            for i, s in enumerate(slides, 1):
                layout = s.get("layout", "content")
                ai_prompt = s.get("image_prompt", "")
                kw = s.get("photo_keywords", "")

                if layout == "infographic":
                    continue  # infographic intentionally has no photo

                if ai_prompt:
                    photo_tasks[i] = _generate_ai_image_base64(ai_prompt, executor, session_id)
                    photo_sources[i] = "ai"
                elif kw:
                    photo_tasks[i] = _fetch_photo_base64(kw, executor, session_id)
                    photo_sources[i] = "unsplash"

            photos: Dict[int, Optional[str]] = {}
            if photo_tasks:
                results = await asyncio.gather(
                    *photo_tasks.values(), return_exceptions=True
                )
                for (idx, _), res in zip(photo_tasks.items(), results):
                    photos[idx] = res if isinstance(res, str) else None

            # Fallback: если AI-изображение не загрузилось, попробовать Unsplash
            for idx, source in photo_sources.items():
                if source == "ai" and photos.get(idx) is None:
                    # AI failed — try Unsplash fallback
                    slide_data = slides[idx - 1] if idx > 0 else (slides[0] if slides else {})
                    fallback_kw = slide_data.get("photo_keywords", "")
                    if fallback_kw:
                        logger.info(f"AI image failed for slide {idx}, trying Unsplash fallback")
                        photos[idx] = await _fetch_photo_base64(fallback_kw, executor, session_id)

            ai_loaded = sum(1 for idx, v in photos.items() if v and photo_sources.get(idx) == "ai")
            unsplash_loaded = sum(1 for idx, v in photos.items() if v and photo_sources.get(idx) == "unsplash")
            total_loaded = sum(1 for v in photos.values() if v)
            logger.info(f"Images loaded: {total_loaded}/{len(photo_tasks)} (AI: {ai_loaded}, Unsplash: {unsplash_loaded})")

            # ── 2. Генерировать HTML ──
            html = _build_html(title, slides, t, photos)
            html_b64 = base64.b64encode(html.encode("utf-8")).decode()

            html_path = "/home/ubuntu/workspace/_slides.html"
            shots_dir = "/home/ubuntu/workspace/_slides_shots"
            script_path = "/home/ubuntu/workspace/_slides_pw.py"

            # Записать HTML
            write_html = f"echo '{html_b64}' | base64 -d > {html_path}"
            r = await executor.run_command(session_id, write_html, timeout=30)
            if not r.get("success"):
                return {"success": False, "error": f"HTML write failed: {r.get('error')}"}

            # Создать папку
            await executor.run_command(
                session_id,
                f"mkdir -p {shots_dir} && rm -f {shots_dir}/*.png",
                timeout=10
            )

            # Записать Playwright скрипт
            script_b64 = base64.b64encode(PLAYWRIGHT_SCRIPT.encode()).decode()
            write_script = f"echo '{script_b64}' | base64 -d > {script_path}"
            await executor.run_command(session_id, write_script, timeout=15)

            # ── 3. Запустить Playwright ──
            pw_cmd = (
                f"python3 {script_path} "
                f"{html_path} {shots_dir} {total_slides} 2>&1"
            )
            pw = await executor.run_command(session_id, pw_cmd, timeout=180)
            pw_out = pw.get("output", "")

            if not pw.get("success"):
                return {
                    "success": False,
                    "error": f"Playwright error: {pw_out[-500:]}"
                }

            # ── 4. Проверить скриншоты ──
            check = await executor.run_command(
                session_id,
                f"ls {shots_dir}/*.png 2>/dev/null | wc -l",
                timeout=10
            )
            out_str = check.get("output", "0")
            nums = [int(s) for s in out_str.split() if s.isdigit()]
            shots_count = nums[-1] if nums else 0
            if shots_count == 0:
                return {
                    "success": False,
                    "error": f"No screenshots. Playwright output: {pw_out[-300:]}"
                }

            # ── 5. Собрать PPTX ──
            from pptx import Presentation as Pptx
            from pptx.util import Inches

            prs = Pptx()
            prs.slide_width = Inches(13.33)
            prs.slide_height = Inches(7.5)

            for i in range(1, total_slides + 1):
                shot = f"{shots_dir}/slide_{i:03d}.png"
                read = await executor.run_command(
                    session_id, f"base64 -w 0 {shot}", timeout=30
                )
                if not read.get("success"):
                    continue

                img_data = base64.b64decode(read["output"].strip())
                blank = prs.slide_layouts[6]
                slide = prs.slides.add_slide(blank)
                slide.shapes.add_picture(
                    io.BytesIO(img_data),
                    left=0, top=0,
                    width=prs.slide_width,
                    height=prs.slide_height
                )

            # ── 6. Сохранить PPTX в контейнер ──
            buf = io.BytesIO()
            prs.save(buf)
            buf.seek(0)
            pptx_b64 = base64.b64encode(buf.read()).decode()

            remote_path = f"/home/ubuntu/workspace/{filename}"
            save = await executor.run_command(
                session_id,
                f"echo '{pptx_b64}' | base64 -d > {remote_path}",
                timeout=60
            )
            if not save.get("success"):
                return {"success": False, "error": f"Save failed: {save.get('error')}"}

            # Cleanup
            await executor.run_command(
                session_id,
                f"rm -rf {shots_dir} {script_path} {html_path}",
                timeout=10
            )

            return {
                "success": True,
                "output": (
                    f"✓ '{filename}' — {total_slides} slides, theme: {theme}, "
                    f"images: {total_loaded}/{len(photo_tasks)} "
                    f"(AI: {ai_loaded}, Unsplash: {unsplash_loaded}). "
                    f"Rendered via Chromium — Gamma/Kimi-level quality."
                ),
                "path": remote_path
            }

        except Exception as e:
            logger.error(f"SlidesTool error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
