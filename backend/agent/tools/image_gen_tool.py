import os
import re
import logging
import requests
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ─── System prompts ───────────────────────────────────────────────────────────

ENHANCER_SYSTEM_PROMPT = """You are a world-class prompt engineer specializing in text-to-image AI models.

Your task: take the user's short description and rewrite it into a highly detailed,
photorealistic or artistically rich prompt **in English** that will produce a stunning
image when fed to a Flux diffusion model.

Rules:
- Output ONLY the enhanced prompt text, no explanations, no quotes.
- Include specific details: lighting, camera angle, color palette, mood, texture, style.
- If the original prompt is in a non-English language, translate it to English.
- Keep the prompt under 200 words.
- Use comma-separated descriptors that diffusion models respond well to.
- Mention relevant artistic quality keywords: masterpiece, 8k, ultra-detailed, cinematic lighting, etc.
"""

CRITIC_SYSTEM_PROMPT = """You are an expert image quality critic for AI-generated images.

You will receive an image and the original user request.
Your job:
1. Rate the image from 1 to 10 based on how well it matches the request and overall visual quality.
2. If the rating is below 8, provide a corrected/improved prompt that would fix the issues.

You MUST respond in this exact format (no other text):
SCORE: <number>
FEEDBACK: <one-line feedback>
IMPROVED_PROMPT: <improved prompt or "NONE" if score >= 8>
"""

# ─── Tool class ───────────────────────────────────────────────────────────────

class ImageGenTool:
    """
    Инструмент для генерации изображений с использованием Pollinations.ai API
    с автоматическим улучшением промптов (Prompt Enhancer) и проверкой
    качества через Vision-модель (Vision Critic).
    """

    MAX_CRITIQUE_RETRIES = 2  # Maximum re-generation attempts after critic feedback

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "image_gen",
            "description": "Генерация изображений по текстовому описанию с автоматическим улучшением промпта и контролем качества.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Текстовое описание изображения"},
                    "width": {"type": "integer", "description": "Ширина изображения", "default": 1024},
                    "height": {"type": "integer", "description": "Высота изображения", "default": 1024},
                    "seed": {"type": "integer", "description": "Случайное число для генерации"},
                    "model": {"type": "string", "description": "Модель для генерации (flux, turbo и др.)", "default": "flux"}
                },
                "required": ["prompt"]
            }
        }

    # ── Prompt Enhancer ───────────────────────────────────────────────────────

    async def _enhance_prompt(self, short_prompt: str) -> str:
        """Use Gemini Flash to expand a short prompt into a detailed one."""
        try:
            from backend.models.gemini_client import GeminiClient
            from backend.config import settings

            if not settings.GOOGLE_API_KEY:
                logger.warning("No GOOGLE_API_KEY — skipping prompt enhancement.")
                return short_prompt

            client = GeminiClient()
            enhanced = await client.generate_simple(
                prompt=short_prompt,
                system_prompt=ENHANCER_SYSTEM_PROMPT,
                model_override=settings.IMAGE_CRITIQUE_MODEL,
            )
            enhanced = enhanced.strip().strip('"').strip("'")
            if enhanced:
                logger.info(f"[Enhancer] '{short_prompt}' → '{enhanced[:120]}…'")
                return enhanced
            return short_prompt
        except Exception as e:
            logger.error(f"Prompt enhancement failed, using original: {e}")
            return short_prompt

    # ── Image Generation (Pollinations.ai) ────────────────────────────────────

    def _generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        model: str = "flux",
    ) -> Optional[str]:
        """Download generated image from Pollinations.ai and save to disk.
        Returns the local file path or None on failure."""
        if seed is None:
            seed = uuid.uuid4().int % 1_000_000

        encoded_prompt = requests.utils.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&seed={seed}&model={model}"
        )

        output_dir = "generated_images"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"image_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(output_dir, filename)

        try:
            response = requests.get(url, timeout=120)
            if response.status_code == 200 and len(response.content) > 1000:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                logger.info(f"[Generator] Saved image to {filepath} ({len(response.content)} bytes)")
                return filepath
            else:
                logger.error(f"Pollinations API returned status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Image download failed: {e}")
            return None

    # ── Vision Critic ─────────────────────────────────────────────────────────

    async def _critique_image(self, filepath: str, original_request: str) -> Dict[str, Any]:
        """Send the generated image to Gemini Vision for quality check.
        Returns dict with keys: score (int), feedback (str), improved_prompt (str|None)."""
        try:
            from backend.models.gemini_client import GeminiClient
            from backend.config import settings

            if not settings.GOOGLE_API_KEY:
                logger.warning("No GOOGLE_API_KEY — skipping image critique.")
                return {"score": 10, "feedback": "Skipped (no API key)", "improved_prompt": None}

            with open(filepath, "rb") as f:
                image_bytes = f.read()

            client = GeminiClient()
            critique_prompt = (
                f"The user asked for: \"{original_request}\"\n\n"
                "Please evaluate the attached image against this request."
            )

            raw = await client.generate_simple(
                prompt=critique_prompt,
                system_prompt=CRITIC_SYSTEM_PROMPT,
                image_bytes=image_bytes,
                image_mime="image/png",
                model_override=settings.IMAGE_CRITIQUE_MODEL,
            )

            return self._parse_critique(raw)
        except Exception as e:
            logger.error(f"Vision critique failed: {e}")
            return {"score": 10, "feedback": f"Critique error: {e}", "improved_prompt": None}

    @staticmethod
    def _parse_critique(raw: str) -> Dict[str, Any]:
        """Parse the structured response from the critic model."""
        score = 10
        feedback = ""
        improved_prompt = None

        score_match = re.search(r"SCORE:\s*(\d+)", raw)
        if score_match:
            score = int(score_match.group(1))

        feedback_match = re.search(r"FEEDBACK:\s*(.+)", raw)
        if feedback_match:
            feedback = feedback_match.group(1).strip()

        prompt_match = re.search(r"IMPROVED_PROMPT:\s*(.+)", raw, re.DOTALL)
        if prompt_match:
            val = prompt_match.group(1).strip()
            if val.upper() != "NONE":
                improved_prompt = val

        logger.info(f"[Critic] Score: {score}/10 | Feedback: {feedback}")
        return {"score": score, "feedback": feedback, "improved_prompt": improved_prompt}

    # ── Main execution ────────────────────────────────────────────────────────

    async def execute(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            width = kwargs.get("width", 1024)
            height = kwargs.get("height", 1024)
            seed = kwargs.get("seed")
            model = kwargs.get("model", "flux")

            original_prompt = prompt

            # ── Phase 1: Enhance the prompt ──────────────────────────────────
            enhanced_prompt = await self._enhance_prompt(prompt)

            # ── Phase 2 + 3: Generate → Critique → (Retry) loop ─────────────
            best_filepath = None
            best_score = 0
            current_prompt = enhanced_prompt
            attempts = 0

            while attempts <= self.MAX_CRITIQUE_RETRIES:
                attempts += 1
                logger.info(f"[ImageGen] Attempt {attempts} with prompt: {current_prompt[:100]}…")

                # Generate
                filepath = self._generate_image(
                    prompt=current_prompt,
                    width=width,
                    height=height,
                    seed=seed,
                    model=model,
                )
                if not filepath:
                    return {"success": False, "error": "Image generation failed (API error)"}

                # Use a new seed for the next attempt to get variety
                seed = uuid.uuid4().int % 1_000_000

                # Critique
                critique = await self._critique_image(filepath, original_prompt)

                if critique["score"] > best_score:
                    # Delete the previous best if it exists and is different
                    if best_filepath and best_filepath != filepath:
                        try:
                            os.remove(best_filepath)
                        except OSError:
                            pass
                    best_score = critique["score"]
                    best_filepath = filepath
                else:
                    # This attempt was worse, delete it
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass

                # If score is good enough, stop
                if critique["score"] >= 8:
                    logger.info(f"[ImageGen] Accepted on attempt {attempts} (score {critique['score']})")
                    break

                # If critic gave us an improved prompt, use it
                if critique.get("improved_prompt"):
                    current_prompt = critique["improved_prompt"]
                    logger.info(f"[ImageGen] Critic suggested new prompt: {current_prompt[:100]}…")
                else:
                    # No improved prompt and score < 8 — not much we can do, stop
                    break

            return {
                "success": True,
                "local_path": best_filepath,
                "score": best_score,
                "attempts": attempts,
                "original_prompt": original_prompt,
                "enhanced_prompt": enhanced_prompt,
                "message": f"Изображение сгенерировано (оценка: {best_score}/10, попыток: {attempts})"
            }

        except Exception as e:
            logger.error(f"ImageGenTool error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
