import os
import re
import logging
import requests
import uuid
import base64
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ─── System prompts ───────────────────────────────────────────────────────────

ENHANCER_SYSTEM_PROMPT = """You are an expert prompt engineer for the Flux text-to-image diffusion model.

Rewrite the user's short request into a precise, detailed prompt IN ENGLISH.

STRICT RULES:
- Output ONLY the final prompt text. No explanations, no quotes, no markdown.
- Focus on CLARITY and SHARPNESS: always include "sharp focus, high resolution, 4k, ultra detailed".
- Specify a concrete subject with clear physical attributes (breed, color, pose, expression).
- Specify lighting: prefer "studio lighting", "natural daylight", "soft diffused light".
- Specify camera: "shot on Canon EOS R5, 85mm f/1.4 lens, shallow depth of field".
- Specify style: "professional photography, photorealistic, award-winning photo".
- Do NOT use vague dreamy/fantasy descriptors unless the user explicitly asks for it.
- Do NOT add "masterpiece, 8k" spam — be specific instead.
- Keep under 120 words.
- If the user asks for a cat, describe a REAL specific cat breed with realistic proportions.

Example input: "кот"
Example output: "A beautiful British Shorthair cat with dense blue-gray fur, sitting on a wooden table, looking directly at camera with bright amber eyes, sharp focus, professional pet photography, natural window light from the left, shot on Canon EOS R5 with 85mm f/1.4 lens, shallow depth of field, soft cream-colored background, ultra detailed fur texture, high resolution 4k"
"""

CRITIC_SYSTEM_PROMPT = """You are a strict image quality inspector for AI-generated images.

You will receive an image and the original user request.
Evaluate on these criteria:
1. SHARPNESS: Is the image crisp and in focus? (blurry = instant low score)
2. ACCURACY: Does it match what the user asked for?
3. ANATOMY: Are proportions correct? (no extra limbs, weird faces, distorted body parts)
4. QUALITY: Overall photographic/artistic quality.

Be HARSH. Most AI images have subtle flaws — find them.
If the image is blurry, has weird anatomy, or doesn't match the request, score it LOW.

You MUST respond in this EXACT format (nothing else):
SCORE: <number 1-10>
FEEDBACK: <one-line description of the main issues>
IMPROVED_PROMPT: <a corrected prompt that fixes the issues, or "NONE" if score >= 8>

When writing IMPROVED_PROMPT, always include: "sharp focus, high resolution, 4k, ultra detailed, photorealistic, correct anatomy, professional photography"
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

    # ── Vision API call with Gemini → Groq fallback ───────────────────────────

    async def _call_vision_llm(
        self,
        prompt: str,
        system_prompt: str,
        image_bytes: Optional[bytes] = None,
    ) -> str:
        """Call a vision-capable LLM. Tries Gemini Flash first, falls back to Groq Vision."""
        errors = []

        # ── Try 1: Gemini Flash ──────────────────────────────────────────
        try:
            from backend.models.gemini_client import GeminiClient
            from backend.config import settings

            if settings.GOOGLE_API_KEY:
                client = GeminiClient()
                result = await client.generate_simple(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    image_bytes=image_bytes,
                    image_mime="image/png",
                    model_override=settings.IMAGE_CRITIQUE_MODEL,
                )
                if result and result.strip():
                    logger.info("[VisionLLM] Gemini Flash responded successfully")
                    return result.strip()
        except Exception as e:
            errors.append(f"Gemini: {e}")
            logger.warning(f"[VisionLLM] Gemini failed: {e}")

        # ── Try 2: Groq Vision (llama-3.2-90b-vision-preview) ────────────
        try:
            from backend.config import settings

            if settings.GROQ_API_KEY:
                from groq import AsyncGroq
                groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

                messages_content = []
                if image_bytes:
                    b64 = base64.b64encode(image_bytes).decode("utf-8")
                    messages_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}
                    })
                messages_content.append({"type": "text", "text": prompt})

                response = await groq_client.chat.completions.create(
                    model="llama-3.2-90b-vision-preview",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": messages_content},
                    ],
                    max_tokens=500,
                )
                text = response.choices[0].message.content or ""
                if text.strip():
                    logger.info("[VisionLLM] Groq Vision responded successfully")
                    return text.strip()
        except Exception as e:
            errors.append(f"Groq: {e}")
            logger.warning(f"[VisionLLM] Groq Vision failed: {e}")

        raise RuntimeError(f"All vision LLMs failed: {'; '.join(errors)}")

    # ── Prompt Enhancer ───────────────────────────────────────────────────────

    async def _enhance_prompt(self, short_prompt: str) -> str:
        """Use LLM to expand a short prompt into a detailed one."""
        try:
            enhanced = await self._call_vision_llm(
                prompt=short_prompt,
                system_prompt=ENHANCER_SYSTEM_PROMPT,
                image_bytes=None,
            )
            enhanced = enhanced.strip().strip('"').strip("'")
            if enhanced and len(enhanced) > 20:
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
            f"&nologo=true&enhance=true"
        )

        output_dir = "generated_images"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"image_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(output_dir, filename)

        try:
            response = requests.get(url, timeout=180)
            if response.status_code == 200 and len(response.content) > 5000:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                logger.info(f"[Generator] Saved image to {filepath} ({len(response.content)} bytes)")
                return filepath
            else:
                logger.error(f"Pollinations API error: status={response.status_code}, size={len(response.content)}")
                return None
        except Exception as e:
            logger.error(f"Image download failed: {e}")
            return None

    # ── Vision Critic ─────────────────────────────────────────────────────────

    async def _critique_image(self, filepath: str, original_request: str) -> Dict[str, Any]:
        """Send the generated image to a Vision LLM for quality check.
        Returns dict with keys: score (int), feedback (str), improved_prompt (str|None)."""
        try:
            with open(filepath, "rb") as f:
                image_bytes = f.read()

            critique_prompt = (
                f"The user asked for: \"{original_request}\"\n\n"
                "Evaluate the attached image. Be strict about sharpness, anatomy and accuracy."
            )

            raw = await self._call_vision_llm(
                prompt=critique_prompt,
                system_prompt=CRITIC_SYSTEM_PROMPT,
                image_bytes=image_bytes,
            )

            return self._parse_critique(raw)
        except Exception as e:
            logger.error(f"Vision critique failed completely: {e}")
            # Critic unavailable — score 5 so we still try to regenerate at least once
            return {
                "score": 5,
                "feedback": f"Critic unavailable ({e}), forcing retry",
                "improved_prompt": None,
            }

    @staticmethod
    def _parse_critique(raw: str) -> Dict[str, Any]:
        """Parse the structured response from the critic model."""
        score = 5  # Default to mediocre if parsing fails
        feedback = "Could not parse critique"
        improved_prompt = None

        score_match = re.search(r"SCORE:\s*(\d+)", raw)
        if score_match:
            score = min(10, max(1, int(score_match.group(1))))

        feedback_match = re.search(r"FEEDBACK:\s*(.+)", raw)
        if feedback_match:
            feedback = feedback_match.group(1).strip()

        prompt_match = re.search(r"IMPROVED_PROMPT:\s*(.+)", raw, re.DOTALL)
        if prompt_match:
            val = prompt_match.group(1).strip()
            if val.upper() != "NONE" and len(val) > 10:
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
                logger.info(f"[ImageGen] Attempt {attempts}/{self.MAX_CRITIQUE_RETRIES + 1} | Prompt: {current_prompt[:100]}…")

                # Generate
                filepath = self._generate_image(
                    prompt=current_prompt,
                    width=width,
                    height=height,
                    seed=seed,
                    model=model,
                )
                if not filepath:
                    if best_filepath:
                        # Return whatever we have so far
                        break
                    return {"success": False, "error": "Image generation failed (API error)"}

                # New seed for next attempt
                seed = uuid.uuid4().int % 1_000_000

                # Critique
                critique = await self._critique_image(filepath, original_prompt)

                if critique["score"] > best_score:
                    # This is our new best — delete old best
                    if best_filepath and best_filepath != filepath:
                        try:
                            os.remove(best_filepath)
                        except OSError:
                            pass
                    best_score = critique["score"]
                    best_filepath = filepath
                else:
                    # This attempt was worse — delete it
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass

                # If score is good enough, stop
                if critique["score"] >= 8:
                    logger.info(f"[ImageGen] ✅ Accepted on attempt {attempts} (score {critique['score']}/10)")
                    break

                # If this was the last attempt, stop
                if attempts > self.MAX_CRITIQUE_RETRIES:
                    logger.info(f"[ImageGen] ⚠️ Max retries reached. Best score: {best_score}/10")
                    break

                # If critic gave us an improved prompt, use it for next attempt
                if critique.get("improved_prompt"):
                    current_prompt = critique["improved_prompt"]
                    logger.info(f"[ImageGen] 🔄 Critic suggested new prompt: {current_prompt[:100]}…")
                else:
                    # No improved prompt — add sharpness keywords to current prompt and retry
                    current_prompt = current_prompt + ", sharp focus, high resolution, crisp details, correct anatomy, photorealistic"
                    logger.info(f"[ImageGen] 🔄 Adding sharpness keywords for retry")

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
