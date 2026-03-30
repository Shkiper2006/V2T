# V2T (Voice-to-Text)

Инфраструктурный шаблон с FastAPI API, Telegram-ботом и Celery-воркером поверх Redis/PostgreSQL.

## Стек

- **API**: FastAPI (`app.main:app`)
- **Bot**: Aiogram (`python -m app.bot.run`)
- **Worker**: Celery (`celery -A app.celery_app:celery_app worker --loglevel=INFO --queues=transcription`)
- **Infra**: Redis, PostgreSQL, Nginx
- **Quality**: Ruff + Pytest
- **CI**: GitHub Actions (lint + unit tests + docker build)

## 1) Быстрый старт

```bash
cp .env.example .env
```

Заполните в `.env` обязательные блоки:

- Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`
- Google: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URL`
- Redis: `REDIS_URL`
- Postgres: `DATABASE_URL` (или `POSTGRES_*`)
- STT: `STT_PROVIDER` + ключи выбранного провайдера (`STT_GOOGLE_API_KEY` / `STT_YANDEX_*` / `STT_VOSK_MODEL_PATH`)
- Платежи: `PAYMENTS_PROVIDER` + секрет соответствующего провайдера
  (`PAYMENTS_YOOKASSA_WEBHOOK_SECRET` / `PAYMENTS_CLOUDPAYMENTS_SECRET` / `PAYMENTS_ROBOKASSA_PASSWORD2`)
- Тарифы: `TARIFF_BASIC_MAX_VOICE_SECONDS`, `TARIFF_PRO_MAX_VOICE_SECONDS`, `TARIFF_BASIC_PRICE_RUB`, `TARIFF_PRO_PRICE_RUB`

Запуск через Docker Compose:

```bash
docker compose up -d --build
```

Проверка:

```bash
curl http://localhost/health
```

## 2) Локальные команды разработки

Установить зависимости:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

Проверки качества:

```bash
ruff check app tests
pytest
```

Запуск API локально:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Запуск воркера:

```bash
celery -A app.celery_app:celery_app worker --loglevel=INFO --queues=transcription
```

Запуск polling-бота:

```bash
python -m app.bot.run
```

## 3) CI

Workflow `.github/workflows/ci.yml` выполняет:

1. `ruff check app tests`
2. `pytest`
3. `docker build` по target'ам `api`, `worker`, `bot`

## 4) Полезные Docker команды

```bash
# Логи API
docker compose logs -f app

# Логи worker
docker compose logs -f worker

# Пересобрать только API
docker compose build app

# Остановить всё
docker compose down
```
