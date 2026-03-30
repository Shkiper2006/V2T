from urllib.parse import urlencode

from app.config import get_settings


class GoogleOAuthService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_auth_url(self) -> str:
        query = urlencode(
            {
                "client_id": self.settings.google_client_id,
                "redirect_uri": self.settings.google_redirect_url,
                "response_type": "code",
                "scope": "openid email profile",
                "access_type": "offline",
                "prompt": "consent",
            }
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    async def exchange_code_for_token(self, code: str) -> str:
        # Stub implementation. In production, call Google token endpoint.
        return f"token_from_code_{code}"
