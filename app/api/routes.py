from fastapi import APIRouter, HTTPException, Request

from app.bot.dispatcher import bot, dp
from app.google.oauth import GoogleOAuthService
from app.payments.webhooks import PaymentWebhookService

router = APIRouter()
google_oauth_service = GoogleOAuthService()
payment_webhook_service = PaymentWebhookService()


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request) -> dict[str, str]:
    if bot is None:
        raise HTTPException(status_code=503, detail="Telegram bot token is not configured")

    data = await request.json()
    await dp.feed_raw_update(bot=bot, update=data)
    return {"status": "ok"}


@router.get("/auth/google")
async def auth_google() -> dict[str, str]:
    return {"auth_url": google_oauth_service.build_auth_url()}


@router.get("/auth/google/callback")
async def auth_google_callback(code: str) -> dict[str, str]:
    token = await google_oauth_service.exchange_code_for_token(code=code)
    return {"status": "connected", "access_token": token}


@router.post("/payment/webhook")
async def payment_webhook(request: Request) -> dict[str, str]:
    payload = await request.json()
    await payment_webhook_service.handle(payload)
    return {"status": "processed"}
