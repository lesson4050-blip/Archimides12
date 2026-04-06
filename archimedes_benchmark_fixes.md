# Archimedes — Fix All Benchmark Errors

Во время тестирования были найдены реальные баги. Применить все фиксы ниже.
Два файла уже были исправлены во время теста (executor.py и ollama_client.py) — убедись что новые версии совпадают с тем что написано здесь.

---

## FIX 1 — executor.py: уже исправлен, проверь

**Файл:** `backend/sandbox/executor.py`

Убедись что строка с командой выглядит так (список, не строка):
```python
cmd_list = ["timeout", str(timeout), "bash", "-c", command]
```

А НЕ так (старый баг):
```python
wrapped_command = f'timeout {timeout} bash -c {command!r}'
```

Если уже исправлено — пропусти. Если нет — примени.

---

## FIX 2 — ollama_client.py: уже исправлен, проверь

**Файл:** `backend/models/ollama_client.py`

В вызове `self.client.chat(...)` убедись что options содержит оба параметра:
```python
options={
    "num_ctx": settings.AGENT_MAX_CONTEXT_TOKENS,
    "num_predict": 4096
}
```

И убедись что парсинг JSON умеет обрабатывать markdown блоки:
```python
import json
if "{" in text and "}" in text:
    try:
        json_text = text
        if "```json" in text:
            json_text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            json_text = text.split("```")[1].split("```")[0]
        
        start = json_text.find("{")
        end = json_text.rfind("}") + 1
        if start != -1 and end != -1:
            json_str = json_text[start:end]
            data = json.loads(json_str)
            
            if "tool_call" in data:
                tool_call = data["tool_call"]
                text = text.split(json_str)[0].strip()
            elif "name" in data and ("params" in data or "arguments" in data):
                tool_call = {
                    "name": data["name"],
                    "params": data.get("params") or data.get("arguments")
                }
                text = text.split(json_str)[0].strip()
    except Exception as e:
        logger.warning(f"Failed to parse JSON from Ollama output: {e}")
        pass
```

---

## FIX 3 — shell_tool.py: баг с фоновыми процессами

**Файл:** `backend/tools/shell_tool.py`

Текущий код проверяет `endswith('&')` РАНЬШЕ чем реально запускает процесс — из-за этого фоновые команды не выполняются, просто возвращают строку без запуска.

Найди этот блок:
```python
if command.strip().endswith('&') or command.strip().startswith('nohup'):
    return {"success": True, "output": f"Command started in background: {command}"}

if command.strip().endswith(' &'):
    bg_cmd = command.strip()
    result = await self.executor.run_command(session_id, bg_cmd, timeout=5)
    return {"success": True, "output": f"Background process started."}
```

Замени на:
```python
is_background = command.strip().endswith(' &') or command.strip().startswith('nohup ')
if is_background:
    result = await self.executor.run_command(session_id, command.strip(), timeout=10)
    out = result.get('output', '').strip()
    return {"success": True, "output": f"Background process started. {out}"}
```

---

## FIX 4 — thought_engine.py: добавить правила для надёжности

**Файл:** `backend/agent/thought_engine.py`

В конец секции `MANDATORY RULES:` добавь следующие строки:

```
- When writing a Python script, ALWAYS verify it runs without errors by executing it with shell immediately after writing.
- When searching with the search tool, ALWAYS save results to a file — never just print them.
- To start any server in background use exactly: shell(action="exec", command="nohup python3 server.py > /tmp/server.log 2>&1 &")
- After nohup command always wait 2 seconds: shell(action="exec", command="sleep 2 && curl -s http://localhost:PORT/health")
- NEVER assume a background process started successfully — always verify with curl or ps aux | grep process_name.
- When task requires exposing a port, always call expose(port=NUMBER) with port as plain integer.
- If find command returns 0 results, try broader search: find / -name "*.py" 2>/dev/null instead of find /home/ubuntu/ -name "*.py"
```

---

## FIX 5 — config.py: оптимальный контекст для Gemma 4 26B

**Файл:** `backend/config.py`

Убедись что стоит именно 16384 (не 8192 и не 65536):
```python
AGENT_MAX_CONTEXT_TOKENS: int = 16384
```

И в `backend/memory/context_manager.py`:
```python
def __init__(self, max_tokens: int = 16384, summarization_threshold: int = 12000):
```

---

## FIX 6 — OLLAMA_MODEL в config.py: убедись что модель правильная

**Файл:** `backend/config.py`

Убедись что прописана Gemma 4:
```python
OLLAMA_MODEL: str = "gemma4:26b"
```

---

## ИТОГО — что было найдено и исправлено

| # | Файл | Проблема | Исправление |
|---|------|---------|-------------|
| 1 | executor.py | Строковый bash -c ломался на кавычках | Список ["bash", "-c", cmd] |
| 2 | ollama_client.py | Обрезание ответа + JSON в markdown не парсился | num_predict:4096 + markdown strip |
| 3 | shell_tool.py | Фоновые процессы не запускались реально | Убрана ранняя return до выполнения |
| 4 | thought_engine.py | Агент не проверял результаты, не верифицировал сервер | Добавлены правила верификации |
| 5 | config.py | Контекст 65536 — слишком много для железа | Установлен 16384 |
| 6 | config.py | Модель не обновлена после миграции | gemma4:26b |

После применения всех фиксов перезапусти бэкенд.
