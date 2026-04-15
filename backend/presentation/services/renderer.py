import os
import uuid
import logging
from typing import List
from playwright.async_api import async_playwright

from backend.presentation.schemas import RenderedSlide

logger = logging.getLogger(__name__)

class RendererService:
    """
    Renders a collection of HTML slides into a single PDF using Playwright Chromium.
    Injects global CSS variables and handles landscape printing.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def _build_full_html(self, slides: List[RenderedSlide], theme_css: str) -> str:
        """
        Wraps individual slide HTMLs into a single HTML document with global styles.
        """
        slides_html = "\n".join([f'<div class="slide-page">{s.html}</div>' for s in slides])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                {theme_css}
                
                /* Base Reset */
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                html, body {{ width: 100%; height: 100%; font-family: var(--type-font-family); background-color: var(--color-bg-color); color: var(--color-text-main); }}
                
                /* Strict Slide Paging for PDF Export */
                @page {{ size: 1920px 1080px; margin: 0; }}
                
                .slide-page {{
                    width: 1920px;
                    height: 1080px;
                    overflow: hidden;
                    position: relative;
                    page-break-after: always;
                    background-color: var(--color-bg-color);
                    padding: var(--space-padding-main);
                    display: flex;
                    flex-direction: column;
                }}

                /* Utility layout classes used by the engine */
                .center-text {{ text-align: center; }}
                .full-width {{ width: 100%; }}
                
                /* title-bullets layout */
                .title-bullets {{ height: 100%; display: flex; gap: var(--space-gap-lg); }}
                .title-bullets .content-col {{ flex: 1; display: flex; flex-direction: column; justify-content: center; }}
                .title-bullets .asset-col {{ flex: 1; display: flex; align-items: center; justify-content: center; }}
                .slide-title {{ font-size: var(--type-title-size); font-weight: var(--type-heading-weight); margin-bottom: var(--space-gap-md); color: var(--color-text-main); }}
                .slide-bullets {{ font-size: var(--type-body-size); font-weight: var(--type-body-weight); padding-left: 2rem; list-style-type: disc; display: flex; flex-direction: column; gap: var(--space-gap-md); }}
                .slide-asset {{ width: 100%; height: 100%; object-fit: cover; border-radius: var(--space-border-radius); }}
                
                /* timeline layout */
                .timeline-container {{ display: flex; justify-content: space-between; align-items: center; flex: 1; overflow: hidden; }}
                .timeline-item {{ flex: 1; text-align: center; border-top: 4px solid var(--color-text-accent); padding-top: var(--space-gap-md); font-size: var(--type-body-size); }}
                
                /* two-columns layout */
                .two-columns .cols {{ display: flex; gap: var(--space-gap-lg); flex: 1; margin-top: var(--space-gap-lg); }}
                .two-columns .col {{ flex: 1; }}
                
                /* quote-full layout */
                .quote-full {{ height: 100%; display: flex; align-items: center; justify-content: center; position: relative; }}
                .quote-full .overlay {{ background: var(--color-surface-1); padding: var(--space-gap-lg); border-radius: var(--space-border-radius); text-align: center; max-width: 80%; }}
                .quote-full .quote {{ font-size: 4rem; font-style: italic; }}
                .quote-full .quote-author {{ font-size: 2rem; margin-top: var(--space-gap-md); color: var(--color-text-accent); font-weight: bold; }}
                
                /* chart-grid layout */
                .chart-grid .grid-container {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-gap-lg); flex: 1; align-items: center; }}
                .chart-grid .grid-card {{ background: var(--color-surface-1); padding: var(--space-gap-lg); border: 1px solid var(--color-border); border-radius: var(--space-border-radius); font-size: var(--type-body-size); }}

            </style>
        </head>
        <body>
            {slides_html}
        </body>
        </html>
        """

    async def render_pdf(self, slides: List[RenderedSlide], theme_css: str, output_filename: str = None) -> str:
        """
        Uses Playwright to render the HTML document to PDF.
        """
        html_content = self._build_full_html(slides, theme_css)
        
        if not output_filename:
            output_filename = f"presentation_{uuid.uuid4().hex[:8]}.pdf"
            
        output_path = os.path.join(self.output_dir, output_filename)
        output_path = os.path.abspath(output_path)

        logger.info(f"Rendering PDF to {output_path}...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Use waitUntil 'load' and a small explicit delay to handle slow asset loads more gracefully
            await page.set_content(html_content, wait_until="load", timeout=60000)
            # Give a small buffer for heavy assets
            await page.wait_for_timeout(2000)
            
            await page.pdf(
                path=output_path,
                landscape=True,
                print_background=True,
                width="1920px",
                height="1080px",
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
            )
            
            await browser.close()
            
        logger.info(f"PDF successfully rendered: {output_path}")
        return output_path

renderer_service = RendererService()
