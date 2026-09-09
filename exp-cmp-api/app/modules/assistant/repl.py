import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BASE_URL = os.environ.get("ASSISTANT_BASE_URL", "http://127.0.0.1:8000")


def _login() -> str:
    email = os.environ.get("SUPER_USER_EMAIL", "gafclerck@gmail.com")
    password = os.environ.get("SUPER_USER_PASSWORD", "Passer123/")
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{BASE_URL}/api/auth/login",
            data={"username": email, "password": password},
        )
        response.raise_for_status()
        return response.json()["access_token"]


def main() -> None:
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}
    session_id = None
    print("Assistante comptable (Assurance). 'exit'/'quit' pour quitter. 'aide' pour les commandes.")
    with httpx.Client(timeout=30) as client:
        while True:
            try:
                message = input("assistant> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if message.lower() in ("exit", "quit", "q"):
                break
            if not message:
                continue
            response = client.post(
                f"{BASE_URL}/api/assistant/chat",
                headers=headers,
                json={"message": message, "session_id": session_id},
            )
            if response.status_code != 200:
                print(f"Erreur HTTP {response.status_code}: {response.text}")
                continue
            data = response.json()
            session_id = data["session_id"]
            print(data["text"])
            if data["clarification"]:
                print("[question en attente]")

    print("Au revoir.")

if __name__ == "__main__":
    main()