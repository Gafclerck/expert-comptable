"""Client Telegram minimal (long polling) en httpx, sans nouvelle
dependance. Testable par monkeypatch de `httpx.get`/`httpx.post` (meme
pattern que l'appel LLM du moteur : distinction par URL).

Phase 1 : get_me (diagnostic), get_updates (polling), send_message (envoi).
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

    def get_updates(self, offset: int | None = None, timeout: int | None = None) -> list[dict]:
        """Long polling getUpdates. `offset` = premier update_id a recevoir.
        `timeout` (long polling Telegram) doit rester sous le timeout HTTP."""
        poll = timeout or settings.TELEGRAM_POLL_TIMEOUT_SECONDS
        params = {"timeout": poll, "limit": 100}
        if offset is not None:
            params["offset"] = offset
        response = httpx.get(f"{self.base_url}/getUpdates", params=params, timeout=poll + 15)
        response.raise_for_status()
        result = _parse(response)
        return result if isinstance(result, list) else []

    def send_message(self, chat_id: int, text: str) -> int | None:
        """Envoie un message texte (tronque par le worker en blocs <= 4096).
        Retourne le message_id en cas de succes."""
        response = httpx.post(
            f"{self.base_url}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        result = _parse(response)
        if isinstance(result, dict) and result.get("message_id") is not None:
            return int(result["message_id"])
        return None