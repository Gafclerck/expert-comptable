"""Boucle d'orchestration multi-tool-call.

Deux boucles distinctes (voir la discussion d'architecture qui a precede ce
module) :
  - une boucle INTERNE, dans `_run_loop`, entierement a l'interieur d'une
    seule requete HTTP : le LLM peut demander plusieurs tool calls d'affilee,
    dont les resultats lui sont reinjectes, jusqu'a plafond `_run_loop`
    n'appelle plus le LLM que si necessaire ;
  - une boucle EXTERNE, quand une clarification ou une confirmation est
    necessaire : le tour s'arrete, le Plan est persiste (session_store), et le
    tour suivant reprend exactement a cet endroit SANS rappeler le LLM
    (simplification assumee : voir _resume_after_clarification /
    _resume_after_confirmation. Le LLM n'est pas resollicite pour proposer
    d'autres outils apres une clarification/confirmation dans ce premier
    jet ; c'est suffisant pour le cas courant d'une seule etape ambigue par
    tour, et evite d'avoir a reconstituer fidelement l'historique de
    conversation LLM entre deux requetes).
"""
from __future__ import annotations

import json
import logging
import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.events import publish
from app.modules.assistantv2 import parsing, registry, resolvers, session_store
from app.modules.assistantv2.formulator import get_formulator
from app.modules.assistantv2.plan import Plan, PlanStatus, PlanStep, StepStatus
from app.modules.assistantv2.schemas import AssistantReplyV2
from app.modules.identity.service import get_business_by_code, list_businesses
from app.modules.insurance import service as insurance_service

# Declenche l'auto-enregistrement de tous les outils (voir tools/__init__.py).
from app.modules.assistantv2 import tools as _tools  # noqa: F401

logger = logging.getLogger(__name__)

_CANCEL = {"annuler", "annule", "cancel", "stop", "quitter"}
_AFFIRMATIVE = {"oui", "ok", "d'accord", "daccord", "confirme", "confirmer", "yes", "vas-y", "vasy", "valide", "go"}
_RESOLVABLE_FIELDS = {"contract", "account", "category", "driver", "vehicle"}


def _new_session_id() -> str:
    return f"assistantv2-{uuid.uuid4().hex[:10]}"


def handle_message(db: Session, actor, message: str, session_id: str | None) -> AssistantReplyV2:
    if not settings.ASSISTANT_LLM_API_KEY:
        return AssistantReplyV2(
            text=(
                "L'assistant v2 necessite une cle LLM configuree "
                "(ASSISTANT_LLM_API_KEY) : pas de repli sur des regles pour l'instant."
            ),
            session_id=session_id or _new_session_id(),
        )

    sid = session_id or _new_session_id()
    norm = parsing.normalize(message)

    if norm in _CANCEL:
        session_store.delete_plan(sid)
        return AssistantReplyV2(text="Session annulee.", session_id=sid)

    plan = session_store.load_plan(sid)

    if plan is not None and plan.status == PlanStatus.AWAITING_CLARIFICATION:
        return _resume_after_clarification(db, actor, plan, message)

    if plan is not None and plan.status == PlanStatus.AWAITING_CONFIRMATION:
        return _resume_after_confirmation(db, actor, plan, message)

    new_plan = Plan(session_id=sid, user_message=message)
    return _run_loop(db, actor, new_plan)


def _run_loop(db: Session, actor, plan: Plan) -> AssistantReplyV2:
    messages = [
        {"role": "system", "content": _build_system_prompt(db)},
        {"role": "user", "content": plan.user_message[:1000]},
    ]
    max_iterations = settings.ASSISTANTV2_MAX_ITERATIONS

    while plan.iterations < max_iterations:
        plan.iterations += 1
        try:
            message_out = _call_llm(messages)
        except Exception:
            logger.warning("Assistant v2: appel LLM indisponible", exc_info=True)
            if not plan.steps:
                return AssistantReplyV2(
                    text="Assistant indisponible pour le moment, reessayez plus tard.",
                    session_id=plan.session_id,
                )
            return _finalize(plan)

        tool_calls = message_out.get("tool_calls") or []
        if not tool_calls:
            return _finalize(plan)

        messages.append({"role": "assistant", "content": message_out.get("content"), "tool_calls": tool_calls})

        for call in tool_calls:
            fn = call.get("function", {})
            spec = registry.get(fn.get("name"))
            if spec is None:
                messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": "outil inconnu, ignore"})
                continue

            params = parsing.coerce_params(_safe_json_loads(fn.get("arguments")))
            plan.steps.append(PlanStep(tool=spec.name, params=params))
            index = len(plan.steps) - 1

            if not _prepare_step(db, actor, plan, index):
                if plan.status != PlanStatus.AWAITING_CLARIFICATION:
                    return _finalize(plan)
                session_store.save_plan(plan)
                return _ask_clarification_reply(plan)

            if spec.is_critical and not plan.steps[index].params.get("_confirmed"):
                plan.status = PlanStatus.AWAITING_CONFIRMATION
                plan.pending_step_index = index
                session_store.save_plan(plan)
                return _ask_confirmation_reply(plan, spec)

            if not _execute_step(db, actor, plan, index, spec):
                session_store.save_plan(plan)
                return _ask_clarification_reply(plan)
            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id"),
                "content": json.dumps(plan.steps[index].result or {"error": plan.steps[index].error}, ensure_ascii=False, default=str),
            })

    return _finalize(plan)


def _resume_after_clarification(db: Session, actor, plan: Plan, message: str) -> AssistantReplyV2:
    index = plan.pending_step_index
    step = plan.steps[index]
    field = plan.pending_field
    choices = plan.pending_choices

    if not _fill_field(db, actor, step, field, message, choices):
        session_store.save_plan(plan)
        return _ask_clarification_reply(plan)

    plan.pending_field = None
    plan.pending_question = None
    plan.pending_choices = []
    plan.status = PlanStatus.RUNNING

    if not _prepare_step(db, actor, plan, index):
        if plan.status != PlanStatus.AWAITING_CLARIFICATION:
            return _finalize(plan)
        session_store.save_plan(plan)
        return _ask_clarification_reply(plan)

    spec = registry.get(step.tool)
    if spec.is_critical and not step.params.get("_confirmed"):
        plan.status = PlanStatus.AWAITING_CONFIRMATION
        plan.pending_step_index = index
        session_store.save_plan(plan)
        return _ask_confirmation_reply(plan, spec)

    if not _execute_step(db, actor, plan, index, spec):
        session_store.save_plan(plan)
        return _ask_clarification_reply(plan)
    return _finalize(plan)


def _resume_after_confirmation(db: Session, actor, plan: Plan, message: str) -> AssistantReplyV2:
    norm = parsing.normalize(message)
    index = plan.pending_step_index
    if norm not in _AFFIRMATIVE:
        session_store.delete_plan(plan.session_id)
        return AssistantReplyV2(text="Action annulee.", session_id=plan.session_id)

    step = plan.steps[index]
    step.params["_confirmed"] = True
    plan.status = PlanStatus.RUNNING
    plan.pending_step_index = None
    spec = registry.get(step.tool)
    if not _execute_step(db, actor, plan, index, spec):
        session_store.save_plan(plan)
        return _ask_clarification_reply(plan)
    return _finalize(plan)


def _prepare_step(db: Session, actor, plan: Plan, index: int) -> bool:
    step = plan.steps[index]
    spec = registry.get(step.tool)
    for field in spec.order:
        if field in _RESOLVABLE_FIELDS:
            id_key = f"{field}_id"
            if step.params.get(id_key):
                continue
            try:
                _resolve_field(db, actor, spec, step, field)
            except resolvers.ClarificationNeeded as exc:
                _pause_for_clarification(plan, index, exc.field, exc.question, exc.choices)
                return False
            except HTTPException as exc:
                # Erreur dure (ex. business introuvable) : pas quelque chose que
                # l'utilisateur peut corriger en repondant a une question, donc
                # on echoue l'etape plutot que de la faire passer pour une
                # clarification.
                step.status = StepStatus.FAILED
                step.error = str(exc.detail)
                return False
            if step.params.get(id_key):
                continue
            _pause_for_clarification(plan, index, field, spec.questions.get(field, f"Precisez : {field}"), [])
            return False
        else:
            if _is_present_and_valid(field, step.params.get(field)):
                continue
            step.params.pop(field, None)
            _pause_for_clarification(plan, index, field, spec.questions.get(field, f"Precisez : {field}"), [])
            return False
    return True


def _is_present_and_valid(field: str, value) -> bool:
    """Au-dela de la simple presence : les valeurs numeriques fournies
    directement par le LLM (pas encore passees par la validation de
    `_fill_field`, qui ne s'applique qu'aux reponses de clarification) doivent
    aussi etre semantiquement valides. Une quantite ou un montant a zero ou
    negatif ne doit jamais atteindre un outil (ex. division par zero dans
    add_purchase/add_sale)."""
    if value in (None, ""):
        return False
    if field == "quantity":
        return isinstance(value, int) and value > 0
    if field in ("amount", "premium", "expected_amount"):
        return isinstance(value, Decimal) and value > 0
    return True


def _resolve_field(db: Session, actor, spec, step: PlanStep, field: str) -> None:
    params = step.params
    if field == "contract":
        ref = params.get("contract")
        if not ref:
            return
        try:
            contract = resolvers.resolve_contract(db, actor, ref)
        except HTTPException as exc:
            raise resolvers.ClarificationNeeded("contract", str(exc.detail))
        params["contract_id"] = str(contract.id)
    elif field == "account":
        business = get_business_by_code(db, spec.business)
        account, candidates = resolvers.resolve_account(db, actor, business.id, params.get("account"))
        if account is not None:
            params["account_id"] = str(account.id)
            params["account_name"] = account.name
        elif candidates:
            raise resolvers.ClarificationNeeded(
                "account", "Sur quelle caisse ?", [{"name": a.name, "id": str(a.id)} for a in candidates]
            )
        else:
            raise resolvers.ClarificationNeeded("account", "Aucune caisse pour cette activite.")
    elif field == "category":
        category, candidates = resolvers.resolve_category(db, spec.category_type, params.get("category"))
        if category is not None:
            params["category_id"] = str(category.id)
        elif candidates:
            raise resolvers.ClarificationNeeded(
                "category", "Sous quelle categorie ?", [{"name": c.name, "id": str(c.id)} for c in candidates]
            )
        else:
            raise resolvers.ClarificationNeeded("category", "Aucune categorie de ce type.")
    elif field == "driver":
        ref = params.get("driver")
        if not ref:
            return
        try:
            driver = resolvers.resolve_driver(db, actor, ref)
        except HTTPException as exc:
            raise resolvers.ClarificationNeeded("driver", str(exc.detail))
        params["driver_id"] = str(driver["id"])
        params["driver_name"] = driver["full_name"]
    elif field == "vehicle":
        ref = params.get("vehicle")
        if not ref:
            return
        try:
            vehicle = resolvers.resolve_vehicle(db, actor, ref)
        except HTTPException as exc:
            raise resolvers.ClarificationNeeded("vehicle", str(exc.detail))
        params["vehicle_id"] = str(vehicle.id)
        params["vehicle_label"] = f"{vehicle.make} {vehicle.model} ({vehicle.registration})"


def _fill_field(db: Session, actor, step: PlanStep, field: str, message: str, choices: list[dict]) -> bool:
    params = step.params
    if field == "client":
        name = parsing.extract_client_name(message) or parsing.clean_free_text(message)
        if not name:
            return False
        params["client"] = name
        return True
    if field == "matricule":
        m = parsing.parse_matricule(message)
        if not m:
            return False
        params["matricule"] = m
        return True
    if field in ("premium", "amount", "expected_amount"):
        amount = parsing.parse_amount(message)
        if amount is None and field == "amount" and params.get("contract_id"):
            norm = parsing.normalize(message)
            if any(word in norm for word in ("reste", "reliquat")):
                contract = insurance_service.get_contract(db, actor, uuid.UUID(params["contract_id"]))
                amount = insurance_service.remaining_amount(db, contract)
        if amount is None or amount <= 0:
            return False
        params[field] = amount
        return True
    if field == "due_date":
        d = parsing.parse_due_date(message)
        if not d:
            return False
        params["due_date"] = d
        return True
    if field == "quantity":
        text = message.strip()
        q = parsing.parse_quantity(message) or (int(text) if text.isdigit() else None)
        if not q or q <= 0:
            return False
        params["quantity"] = q
        return True
    if field == "contract":
        ref = (
            parsing.parse_matricule(message)
            or parsing.parse_client_number(message)
            or parsing.extract_client_name(message)
            or parsing.clean_free_text(message)
        )
        if not ref:
            return False
        params["contract"] = ref
        params.pop("contract_id", None)
        return True
    if field == "driver":
        name = parsing.extract_client_name(message) or parsing.clean_free_text(message)
        if not name:
            return False
        params["driver"] = name
        params.pop("driver_id", None)
        return True
    if field == "vehicle":
        ref = parsing.clean_free_text(message) or parsing.extract_client_name(message)
        if not ref:
            return False
        params["vehicle"] = ref
        params.pop("vehicle_id", None)
        return True
    if field == "account":
        index = _choose_index(message, choices)
        if index is not None:
            params["account_id"] = choices[index]["id"]
            params["account_name"] = choices[index]["name"]
            return True
        params["account"] = message.strip(".,")
        return True
    if field == "category":
        index = _choose_index(message, choices)
        if index is not None:
            params["category_id"] = choices[index]["id"]
            return True
        params["category"] = message.strip(".,")
        return True
    if field == "affectation":
        index = _choose_index(message, choices)
        if index is not None:
            params["affectation_id"] = choices[index]["id"]
            return True
        return False
    return False


def _choose_index(message: str, items: list[dict]) -> int | None:
    text = parsing.normalize(message).strip()
    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(items):
            return index
    words = {"1": 0, "premier": 0, "premiere": 0, "2": 1, "deuxieme": 1, "3": 2, "troisieme": 2, "4": 3}
    if text in words and words[text] < len(items):
        return words[text]
    return None


def _pause_for_clarification(plan: Plan, index: int, field: str, question: str, choices: list[dict]) -> None:
    plan.status = PlanStatus.AWAITING_CLARIFICATION
    plan.pending_step_index = index
    plan.pending_field = field
    plan.pending_question = question
    plan.pending_choices = choices


def _ask_clarification_reply(plan: Plan) -> AssistantReplyV2:
    question = plan.pending_question or "Precisez."
    if plan.pending_choices:
        lines = [f"{i + 1}) {c['name']}" for i, c in enumerate(plan.pending_choices)]
        question = question + "\n" + "\n".join(lines)
    return AssistantReplyV2(
        text=question,
        session_id=plan.session_id,
        clarification=True,
        missing_field=plan.pending_field,
        options=[c["name"] for c in plan.pending_choices],
    )


def _ask_confirmation_reply(plan: Plan, spec) -> AssistantReplyV2:
    step = plan.steps[plan.pending_step_index]
    summary = _summarize_params(step)
    detail = f" ({summary})" if summary else ""
    note = f" {spec.confirmation_note}" if spec.confirmation_note else ""
    text = f"Confirmez-vous cette action : {spec.label}{detail} ?{note} Repondez \"oui\" pour valider ou \"non\" pour annuler."
    return AssistantReplyV2(
        text=text,
        session_id=plan.session_id,
        confirmation_required=True,
        pending_action=spec.name,
    )


_PARAM_LABELS = {
    "client": "client",
    "matricule": "matricule",
    "premium": "prime",
    "contract": "contrat",
    "amount": "montant",
    "quantity": "quantite",
    "due_date": "date",
    "account_name": "caisse",
    "driver_name": "chauffeur",
    "vehicle_label": "vehicule",
    "expected_amount": "montant attendu",
    "expense_type": "type de depense",
    "start_date": "date de debut",
    "end_date": "date de fin",
    "registration": "immatriculation",
}


def _summarize_params(step: PlanStep) -> str:
    """Resume lisible des parametres resolus, pour que le message de
    confirmation restitue vraiment ce qui va etre execute (montant, contrat,
    caisse...) plutot que le seul nom de l'outil : sans ca, l'utilisateur ne
    peut pas verifier ce qu'il confirme."""
    parts = []
    for key, value in step.params.items():
        if key.endswith("_id") or key.startswith("_") or key in ("account", "category"):
            continue
        label = _PARAM_LABELS.get(key, key)
        parts.append(f"{label}: {value}")
    return ", ".join(parts)


def _execute_step(db: Session, actor, plan: Plan, index: int, spec) -> bool:
    """Execute le step. Retourne False si l'execution a ete interrompue par une
    clarification necessaire, levee par le handler lui-meme (ex. get_balance
    sur une reference ambigue detectee pendant sa propre resolution, plutot
    qu'en amont via `_prepare_step`) : dans ce cas le plan est deja mis a jour
    en AWAITING_CLARIFICATION, a l'appelant de sauvegarder et repondre."""
    step = plan.steps[index]
    try:
        facts, target_id, static_text = spec.handler(db, actor, step.params)
    except resolvers.ClarificationNeeded as exc:
        _pause_for_clarification(plan, index, exc.field, exc.question, exc.choices)
        return False
    except HTTPException as exc:
        db.rollback()
        step.status = StepStatus.FAILED
        step.error = str(exc.detail)
        return True
    step.result = facts
    step.static_text = static_text
    step.status = StepStatus.DONE
    publish(
        "assistant.command.executed",
        actor_id=str(actor.id),
        entity_id=str(target_id) if target_id else None,
        new_values={"operation": step.tool, "params": {k: str(v) for k, v in step.params.items()}},
    )
    return True


def _finalize(plan: Plan) -> AssistantReplyV2:
    session_store.delete_plan(plan.session_id)
    plan.status = PlanStatus.DONE

    if not plan.steps:
        return AssistantReplyV2(
            text="Je n'ai pas compris. Dites \"aide\" pour la liste des commandes possibles.",
            session_id=plan.session_id,
        )

    done_steps = [s for s in plan.steps if s.status == StepStatus.DONE]
    failed_steps = [s for s in plan.steps if s.status == StepStatus.FAILED]

    if not done_steps:
        text = "Erreur: " + " ; ".join(s.error or "operation echouee" for s in failed_steps)
        return AssistantReplyV2(text=text, session_id=plan.session_id, executed_tools=[])

    static_text = "\n".join(s.static_text for s in done_steps if s.static_text)

    formulator = get_formulator()
    if formulator is not None:
        try:
            text = formulator.formulate([(s.tool, s.result) for s in done_steps], plan.user_message)
        except Exception:
            logger.warning("Assistant v2: formulation LLM indisponible, repli sur le texte statique", exc_info=True)
            text = static_text
    else:
        text = static_text

    if failed_steps:
        # Le formulateur ne voit que les etapes reussies (voir son appel
        # ci-dessus) : les echecs sont donc toujours rattaches ici, une seule
        # fois, qu'il ait ete utilise ou non, pour ne jamais disparaitre
        # silencieusement derriere une reponse qui ne parle que des succes.
        text += "\n" + "\n".join(f"Erreur ({s.tool}): {s.error}" for s in failed_steps)

    return AssistantReplyV2(text=text, session_id=plan.session_id, executed_tools=[s.tool for s in done_steps])


def _safe_json_loads(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _call_llm(messages: list[dict]) -> dict:
    import httpx

    url = f"{(settings.ASSISTANT_LLM_API_URL or 'https://api.openai.com/v1').rstrip('/')}/chat/completions"
    payload = {
        "model": settings.ASSISTANT_LLM_MODEL,
        "messages": messages,
        "tools": registry.build_llm_tool_definitions(),
        "tool_choice": "auto",
        "temperature": 0,
    }
    response = httpx.post(url, headers={"Authorization": f"Bearer {settings.ASSISTANT_LLM_API_KEY}"}, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


def _build_system_prompt(db: Session) -> str:
    codes = ", ".join(b.code for b in list_businesses(db)) or "aucune activite configuree"
    return (
        "Tu es l'assistant d'une application de gestion financiere multi-activites "
        f"(activites actuelles : {codes} ; d'autres peuvent etre ajoutees plus tard). "
        "Pour repondre a la demande, appelle un ou plusieurs outils si necessaire : tu peux "
        "renvoyer plusieurs appels d'outils dans la meme reponse si la demande le requiert "
        "(par exemple plusieurs questions posees dans le meme message). N'invente jamais une "
        "valeur : omets un parametre si tu ne le connais pas avec certitude plutot que de "
        "deviner, le systeme demandera une precision a l'utilisateur si besoin. Si la demande "
        "ne correspond a aucun outil, n'appelle aucun outil."
    )
