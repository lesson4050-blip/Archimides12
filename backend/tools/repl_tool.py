import sys
import io
import traceback
from typing import Dict, Any
import contextlib

# Persistent state across tool calls within the same worker process
_SESSION_STATES: dict[str, dict] = {}

def clear_session(session_id: str) -> None:
    _SESSION_STATES.pop(session_id, None)

class ReplTool:
    """
    Interactive Python REPL with persistent memory for quick code experimentation.
    """
    def __init__(self):
        pass

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "python_repl",
                "description": "SUPER WEAPON: Execute raw Python code in a persistent sandbox memory state. Use this to quickly test a complex regex, verify a small algorithm, or check how a library works WITHOUT writing a temporary file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string", 
                            "description": "Python code to execute. Variables created here will persist in memory for future repl calls."
                        }
                    },
                    "required": ["code"]
                }
            }
        }

    async def execute(self, session_id: str, code: str) -> Dict[str, Any]:
        if session_id not in _SESSION_STATES:
            _SESSION_STATES[session_id] = {}
        state = _SESSION_STATES[session_id]

        # Capture stdout and stderr
        stdout = io.StringIO()
        stderr = io.StringIO()
        
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                # We compile it as 'exec' to run multiple statements
                # But we want to mimic a REPL where the last expression is printed if it evaluates to something
                
                # Split code to execute all but last, and eval the last
                import ast
                parsed = ast.parse(code)
                if len(parsed.body) > 0 and isinstance(parsed.body[-1], ast.Expr):
                    # Last statement is an expression. We can eval it to return its value
                    exec_part = ast.unparse(parsed.body[:-1]) if hasattr(ast, 'unparse') else ""
                    eval_part = ast.unparse(parsed.body[-1].value) if hasattr(ast, 'unparse') else ""
                    
                    if exec_part:
                        exec(compile(parsed.body[:-1], "<repl>", "exec"), state)
                    
                    if eval_part:
                        val = eval(compile(parsed.body[-1].value, "<repl>", "eval"), state)
                        if val is not None:
                            print(val)
                else:
                    # Just exec the whole block
                    exec(code, state)
                    
            out = stdout.getvalue()
            err = stderr.getvalue()
            
            result = out
            if err:
                result += f"\n[STDERR]\n{err}"
                
            return {
                "success": True, 
                "result": result.strip() or "[Executed successfully, no output]"
            }
            
        except Exception:
            err = traceback.format_exc()
            return {
                "success": False,
                "error": err
            }
