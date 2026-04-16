class AdversarialReviewer:
    """Атакует собственный ответ перед финальной отправкой."""
    
    ATTACKER_PROMPT = """
You are a brutal critic. Attack this answer ruthlessly.
Find factual errors, logical gaps, missing edge cases, wrong assumptions.
Format: ISSUE: [description] for each problem.
If perfect: VERDICT: PASS

Answer: {answer}
Task: {task}
"""
    async def review(self, task: str, answer: str, router) -> dict:
        resp = await router.generate(
            messages=[{"role": "user", "content": 
                self.ATTACKER_PROMPT.format(answer=answer, task=task)}],
            task_hint="think"
        )
        text = resp.get("text", "")
        if "VERDICT: PASS" in text.upper():
            return {"passed": True, "issues": []}
        issues = [line.replace("ISSUE:", "").strip() 
                  for line in text.split("\n") if line.startswith("ISSUE:")]
        
        # Fallback if the model didn't format issues exactly as requested, but also didn't PASS
        if not issues:
            issues = [text]

        return {"passed": False, "issues": issues[:3]} # Max 3 issues to prevent overwhelming loop
