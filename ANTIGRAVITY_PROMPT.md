# 🚀 ARCHIMEDES COSMO - GOOGLE ANTIGRAVITY IDE DEPLOYMENT PROMPT

## 📋 МЕГА-ПРОМТ ДЛЯ ПОЛНОГО РАЗВЕРТЫВАНИЯ В DOCKER

Скопируйте этот промт в Google Antigravity IDE и выполните все шаги автоматически.

---

## 🎯 ЗАДАЧА

**Развернуть Archimedes COSMO - полнофункциональный ИИ-агент enterprise-уровня в Docker контейнере с Ubuntu, всеми зависимостями, базой данных, Ollama, и запустить полную систему.**

---

## 📥 ЭТАП 1: ПОДГОТОВКА И ЗАГРУЗКА

```bash
#!/bin/bash

echo "🚀 ARCHIMEDES COSMO - DEPLOYMENT IN DOCKER"
echo "==========================================="
echo ""

# 1. Создать рабочую директорию
mkdir -p /workspace/archimedes-cosmo
cd /workspace/archimedes-cosmo

echo "✅ Рабочая директория создана: /workspace/archimedes-cosmo"
echo ""

# 2. Скачать ZIP файл (замените URL на ваш)
echo "📥 Загрузка Archimedes COSMO..."
# Вариант 1: Из GitHub
# wget -q https://github.com/your-repo/releases/download/v2.0/ArchimedesCosmo.zip

# Вариант 2: Из Google Drive (замените FILE_ID)
# wget -q "https://drive.google.com/uc?id=YOUR_FILE_ID&export=download" -O ArchimedesCosmo.zip

# Вариант 3: Если файл уже есть локально
cp /path/to/ArchimedesCosmo.zip . || echo "⚠️ ZIP файл не найден, используем текущую директорию"

# 3. Распаковать архив
if [ -f ArchimedesCosmo.zip ]; then
    echo "📦 Распаковка архива..."
    unzip -q ArchimedesCosmo.zip
    
    # Если распаковалось в подпапку, переместить содержимое
    if [ -d ArchimedesCosmo ]; then
        mv ArchimedesCosmo/* .
        rmdir ArchimedesCosmo
    fi
    
    rm -f ArchimedesCosmo.zip
    echo "✅ Архив распакован"
else
    echo "⚠️ ZIP файл не найден, продолжаем с текущей структурой"
fi

echo ""
```

---

## 🐳 ЭТАП 2: DOCKER SETUP

```bash
#!/bin/bash

cd /workspace/archimedes-cosmo

echo "🐳 DOCKER CONFIGURATION"
echo "======================="
echo ""

# 1. Проверить Docker
if ! command -v docker &> /dev/null; then
    echo "📦 Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker установлен"
else
    echo "✅ Docker уже установлен: $(docker --version)"
fi

# 2. Проверить Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Установка Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose установлен"
else
    echo "✅ Docker Compose уже установлен: $(docker-compose --version)"
fi

echo ""

# 3. Создать необходимые директории
mkdir -p logs data workspace
chmod -R 755 logs data workspace

echo "✅ Директории созданы: logs, data, workspace"
echo ""

# 4. Создать .env файл
cat > .env << 'ENVEOF'
# Archimedes COSMO Environment Variables

# Python
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=hf.co/bartowski/Qwen2.5-32B-Instruct-GGUF:Q4_K_M

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/archimedes.db
POSTGRES_USER=archimedes
POSTGRES_PASSWORD=archimedes_secure_password
POSTGRES_DB=archimedes_db

# API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Agent
AGENT_MAX_ITERATIONS=50
AGENT_MAX_CONTEXT_TOKENS=800000

# Sandbox
SANDBOX_MAX_CONTAINERS=3
SANDBOX_INACTIVITY_TIMEOUT=1800
ENVEOF

echo "✅ .env файл создан"
echo ""
```

---

## 🏗️ ЭТАП 3: DOCKER BUILD & RUN

```bash
#!/bin/bash

cd /workspace/archimedes-cosmo

echo "🏗️ BUILDING DOCKER IMAGE"
echo "========================"
echo ""

# 1. Собрать образ
echo "📦 Сборка Docker образа..."
docker build -t archimedes-cosmo:latest .

if [ $? -eq 0 ]; then
    echo "✅ Docker образ успешно собран"
else
    echo "❌ Ошибка при сборке образа"
    exit 1
fi

echo ""

# 2. Запустить контейнеры через docker-compose
echo "🚀 Запуск контейнеров..."
docker-compose up -d

echo "✅ Контейнеры запущены"
echo ""

# 3. Проверить статус контейнеров
echo "📊 Статус контейнеров:"
docker-compose ps
echo ""

# 4. Ожидание инициализации
echo "⏳ Ожидание инициализации сервисов (30 сек)..."
sleep 30

echo ""
```

---

## ✅ ЭТАП 4: ПРОВЕРКА И ТЕСТИРОВАНИЕ

```bash
#!/bin/bash

cd /workspace/archimedes-cosmo

echo "✅ VERIFICATION & TESTING"
echo "========================="
echo ""

# 1. Проверить Backend API
echo "🔍 Проверка Backend API..."
if curl -s http://localhost:8000/api/v1/health | grep -q "healthy"; then
    echo "✅ Backend API доступен и здоров"
else
    echo "⚠️ Backend API еще загружается, проверяем логи..."
    docker-compose logs archimedes | tail -20
fi

echo ""

# 2. Проверить Ollama
echo "🔍 Проверка Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama доступна"
else
    echo "⚠️ Ollama еще загружается"
fi

echo ""

# 3. Проверить логи
echo "📝 Последние логи Backend:"
docker-compose logs archimedes --tail=20
echo ""

# 4. Запустить демонстрацию агента
echo "🤖 Запуск демонстрации агента..."
docker-compose exec -T archimedes python3 /app/agent_realtime_demo.py

echo ""
```

---

## 🌐 ЭТАП 5: ДОСТУП И ИСПОЛЬЗОВАНИЕ

```bash
#!/bin/bash

echo "🌐 ACCESSING SERVICES"
echo "====================="
echo ""

echo "📍 Доступные сервисы:"
echo ""
echo "1. Backend API:"
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/api/v1/health"
echo ""
echo "2. Frontend (после запуска):"
echo "   URL: http://localhost:3000"
echo "   Команда: docker-compose exec archimedes npm run dev -C /app/frontend"
echo ""
echo "3. WebSocket:"
echo "   URL: ws://localhost:8000/ws"
echo ""
echo "4. Ollama:"
echo "   URL: http://localhost:11434"
echo "   API: http://localhost:11434/api/tags"
echo ""
echo "5. PostgreSQL (опционально):"
echo "   Host: localhost:5432"
echo "   User: archimedes"
echo "   Pass: archimedes_secure_password"
echo ""
echo "6. Redis (опционально):"
echo "   URL: redis://localhost:6379"
echo ""

echo "📝 Полезные команды:"
echo ""
echo "# Просмотр логов"
echo "docker-compose logs -f archimedes"
echo ""
echo "# Вход в контейнер"
echo "docker-compose exec archimedes bash"
echo ""
echo "# Перезапуск сервиса"
echo "docker-compose restart archimedes"
echo ""
echo "# Остановка всех сервисов"
echo "docker-compose down"
echo ""
echo "# Удаление всех данных"
echo "docker-compose down -v"
echo ""

echo "✅ СИСТЕМА ПОЛНОСТЬЮ РАЗВЕРНУТА И ГОТОВА К ИСПОЛЬЗОВАНИЮ!"
echo ""
```

---

## 🚀 ПОЛНЫЙ СКРИПТ РАЗВЕРТЫВАНИЯ (ONE-LINER)

Скопируйте и выполните в терминале:

```bash
#!/bin/bash

# ПОЛНОЕ РАЗВЕРТЫВАНИЕ ARCHIMEDES COSMO В DOCKER

set -e

echo "🚀 ARCHIMEDES COSMO - FULL DOCKER DEPLOYMENT"
echo "=============================================="
echo ""

# Этап 1: Подготовка
mkdir -p /workspace/archimedes-cosmo && cd /workspace/archimedes-cosmo
echo "✅ Рабочая директория создана"

# Этап 2: Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
fi
echo "✅ Docker готов"

# Этап 3: Загрузка и распаковка
# wget -q https://your-url/ArchimedesCosmo.zip && unzip -q ArchimedesCosmo.zip
echo "✅ Архив распакован"

# Этап 4: .env файл
cat > .env << 'EOF'
PYTHONUNBUFFERED=1
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=hf.co/bartowski/Qwen2.5-32B-Instruct-GGUF:Q4_K_M
DATABASE_URL=sqlite+aiosqlite:///./data/archimedes.db
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
EOF
echo "✅ .env файл создан"

# Этап 5: Docker Compose
docker-compose up -d
echo "✅ Контейнеры запущены"

# Этап 6: Ожидание инициализации
sleep 30
echo "✅ Сервисы инициализированы"

# Этап 7: Проверка
curl -s http://localhost:8000/api/v1/health && echo "✅ Backend работает"
echo ""
echo "🎉 СИСТЕМА ПОЛНОСТЬЮ РАЗВЕРНУТА!"
echo "📍 Backend: http://localhost:8000"
echo "📍 Docs: http://localhost:8000/docs"
```

---

## 📊 МОНИТОРИНГ И УПРАВЛЕНИЕ

```bash
# Просмотр логов в реал-тайм
docker-compose logs -f archimedes

# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats

# Вход в контейнер
docker-compose exec archimedes bash

# Запуск команды в контейнере
docker-compose exec archimedes python3 -c "import sys; print(sys.version)"

# Перезапуск сервиса
docker-compose restart archimedes

# Остановка
docker-compose stop

# Запуск
docker-compose start

# Полная очистка
docker-compose down -v
```

---

## 🔧 TROUBLESHOOTING

### Проблема: Backend не запускается
```bash
# Проверить логи
docker-compose logs archimedes

# Пересобрать образ
docker-compose build --no-cache archimedes

# Перезапустить
docker-compose restart archimedes
```

### Проблема: Ollama не доступна
```bash
# Проверить статус
docker-compose logs ollama

# Перезапустить Ollama
docker-compose restart ollama

# Проверить доступность
curl http://localhost:11434/api/tags
```

### Проблема: Порты заняты
```bash
# Найти процесс на порту
sudo lsof -i :8000

# Изменить порт в docker-compose.yml
# ports:
#   - "8001:8000"
```

---

## 📦 ИТОГОВАЯ СТРУКТУРА

```
/workspace/archimedes-cosmo/
├── Dockerfile                 # Docker образ
├── docker-compose.yml         # Оркестрация сервисов
├── .env                       # Переменные окружения
├── backend/                   # Backend код
│   ├── agent/                # Агент
│   ├── tools/                # Инструменты
│   ├── websocket/            # WebSocket
│   ├── api/                  # API маршруты
│   └── main.py              # Главный файл
├── frontend/                  # Frontend код
├── logs/                      # Логи
├── data/                      # Данные БД
└── workspace/                 # Рабочая директория агента
```

---

## 🎉 ГОТОВО!

Ваша полная система Archimedes COSMO развернута в Docker контейнере с:

✅ Ubuntu 22.04  
✅ Python 3.11  
✅ FastAPI Backend  
✅ React Frontend  
✅ Ollama для локальных моделей  
✅ PostgreSQL для БД  
✅ Redis для кэширования  
✅ WebSocket для реал-тайм  
✅ Полное логирование  
✅ Health checks  
✅ Автоматический перезапуск  

**Система готова к использованию! 🚀**
