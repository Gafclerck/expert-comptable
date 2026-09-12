"""Client Telegram minimal (long polling) en httpx, sans nouvelle
dependance. Testable par monkeypatch de `httpx.get`/`httpx.post` (meme
pattern que l'appel LLM du moteur : distinction par URL).

Phase 0 : diagnostic `get_me`. Les methodes `get_updates` et `send_message`
arrivent en Phase 1 (voir docs/TELEGRAM_INTEGRATION.md).
"""
from __future__ import annotations

import httpx

from app.core.config import settings

API_BASE = "https://api.telegram.org"
_HTTP_TIMEOUT = 15.0


class TelegramAPIError(RuntimeError):
    """L'API Telegram a repondu `ok: false` (voir Bot API getMe/getUpdates)."""

    def __init__(self, description: str, parameters: dict | None = None):
        self.description = description
        self.parameters = parameters or {}
        super().__init__(description)


def _parse(response: httpx.Response) -> dict:
    payload = response.json()
    if not payload.get("ok", False):
        raise TelegramAPIError(
            payload.get("description", "Erreur inconnue de l'API Telegram"),
            payload.get("parameters"),
        )
    return payload.get("result")


class TelegramClient:
    """Wrapper minimal autour de la Bot API Telegram."""

    def __init__(self, token: str | None = None):
        self.token = token if token is not None else settings.TELEGRAM_BOT_TOKEN
        if not self.token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN manquant : configurer le canal Telegram "
                "(voir docs/TELEGRAM_INTEGRATION.md)."
            )

    @property
    def base_url(self) -> str:
        return f"{API_BASE}/bot{self.token}"

    def get_me(self) -> dict:
        """Diagnostic : identite du bot (username, first_name, ...)."""
        response = httpx.get(f"{self.base_url}/getMe", timeout=_HTTP_TIMEOUT)
        response.raise_for_status()
        return _parse(response)