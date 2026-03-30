from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.bot.dispatcher import bot, dp
from app.google.oauth import GoogleOAuthService
from app.payments.webhooks import PaymentWebhookService
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.payment_service import PaymentService

router = APIRouter()
google_oauth_service = GoogleOAuthService()
payment_webhook_service = PaymentWebhookService()
subscription_repository = SubscriptionRepository()
payment_service = PaymentService(
    payment_repository=PaymentRepository(),
    subscription_repository=subscription_repository,
)


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
async def auth_google_callback(code: str, telegram_user_id: int | None = Query(default=None)) -> dict[str, str]:
    token_payload = await google_oauth_service.exchange_code_for_token(code=code)

    access_token = str(token_payload["access_token"])
    refresh_token = token_payload.get("refresh_token")
    expires_in = token_payload.get("expires_in")
    expires_at = (
        datetime.now(tz=timezone.utc) + timedelta(seconds=int(expires_in))
        if expires_in is not None
        else None
    )

    if telegram_user_id is not None:
        await subscription_repository.save_google_tokens(
            user_id=telegram_user_id,
            access_token=access_token,
            refresh_token=str(refresh_token) if refresh_token else None,
            expires_at=expires_at,
        )

    return {"status": "connected", "access_token": access_token}


@router.post("/users/{telegram_user_id}/google-mode")
async def set_google_mode(telegram_user_id: int, mode: str = Query(pattern="^(docs|sheets)$")) -> dict[str, str]:
    user = await subscription_repository.set_google_notes_mode(user_id=telegram_user_id, mode=mode)
    effective_mode = user.google_notes_mode or "docs"
    return {"status": "ok", "mode": effective_mode}


@router.post("/payment/webhook")
async def payment_webhook(
    request: Request,
    x_payment_provider: str = Header(alias="X-Payment-Provider"),
    x_payment_signature: str = Header(alias="X-Payment-Signature"),
) -> dict[str, str]:
    payload = await request.json()
    try:
        await payment_webhook_service.handle(
            provider=x_payment_provider,
            payload=payload,
            signature=x_payment_signature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "processed"}


@router.post("/payment/session")
async def create_payment_session(telegram_user_id: int, tariff: str = Query(default="pro")) -> dict:
    return await payment_service.create_payment_session(
        telegram_user_id=telegram_user_id,
        tariff_code=tariff,
    )
