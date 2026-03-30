from __future__ import annotations

from app.repositories.note_repository import NoteRepository
from app.repositories.subscription_repository import SubscriptionRepository


class NoteService:
    def __init__(
        self,
        note_repository: NoteRepository,
        subscription_repository: SubscriptionRepository,
    ) -> None:
        self.note_repository = note_repository
        self.subscription_repository = subscription_repository

    async def create_summary_note(self, telegram_user_id: int, transcript: str, duration_seconds: int = 0) -> str:
        user = await self.subscription_repository.get_user(user_id=telegram_user_id)
        note_text = f"Краткая заметка: {transcript}"
        note = await self.note_repository.create(user_id=user.id, text=note_text, duration_seconds=duration_seconds)
        return note.text
