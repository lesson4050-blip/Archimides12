# Dockerfile для Archimedes COSMO - Multi-stage build
FROM python:3.11-slim as builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    build-essential gcc g++ make curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt /app/
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Final Stage
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC \
    PYTHONPATH=/app:$PYTHONPATH \
    OLLAMA_BASE_URL=http://localhost:11434 \
    OLLAMA_MODEL=hf.co/bartowski/Qwen2.5-32B-Instruct-GGUF:Q4_K_M \
    DATABASE_URL=sqlite+aiosqlite:///./data/archimedes.db

# Install runtime dependencies and Node.js
RUN apt-get update && apt-get install -y \
    curl wget vim nano htop tmux netcat-traditional iputils-ping \
    unzip zip tar gzip sqlite3 procps ca-certificates openssl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm typescript \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy built wheels and install them
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Install Playwright browsers (if needed for COSMO)
RUN python3 -m playwright install --with-deps chromium || true

# Copy application
COPY . /app/

# Create directories and set permissions
RUN mkdir -p /app/logs /app/data /app/workspace && \
    chmod -R 755 /app

# Expose ports
EXPOSE 8000 3000 11434

# Startup script
RUN cat > /app/start.sh << 'EOF'
#!/bin/bash
echo "🚀 ARCHIMEDES COSMO - DOCKER STARTUP"
echo "======================================"

mkdir -p /app/logs /app/data /app/workspace

echo "📊 Инициализация базы данных..."
python3 -c "
import asyncio
from backend.db.crud import init_db
asyncio.run(init_db())
print('✅ БД инициализирована')
" 2>/dev/null || echo "⚠️ БД уже инициализирована"

echo "🔧 Запуск backend сервера..."
cd /app
nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2 > /app/logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend запущен (PID: $BACKEND_PID)"
sleep 2

if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ Backend доступен на http://localhost:8000"
else
    echo "⚠️ Backend еще загружается..."
fi

echo "✅ Archimedes is ready. Backend running on port 8000."
tail -f /app/logs/backend.log 2>/dev/null || sleep infinity
EOF

RUN chmod +x /app/start.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["/app/start.sh"]
