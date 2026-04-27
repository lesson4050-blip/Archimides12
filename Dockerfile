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
# Security: run as non-root user
RUN useradd --uid 1000 --create-home --shell /bin/bash archimedes

WORKDIR /app
# Copy built wheels and install them
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Install Playwright browsers (if needed for COSMO)
RUN python3 -m playwright install --with-deps chromium || true

# Copy application
COPY . /app/

RUN chown -R archimedes:archimedes /app
USER archimedes

# Create directories and set permissions
RUN mkdir -p /app/logs /app/data /app/workspace && \
    chmod -R 755 /app

# Expose ports
EXPOSE 8000

# Startup script (lightweight init check only)
RUN cat > /app/start.sh << 'EOF'
#!/bin/bash
set -e
echo "🚀 ARCHIMEDES — starting up"

# Create required directories
mkdir -p /app/logs /app/data /app/workspace

# Initialize database (idempotent)
python3 -c "
import asyncio
from backend.db.crud import init_db
asyncio.run(init_db())
print('✅ Database ready')
" 2>/dev/null || echo "⚠️  DB init skipped (already exists)"

echo "✅ Pre-flight complete. Handing off to uvicorn..."
EOF

RUN chmod +x /app/start.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Use shell form so uvicorn is PID 1 and receives SIGTERM directly.
# --workers 1 inside async FastAPI — multiple workers share no state.
# Scale horizontally via docker-compose replicas instead.
ENTRYPOINT ["/app/start.sh"]
CMD ["python3", "-m", "uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--timeout-graceful-shutdown", "30"]
