import os
import asyncio
import logging
from typing import Optional, Dict

from backend.presentation.schemas import TaskStatus, RenderedSlide, Theme
from backend.presentation.agents.planner import PlannerAgent
from backend.presentation.agents.content import ContentAgent
from backend.presentation.engine.design import DesignEngine
from backend.presentation.engine.themes import get_theme
from backend.presentation.services.asset import asset_service
from backend.presentation.services.renderer import renderer_service

logger = logging.getLogger(__name__)

# Simple in-memory task store for demonstration
TASKS_STORE: Dict[str, TaskStatus] = {}

class PresentationPipeline:
    """
    Coordinates the full Manus/Gamma-style presentation generation process.
    """
    def __init__(self):
        self.planner = PlannerAgent()
        self.content_agent = ContentAgent()
        self.design_engine = DesignEngine()

    async def generate_background(self, task_id: str, prompt: str, theme_id: str = "tech-blue", output_filename: Optional[str] = None):
        """
        Background task executor.
        """
        task_status = TASKS_STORE.get(task_id)
        if not task_status:
            return

        try:
            task_status.status = "processing"
            task_status.progress = 0.1
            
            logger.info(f"[Task {task_id}] Planning presentation...")
            plan = await self.planner.generate_plan(prompt)
            task_status.progress = 0.3

            logger.info(f"[Task {task_id}] Generating content and resolving assets...")
            rendered_slides = []
            
            # Retrieve global theme parameters
            theme = get_theme(theme_id)
            theme_css = self.design_engine.generate_theme_css(theme)
            
            total_slides = len(plan.slides)
            
            for index, slide_plan in enumerate(plan.slides):
                # 1. Expand Content
                content = await self.content_agent.generate_content(
                    slide_plan=slide_plan,
                    global_context=f"Presentation about: {prompt}. Main title: {plan.title}"
                )
                
                # 2. Get Assets
                assets = await asset_service.get_assets(content.asset_query)
                
                # 3. Apply Design Phase
                rendered_slide = self.design_engine.render_slide(
                    content=content,
                    theme_id=theme_id,
                    resolved_assets=assets
                )
                
                rendered_slides.append(rendered_slide)
                
                # Update progress incrementally
                task_status.progress = 0.3 + (0.4 * ((index + 1) / total_slides))

            logger.info(f"[Task {task_id}] Rendering PDF via Playwright...")
            task_status.status = "rendering"
            
            # Step 5: Render PDF
            output_path = await renderer_service.render_pdf(
                slides=rendered_slides, 
                theme_css=theme_css, 
                output_filename=output_filename
            )
            
            task_status.status = "done"
            task_status.progress = 1.0
            task_status.result_url = output_path
            logger.info(f"[Task {task_id}] Completed successfully. Output: {output_path}")

        except Exception as e:
            logger.error(f"[Task {task_id}] Pipeline failed: {e}")
            task_status.status = "failed"
            task_status.error = str(e)
            
    async def generate(self, prompt: str, theme: str, output_path: str = None) -> TaskStatus:
        """
        Synchronous-style call specifically for tests, wraps background task into await.
        """
        task_id = "test_task_sync"
        TASKS_STORE[task_id] = TaskStatus(task_id=task_id, status="pending")
        await self.generate_background(task_id, prompt, theme, output_path)
        return type('Obj', (object,), {'pdf_path': TASKS_STORE[task_id].result_url})()
