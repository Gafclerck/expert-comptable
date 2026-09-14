"""Persistance du plan d'execution en cours, par session_id, dans Redis.
Identique en esprit a assistantv2/session_store.py : cle prefixee, TTL, pas de
verite alternative a synchroniser ailleurs.
"""
import json

from app.modules.assistantv3.plan import Plan

PLAN_TTL_SECONDS = 30 * 60  # 30 minutes d'inactivite
_KEY_PREFIX = "assistantv3:plan:"

_client = None


def get_redis_client():
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
    get_redis_client().set(_key(plan.session_id), json.dumps(plan.to_dict(), ensure_ascii=False), ex=PLAN_TTL_SECONDS)


def delete_plan(session_id: str) -> None:
    get_redis_client().delete(_key(session_id))
