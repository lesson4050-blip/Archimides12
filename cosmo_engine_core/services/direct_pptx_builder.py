"""
DirectPptxBuilder — Premium-quality PPTX generator using python-pptx.

Reproduces the editorial design patterns from the Kimi reference presentation:
- Full-bleed title images with gradient overlays
- 2-column TOC with numbered cards and accent bars
- Content slides with section numbers, serif titles, accent lines, bullet grids
- Statistics footers, image captions, and consistent spacing

All layout math is based on the 13.33" × 7.50" widescreen canvas.
"""
import asyncio
import datetime
import os
import re
import tempfile
from typing import List, Optional

import aiohttp
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

from utils.download_helpers import download_files
from services.temp_file_service import TEMP_FILE_SERVICE
from services.pptx_themes import Theme, THEMES, guess_theme

# ── Slide canvas (widescreen, matches Kimi reference) ──────────
SLIDE_WIDTH = Emu(12192000)   # 13.33 inches
SLIDE_HEIGHT = Emu(6858000)   # 7.50 inches
MARGIN = Inches(0.42)         # ~0.42" margin on all sides
CONTENT_W = Inches(12.50)     # full content width
BLANK_LAYOUT = 6


class DirectPptxBuilder:
    """Builds a premium PPTX directly from slide JSON data."""

    def __init__(self, theme: Optional[Theme] = None):
        self.theme = theme or THEMES["editorial"]
        self.prs = Presentation()
        self.prs.slide_width = SLIDE_WIDTH
        self.prs.slide_height = SLIDE_HEIGHT
        self._temp_dir = TEMP_FILE_SERVICE.create_temp_dir()

    # ================================================================
    #  PUBLIC API
    # ================================================================
    async def build(self, slides_data: list, title: str = "") -> None:
        """Build all slides from structured JSON slide data."""
        for idx, slide_data in enumerate(slides_data):
            content = slide_data.get("content", slide_data)
            slide_type = slide_data.get("slideType", slide_data.get("type", ""))
            speaker_note = slide_data.get("speakerNotes", "")

            if idx == 0 or slide_type in ("intro", "title", "introSlide"):
                await self._build_title_slide(content, speaker_note, title)
            elif slide_type in ("tableOfContents", "toc"):
                self._build_toc_slide(content, speaker_note)
            elif slide_type in ("conclusion", "thankyou", "end"):
                self._build_conclusion_slide(content, speaker_note)
            else:
                await self._build_content_slide(content, speaker_note, idx)

    def save(self, path: str) -> str:
        self.prs.save(path)
        return path

    # ================================================================
    #  TEXT HELPERS
    # ================================================================
    @staticmethod
    def _clean(text) -> str:
        """Strip LLM artifacts from text."""
        if not text:
            return ""
        text = str(text)
        text = re.sub(r'\{[^}]*\}', '', text)
        text = re.sub(r'\[Speaker Notes?\]:?.*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Image:.*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'icon:.*', '', text, flags=re.IGNORECASE)
        return text.strip()

    def _add_text(
        self, slide: Slide, text: str,
        left, top, width, height,
        font_name: str = None,
        font_size=Pt(14),
        font_color: RGBColor = None,
        bold: bool = False,
        italic: bool = False,
        alignment=PP_ALIGN.LEFT,
    ):
        """Add a clean, styled text box."""
        font_name = font_name or self.theme.font_body
        font_color = font_color or self.theme.body
        text = self._clean(text)
        if not text:
            return None

        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = True
        tf.margin_left = Pt(0)
        tf.margin_right = Pt(0)
        tf.margin_top = Pt(0)
        tf.margin_bottom = Pt(0)

        p = tf.paragraphs[0]
        p.alignment = alignment
        p.space_before = Pt(0)
        p.space_after = Pt(0)

        run = p.add_run()
        run.text = text
        run.font.name = font_name
        run.font.size = font_size
        run.font.color.rgb = font_color
        run.font.bold = bold
        run.font.italic = italic
        return txBox

    def _add_accent_bar(self, slide: Slide, left, top, width, height=Inches(0.04), color=None):
        """Draw a thin accent rectangle (horizontal or vertical bar)."""
        color = color or self.theme.accent
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
        bar.fill.solid()
        bar.fill.fore_color.rgb = color
        bar.line.fill.background()
        return bar

    def _add_card(self, slide: Slide, left, top, width, height, color=None):
        """Draw a rounded-rectangle card background."""
        color = color or self.theme.card_bg
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = color
        card.line.fill.background()
        return card

    def _set_bg(self, slide: Slide, color: RGBColor = None):
        color = color or self.theme.bg
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = color

    def _blank_slide(self, speaker_note: str = "") -> Slide:
        layout = self.prs.slide_layouts[BLANK_LAYOUT]
        slide = self.prs.slides.add_slide(layout)
        if speaker_note:
            clean = self._clean(speaker_note)
            if clean:
                slide.notes_slide.notes_text_frame.text = clean
        return slide

    # ================================================================
    #  IMAGE HELPERS
    # ================================================================
    def _extract_image_url(self, content: dict) -> Optional[str]:
        """Extract image URL from slide content."""
        if isinstance(content, dict):
            for key in ("imageUrl", "image_url", "image", "backgroundImage"):
                url = content.get(key)
                if url and isinstance(url, str) and url.startswith("http"):
                    return url
            # Check nested
            for val in content.values():
                if isinstance(val, dict):
                    url = self._extract_image_url(val)
                    if url:
                        return url
        return None

    async def _download_image(self, url: str) -> Optional[str]:
        """Download image to temp dir, return local path."""
        try:
            result = await download_files([url], self._temp_dir)
            if result:
                return result[0]
        except Exception:
            pass
        return None

    # ================================================================
    #  TITLE SLIDE
    # ================================================================
    async def _build_title_slide(self, content: dict, speaker_note: str, fallback_title: str = ""):
        slide = self._blank_slide(speaker_note)
        self._set_bg(slide)

        title = content.get("title", fallback_title) or fallback_title
        subtitle = content.get("subtitle", content.get("description", ""))
        eyebrow = content.get("eyebrow", "")

        # Try to place full-bleed background image
        image_url = self._extract_image_url(content)
        img_placed = False
        if image_url:
            img_path = await self._download_image(image_url)
            if img_path:
                try:
                    slide.shapes.add_picture(img_path, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
                    img_placed = True
                except Exception:
                    pass

        # Overlay: solid color block on the right side for text (like Kimi)
        if img_placed:
            overlay_left = Inches(6.0)
            overlay = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, overlay_left, 0, SLIDE_WIDTH - overlay_left, SLIDE_HEIGHT
            )
            overlay.fill.solid()
            overlay.fill.fore_color.rgb = self.theme.bg
            overlay.line.fill.background()
            # Make overlay semi-transparent via XML
            try:
                solidFill = overlay.fill._fill
                srgb = solidFill.find(qn('a:solidFill')).find(qn('a:srgbClr'))
                if srgb is not None:
                    alpha = srgb.makeelement(qn('a:alpha'), {'val': '85000'})  # 85% opaque
                    srgb.append(alpha)
            except Exception:
                pass
            text_left = Inches(6.5)
            text_w = Inches(6.0)
        else:
            text_left = Inches(3.5)
            text_w = Inches(6.0)

        # Eyebrow
        if eyebrow:
            self._add_text(
                slide, eyebrow.upper(),
                left=text_left, top=Inches(1.2),
                width=text_w, height=Inches(0.3),
                font_size=Pt(13), font_color=self.theme.accent, bold=True
            )

        # Title (large serif)
        self._add_text(
            slide, title,
            left=text_left, top=Inches(2.0),
            width=text_w, height=Inches(1.2),
            font_name=self.theme.font_heading, font_size=Pt(48),
            font_color=self.theme.heading, bold=True,
            alignment=PP_ALIGN.LEFT
        )

        # Accent line
        self._add_accent_bar(slide, text_left + Inches(1.5), Inches(3.4), Inches(1.3))

        # Subtitle
        if subtitle:
            self._add_text(
                slide, subtitle,
                left=text_left, top=Inches(3.8),
                width=text_w, height=Inches(0.5),
                font_size=Pt(20), font_color=self.theme.muted
            )

        # Date
        date_str = datetime.datetime.now().strftime("%Y")
        self._add_text(
            slide, date_str,
            left=text_left, top=Inches(6.0),
            width=Inches(1.0), height=Inches(0.25),
            font_size=Pt(12), font_color=self.theme.muted
        )

    # ================================================================
    #  TABLE OF CONTENTS
    # ================================================================
    def _build_toc_slide(self, content: dict, speaker_note: str):
        slide = self._blank_slide(speaker_note)
        self._set_bg(slide)

        # Eyebrow
        self._add_text(
            slide, "СТРУКТУРА ПРЕЗЕНТАЦИИ",
            left=MARGIN, top=MARGIN,
            width=CONTENT_W, height=Inches(0.21),
            font_size=Pt(10), font_color=self.theme.accent, bold=True
        )

        # Title
        self._add_text(
            slide, "Содержание",
            left=MARGIN, top=Inches(0.71),
            width=CONTENT_W, height=Inches(0.50),
            font_name=self.theme.font_heading, font_size=Pt(36),
            font_color=self.theme.heading, bold=True
        )

        # Accent line
        self._add_accent_bar(slide, MARGIN, Inches(1.38), Inches(1.0))

        # Sections
        sections = content.get("sections", content.get("bulletPoints", content.get("items", [])))
        if not sections:
            return

        # 2-column layout, like Kimi: col_w ~5.98", gap between cols
        col_w = Inches(5.98)
        col_gap = Inches(0.50)
        card_h = Inches(1.33)
        row_gap = Inches(0.17)
        start_y = Inches(1.75)

        for idx, section in enumerate(sections[:8]):
            col = idx % 2
            row = idx // 2
            x = MARGIN + col * (col_w + col_gap)
            y = start_y + row * (card_h + row_gap)

            # Card background
            self._add_card(slide, x, y, col_w, card_h)

            # Left accent bar (vertical)
            self._add_accent_bar(slide, x, y, Inches(0.04), card_h)

            # Section number
            num = f"{idx + 1:02d}"
            self._add_text(
                slide, num,
                left=x + Inches(0.25), top=y + Inches(0.20),
                width=Inches(0.62), height=Inches(0.42),
                font_size=Pt(27), font_color=self.theme.accent, bold=True
            )

            # Section title
            sec_title = section.get("title", f"Section {idx + 1}") if isinstance(section, dict) else str(section)
            self._add_text(
                slide, sec_title,
                left=x + Inches(1.0), top=y + Inches(0.20),
                width=Inches(4.6), height=Inches(0.30),
                font_size=Pt(15), font_color=self.theme.heading, bold=True
            )

            # Section description
            sec_desc = section.get("description", section.get("pageNumber", "")) if isinstance(section, dict) else ""
            if sec_desc:
                self._add_text(
                    slide, str(sec_desc),
                    left=x + Inches(1.0), top=y + Inches(0.58),
                    width=Inches(4.6), height=Inches(0.55),
                    font_size=Pt(12), font_color=self.theme.muted
                )

    # ================================================================
    #  CONTENT SLIDE
    # ================================================================
    async def _build_content_slide(self, content: dict, speaker_note: str, slide_idx: int):
        slide = self._blank_slide(speaker_note)
        self._set_bg(slide)

        title = content.get("title", "")
        description = content.get("description", "")
        bullets = content.get("bulletPoints", content.get("sections", content.get("items", [])))

        # Check for image
        image_url = self._extract_image_url(content)
        has_image = bool(image_url)

        # Layout: text on left, image on right (like Kimi slide 3+)
        if has_image:
            text_w = Inches(7.40)
            img_left = Inches(8.07)
            img_w = Inches(4.85)
            img_top = Inches(1.75)
            img_h = Inches(5.33)
        else:
            text_w = CONTENT_W
            img_left = img_w = img_top = img_h = 0

        # Section number (large, accent color)
        section_num = str(slide_idx)
        self._add_text(
            slide, section_num,
            left=MARGIN, top=MARGIN,
            width=Inches(0.40), height=Inches(0.38),
            font_size=Pt(22), font_color=self.theme.accent, bold=True
        )

        # Eyebrow label
        eyebrow = content.get("eyebrow", content.get("sectionTitle", ""))
        if eyebrow:
            self._add_text(
                slide, eyebrow.upper(),
                left=Inches(0.85), top=Inches(0.50),
                width=text_w, height=Inches(0.21),
                font_size=Pt(10), font_color=self.theme.accent, bold=True
            )

        # Title (serif, large)
        self._add_text(
            slide, title,
            left=MARGIN, top=Inches(0.92),
            width=text_w, height=Inches(0.42),
            font_name=self.theme.font_heading, font_size=Pt(28),
            font_color=self.theme.heading, bold=True
        )

        # Accent line below title
        self._add_accent_bar(slide, MARGIN, Inches(1.46), Inches(1.0))

        # Bullet points
        if bullets and isinstance(bullets, list):
            self._render_bullets(slide, bullets, text_w, has_image)
        elif description:
            # No bullets, just description
            self._add_text(
                slide, description,
                left=MARGIN, top=Inches(1.75),
                width=text_w, height=Inches(4.5),
                font_size=Pt(14), font_color=self.theme.body
            )

        # Place image if available
        if has_image:
            img_path = await self._download_image(image_url)
            if img_path:
                try:
                    slide.shapes.add_picture(
                        img_path, Emu(int(img_left)), Emu(int(img_top)),
                        Emu(int(img_w)), Emu(int(img_h))
                    )
                except Exception:
                    pass

        # Statistics footer (if present)
        stats = content.get("statistics", content.get("stats", []))
        if stats and isinstance(stats, list):
            self._render_stats_footer(slide, stats, text_w)

    def _render_bullets(self, slide: Slide, bullets: list, text_w, has_image: bool):
        """Render bullet points with icon-style markers."""
        y_start = Inches(1.75)

        for i, bullet in enumerate(bullets):
            if isinstance(bullet, dict):
                btitle = bullet.get("title", bullet.get("heading", ""))
                bdesc = bullet.get("description", bullet.get("text", bullet.get("content", "")))
            else:
                btitle = ""
                bdesc = str(bullet)

            y = y_start + i * Inches(1.0)
            if y > Inches(6.0):
                break  # Don't overflow the slide

            # Diamond icon marker
            icon_size = Inches(0.21)
            icon = slide.shapes.add_shape(
                MSO_SHAPE.DIAMOND, MARGIN + Inches(0.02), y + Inches(0.04),
                icon_size, icon_size
            )
            icon.fill.solid()
            icon.fill.fore_color.rgb = self.theme.accent
            icon.line.fill.background()

            # Bullet title (bold)
            if btitle:
                self._add_text(
                    slide, btitle,
                    left=MARGIN + Inches(0.35), top=y,
                    width=text_w - Inches(0.50), height=Inches(0.29),
                    font_size=Pt(15), font_color=self.theme.heading, bold=True
                )
                # Bullet description
                if bdesc:
                    self._add_text(
                        slide, bdesc,
                        left=MARGIN, top=y + Inches(0.38),
                        width=text_w, height=Inches(0.55),
                        font_size=Pt(12), font_color=self.theme.body
                    )
            else:
                # Just description, no title
                self._add_text(
                    slide, bdesc,
                    left=MARGIN + Inches(0.35), top=y,
                    width=text_w - Inches(0.50), height=Inches(0.80),
                    font_size=Pt(14), font_color=self.theme.body
                )

            # Sub-note (muted)
            sub = bullet.get("note", bullet.get("subtext", "")) if isinstance(bullet, dict) else ""
            if sub:
                note_top = y + Inches(0.70) if btitle else y + Inches(0.55)
                self._add_text(
                    slide, sub,
                    left=MARGIN, top=note_top,
                    width=text_w, height=Inches(0.25),
                    font_size=Pt(12), font_color=self.theme.muted
                )

    def _render_stats_footer(self, slide: Slide, stats: list, text_w):
        """Render a statistics footer row at the bottom (like Kimi slide 3)."""
        # Divider line above stats
        self._add_accent_bar(
            slide, MARGIN, Inches(6.33), text_w,
            height=Inches(0.01), color=self.theme.divider
        )

        stat_w = Inches(2.51)
        y_num = Inches(6.50)
        y_label = Inches(6.88)

        for i, stat in enumerate(stats[:3]):
            if isinstance(stat, dict):
                value = stat.get("value", stat.get("number", ""))
                label = stat.get("label", stat.get("description", ""))
            else:
                continue

            x = MARGIN + i * stat_w

            # Large number
            self._add_text(
                slide, str(value),
                left=x, top=y_num,
                width=stat_w, height=Inches(0.38),
                font_size=Pt(22), font_color=self.theme.accent, bold=True
            )

            # Label
            self._add_text(
                slide, str(label),
                left=x, top=y_label,
                width=stat_w, height=Inches(0.21),
                font_size=Pt(10), font_color=self.theme.muted
            )

    # ================================================================
    #  CONCLUSION SLIDE
    # ================================================================
    def _build_conclusion_slide(self, content: dict, speaker_note: str):
        slide = self._blank_slide(speaker_note)
        self._set_bg(slide)

        title = content.get("title", "Заключение")
        description = content.get("description", content.get("summary", ""))

        # Centered layout
        self._add_text(
            slide, title,
            left=Inches(2.0), top=Inches(2.5),
            width=Inches(9.0), height=Inches(1.0),
            font_name=self.theme.font_heading, font_size=Pt(42),
            font_color=self.theme.heading, bold=True,
            alignment=PP_ALIGN.CENTER
        )

        # Accent line
        self._add_accent_bar(slide, Inches(5.5), Inches(3.6), Inches(2.0))

        if description:
            self._add_text(
                slide, description,
                left=Inches(2.0), top=Inches(4.0),
                width=Inches(9.0), height=Inches(1.5),
                font_size=Pt(18), font_color=self.theme.body,
                alignment=PP_ALIGN.CENTER
            )

        # Year badge
        self._add_text(
            slide, datetime.datetime.now().strftime("%Y"),
            left=Inches(6.0), top=Inches(6.0),
            width=Inches(1.0), height=Inches(0.25),
            font_size=Pt(12), font_color=self.theme.muted,
            alignment=PP_ALIGN.CENTER
        )
