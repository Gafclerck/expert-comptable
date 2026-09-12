"""Point d'entree du processus de canal Telegram (worker de long polling).

Codes de sortie :
  0  canal desactive (TELEGRAM_ENABLED=false) ou arret propre du worker ;
  1  canal active mais TELEGRAM_BOT_TOKEN absent ;
  2  token refuse par l'API Telegram (get_me en echec) - pas de boucle qui
     poll en 401.

Lancer : python -m app.modules.assistantv2.telegram (depuis exp-cmp-api/).
"""
from app.core.config import settings
from app.modules.assistantv2.telegram.client import TelegramAPIError, TelegramClient
from app.modules.assistantv2.telegram.worker import TelegramWorker


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
    print(f"[telegram] @{me.get('username') or '?'} valide : lancement du polling.")
    return TelegramWorker(client=client).run_forever()


if __name__ == "__main__":
    raise SystemExit(main())