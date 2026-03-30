from __future__ import annotations

import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class GoogleSheetsServiceError(RuntimeError):
    """Raised when writing to Google Sheets fails."""


class GoogleSheetsService:
    def __init__(self, spreadsheet_id: str, tab_name: str = "Sheet1") -> None:
        self.spreadsheet_id = spreadsheet_id
        self.tab_name = tab_name

    def append_note(self, access_token: str, text: str) -> None:
        now = datetime.now()
        payload = {
            "values": [[now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), text]],
        }
        tab_range = quote(f"{self.tab_name}!A:C", safe="")
        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/"
            f"{tab_range}:append?valueInputOption=USER_ENTERED"
        )
        self._request(url=url, access_token=access_token, payload=payload)

    def _request(self, url: str, access_token: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            raise GoogleSheetsServiceError(f"Google Sheets API HTTP {exc.code}: {message}") from exc
        except URLError as exc:
            raise GoogleSheetsServiceError(f"Google Sheets API unavailable: {exc.reason}") from exc
