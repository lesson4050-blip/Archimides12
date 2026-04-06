# Archimedes Benchmark Test — 10 Tasks

## ПРАВИЛА ДЛЯ ANTIGRAVITY — ЧИТАТЬ ОБЯЗАТЕЛЬНО

Ты проводишь независимое тестирование агента Archimedes. Твоя роль — технический оператор, не помощник агента.

**ЗАПРЕЩЕНО:**
- Подсказывать агенту что делать
- Исправлять команды агента
- Дописывать или редактировать файлы которые создал агент
- Вмешиваться в ход выполнения задачи
- Повторно запускать задачу если агент провалился — фиксируй провал как есть

**РАЗРЕШЕНО:**
- Запустить бэкенд и фронтенд перед тестом
- Убедиться что Docker запущен
- Копировать задания в интерфейс агента дословно
- После каждого задания записывать результат (✅ / ⚠️ / ❌)
- Сохранить итоговый отчёт

**Главное правило:** агент должен справляться сам. Если он застрял, сделал ошибку, создал неправильный файл — это его результат. Не помогай.

---

## ШАГ 1 — Подготовка (делаешь сам)

1. Убедись что Docker Desktop запущен
2. Запусти бэкенд: `cd backend && python run.py`
3. Запусти фронтенд: `cd frontend && npm run dev`
4. Открой `http://localhost:3000` в браузере
5. Дождись сообщения "Sandbox container is ready"
6. Создай папку для отчёта: сохраняй результат каждого задания

---

## ШАГ 2 — Задания (копируй в интерфейс дословно)

После каждого задания:
- Жди пока агент напишет финальный результат (message type=result)
- Проверь существует ли файл в workspace
- Запиши: номер задания / статус / сколько итераций потратил / были ли ошибки

---

### Задание 1 — File Tool (базовое)

Скопируй в интерфейс агента:

```
Create a file /home/ubuntu/workspace/test1.txt with the following content: "Archimedes Test Suite — Task 1 Complete. Timestamp: {current date and time}". Then read it back and confirm the content is correct.
```

Ожидаемый результат: файл `workspace/test1.txt` с текстом и датой.

---

### Задание 2 — Shell Tool (базовое)

```
Using shell commands, find all .py files in /home/ubuntu/ directory, count how many there are, and save the result to /home/ubuntu/workspace/test2.txt in format: "Found N Python files: [list of paths]"
```

Ожидаемый результат: файл `workspace/test2.txt` со списком путей.

---

### Задание 3 — Search + File (средняя)

```
Search the internet for "top 5 programming languages 2026" and save a structured report to /home/ubuntu/workspace/test3.md with a markdown table: language name, why it's popular, one use case.
```

Ожидаемый результат: файл `workspace/test3.md` с таблицей.

---

### Задание 4 — Code Generation + Shell (средняя)

```
Write a Python script /home/ubuntu/workspace/test4.py that generates the first 20 Fibonacci numbers, calculates their sum, and prints results in a formatted table. Then run it and save the output to /home/ubuntu/workspace/test4_output.txt.
```

Ожидаемый результат: файлы `test4.py` и `test4_output.txt`.

---

### Задание 5 — HTML/CSS/JS (средняя)

```
Create a single HTML file /home/ubuntu/workspace/test5.html with a fully working calculator (add, subtract, multiply, divide) using only vanilla HTML, CSS and JavaScript. No libraries. The UI must be clean and styled.
```

Ожидаемый результат: файл `workspace/test5.html` который открывается в браузере и работает.

---

### Задание 6 — Browser + File (средняя)

```
Navigate to https://github.com/trending using the browser tool, extract the top 5 trending repositories (name, description, stars), and save them to /home/ubuntu/workspace/test6.md as a markdown list.
```

Ожидаемый результат: файл `workspace/test6.md` с 5 репозиториями.

---

### Задание 7 — Multi-step FastAPI (сложная)

```
Create a complete REST API using Python and FastAPI: endpoint GET /health returns {"status": "ok"}, endpoint POST /echo takes JSON body and returns it back. Save all files to /home/ubuntu/workspace/test7/. Include a requirements.txt. Run the server in background on port 9000, test both endpoints with curl and save the test results to /home/ubuntu/workspace/test7/results.txt.
```

Ожидаемый результат: папка `workspace/test7/` с кодом, `requirements.txt` и `results.txt` с curl выводом.

---

### Задание 8 — Data Analysis (сложная)

```
Write a Python script /home/ubuntu/workspace/test8.py that: generates a dataset of 100 random sales records (product, quantity, price), calculates total revenue per product, finds the top 3 products, and saves a summary report to /home/ubuntu/workspace/test8_report.txt. Run it and confirm output.
```

Ожидаемый результат: файлы `test8.py` и `test8_report.txt` с данными.

---

### Задание 9 — Full Web App + Expose (очень сложная)

```
Create a complete working Notes web app at /home/ubuntu/workspace/test9/index.html. Requirements: single HTML file with inline CSS and JS, ability to add notes with title and body, display all notes in a list, delete individual notes, notes persist in localStorage, clean modern UI with dark theme. Serve it on port 8090 using Python and expose the port so I can access it.
```

Ожидаемый результат: файл `workspace/test9/index.html`, сервер на 8090, публичная ссылка.

---

### Задание 10 — Research Report (очень сложная)

```
Search the internet for information about "Gemma 4 vs Llama 4 comparison 2026". Write a comprehensive research report in /home/ubuntu/workspace/test10_report.md that includes: executive summary, detailed comparison table of benchmarks, analysis of which model wins in what category, conclusion with recommendation. Minimum 500 words, proper markdown formatting with headers and tables.
```

Ожидаемый результат: файл `workspace/test10_report.md` объёмом 500+ слов.

---

## ШАГ 3 — Итоговый отчёт (заполняешь сам)

После всех 10 заданий создай файл `workspace/BENCHMARK_RESULTS.md` со следующей структурой:

```markdown
# Archimedes Benchmark Results
Date: [дата]
Local model: gemma4:26b

| # | Task | Status | Iterations | Errors | Notes |
|---|------|--------|------------|--------|-------|
| 1 | File Tool | ✅/⚠️/❌ | N | да/нет | ... |
| 2 | Shell Tool | ✅/⚠️/❌ | N | да/нет | ... |
| 3 | Search + File | ✅/⚠️/❌ | N | да/нет | ... |
| 4 | Code + Run | ✅/⚠️/❌ | N | да/нет | ... |
| 5 | HTML Calculator | ✅/⚠️/❌ | N | да/нет | ... |
| 6 | Browser + File | ✅/⚠️/❌ | N | да/нет | ... |
| 7 | FastAPI Server | ✅/⚠️/❌ | N | да/нет | ... |
| 8 | Data Analysis | ✅/⚠️/❌ | N | да/нет | ... |
| 9 | Web App + Expose | ✅/⚠️/❌ | N | да/нет | ... |
| 10 | Research Report | ✅/⚠️/❌ | N | да/нет | ... |

**Total: X/10**
**Overall assessment:** [твой комментарий]
```

---

## ШАГ 4 — Передача результатов

После завершения:
1. Скачай все файлы из `workspace/` 
2. Скачай `workspace/BENCHMARK_RESULTS.md`
3. Передай пользователю — он отправит результаты на независимую оценку

**Не редактируй содержимое файлов созданных агентом. Передавай как есть.**
