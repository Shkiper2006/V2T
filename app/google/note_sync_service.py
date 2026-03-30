from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from app.config import get_settings
from app.google.docs_service import GoogleDocsService
from app.google.oauth import GoogleOAuthService
from app.google.sheets_service import GoogleSheetsService
from app.repositories.subscription_repository import SubscriptionRepository


class GoogleNoteSyncServiceError(RuntimeError):
    """Raised when sync to Google cannot be completed."""


class GoogleNoteSyncService:
    def __init__(self, subscription_repository: SubscriptionRepository | None = None) -> None:
        self.settings = get_settings()
        self.subscription_repository = subscription_repository or SubscriptionRepository()
        self.oauth_service = GoogleOAuthService()

    def sync_note(self, telegram_user_id: int, text: str) -> str:
        user = asyncio.run(self.subscription_repository.get_user(user_id=telegram_user_id))
        access_token = user.google_access_token
        refresh_token = user.google_refresh_token

        if not access_token:
            raise GoogleNoteSyncServiceError("Google access token is not configured for user")

        if self._is_expired(user.google_token_expires_at):
            if not refresh_token:
                raise GoogleNoteSyncServiceError("Google refresh token is required to refresh access token")

            refresh_payload = asyncio.run(self.oauth_service.refresh_access_token(refresh_token=refresh_token))
            access_token = str(refresh_payload["access_token"])
            expires_at = self._build_expires_at(refresh_payload.get("expires_in"))
            asyncio.run(
                self.subscription_repository.save_google_tokens(
                    user_id=telegram_user_id,
                    access_token=access_token,
                    refresh_token=str(refresh_payload.get("refresh_token") or refresh_token),
                    expires_at=expires_at,
                )
            )

        mode = (user.google_notes_mode or self.settings.google_notes_mode or "docs").lower()

        if mode == "sheets":
            spreadsheet_id = self.settings.google_sheets_spreadsheet_id
            if not spreadsheet_id:
                raise GoogleNoteSyncServiceError("GOOGLE_SHEETS_SPREADSHEET_ID is not configured")
            GoogleSheetsService(
                spreadsheet_id=spreadsheet_id,
                tab_name=self.settings.google_sheets_tab_name,
            ).append_note(access_token=access_token, text=text)
            return "sheets"

        if mode == "docs":
            document_id = self.settings.google_docs_document_id
            if not document_id:
                raise GoogleNoteSyncServiceError("GOOGLE_DOCS_DOCUMENT_ID is not configured")
            GoogleDocsService(document_id=document_id).append_note(access_token=access_token, text=text)
            return "docs"

        raise GoogleNoteSyncServiceError(f"Unsupported google notes mode: {mode}")

    @staticmethod
    def _is_expired(expires_at: datetime | None) -> bool:
        if expires_at is None:
            return False
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(tz=UTC)

    @staticmethod
    def _build_expires_at(expires_in: object) -> datetime | None:
        if expires_in is None:
            return None
        return datetime.now(tz=UTC) + timedelta(seconds=int(expires_in))
