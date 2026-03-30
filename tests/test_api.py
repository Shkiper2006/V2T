import asyncio

from app.api.routes import auth_google
from app.main import health


def test_healthcheck() -> None:
    payload = asyncio.run(health())
    assert payload == {"status": "ok"}


def test_google_auth_url_endpoint() -> None:
    payload = asyncio.run(auth_google())
    assert "auth_url" in payload
    assert payload["auth_url"].startswith("https://accounts.google.com/o/oauth2/v2/auth")
