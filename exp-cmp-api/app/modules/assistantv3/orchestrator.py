"""Boucle d'orchestration multi-tool-call. Generique par construction : ce
fichier ne contient AUCUN nom de champ business ("contract", "account"...).
Toute connaissance specifique passe par le registre (ToolSpec.order +
FieldType), jamais par un if/elif ici. C'est le "noyau" au sens
microkernel/plugin : minimal, stable, aveugle au contenu des business.

Deux boucles, comme en v2 :
  - interne (`_run_loop`) : plusieurs tool calls resolus dans la meme requete
    HTTP, resultats reinjectes au LLM, jusqu'a plafond d'iterations ;
  - externe (clarification/confirmation) : le tour s'arrete, le Plan est
    persiste, le LLM n'est pas rappele a la reprise (simplification assumee,
    identique a v2).
"""
from __future__ import annotations

import json
import logging
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.events import publish
from app.modules.assistantv3 import parsing, registry, resolvers, session_store
from app.modules.assistantv3.formulator import get_formulator
from app.modules.assistantv3.plan import Plan, PlanStatus, PlanStep, StepStatus
from app.modules.assistantv3.schemas import AssistantReplyV3

# Declenche l'auto-enregistrement des types de champs communs puis des outils.
from app.modules.assistantv3 import field_types as _field_types  # noqa: F401
from app.modules.assistantv3 import tools as _tools  # noqa: F401

logger = logging.getLogger(__name__)

_CANCEL = {"annuler", "annule", "cancel", "stop", "quitter"}
_AFFIRMATIVE = {"oui", "ok", "d'accord", "daccord", "confirme", "confirmer", "yes", "vas-y", "vasy", "valide", "go"}


def _new_session_id() -> str:
    return f"assistantv3-{uuid.uuid4().hex[:10]}"


def handle_message(db: Session, actor, message: str, session_id: str | None) -> AssistantReplyV3:
    if not settings.ASSISTANT_LLM_API_KEY:
        return AssistantReplyV3(
            text=(
                "L'assistant v3 necessite une cle LLM configuree "
                "(ASSISTANT_LLM_API_KEY) : pas de repli sur des regles pour l'instant."
            ),
            session_id=session_id or _new_session_id(),
        )

    sid = session_id or _new_session_id()
    norm = parsing.normalize(message)

    if norm in _CANCEL:
        session_store.delete_plan(sid)
        return AssistantReplyV3(text="Session annulee.", session_id=sid)

    plan = session_store.load_plan(sid)

    if plan is not None and plan.status == PlanStatus.AWAITING_CLARIFICATION:
        return _resume_after_clarification(db, actor, plan, message)

    if plan is not None and plan.status == PlanStatus.AWAITING_CONFIRMATION:
        return _resume_after_confirmation(db, actor, plan, message)

    accessible_codes = resolvers.accessible_business_codes(db, actor)
    new_plan = Plan(session_id=sid, user_message=message)
    return _run_loop(db, actor, new_plan, accessible_codes)


def _run_loop(db: Session, actor, plan: Plan, accessible_codes: set[str] | None) -> AssistantReplyV3:
    messages = [
        {"role": "system", "content": _build_system_prompt(db, accessible_codes)},
        {"role": "user", "content": plan.user_message[:1000]},
    ]
    max_iterations = settings.ASSISTANTV2_MAX_ITERATIONS

    while plan.iterations < max_iterations:
        plan.iterations += 1
        try:
            message_out = _call_llm(messages, accessible_codes)
        except Exception:
            logger.warning("Assistant v3: appel LLM indisponible", exc_info=True)
            if not plan.steps:
                return AssistantReplyV3(
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

            if accessible_codes is not None and spec.business is not None and spec.business not in accessible_codes:
                # Defense en profondeur : le tool a deja ete exclu de la liste
                # proposee au LLM (voir _call_llm), mais on ne fait jamais
                # confiance uniquement a ce filtrage en amont pour une
                # verification d'acces. On enregistre un step FAILED (pas
                # seulement un message au LLM) pour que l'utilisateur recoive
                # un message clair via _finalize si c'etait le seul appel du
                # tour, plutot que le "je n'ai pas compris" generique.
                plan.steps.append(PlanStep(
                    tool=spec.name,
                    params={},
                    status=StepStatus.FAILED,
                    error=f"Acces refuse a l'activite '{spec.business}'.",
                ))
                messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": "Acces refuse a cette activite."})
                continue

            params = _clean_raw_params(_safe_json_loads(fn.get("arguments")))
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


def _resume_after_clarification(db: Session, actor, plan: Plan, message: str) -> AssistantReplyV3:
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


def _resume_after_confirmation(db: Session, actor, plan: Plan, message: str) -> AssistantReplyV3:
    norm = parsing.normalize(message)
    index = plan.pending_step_index
    if norm not in _AFFIRMATIVE:
        session_store.delete_plan(plan.session_id)
        return AssistantReplyV3(text="Action annulee.", session_id=plan.session_id)

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
    """Generique : ne connait aucun nom de champ. Delegue tout a
    registry.get_field_type(...) pour chaque champ declare dans spec.order."""
    step = plan.steps[index]
    spec = registry.get(step.tool)
    for field in spec.order:
        type_name = registry.field_type_name_for(spec, field)
        ftype = registry.get_field_type(type_name)

        if ftype is None:
            # Aucun type enregistre pour ce nom : simple verification de
            # presence, filet de securite plutot que blocage.
            if step.params.get(field) not in (None, ""):
                continue
            _pause_for_clarification(plan, index, field, spec.questions.get(field, f"Precisez : {field}"), [])
            return False

        if ftype.is_entity_ref:
            id_key = f"{field}_id"
            if step.params.get(id_key):
                continue
            try:
                ftype.resolve(db, actor, spec, step, field)
                if db.new or db.dirty or db.deleted:
                    # resolve() ne doit jamais ecrire en base (voir le contrat
                    # documente sur FieldType.resolve). Ce n'est pas une garantie
                    # absolue : un resolve() qui appellerait explicitement
                    # db.commit() aurait deja persiste avant qu'on l'annule ici.
                    # Mais ca attrape le cas le plus probable (une ecriture
                    # accidentelle jamais commitee), au lieu de laisser passer
                    # silencieusement une violation du contrat.
                    db.rollback()
                    raise RuntimeError(
                        f"Le type de champ '{type_name}' a tente une ecriture en base pendant resolve()"
                    )
            except resolvers.ClarificationNeeded as exc:
                _pause_for_clarification(plan, index, exc.field, exc.question, exc.choices)
                return False
            except HTTPException as exc:
                # Erreur dure (ex. business introuvable) : pas quelque chose
                # que l'utilisateur peut corriger en repondant, donc l'etape
                # echoue plutot que de se faire passer pour une clarification.
                step.status = StepStatus.FAILED
                step.error = str(exc.detail)
                return False
            except Exception:
                # Erreur inattendue (bug dans un FieldType business, cle
                # manquante...) : echoue proprement l'etape plutot que de
                # laisser planter toute la requete avec un 500.
                logger.exception(
                    "Assistant v3: erreur inattendue pendant la resolution du champ '%s' (%s)", field, step.tool
                )
                db.rollback()
                step.status = StepStatus.FAILED
                step.error = "Erreur interne lors du traitement de cette demande."
                return False
            if step.params.get(id_key):
                continue
            _pause_for_clarification(plan, index, field, spec.questions.get(field, f"Precisez : {field}"), [])
            return False

        raw = step.params.get(field)
        if raw is not None and ftype.validate(raw):
            continue
        step.params.pop(field, None)
        _pause_for_clarification(plan, index, field, spec.questions.get(field, f"Precisez : {field}"), [])
        return False
    return True


def _fill_field(db: Session, actor, step: PlanStep, field: str, message: str, choices: list[dict]) -> bool:
    spec = registry.get(step.tool)
    type_name = registry.field_type_name_for(spec, field)
    ftype = registry.get_field_type(type_name)
    if ftype is None:
        text = message.strip()
        if not text:
            return False
        step.params[field] = text
        return True
    return ftype.fill(db, actor, step, field, message, choices)


def _materialize_params(spec, step: PlanStep) -> dict:
    """Convertit les valeurs JSON-safe de step.params vers les types riches
    attendus par le handler (Decimal, date...), sans jamais modifier
    step.params lui-meme : la version persistee reste toujours JSON-safe."""
    materialized = dict(step.params)
    for field in spec.order:
        type_name = registry.field_type_name_for(spec, field)
        ftype = registry.get_field_type(type_name)
        if ftype is not None and not ftype.is_entity_ref and field in materialized:
            materialized[field] = ftype.coerce(materialized[field])
    return materialized


def _pause_for_clarification(plan: Plan, index: int, field: str, question: str, choices: list[dict]) -> None:
    plan.status = PlanStatus.AWAITING_CLARIFICATION
    plan.pending_step_index = index
    plan.pending_field = field
    plan.pending_question = question
    plan.pending_choices = choices


def _ask_clarification_reply(plan: Plan) -> AssistantReplyV3:
    question = plan.pending_question or "Precisez."
    if plan.pending_choices:
        lines = [f"{i + 1}) {c['name']}" for i, c in enumerate(plan.pending_choices)]
        question = question + "\n" + "\n".join(lines)
    return AssistantReplyV3(
        text=question,
        session_id=plan.session_id,
        clarification=True,
        missing_field=plan.pending_field,
        options=[c["name"] for c in plan.pending_choices],
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
}


def _summarize_params(step: PlanStep) -> str:
    parts = []
    for key, value in step.params.items():
        if key.endswith("_id") or key.startswith("_") or key in ("account", "category"):
            continue
        label = _PARAM_LABELS.get(key, key)
        parts.append(f"{label}: {value}")
    return ", ".join(parts)


def _ask_confirmation_reply(plan: Plan, spec) -> AssistantReplyV3:
    step = plan.steps[plan.pending_step_index]
    summary = _summarize_params(step)
    detail = f" ({summary})" if summary else ""
    note = f" {spec.confirmation_note}" if spec.confirmation_note else ""
    text = f"Confirmez-vous cette action : {spec.label}{detail} ?{note} Repondez \"oui\" pour valider ou \"non\" pour annuler."
    return AssistantReplyV3(
        text=text,
        session_id=plan.session_id,
        confirmation_required=True,
        pending_action=spec.name,
    )


def _execute_step(db: Session, actor, plan: Plan, index: int, spec) -> bool:
    """Retourne False si l'execution a ete interrompue par une clarification
    levee par le handler lui-meme (ex. get_balance sur une reference ambigue)."""
    step = plan.steps[index]
    try:
        handler_params = _materialize_params(spec, step)
        facts, target_id, static_text = spec.handler(db, actor, handler_params)
    except resolvers.ClarificationNeeded as exc:
        _pause_for_clarification(plan, index, exc.field, exc.question, exc.choices)
        return False
    except HTTPException as exc:
        db.rollback()
        step.status = StepStatus.FAILED
        step.error = str(exc.detail)
        return True
    except Exception:
        # Erreur inattendue dans un handler business : echoue proprement
        # l'etape plutot que de laisser planter toute la requete avec un 500.
        logger.exception("Assistant v3: erreur inattendue dans le handler de '%s'", step.tool)
        db.rollback()
        step.status = StepStatus.FAILED
        step.error = "Erreur interne lors de l'execution de cette action."
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


def _finalize(plan: Plan) -> AssistantReplyV3:
    session_store.delete_plan(plan.session_id)
    plan.status = PlanStatus.DONE

    if not plan.steps:
        return AssistantReplyV3(
            text="Je n'ai pas compris. Dites \"aide\" pour la liste des commandes possibles.",
            session_id=plan.session_id,
        )

    done_steps = [s for s in plan.steps if s.status == StepStatus.DONE]
    failed_steps = [s for s in plan.steps if s.status == StepStatus.FAILED]

    if not done_steps:
        text = "Erreur: " + " ; ".join(s.error or "operation echouee" for s in failed_steps)
        return AssistantReplyV3(text=text, session_id=plan.session_id, executed_tools=[])

    static_text = "\n".join(s.static_text for s in done_steps if s.static_text)

    formulator = get_formulator()
    if formulator is not None:
        try:
            text = formulator.formulate([(s.tool, s.result) for s in done_steps], plan.user_message)
        except Exception:
            logger.warning("Assistant v3: formulation LLM indisponible, repli sur le texte statique", exc_info=True)
            text = static_text
    else:
        text = static_text

    if failed_steps:
        # Ne jamais laisser un echec disparaitre derriere une formulation qui
        # ne voit que les etapes reussies (bug trouve et corrige en v2).
        text += "\n" + "\n".join(f"Erreur ({s.tool}): {s.error}" for s in failed_steps)

    return AssistantReplyV3(text=text, session_id=plan.session_id, executed_tools=[s.tool for s in done_steps])


def _clean_raw_params(raw: dict) -> dict:
    """Nettoyage minimal des arguments bruts renvoyes par le LLM : on ne
    convertit plus rien ici (voir _materialize_params), juste le rejet des
    valeurs vides. step.params reste JSON-safe de bout en bout."""
    return {k: v for k, v in raw.items() if v not in (None, "None", "")}


def _safe_json_loads(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _call_llm(messages: list[dict], accessible_codes: set[str] | None) -> dict:
    import httpx

    url = f"{(settings.ASSISTANT_LLM_API_URL or 'https://api.openai.com/v1').rstrip('/')}/chat/completions"
    payload = {
        "model": settings.ASSISTANT_LLM_MODEL,
        "messages": messages,
        "tools": registry.build_llm_tool_definitions(accessible_codes),
        "tool_choice": "auto",
        "temperature": 0,
    }
    response = httpx.post(url, headers={"Authorization": f"Bearer {settings.ASSISTANT_LLM_API_KEY}"}, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


def _build_system_prompt(db: Session, accessible_codes: set[str] | None) -> str:
    from app.modules.identity.service import list_businesses

    codes = ", ".join(b.code for b in list_businesses(db) if accessible_codes is None or b.code in accessible_codes)
    codes = codes or "aucune activite accessible"
    hints = registry.business_context_hints(accessible_codes)
    hints_text = ("\n" + "\n".join(f"- {h}" for h in hints)) if hints else ""
    return (
        "Tu es l'assistant d'une application de gestion financiere multi-activites "
        f"(activites accessibles a cet utilisateur : {codes}).{hints_text}\n"
        "Pour repondre a la demande, appelle un ou plusieurs outils si necessaire : tu peux "
        "renvoyer plusieurs appels d'outils dans la meme reponse si la demande le requiert "
        "(par exemple plusieurs questions posees dans le meme message). N'invente jamais une "
        "valeur : omets un parametre si tu ne le connais pas avec certitude plutot que de "
        "deviner, le systeme demandera une precision a l'utilisateur si besoin. Si la demande "
        "ne correspond a aucun outil, n'appelle aucun outil."
    )
