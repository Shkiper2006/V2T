from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import get_settings


GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


class GoogleOAuthError(RuntimeError):
    """Raised when Google OAuth interaction fails."""


class GoogleOAuthService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_auth_url(self) -> str:
        query = urlencode(
            {
                "client_id": self.settings.google_client_id,
                "redirect_uri": self.settings.google_redirect_url,
                "response_type": "code",
                "scope": "openid email profile https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/spreadsheets",
                "access_type": "offline",
                "prompt": "consent",
            }
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    async def exchange_code_for_token(self, code: str) -> dict[str, str | int | None]:
        payload = {
            "code": code,
            "client_id": self.settings.google_client_id,
            "client_secret": self.settings.google_client_secret,
            "redirect_uri": self.settings.google_redirect_url,
            "grant_type": "authorization_code",
        }
        return await asyncio.to_thread(self._post_form, payload)

    async def refresh_access_token(self, refresh_token: str) -> dict[str, str | int | None]:
        payload = {
            "client_id": self.settings.google_client_id,
            "client_secret": self.settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        return await asyncio.to_thread(self._post_form, payload)

    def calculate_expiry(self, expires_in: int | None) -> datetime | None:
        if not expires_in:
            return None
        return datetime.now(tz=timezone.utc).replace(microsecond=0) + timedelta(seconds=int(expires_in))

    def _post_form(self, payload: dict[str, str]) -> dict[str, str | int | None]:
        body = urlencode(payload).encode("utf-8")
        request = Request(
            GOOGLE_TOKEN_ENDPOINT,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310
                parsed = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            raise GoogleOAuthError(f"Google token endpoint HTTP {exc.code}: {message}") from exc
        except URLError as exc:
            raise GoogleOAuthError(f"Google token endpoint unavailable: {exc.reason}") from exc

        if "access_token" not in parsed:
            raise GoogleOAuthError(f"Google token response has no access_token: {parsed}")

        return {
            "access_token": parsed.get("access_token"),
            "refresh_token": parsed.get("refresh_token"),
            "expires_in": parsed.get("expires_in"),
            "scope": parsed.get("scope"),
            "token_type": parsed.get("token_type"),
            "id_token": parsed.get("id_token"),
        }
