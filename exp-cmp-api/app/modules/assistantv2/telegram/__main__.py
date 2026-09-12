"""Point d'entree du processus de canal Telegram (worker).

Phase 0 : valide la config et le token (`get_me`) puis quitte. La boucle de
long polling (`get_updates`) arrive en Phase 1 (docs/TELEGRAM_INTEGRATION.md).

Codes de sortie :
  0  canal desactive (TELEGRAM_ENABLED=false) ou bot valide ;
  1  canal active mais TELEGRAM_BOT_TOKEN absent ;
  2  token refuse par l'API Telegram (get_me en echec).

Lancer : python -m app.modules.assistantv2.telegram (depuis exp-cmp-api/).
"""
from app.core.config import settings
from app.modules.assistantv2.telegram.client import TelegramAPIError, TelegramClient


def main() -> int:
    if not settings.TELEGRAM_ENABLED:
        print("[telegram] TELEGRAM_ENABLED=false : canal inactif, sortie.")
        return 0
    if not settings.TELEGRAM_BOT_TOKEN:
        print("[telegram] TELEGRAM_ENABLED=true mais TELEGRAM_BOT_TOKEN absent : sortie (code 1).")
        return 1
    client = TelegramClient()
    try:
        me = client.get_me()
    except TelegramAPIError as exc:
        print(f"[telegram] get_me refuse par l'API : {exc.description} (code 2).")
        return 2
    username = me.get("username") or "?"
    print(f"[telegram] {username} valide et pret pour la Phase 1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())