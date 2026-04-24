"""
Chain of Thought Engine.
"""
from typing import Dict, List

COT_PREFIXES = {
    "code": (
        "Before writing any code, use the <thinking> tags to reason:\n"
        "1. What exactly is the goal?\n"
        "2. What are the edge cases and constraints?\n"
        "3. What is the simplest robust solution?\n"
        "4. How does this fit into the expected output format?"
    ),
    "agent_action": (
        "Reason briefly in <thinking> tags, then take the next logical action using a tool."
    ),
    "default": (
        "Think step-by-step before answering:\n"
        "1. Analyze the request.\n"
        "2. Formulate the approach.\n"
        "3. Verify against constraints."
    ),
}

COT_SUFFIX = "\n</thinking>\n\nNow, providing the final response in the strict required format:"

def detect_task_type(task: str) -> str:
    task_lower = task.lower()
    if any(w in task_lower for w in ["tool", "action", "json", "execute", "инструмент", "действие", "написать", "write", "create", "создать"]):
        return "agent_action"
    if any(w in task_lower for w in ["code", "function", "implement", "fix", "код", "исправить", "script"]):
        return "code"
    return "default"

def inject_cot(messages: List[Dict], task: str = "", include_assistant: bool = True) -> List[Dict]:
    if not messages:
        return messages
    
    task_type = detect_task_type(task)
    prefix = COT_PREFIXES[task_type]
    
    result = messages.copy()
    for i in range(len(result) - 1, -1, -1):
        if result[i].get("role") == "user":
            original = result[i]["content"]
            result[i] = {
                **result[i],
                "content": f"{original}\n\nCRITICAL INSTRUCTION: You MUST wrap your reasoning in <thinking>...</thinking> tags. After the tags, output ONLY the requested final format.\n\n{prefix}"
            }
            break

    if include_assistant:
        result.append({
            "role": "assistant",
            "content": "<thinking>\n"
        })
    return result


def extract_cot_answer(text: str) -> Dict[str, str]:
    if "</thinking>" in text:
        parts = text.split("</thinking>", 1)
        thinking = parts[0].replace("<thinking>", "").strip()
        answer = parts[1].strip()
        if "Now, providing the final response" in answer:
            answer = answer.split(":", 1)[-1].strip()
        return {"thinking": thinking, "answer": answer}
    return {"thinking": "", "answer": text}
