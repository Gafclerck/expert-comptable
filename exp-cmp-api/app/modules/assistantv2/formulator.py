"""Formule la reponse finale a partir des FAITS structures rassembles par un
ou plusieurs outils executes dans le meme tour. Meme garde-fou anti-
hallucination qu'en v1 (`assistant/formulator.py`), assoupli sur un point :
la comparaison ignore les espaces, pour ne pas rejeter une reponse a cause
d'un simple "40000" ecrit par le LLM la ou le fait donne "40 000".
"""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Tu rediges la reponse finale d'un assistant de gestion financiere multi-activites "
    "(assurance, poulailler, et d'autres a venir) apres qu'une ou plusieurs operations aient "
    "ete executees par le systeme. On te fournit des FAITS exacts par operation (montants, "
    "matricules, noms, dates, statuts, quantites). Appuie-toi uniquement sur ces faits : "
    "reproduis exactement les valeurs chiffrees, matricules, dates et quantites, tels qu'ils "
    "sont donnes, sans arrondir, sans additionner, sans inventer et sans en omettre aucun. "
    "Si plusieurs operations ont ete executees, resume-les toutes en une reponse coherente. "
    "Reponds en francais, de facon naturelle et concise, en phrases courtes. Si une liste est "
    "vide, indique qu'il n'y a rien a afficher. N'utilise jamais le mot 'fait' et ne mentionne "
    "jamais la source des donnees."
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


def _squash(text: str) -> str:
    return "".join(text.split())


def _assert_facts_present(results: list[dict], content: str) -> None:
    squashed_content = _squash(content)
    missing = []
    for result in results:
        for fact in _iter_fact_strings(result):
            if _squash(fact) not in squashed_content:
                missing.append(fact)
    if missing:
        raise ValueError(f"reponse LLM omettant des faits: {missing}")


class Formulator:
    def __init__(self, api_url: str, api_key: str, model: str):
        self._api_url = api_url
        self._api_key = api_key
        self._model = model

    def formulate(self, operations: list[tuple[str, dict]], user_message: str = "") -> str:
        import httpx

        url = f"{self._api_url.rstrip('/')}/chat/completions"
        facts_blob = json.dumps(
            [{"operation": op, "facts": facts} for op, facts in operations],
            ensure_ascii=False,
            default=str,
        )
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Operations realisees et leurs FAITS (a reprendre tels quels):\n{facts_blob}\n"
                        f"Demande initiale de l'utilisateur: {user_message[:300]}"
                    ),
                },
            ],
            "temperature": 0,
        }
        response = httpx.post(url, headers={"Authorization": f"Bearer {self._api_key}"}, json=payload, timeout=20)
        response.raise_for_status()
        content = (response.json()["choices"][0]["message"].get("content") or "").strip()
        if not content:
            raise ValueError("reponse LLM vide")
        _assert_facts_present([facts for _, facts in operations], content)
        return content


def get_formulator():
    from app.core.config import settings

    if settings.ASSISTANT_LLM_API_KEY and settings.ASSISTANT_LLM_ENABLE_FORMULATION:
        return Formulator(
            settings.ASSISTANT_LLM_API_URL or "https://api.openai.com/v1",
            settings.ASSISTANT_LLM_API_KEY,
            settings.ASSISTANT_LLM_MODEL,
        )
    return None
