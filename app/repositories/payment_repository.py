from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_sessionmaker
from app.models import Payment


class PaymentRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._session_factory = session_factory or get_sessionmaker()

    async def create_or_update(
        self,
        *,
        user_id: int,
        provider: str,
        external_payment_id: str,
        status: str,
        amount: Decimal,
        currency: str,
        payload: dict,
    ) -> Payment:
        async with self._session_factory() as session:
            stmt = select(Payment).where(Payment.external_payment_id == external_payment_id)
            payment = await session.scalar(stmt)
            if payment is None:
                payment = Payment(
                    user_id=user_id,
                    provider=provider,
                    external_payment_id=external_payment_id,
                    status=status,
                    amount=amount,
                    currency=currency,
                    payload=payload,
                )
                session.add(payment)
            else:
                payment.status = status
                payment.payload = payload

            await session.commit()
            await session.refresh(payment)
            return payment
