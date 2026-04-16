
from backend.agent.llm_router import llm_router, OutputMode
from backend.presentation.schemas import PresentationPlan

class PlannerAgent:
    """
    Receives user prompt -> outputs PresentationPlan (titles, order, goals).
    """

    async def generate_plan(self, prompt: str) -> PresentationPlan:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert presentation planner (Manus/Gamma-level). "
                    "Your goal is to parse the user's prompt and outline a logical "
                    "flow for a presentation. Create a PresentationPlan containing "
                    "a list of slides. Each slide must have a title and a goal. "
                    "Focus purely on the narrative arc and slide logical sequence."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        result = await llm_router.call(
            messages=messages,
            mode=OutputMode.STRICT_JSON,
            response_model=PresentationPlan,
            task_hint="plan"
        )
        return result
