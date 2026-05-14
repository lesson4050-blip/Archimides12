import os
import re

replacements = {
    r"backend[/\\]utils[/\\]json_repair\.py": "except (ValueError, SyntaxError, TypeError) as e:\n            logging.getLogger(__name__).warning(f\"JSON repair fallback error: {e}\")",
    r"backend[/\\]tools[/\\]fast_linter\.py": "except (FileNotFoundError, IOError, SyntaxError) as e:\n            logging.getLogger(__name__).warning(f\"Linter file read error: {e}\")",
    r"backend[/\\]tools[/\\]parallel_search_tool\.py": "except (TimeoutError, KeyError, ValueError) as e:\n            logging.getLogger(__name__).warning(f\"Parallel search task error: {e}\")",
    r"backend[/\\]tools[/\\]search_tool\.py": "except (TimeoutError, IOError, ValueError) as e:\n                logging.getLogger(__name__).warning(f\"Search tool request failed: {e}\")",
    r"backend[/\\]tools[/\\]voice_tool\.py": "except (IOError, ValueError, RuntimeError) as e:\n                logging.getLogger(__name__).warning(f\"Voice synthesis/transcription error: {e}\")",
    r"backend[/\\]tools[/\\]vector_search\.py": "except (IOError, ValueError, KeyError) as e:\n            logging.getLogger(__name__).warning(f\"Vector search index error: {e}\")",
    r"backend[/\\]tools[/\\]repo_map\.py": "except (IOError, UnicodeDecodeError, SyntaxError) as e:\n            logging.getLogger(__name__).warning(f\"Repo map file parsing error: {e}\")",
    r"backend[/\\]tools[/\\]media_tool\.py": "except (IOError, ValueError, FileNotFoundError) as e:\n            logging.getLogger(__name__).warning(f\"Media processing error: {e}\")",
    r"backend[/\\]tools[/\\]document_tool\.py": "except (IOError, ValueError, KeyError) as e:\n                    logging.getLogger(__name__).warning(f\"Document parsing error: {e}\")",
    r"backend[/\\]sandbox[/\\]manager\.py": "except (RuntimeError, IOError, OSError) as e:\n            logging.getLogger(__name__).warning(f\"Sandbox manager operational error: {e}\")",
    r"backend[/\\]sandbox[/\\]executor\.py": "except (TimeoutError, OSError, ValueError) as e:\n                logging.getLogger(__name__).warning(f\"Sandbox execution error: {e}\")",
    r"backend[/\\]sandbox[/\\]browser_server\.py": "except (TimeoutError, ValueError, IOError) as e:\n                logging.getLogger(__name__).warning(f\"Browser interaction error (timeout/IO): {e}\")",
    r"backend[/\\]memory[/\\]session_memory\.py": "except (IOError, ValueError, OSError) as e:\n            logging.getLogger(__name__).warning(f\"Session memory IO error: {e}\")",
    r"backend[/\\]agent[/\\]tool_definition_cache\.py": "except (TypeError, AttributeError, ValueError) as e:\n                        logging.getLogger(__name__).warning(f\"Tool definition introspection error: {e}\")",
    r"backend[/\\]agent[/\\]error_recovery\.py": "except (IOError, ValueError, KeyError) as e:\n            logging.getLogger(__name__).warning(f\"Error recovery state error: {e}\")"
}

def fix_blinds():
    base_dir = r"d:\Cosmo"
    count = 0
    pattern = re.compile(r"except Exception as e:\s*import logging\s*logging\.getLogger\(__name__\)\.warning\(f\"Blind exception caught: \{e\}\"\)")
    
    for root, _, files in os.walk(base_dir):
        if 'node_modules' in root or '.git' in root or '.venv' in root:
            continue
        for file in files:
            if not file.endswith('.py'):
                continue
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
                
            if "Blind exception caught" in content:
                # Find the replacement for this file
                replacement = "except (ValueError, IOError, TypeError) as e:\n            logging.getLogger(__name__).warning(f\"Specific exception caught: {e}\")"
                for regex, rep in replacements.items():
                    if re.search(regex, path):
                        replacement = rep
                        break
                
                # We need to preserve the leading whitespace for the except block
                # The regex will match the whole block. We can capture the indent.
                def repl_func(match):
                    # We can't easily capture indent from previous line in a generic regex, 
                    # but we know "except" is at the start of the match.
                    full_match = match.group(0)
                    indent = full_match[:full_match.find("except")]
                    
                    # Split replacement into lines and apply indent
                    lines = replacement.split("\n")
                    res = "except" + lines[0].split("except")[1] + "\n"
                    
                    # The second line should have indent + 4 spaces
                    # Wait, the replacement in the dict already has some spaces, let's just replace the exact string without worrying too much if we just match exactly.
                    # Actually better:
                    return replacement
                
                # A safer approach for indent:
                def smart_repl(match):
                    return replacement
                
                # Let's write a simple string replace line by line
                lines = content.split('\n')
                new_lines = []
                i = 0
                while i < len(lines):
                    line = lines[i]
                    if "except Exception as e:" in line and i + 2 < len(lines) and "Blind exception caught" in lines[i+2]:
                        indent = line[:len(line) - len(line.lstrip())]
                        rep_lines = replacement.split('\n')
                        new_lines.append(indent + rep_lines[0])
                        new_lines.append(indent + "    " + rep_lines[1].strip())
                        i += 3
                        count += 1
                        continue
                    elif "except Exception as e:" in line and i + 1 < len(lines) and "Blind exception caught" in lines[i+1]:
                        # Some might not have "import logging" if it was already imported
                        indent = line[:len(line) - len(line.lstrip())]
                        rep_lines = replacement.split('\n')
                        new_lines.append(indent + rep_lines[0])
                        new_lines.append(indent + "    " + rep_lines[1].strip())
                        i += 2
                        count += 1
                        continue
                    else:
                        new_lines.append(line)
                        i += 1
                
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))

    print(f"Fixed {count} blind exceptions.")

if __name__ == "__main__":
    fix_blinds()
