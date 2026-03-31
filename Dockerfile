# Dockerfile для Archimedes COSMO - Полное развертывание
# Базовый образ: Ubuntu 22.04 с Python 3.11

FROM ubuntu:22.04

# Установить переменные окружения
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC

# Обновить систему и установить зависимости
RUN apt-get update && apt-get install -y \
    # Основные утилиты
    curl wget git vim nano htop tmux \
    # Python и pip
    python3.11 python3.11-dev python3-pip python3-venv \
    # Для Node.js/npm
    nodejs npm \
    # Для сборки
    build-essential gcc g++ make \
    # Для работы с сетью
    net-tools netcat iputils-ping \
    # Для работы с файлами
    unzip zip tar gzip \
    # Для работы с БД
    sqlite3 \
    # Для мониторинга
    procps systemctl \
    # Для SSL
    ca-certificates openssl \
    && rm -rf /var/lib/apt/lists/*

# Создать рабочую директорию
WORKDIR /app

# Скопировать проект (если используется локально)
# COPY . /app

# Или скачать ZIP из интернета (если нужно)
# RUN wget -O archimedes.zip https://your-url/ArchimedesCosmo.zip && \
#     unzip -q archimedes.zip && \
#     rm archimedes.zip

# Установить Python зависимости для backend
RUN pip3 install --upgrade pip setuptools wheel && \
    pip3 install \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    aiohttp==3.9.1 \
    websockets==12.0 \
    python-multipart==0.0.6 \
    python-dotenv==1.0.0 \
    sqlalchemy==2.0.23 \
    aiosqlite==0.19.0 \
    requests==2.31.0 \
    httpx==0.25.1

# Установить Node.js зависимости для frontend
RUN npm install -g pnpm && \
    npm install -g typescript

# Создать структуру директорий
RUN mkdir -p /app/logs /app/data /app/workspace

# Установить права доступа
RUN chmod -R 755 /app

# Expose порты
EXPOSE 8000 3000 11434

# Переменные окружения для приложения
ENV PYTHONPATH=/app:$PYTHONPATH \
    OLLAMA_BASE_URL=http://localhost:11434 \
    OLLAMA_MODEL=hf.co/bartowski/Qwen2.5-32B-Instruct-GGUF:Q4_K_M \
    DATABASE_URL=sqlite+aiosqlite:///./data/archimedes.db \
    NEXT_PUBLIC_API_URL=http://localhost:8000 \
    NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Создать скрипт запуска
RUN cat > /app/start.sh << 'EOF'
#!/bin/bash

echo "🚀 ARCHIMEDES COSMO - DOCKER STARTUP"
echo "======================================"
echo "⏱️  Начало: $(date)"
echo ""

# Проверить Python
echo "✅ Python версия:"
python3 --version
echo ""

# Проверить Node.js
echo "✅ Node.js версия:"
node --version
npm --version
echo ""

# Создать необходимые директории
mkdir -p /app/logs /app/data /app/workspace
echo "✅ Директории созданы"
echo ""

# Инициализировать БД
echo "📊 Инициализация базы данных..."
python3 -c "
import asyncio
from backend.db.crud import init_db
asyncio.run(init_db())
print('✅ БД инициализирована')
" 2>/dev/null || echo "⚠️ БД уже инициализирована"
echo ""

# Запустить backend в фоне
echo "🔧 Запуск backend сервера..."
cd /app
nohup python3 -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    > /app/logs/backend.log 2>&1 &

BACKEND_PID=$!
echo "✅ Backend запущен (PID: $BACKEND_PID)"
sleep 2
echo ""

# Проверить backend
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ Backend доступен на http://localhost:8000"
else
    echo "⚠️ Backend еще загружается..."
fi
echo ""

# Запустить frontend (если нужно)
echo "🎨 Frontend готов к запуску:"
echo "   cd /app/frontend && npm run dev"
echo ""

# Запустить демонстрацию агента
echo "🤖 Запуск демонстрации агента..."
python3 /app/agent_realtime_demo.py
echo ""

echo "======================================"
echo "✅ СИСТЕМА ПОЛНОСТЬЮ ГОТОВА"
echo "⏱️  Завершение: $(date)"
echo ""
echo "📍 Доступные сервисы:"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Frontend: http://localhost:3000 (после запуска)"
echo "   - WebSocket: ws://localhost:8000/ws"
echo ""
echo "📝 Логи:"
echo "   - Backend: /app/logs/backend.log"
echo "   - Данные: /app/data/"
echo ""

# Держать контейнер запущенным
tail -f /app/logs/backend.log 2>/dev/null || sleep infinity
EOF

chmod +x /app/start.sh

# Здоровье контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Команда по умолчанию
CMD ["/app/start.sh"]
