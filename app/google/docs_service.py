from __future__ import annotations

import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GoogleDocsServiceError(RuntimeError):
    """Raised when writing to Google Docs fails."""


class GoogleDocsService:
    def __init__(self, document_id: str) -> None:
        self.document_id = document_id

    def append_note(self, access_token: str, text: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] {text}\n"

        end_index = self._resolve_document_end_index(access_token=access_token)
        payload = {
            "requests": [
                {
                    "insertText": {
                        "location": {"index": end_index - 1},
                        "text": formatted,
                    }
                }
            ]
        }
        self._request(
            url=f"https://docs.googleapis.com/v1/documents/{self.document_id}:batchUpdate",
            access_token=access_token,
            method="POST",
            payload=payload,
        )

    def _resolve_document_end_index(self, access_token: str) -> int:
        response = self._request(
            url=f"https://docs.googleapis.com/v1/documents/{self.document_id}",
            access_token=access_token,
            method="GET",
            payload=None,
        )
        content = response.get("body", {}).get("content", [])
        if not content:
            raise GoogleDocsServiceError("Google Docs response does not contain document content")

        end_index = content[-1].get("endIndex")
        if not isinstance(end_index, int):
            raise GoogleDocsServiceError("Google Docs response does not contain endIndex")

        return end_index

    def _request(self, url: str, access_token: str, method: str, payload: dict | None) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            raise GoogleDocsServiceError(f"Google Docs API HTTP {exc.code}: {message}") from exc
        except URLError as exc:
            raise GoogleDocsServiceError(f"Google Docs API unavailable: {exc.reason}") from exc
