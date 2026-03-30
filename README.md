# V2T (Voice-to-Text)

Инфраструктурный шаблон для API, Telegram-бота и Celery-воркера с Redis/PostgreSQL, Nginx reverse proxy и HTTPS.

## Стек

- **API**: FastAPI (`app.main:app`)
- **Bot**: Aiogram (`app.bot.run`)
- **Worker**: Celery (`app.celery_app:celery_app`)
- **Infra**: Redis, PostgreSQL, Nginx
- **CI**: GitHub Actions (lint, unit tests, image build)

---

## 1) Быстрый локальный запуск

### Подготовка

```bash
cp .env.example .env
```

Заполните минимум:

- `TELEGRAM_BOT_TOKEN`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `POSTGRES_PASSWORD`
- платежные ключи (`STRIPE_*` или `YOOKASSA_*`)
- ключи STT, если используете облачные провайдеры

### Запуск API + worker + infra

```bash
docker compose up -d --build
```

Проверка:

```bash
curl http://localhost/health
```

### Запуск Telegram polling-бота (опционально)

Сервис `bot` подключен как profile:

```bash
docker compose --profile bot up -d --build bot
```

> Для production обычно используется **webhook** (а не polling), поэтому `bot` можно не запускать.

---

## 2) Деплой на сервер (Docker Compose)

1. Установите Docker + Docker Compose Plugin.
2. Скопируйте проект на сервер.
3. Создайте `.env` на базе `.env.example`.
4. Обновите домен в `deploy/nginx/conf.d/default.conf`:
   - `server_name v2t.example.com;`
   - путь сертификатов `/etc/letsencrypt/live/v2t.example.com/...`
5. Поднимите стек:

```bash
docker compose up -d --build
```

---

## 3) Nginx reverse proxy + HTTPS (Let's Encrypt)

Nginx уже настроен на:

- reverse proxy на `app:8000`
- отдельные маршруты для:
  - `/webhook/telegram`
  - `/auth/google/callback`
- ACME webroot: `/.well-known/acme-challenge/`
- редирект `HTTP -> HTTPS`

### Получение сертификата

Пример с `certbot` (на хосте):

```bash
mkdir -p deploy/nginx/certbot/conf deploy/nginx/certbot/www

certbot certonly \
  --webroot \
  -w ./deploy/nginx/certbot/www \
  -d v2t.example.com \
  --email you@example.com \
  --agree-tos \
  --non-interactive
```

После выпуска перезапустите Nginx:

```bash
docker compose restart nginx
```

### Автопродление

Добавьте cron на сервере:

```bash
0 3 * * * certbot renew --quiet && cd /path/to/V2T && docker compose restart nginx
```

---

## 4) Настройка Telegram webhook

После деплоя и получения HTTPS-сертификата:

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://v2t.example.com/webhook/telegram",
    "secret_token": "<TELEGRAM_WEBHOOK_SECRET>"
  }'
```

Проверка:

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

---

## 5) Настройка Google OAuth

В Google Cloud Console:

1. Создайте OAuth Client ID (Web application).
2. Добавьте Authorized redirect URI:
   - `https://v2t.example.com/auth/google/callback`
3. Сохраните значения в `.env`:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URL=https://v2t.example.com/auth/google/callback`

Проверка ручки:

```bash
curl https://v2t.example.com/auth/google
```

---

## 6) Настройка платежей

Поддержаны переменные под Stripe / YooKassa (провайдер-agnostic слой).

Минимально:

- `PAYMENTS_PROVIDER` (`stripe` или `yookassa`)
- `PAYMENTS_WEBHOOK_SECRET`
- `PAYMENTS_SUCCESS_URL`
- `PAYMENTS_CANCEL_URL`
- для Stripe: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`
- для YooKassa: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`

Webhook endpoint в API:

- `POST /payment/webhook`

---

## 7) Тарифы

Тарифные лимиты и цены задаются env-переменными:

- `TARIFF_BASIC_MAX_VOICE_SECONDS`
- `TARIFF_PRO_MAX_VOICE_SECONDS`
- `TARIFF_BASIC_PRICE_RUB`
- `TARIFF_PRO_PRICE_RUB`

Изменения применяются после перезапуска сервисов:

```bash
docker compose up -d
```

---

## 8) CI (GitHub Actions)

Workflow `.github/workflows/ci.yml` выполняет:

1. **lint**: `ruff check app tests`
2. **unit-tests**: `pytest -q`
3. **build-images**: сборка Docker target'ов `api`, `worker`, `bot`

---

## 9) Полезные команды

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
