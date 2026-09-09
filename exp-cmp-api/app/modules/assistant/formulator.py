import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Tu rediges la reponse finale d'un assistant de gestion financiere (assurance, "
    "poulailler) apres qu'une operation soit executee par le systeme. On te fournit des "
    "FAITS exacts (montants, matricules, noms, dates, statuts, quantites). Reappuie-toi "
    "uniquement sur ces faits : reproduis exactement les valeurs chiffrees, matricules, "
    "dates et quantites, tels qu'ils sont donnes, sans arrondir, sans additionner, sans "
    "inventer et sans en omettre aucun. Reponds en francais, de facon naturelle et "
    "concise, en phrases courtes. Si une liste est vide, indique qu'il n'y a rien a "
    "afficher. N'utilise jamais le mot 'fait' et ne mentionne jamais la source des donnees."
)


def _iter_fact_strings(node: Any):
    if isinstance(node, dict):
        for value in node.values():
            yield from _iter_fact_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_fact_strings(value)
    elif isinstance(node, str):
        if any(ch.isdigit() for ch in node):
            yield node
    elif node is not None:
        yield str(node)


def _assert_facts_present(result: dict, content: str) -> None:
    """Garde-fou anti-hallucination : chaque valeur chiffree du resultat doit apparaitre
    telle quelle dans la reponse du LLM, sinon la formulation est refuse et le repli
    statique est utilise.
    """
    missing = [fact for fact in _iter_fact_strings(result) if fact not in content]
    if missing:
        raise ValueError(f"reponse LLM omettant des faits: {missing}")


class Formulator:
    """Formule la reponse finale (le reply) a partir du resultat STRUCTURE de
    l'execution, via une API compatible OpenAI (/v1/chat/completions). Aucun
    tool-calling ici : le LLM ne fait que rediger, et le garde-fou
    `_assert_facts_present` verifie que les montants/dates/matricules sont
    reproduits tels quels.
    """

    def __init__(self, api_url: str, api_key: str, model: str):
        self._api_url = api_url
        self._api_key = api_key
        self._model = model

    def formulate(self, operation: str, result: dict, user_message: str = "") -> str:
        import httpx

        url = f"{self._api_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Operation realisee: {operation}\n"
                        f"FAITS (a reprendre tels quels):\n"
                        f"{json.dumps(result, ensure_ascii=False, default=str)}\n"
                        f"Demande initiale de l'utilisateur: {user_message[:300]}"
                    ),
                },
            ],
            "temperature": 0,
        }
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        content = (response.json()["choices"][0]["message"].get("content") or "").strip()
        if not content:
            raise ValueError("reponse LLM vide")
        _assert_facts_present(result, content)
        return content


def get_formulator():
    """None si aucune cle LLM : le service garde alors la reponse statique."""
    from app.core.config import settings

    if settings.ASSISTANT_LLM_API_KEY and settings.ASSISTANT_LLM_ENABLE_FORMULATION:
        return Formulator(
            settings.ASSISTANT_LLM_API_URL or "https://api.openai.com/v1",
            settings.ASSISTANT_LLM_API_KEY,
            settings.ASSISTANT_LLM_MODEL,
        )
    return None