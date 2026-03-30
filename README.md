# V2T (Voice-to-Text Telegram Bot)

Подробная инструкция **для начинающих**: как установить, настроить и запустить бота «голос → текст → заметка в Google».

---

## Что делает проект

- принимает голосовые сообщения из Telegram;
- ставит обработку в очередь Celery;
- конвертирует аудио и делает STT;
- сохраняет заметки и синхронизирует в Google;
- поддерживает платежные вебхуки и тарифы.

---

## 0) Что нужно установить заранее

> Ниже команды для Linux/macOS. На Windows используйте PowerShell + Docker Desktop.

1. **Git**
2. **Docker + Docker Compose plugin**
3. (Опционально для локальной разработки без Docker) **Python 3.11+**

Проверка:

```bash
git --version
docker --version
docker compose version
python --version
```

---

## 0.1) Подробная установка и настройка Docker

Ниже — последовательность для новичков. Выберите свою ОС.

### Windows 10/11 (рекомендуется Docker Desktop + WSL2)

1. Установите **Docker Desktop** с официального сайта.
2. Во время установки включите опцию **Use WSL 2 instead of Hyper-V** (если доступно).
3. Перезапустите компьютер.
4. Откройте Docker Desktop → **Settings**:
   - `General` → включить `Use the WSL 2 based engine`.
   - `Resources > WSL Integration` → включить интеграцию для вашего дистрибутива (например, Ubuntu).
5. Проверьте в PowerShell:

```powershell
docker --version
docker compose version
docker info
```

Если `docker info` не возвращает ошибку — движок работает.

### macOS

1. Установите Docker Desktop for Mac.
2. Запустите Docker Desktop и дождитесь статуса **Engine running**.
3. Проверка в терминале:

```bash
docker --version
docker compose version
docker info
```

### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

Проверка:

```bash
docker --version
docker compose version
docker info
```

### Минимальные настройки Docker для этого проекта

1. Убедитесь, что свободны порты:
   - `8000` (API),
   - `80` и `443` (Nginx, если запускаете вместе),
   - `5432` (PostgreSQL, если пробрасываете наружу),
   - `6379` (Redis, если пробрасываете наружу).
2. Проверьте доступные ресурсы Docker Desktop:
   - RAM минимум 4 GB (лучше 6–8 GB),
   - CPU 2+ cores.
3. На Windows добавьте папку проекта в доступные файловые шары Docker Desktop (если возникают проблемы с bind mounts).

### Быстрый smoke-test Docker перед запуском проекта

```bash
docker run --rm hello-world
```

---

## 1) Скачивание проекта

```bash
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ>
cd V2T
```

---

## 2) Создание файла конфигурации `.env`

Скопируйте шаблон:

```bash
cp .env.example .env
```

Откройте `.env` и заполните обязательные значения.

### 2.1 Telegram

- `TELEGRAM_BOT_TOKEN` — токен от `@BotFather`
- `TELEGRAM_WEBHOOK_SECRET` — любая длинная случайная строка

### 2.2 Google OAuth

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URL` (например: `https://your-domain.com/auth/google/callback`)

### 2.3 База данных и очередь

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL` (если используется явно)
- `REDIS_URL`

### 2.4 Speech-to-Text (выберите провайдер)

- `STT_PROVIDER` (`vosk`, `faster_whisper`, `google`, `yandex`)
- Для Vosk: `STT_VOSK_MODEL_PATH`
- Для Google STT: `STT_GOOGLE_API_KEY`
- Для Yandex STT: `STT_YANDEX_API_KEY`, `STT_YANDEX_FOLDER_ID`

### 2.5 Google Notes mode

- `GOOGLE_NOTES_MODE=docs` или `GOOGLE_NOTES_MODE=sheets`
- Для Docs: `GOOGLE_DOCS_DOCUMENT_ID`
- Для Sheets: `GOOGLE_SHEETS_SPREADSHEET_ID`, `GOOGLE_SHEETS_TAB_NAME`

### 2.6 Платежи

- `PAYMENTS_PROVIDER` (`yookassa`, `cloudpayments`, `robokassa`)
- и соответствующие секреты провайдера:
  - `PAYMENTS_YOOKASSA_WEBHOOK_SECRET`
  - `PAYMENTS_CLOUDPAYMENTS_SECRET`
  - `PAYMENTS_ROBOKASSA_PASSWORD2`

---

## 3) Запуск через Docker (рекомендуется)

### Шаг 1. Поднять все сервисы

```bash
docker compose up -d --build
```

Проверить, что контейнеры действительно поднялись:

```bash
docker compose ps
```

### Шаг 2. Проверить, что API поднялся

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

Также можно проверить через Nginx (если контейнер `nginx` запущен):

```bash
curl http://localhost/health
```

### Шаг 3. Посмотреть логи

```bash
docker compose logs -f app
docker compose logs -f worker
docker compose logs -f postgres
docker compose logs -f redis
```

Если какой-то контейнер в статусе `Exit`, получите детали:

```bash
docker compose logs <service_name>
```

---

## 4) Миграции базы данных

Если в проекте используются Alembic-миграции, выполните:

```bash
docker compose exec app alembic upgrade head
```

Проверка текущей ревизии:

```bash
docker compose exec app alembic current
```

---

## 5) Настройка Telegram webhook

После того как у вас есть HTTPS-домен:

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhook/telegram",
    "secret_token": "'"${TELEGRAM_WEBHOOK_SECRET}"'"
  }'
```

Проверка webhook:

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

---

## 6) Настройка Google OAuth (пошагово)

1. Откройте Google Cloud Console.
2. Создайте проект.
3. Включите нужные API (Google Docs API и/или Google Sheets API).
4. Создайте OAuth Client (тип Web Application).
5. Добавьте Redirect URI:  
   `https://your-domain.com/auth/google/callback`
6. Скопируйте `Client ID` и `Client Secret` в `.env`.

Проверка генерации ссылки авторизации:

```bash
curl "http://localhost/auth/google?telegram_user_id=123456789"
```

---

## 7) Локальная разработка без Docker (опционально)

### Шаг 1. Установить зависимости

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

### Шаг 2. Запустить API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Шаг 3. Запустить worker

```bash
celery -A app.celery_app:celery_app worker --loglevel=INFO --queues=transcription
```

### Шаг 4. Запустить Telegram-бота (polling)

```bash
python -m app.bot.run
```

---

## 8) Проверки перед продом

```bash
ruff check app tests
pytest -q
```

---

## 9) Полезные команды Docker

```bash
# Перезапуск сервисов
docker compose restart app worker

# Остановить проект
docker compose down

# Остановить и удалить volumes (ОСТОРОЖНО: удалит данные БД/Redis)
docker compose down -v

# Пересобрать только API
docker compose build app
```

---

## 10) Частые проблемы и решения

### Ошибка `401/403` от Google
- проверьте `GOOGLE_CLIENT_ID/SECRET`;
- проверьте правильность `GOOGLE_REDIRECT_URL`;
- проверьте, что нужные Google API включены.

### Бот не получает сообщения
- проверьте, что webhook установлен;
- проверьте HTTPS и доступность `/webhook/telegram`;
- проверьте `TELEGRAM_BOT_TOKEN`.

### `curl http://localhost/health` не открывается
- проверьте, что контейнеры запущены: `docker compose ps`;
- проверьте API напрямую (минуя Nginx): `curl http://localhost:8000/health`;
- если `nginx` не поднялся, endpoint на `http://localhost/health` работать не будет;
- пересоберите и поднимите сервисы заново: `docker compose up -d --build`.

### Воркеры не обрабатывают задачи
- проверьте `redis` и `worker` в `docker compose ps`;
- проверьте логи: `docker compose logs -f worker`.

### `Cannot connect to redis://redis:6379/0 ... getaddrinfo failed`
- это обычно значит, что вы запускаете процесс **вне Docker**, а в `.env` стоит docker-host `redis`;
- для локального запуска укажите `REDIS_URL=redis://localhost:6379/0`;
- если у вас задано, также обновите:
  - `CELERY_BROKER_URL=redis://localhost:6379/0`
  - `CELERY_RESULT_BACKEND=redis://localhost:6379/0`
- либо запускайте worker внутри compose: `docker compose up -d worker redis`;
- проверьте доступность Redis: `redis-cli -h localhost -p 6379 ping` (должно вернуть `PONG`).

### `socket.gaierror: [Errno 8] getaddrinfo failed` при подключении к PostgreSQL
- это обычно значит, что в `DATABASE_URL` указан docker-host `postgres`, а вы запускаете бота локально;
- для локального запуска используйте, например:  
  `DATABASE_URL=postgresql+asyncpg://v2t:change-me@localhost:5432/v2t`
- убедитесь, что PostgreSQL реально запущен на `localhost:5432`;
- проверьте подключение: `psql -h localhost -p 5432 -U v2t -d v2t`.

### Ошибки STT
- проверьте выбранный `STT_PROVIDER`;
- проверьте ключи/API или путь к модели (`STT_VOSK_MODEL_PATH`).
