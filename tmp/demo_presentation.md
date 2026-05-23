---
marp: true
theme: uncover
class: invert
paginate: true
backgroundColor: #030712
color: #e5e7eb
style: |
  section {
    font-family: 'Inter', -apple-system, sans-serif;
    background: radial-gradient(circle at 50% 50%, #111827 0%, #030712 100%);
    color: #e5e7eb;
    padding: 50px 80px;
    font-size: 1.4rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  h1, h2, h3 {
    font-family: 'Inter', -apple-system, sans-serif;
    font-weight: 800;
    margin-top: 0;
  }
  h1 {
    font-size: 3.2rem;
    color: #ffffff;
    margin-bottom: 20px;
    letter-spacing: -0.025em;
    background: linear-gradient(135deg, #a78bfa 0%, #6366f1 50%, #3b82f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  h2 {
    font-size: 2.2rem;
    color: #a78bfa;
    margin-bottom: 15px;
    border-bottom: 1px solid rgba(167, 139, 250, 0.2);
    padding-bottom: 8px;
  }
  h3 {
    font-size: 1.6rem;
    color: #60a5fa;
    margin-bottom: 10px;
  }
  p, li {
    line-height: 1.6;
    color: #cbd5e1;
  }
  ul, ol {
    margin-top: 10px;
    margin-bottom: 10px;
  }
  li {
    margin-bottom: 8px;
  }
  strong {
    color: #f3f4f6;
    font-weight: 600;
  }
  code {
    background: rgba(255, 255, 255, 0.06);
    color: #38bdf8;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 0.1em 0.4em;
    font-size: 0.85em;
  }
  pre {
    background: #090d16 !important;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px;
    margin-top: 15px;
    overflow: auto;
  }
  pre code {
    background: transparent;
    border: none;
    color: #e5e7eb;
    padding: 0;
    font-size: 0.9em;
  }
  footer {
    font-size: 0.8rem;
    color: #6b7280;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    padding-top: 10px;
  }
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
    margin-top: 15px;
    text-align: left;
  }
  .grid-3 {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 20px;
    margin-top: 15px;
    text-align: left;
  }
  .card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
  }
  .card-purple {
    border-color: rgba(167, 139, 250, 0.2);
    background: linear-gradient(135deg, rgba(167, 139, 250, 0.02) 0%, rgba(99, 102, 241, 0.02) 100%);
  }
  .card-blue {
    border-color: rgba(96, 165, 250, 0.2);
    background: linear-gradient(135deg, rgba(96, 165, 250, 0.02) 0%, rgba(59, 130, 246, 0.02) 100%);
  }
  .highlight-text {
    font-size: 1.8rem;
    font-weight: 300;
    line-height: 1.7;
    color: #e2e8f0;
    text-align: center;
    font-style: italic;
  }
  .metric-value {
    font-size: 3.5rem;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 5px;
    background: linear-gradient(to right, #ffffff, #93c5fd);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .metric-label {
    font-size: 0.9rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
---

# Будущее ИИ-Агентов
### Эра автономных вычислений

<!-- footer: "Архимед ИИ • Конфиденциально • 2026" -->

---

## ⚡ Проблемы старого подхода

- **Высокая задержка**: Генерация слайдов занимала 30–60 секунд из-за массивных JSON-структур
- **Слабый дизайн**: Шаблоны выглядели устаревшими и неубедительными
- **Ломкий экспорт**: PDF-рендеринг через Playwright ломал разметку и кириллицу
- **Ограниченная адаптация**: Невозможно быстро менять стиль или добавлять нестандартные макеты

---

## 🚀 Marp — новый движок презентаций

<div class="grid-2">
  <div class="card card-purple">
    <h3>⚡ Мгновенная генерация</h3>
    <p>Markdown вместо JSON — LLM генерирует слайды в <strong>10× быстрее</strong>. Никаких массивных JSON-схем.</p>
  </div>
  <div class="card card-blue">
    <h3>🎨 Премиальный дизайн</h3>
    <p>Темная тема Archimedes: градиенты, карточки с глассморфизмом, сетки и метрики.</p>
  </div>
</div>

---

## 📊 Метрики эффективности

<div class="grid-3">
  <div class="card">
    <div class="metric-value">92%</div>
    <div class="metric-label">Снижение задержки</div>
  </div>
  <div class="card">
    <div class="metric-value">100%</div>
    <div class="metric-label">Векторный PDF</div>
  </div>
  <div class="card">
    <div class="metric-value">12</div>
    <div class="metric-label">Тестов пройдено</div>
  </div>
</div>

---

## 🏗️ Архитектура системы

<div class="grid-2">
  <div>
    <h3>Backend</h3>
    <ul>
      <li><strong>MarpEngine</strong>: генерация + компиляция</li>
      <li><strong>FastAPI Router</strong>: /research-to-marp</li>
      <li><strong>SecurityGate</strong>: защита от инъекций</li>
      <li><strong>RateLimiter</strong>: 3 req/min на IP</li>
    </ul>
  </div>
  <div>
    <h3>Frontend</h3>
    <ul>
      <li><strong>iframe sandbox</strong>: изолированный рендер</li>
      <li><strong>Клавиши</strong>: ←/→ навигация</li>
      <li><strong>Экспорт</strong>: HTML + PDF одним кликом</li>
      <li><strong>Markdown</strong>: просмотр исходника</li>
    </ul>
  </div>
</div>

---

## 💻 Пример использования

```python
from backend.agent.tools.marp_engine import MarpEngine

engine = MarpEngine(router=model_router)

# Генерация слайдов через LLM
result = await engine.execute(
    action="generate",
    topic="Квантовые вычисления",
    slide_count=8,
    style="technical"
)

# Компиляция в интерактивный HTML
html = await engine.execute(
    action="compile_html",
    markdown=result["markdown"]
)
```

---

<p class="highlight-text">
  "Презентации больше не узкое место.<br/>
  Они стали преимуществом."
</p>
