"""REPL de test manuel pour l'assistant v2, en attendant qu'il soit branche
sur l'API (voir app/modules/assistantv2/__init__.py). Contourne HTTP : ouvre
une session DB directement et appelle assistantv2_service.chat(), ce qui
permet de tester le vrai comportement du LLM (choix des outils, arguments)
que les tests automatises (reponses simulees) ne verifient pas.

Prerequis (dans .env) :
  - ASSISTANT_LLM_API_KEY configuree (et ASSISTANT_LLM_API_URL / ASSISTANT_LLM_MODEL
    si different d'OpenAI). Sans cle, le moteur refuse de repondre.
  - Redis accessible a ASSISTANTV2_REDIS_URL (par defaut redis://localhost:6379/0).
    Le plus simple : `docker compose up -d redis` depuis la racine du projet.
  - Une base de dev deja initialisee (le super-admin doit exister : lancez
    l'app une premiere fois, ou appelez init_db, si ce n'est pas deja fait).

Lancement, depuis exp-cmp-api :
    uv run python -m app.modules.assistantv2.repl
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.core.config import settings
from app.core.db import session as db_session_factory
from app.modules.assistantv2 import service as assistantv2_service
from app.modules.identity.models import User

_CANCEL_HINT = "'exit'/'quit' pour quitter, 'annuler' pour reinitialiser la session en cours."


def _get_user(db) -> User:
    user = db.query(User).filter(User.email == settings.SUPER_USER_EMAIL).first()
    if user is None:
        raise SystemExit(
            f"Aucun utilisateur {settings.SUPER_USER_EMAIL!r} en base. Lancez l'app une "
            "premiere fois (ou appelez init_db) pour creer le super-admin avant de relancer ce REPL."
        )
    return user


def main() -> None:
    if not settings.ASSISTANT_LLM_API_KEY:
        raise SystemExit(
            "ASSISTANT_LLM_API_KEY n'est pas configuree dans l'environnement : "
            "l'assistant v2 refusera de repondre (voir orchestrator.handle_message). "
            "Ajoutez-la a votre .env avant de relancer."
        )

    db = db_session_factory()
    try:
        user = _get_user(db)
        session_id = None
        print(f"Assistant v2 (multi-tool-call). {_CANCEL_HINT}")
        print("Outils disponibles :")
        for tool in assistantv2_service.list_tools():
            business = tool["business"] or "transverse"
            critical = " [confirmation requise]" if tool["is_critical"] else ""
            print(f"  - [{business}] {tool['label']}{critical} : {tool['example']}")
        print()

        while True:
            try:
                message = input("assistantv2> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if message.lower() in ("exit", "quit", "q"):
                break
            if not message:
                continue

            try:
                reply = assistantv2_service.chat(db, user, message, session_id)
            except Exception as exc:  # confort manuel uniquement, jamais en production
                db.rollback()
                print(f"Erreur inattendue: {exc}")
                continue

            session_id = reply.session_id
            print(reply.text)
            if reply.clarification:
                print(f"  [en attente de clarification: {reply.missing_field}]")
            if reply.confirmation_required:
                print(f"  [en attente de confirmation pour: {reply.pending_action}]")
            if reply.executed_tools:
                print(f"  [outils executes: {', '.join(reply.executed_tools)}]")
    finally:
        db.close()
    print("Au revoir.")


if __name__ == "__main__":
    main()
