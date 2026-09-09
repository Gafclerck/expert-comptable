import logging
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.events import publish
from app.modules.assistant.executor import (
    _name_match,
    execute,
    resolve_account,
    resolve_category,
    resolve_contract,
)
from app.modules.assistant.formulator import get_formulator
from app.modules.assistant.interpreter import (
    extract_client_name,
    get_interpreter,
    parse_amount,
    parse_client_number,
    parse_due_date,
    parse_matricule,
    parse_quantity,
)
from app.modules.assistant.intents import INTENTS, business_code_for
from app.modules.assistant.schemas import AssistantReply
from app.modules.identity.service import get_business_by_code, get_business_ids_for_user, list_businesses
from app.modules.insurance import service as insurance_service
from app.modules.ledger import service as ledger_service
from app.modules.ledger.models import CategoryType

SESSIONS: dict[str, dict] = {}

logger = logging.getLogger(__name__)

_ORDER = {
    "create_client": ["client"],
    "create_contract": ["client", "matricule", "premium"],
    "record_payment": ["contract", "amount", "account", "category"],
    "get_balance": ["account"],
    "get_remaining": ["contract"],
    "get_client_info": ["client"],
    "get_contract_info": ["contract"],
    "get_dues": ["contract"],
    "add_due": ["contract", "due_date", "amount"],
    "add_purchase": ["quantity", "amount", "account", "category"],
    "add_sale": ["quantity", "amount", "account", "category"],
    "get_stock": [],
    "help": [],
}

_CANCEL = {"annuler", "annule", "cancel", "stop", "quitter"}

_QUESTIONS = {
    "client": "Quel client ? Indiquez le nom (ex. Moussa Camara).",
    "matricule": "Quelle matricule ? (ex. MAT-001)",
    "premium": "Quel montant de prime ? (ex. 100 000)",
    "contract": "Pour quel contrat ? Indiquez la matricule (ex. MAT-001) ou le nom du client.",
    "amount": "Quel montant encaisser ? (ex. 40 000)",
    "account": "Sur quelle caisse ?",
    "category": "Sous quelle categorie ?",
    "due_date": "Pour quelle date ? (ex. 30/09/2026)",
    "quantity": "Combien de poulets ?",
}


def _normalize(value: str) -> str:
    import unicodedata

    return "".join(
        ch for ch in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(ch) != "Mn"
    ).strip()


def _clean_free_text(message: str) -> str | None:
    cleaned = _normalize(message).strip(".,;!? ")
    return cleaned or None


def _next_missing(draft: dict) -> str | None:
    params = draft["params"]
    for field in _ORDER.get(draft["operation"], []):
        key = f"{field}_id" if field in ("account", "category") else field
        if not params.get(key):
            return field
    return None


def _choose_index(message: str, items: list) -> int | None:
    text = _normalize(message).strip()
    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(items):
            return index
    words = {"1": 0, "premier": 0, "premiere": 0, "2": 1, "deuxieme": 1, "3": 2, "troisieme": 2, "4": 3}
    if text in words and words[text] < len(items):
        return words[text]
    return None


def _accessible_businesses(db: Session, user, current_code: str) -> list:
    """Liste des activites accessibles, en mettant l'activite courante en tete."""
    accessible_ids = get_business_ids_for_user(db, user)
    result = []
    for b in list_businesses(db):
        if accessible_ids is not None and b.id not in accessible_ids:
            continue
        if b.code == current_code:
            result.insert(0, b)
        else:
            result.append(b)
    return result


def _resolve_account_with_fallback(db: Session, user, draft: dict, business) -> bool:
    """Resout la caisse pour une demande transversale (get_balance). Cherche d'abord
    sur l'activite courante, puis sur les autres activites accessibles quand le nom
    donne ne matche aucune caisse (ex. « solde caisse poulailler » enonce sans
    business, ou une reference qui designe l'activite elle-meme). Enregistre le
    business retenu dans params pour que l'executeur interroge la bonne activite.
    Ne leve jamais : renvoie False si rien n'a ete resolu (les choix eventuels sont
    poses dans draft["choices"]["account"]).
    """
    params = draft["params"]
    ref = params.get("account")
    candidates_by_business: list[tuple] = []
    for b in _accessible_businesses(db, user, business.code):
        try:
            account, candidates = resolve_account(db, user, b.id, ref)
        except HTTPException:
            account, candidates = None, []
        if account is not None:
            params["account_id"] = str(account.id)
            params["account_name"] = account.name
            params["business_id"] = str(b.id)
            return True
        if candidates:
            candidates_by_business.append((b, candidates))
            continue
        if ref and (_name_match(b.name, ref) or _name_match(b.code, ref)):
            # La reference designe l'activite elle-meme (« caisse poulailler » → poulets) :
            # on prend la caisse par defaut de cette activite et on route vers elle.
            default, _ = resolve_account(db, user, b.id)
            if default is not None:
                params["account_id"] = str(default.id)
                params["account_name"] = default.name
                params["business_id"] = str(b.id)
                return True
    if candidates_by_business:
        b, candidates = candidates_by_business[0]
        draft["choices"]["account"] = [{"name": a.name, "id": str(a.id)} for a in candidates]
    return False


def _prepare(db: Session, user, draft: dict) -> None:
    op = draft["operation"]
    params = draft["params"]
    business = get_business_by_code(db, business_code_for(op, draft.get("business")))
    if op in ("record_payment", "get_remaining", "get_contract_info", "get_dues", "add_due"):
        ref = params.get("contract")
        if ref and not params.get("contract_id"):
            try:
                contract = resolve_contract(db, user, ref)
                params["contract_id"] = str(contract.id)
            except HTTPException:
                params.pop("contract", None)
                draft["error"] = "Contrat introuvable ou ambigu. Precisez la matricule."
    if op == "get_balance" and not params.get("account_id"):
        if not _resolve_account_with_fallback(db, user, draft, business):
            if not draft["choices"].get("account"):
                draft["error"] = "Aucune caisse trouvee pour cette activite."
    elif op in ("record_payment", "add_purchase", "add_sale") and not params.get("account_id"):
        try:
            account, candidates = resolve_account(db, user, business.id, params.get("account"))
            if account is not None:
                params["account_id"] = str(account.id)
                params["account_name"] = account.name
            else:
                draft["choices"]["account"] = [{"name": a.name, "id": str(a.id)} for a in candidates]
        except HTTPException as exc:
            params.pop("account", None)
            draft["error"] = str(exc.detail)
    if op in ("record_payment", "add_sale", "add_purchase") and not params.get("category_id"):
        ctype = CategoryType.DEBIT if op == "add_purchase" else CategoryType.CREDIT
        try:
            category, candidates = resolve_category(db, ctype, params.get("category"))
            if category is not None:
                params["category_id"] = str(category.id)
            else:
                draft["choices"]["category"] = [{"name": c.name, "id": str(c.id)} for c in candidates]
        except HTTPException as exc:
            draft["error"] = str(exc.detail)


def _question_text(draft: dict, field: str) -> str:
    question = _QUESTIONS[field]
    options = draft["choices"].get(field, [])
    if options:
        lines = [f"{i + 1}) {item['name']}" for i, item in enumerate(options)]
        return question + "\n" + "\n".join(lines)
    return question


def _ask(session_id: str, draft: dict, field: str) -> AssistantReply:
    return AssistantReply(
        text=_question_text(draft, field),
        session_id=session_id,
        intent=draft["operation"],
        clarification=True,
        missing_field=field,
        options=[item["name"] for item in draft["choices"].get(field, [])],
    )


def _fill(db: Session, user, draft: dict, field: str, message: str) -> bool:
    params = draft["params"]
    business = get_business_by_code(db, business_code_for(draft["operation"], draft.get("business")))
    if field == "client":
        name = extract_client_name(message) or _clean_free_text(message)
        if not name:
            return False
        params["client"] = name
        return True
    if field == "matricule":
        matricule = parse_matricule(message)
        if not matricule:
            return False
        params["matricule"] = matricule
        return True
    if field in ("premium", "amount"):
        amount = parse_amount(message)
        if amount is None and field == "amount" and params.get("contract_id"):
            norm = _normalize(message)
            if any(word in norm for word in ("reste", "reliquat")):
                contract = insurance_service.get_contract(db, user, uuid.UUID(params["contract_id"]))
                amount = insurance_service.remaining_amount(db, contract)
        if amount is None or amount <= 0:
            return False
        params[field] = amount
        return True
    if field == "due_date":
        due_date = parse_due_date(message)
        if not due_date:
            return False
        params["due_date"] = due_date
        return True
    if field == "quantity":
        text = message.strip()
        quantity = parse_quantity(message) or (int(text) if text.isdigit() else None)
        if not quantity or quantity <= 0:
            return False
        params["quantity"] = quantity
        return True
    if field == "contract":
        matricule = parse_matricule(message)
        name = parse_client_number(message) or extract_client_name(message) or _clean_free_text(message)
        params["contract"] = matricule or name
        params.pop("contract_id", None)
        return bool(params.get("contract"))
    if field == "account":
        candidates = draft["choices"].get("account", [])
        index = _choose_index(message, candidates)
        if index is not None:
            params["account_id"] = candidates[index]["id"]
            params["account_name"] = candidates[index]["name"]
            return True
        params["account"] = message.strip(".,")
        return _resolve_account_with_fallback(db, user, draft, business)
    if field == "category":
        candidates = draft["choices"].get("category", [])
        index = _choose_index(message, candidates)
        if index is not None:
            params["category_id"] = candidates[index]["id"]
            return True
        try:
            category, _ = resolve_category(db, CategoryType.DEBIT if draft["operation"] == "add_purchase" else CategoryType.CREDIT, message.strip(".,"))
            if category is not None:
                params["category_id"] = str(category.id)
                return True
        except HTTPException:
            return False
        return False
    return False


def _run(db: Session, user, draft: dict, session_id: str) -> AssistantReply:
    op = draft["operation"]
    params = draft["params"]
    try:
        result, target_id, static_text = execute(db, user, op, params)
    except HTTPException as exc:
        db.rollback()
        text = f"Erreur: {exc.detail}"
        target_id = None
    else:
        formulator = get_formulator()
        if formulator is None:
            text = static_text
        else:
            try:
                text = formulator.formulate(op, result, draft.get("message", ""))
            except Exception:
                logger.warning("Formulation LLM indisponible, repli sur le texte statique", exc_info=True)
                text = static_text
    publish(
        "assistant.command.executed",
        actor_id=str(user.id),
        entity_id=str(target_id) if target_id else None,
        new_values={
            "operation": op,
            "params": {key: str(value) for key, value in params.items()},
            "message": text,
        },
    )
    return AssistantReply(text=text, session_id=session_id, intent=op, executed=True)


def _unknown_reply(session_id: str) -> AssistantReply:
    help_text = (
        "Je n'ai pas compris. Demandez par exemple: \"Encaisser 40 000 pour MAT-E2E\", "
        "\"Creer un client Moussa Camara\" ou \"Solde de la caisse\". "
        "Dites \"aide\" pour la liste complete."
    )
    return AssistantReply(text=help_text, session_id=session_id, intent="unknown")


def _help_reply(session_id: str) -> AssistantReply:
    lines = ["Voici ce que je peux faire:"]
    for op in INTENTS:
        lines.append(f"- {INTENTS[op]['label']} : {INTENTS[op]['example']}")
    return AssistantReply(text="\n".join(lines), session_id=session_id, intent="help")


_QUERIES = {"get_balance", "get_remaining", "get_client_info", "get_contract_info", "get_dues", "get_stock", "help"}


def _is_completion(draft: dict, operation: str) -> bool:
    if operation in ("unknown", draft["operation"]):
        return True
    if draft["operation"] not in _QUERIES and operation in _QUERIES:
        return True
    return False


def chat(db: Session, user, message: str, session_id: str | None) -> AssistantReply:
    sid = session_id or f"assistant-{uuid.uuid4().hex[:10]}"
    norm = _normalize(message)
    if norm in _CANCEL:
        SESSIONS.pop(sid, None)
        return AssistantReply(text="Session annulee.", session_id=sid)
    if norm.replace(" ", "") in ("",):
        return _unknown_reply(sid)

    interpreter = get_interpreter()
    intent = interpreter.interpret(message)
    draft = SESSIONS.get(sid)

    if draft is not None and not _is_completion(draft, intent.operation):
        SESSIONS.pop(sid, None)
        draft = None

    if draft is None:
        if intent.operation == "unknown":
            return _unknown_reply(sid)
        if intent.operation == "help":
            return _help_reply(sid)
        draft = {
            "operation": intent.operation,
            "business": intent.business,
            "params": dict(intent.params),
            "choices": {},
            "error": None,
        }
    else:
        field = _next_missing(draft)
        if field is not None:
            if not _fill(db, user, draft, field, message):
                SESSIONS[sid] = draft
                return _ask(sid, draft, field)

    SESSIONS[sid] = draft
    _prepare(db, user, draft)
    missing = _next_missing(draft)
    if missing is not None:
        return _ask(sid, draft, missing)
    if draft.get("error"):
        _prepare(db, user, draft)
        missing = _next_missing(draft)
        if missing is not None:
            return _ask(sid, draft, missing)
    SESSIONS.pop(sid, None)
    return _run(db, user, draft, sid)


def list_intents() -> list[dict]:
    return [{"operation": op, "label": INTENTS[op]["label"], "example": INTENTS[op]["example"]} for op in INTENTS]