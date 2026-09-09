"""Persistance du plan d'execution en cours, par session_id, dans Redis.
Remplace le `SESSIONS: dict[str, dict] = {}` en memoire de l'assistant v1, qui
ne survit ni a un redemarrage ni a plusieurs workers.

TTL : une session abandonnee (utilisateur qui ne repond jamais a une
clarification) expire d'elle-meme au lieu de s'accumuler indefiniment.
"""
import json

from app.modules.assistantv2.plan import Plan

PLAN_TTL_SECONDS = 30 * 60  # 30 minutes d'inactivite
_KEY_PREFIX = "assistantv2:plan:"

_client = None


def get_redis_client():
    """Cree le client Redis au premier usage (pas a l'import du module, pour ne
    pas exiger Redis disponible juste pour importer ce fichier)."""
    global _client
    if _client is None:
        import redis

        from app.core.config import settings

        _client = redis.from_url(settings.ASSISTANTV2_REDIS_URL, decode_responses=True)
    return _client


def _key(session_id: str) -> str:
    return f"{_KEY_PREFIX}{session_id}"


def load_plan(session_id: str) -> Plan | None:
    raw = get_redis_client().get(_key(session_id))
    if raw is None:
        return None
    return Plan.from_dict(json.loads(raw))


def save_plan(plan: Plan) -> None:
    get_redis_client().set(_key(plan.session_id), json.dumps(plan.to_dict(), ensure_ascii=False, default=str), ex=PLAN_TTL_SECONDS)


def delete_plan(session_id: str) -> None:
    get_redis_client().delete(_key(session_id))
