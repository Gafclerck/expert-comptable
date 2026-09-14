"""Resolution d'entites (client/contrat/caisse/categorie) et formatage des
faits. Portee depuis assistantv2/resolvers.py, avec une difference cle :
`business_code_for`/`name_match` s'appuient sur `registry.all_businesses()`
(alias declares par chaque business a son enregistrement) plutot que sur un
dict BUSINESS_ALIASES fige ici. Ajouter un business avec ses propres alias ne
touche donc plus ce fichier.
"""
from __future__ import annotations

import re
import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.assistantv3 import registry
from app.modules.assistantv3.parsing import normalize
from app.modules.identity.service import get_business_ids_for_user, get_person_summary, list_businesses
from app.modules.insurance import service as insurance_service
from app.modules.ledger import service as ledger_service
from app.modules.ledger.models import CategoryType

DEFAULT_ACCOUNT_NAME = "Caisse Principale"


class ClarificationNeeded(Exception):
    """Leve par un FieldType.resolve() ou un outil quand une reponse
    utilisateur est necessaire pour continuer. Capturee par l'orchestrateur."""

    def __init__(self, field: str, question: str, choices: list[dict] | None = None):
        self.field = field
        self.question = question
        self.choices = choices or []
        super().__init__(question)


def _alias_lookup() -> dict[str, str]:
    """Construit {alias_casefold: code} a partir des business enregistres.
    Reconstruit a chaque appel (peu couteux, quelques business) plutot que
    mis en cache, pour ne jamais servir une version perimee apres un
    enregistrement tardif (tests notamment)."""
    lookup: dict[str, str] = {}
    for module in registry.all_businesses():
        lookup[module.code.casefold()] = module.code
        for alias in module.aliases:
            lookup[alias.casefold()] = module.code
    return lookup


def _canonical_tokens(text: str) -> str:
    lookup = _alias_lookup()
    return " ".join(lookup.get(tok, tok) for tok in text.split())


def name_match(name: str, ref: str) -> bool:
    norm_name = normalize(name)
    norm_ref = normalize(ref)
    if norm_name == norm_ref or norm_ref in norm_name or norm_name in norm_ref:
        return True
    canon_name = _canonical_tokens(norm_name)
    canon_ref = _canonical_tokens(norm_ref)
    return canon_name == canon_ref or canon_ref in canon_name or canon_name in canon_ref


def business_code_for(requested: str | None, default: str) -> str:
    if not requested:
        return default
    norm = requested.strip().casefold()
    code = _alias_lookup().get(norm)
    return code or requested


def fmt_amount(amount: Decimal) -> str:
    value = amount.quantize(Decimal("0.01"))
    if value == value.to_integral_value():
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def fmt_date(value: date | None) -> str:
    if value is None:
        return "sans date de fin"
    return value.strftime("%d/%m/%Y")


def format_remaining(remaining: Decimal) -> str:
    if remaining > 0:
        return f"reste a payer: {fmt_amount(remaining)} FCFA"
    if remaining < 0:
        return f"reste a payer: 0 FCFA (avance de {fmt_amount(-remaining)} FCFA)"
    return "reste a payer: 0 FCFA (solde)"


def remaining_status(remaining: Decimal) -> str:
    if remaining > 0:
        return "reste a payer"
    if remaining < 0:
        return "avance (trop paye)"
    return "solde"


def resolve_contract(db: Session, actor, ref: str):
    if re.fullmatch(r"(?!CLI-)[A-Z]{2,5}-[A-Z0-9]+", ref.upper()):
        return insurance_service.get_active_contract_by_matricule(db, actor, ref)
    client = insurance_service.find_client(db, actor, ref)
    contracts = insurance_service.list_contracts(db, actor, client_id=client.id)
    if not contracts:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun contrat pour le client {get_person_summary(db, client.person_id).full_name}",
        )
    if len(contracts) == 1:
        return contracts[0]
    matricules = ", ".join(c.matricule for c in contracts)
    raise HTTPException(status_code=400, detail=f"Plusieurs contrats pour ce client: {matricules}. Precisez la matricule.")


def resolve_account(db: Session, actor, business_id: uuid.UUID, ref: str | None = None):
    accounts = [a for a in ledger_service.list_accounts(db, actor, business_id) if a.active]
    if not accounts:
        return None, []
    if ref:
        matches = [a for a in accounts if name_match(a.name, ref)]
        if len(matches) == 1:
            return matches[0], []
        return None, matches or accounts
    if len(accounts) == 1:
        return accounts[0], []
    default = next((a for a in accounts if normalize(a.name) == normalize(DEFAULT_ACCOUNT_NAME)), None)
    if default is not None:
        return default, []
    return None, accounts


def resolve_category(db: Session, ctype: CategoryType, ref: str | None = None):
    categories = [c for c in ledger_service.list_categories(db) if c.type == ctype]
    if not categories:
        return None, []
    if ref:
        matches = [c for c in categories if name_match(c.name, ref) or name_match(c.code, ref)]
        if len(matches) == 1:
            return matches[0], []
        return None, matches or categories
    if len(categories) == 1:
        return categories[0], []
    return None, categories


def accessible_businesses(db: Session, actor, prioritized_code: str | None = None) -> list:
    accessible_ids = get_business_ids_for_user(db, actor)
    result = []
    for b in list_businesses(db):
        if accessible_ids is not None and b.id not in accessible_ids:
            continue
        if prioritized_code and b.code == prioritized_code:
            result.insert(0, b)
        else:
            result.append(b)
    return result


def accessible_business_codes(db: Session, actor) -> set[str] | None:
    """None = acces total (meme convention que get_business_ids_for_user), pas
    'aucun acces'. Sert a filtrer les outils/hints exposes au LLM (voir
    orchestrator.py) : sans ca, un utilisateur limite a une activite se voit
    quand meme proposer les outils des autres, gaspillant des tokens et
    pouvant produire des tentatives d'appel vouees a l'echec cote service."""
    allowed_ids = get_business_ids_for_user(db, actor)
    if allowed_ids is None:
        return None
    return {b.code for b in list_businesses(db) if b.id in allowed_ids}


def resolve_balance_targets(db: Session, actor, ref: str | None, business_hint: str | None) -> list[tuple]:
    prioritized = business_code_for(business_hint, "") or None
    businesses = accessible_businesses(db, actor, prioritized)
    if business_hint:
        matched_code = business_code_for(business_hint, business_hint)
        businesses = [b for b in businesses if b.code == matched_code] or businesses

    if ref:
        ambiguous_candidates: list[dict] = []
        for b in businesses:
            account, candidates = resolve_account(db, actor, b.id, ref)
            if account is not None:
                return [(b, account)]
            if candidates:
                ambiguous_candidates = [{"name": a.name, "id": str(a.id)} for a in candidates]
            if name_match(b.name, ref) or name_match(b.code, ref):
                default, _ = resolve_account(db, actor, b.id)
                if default is not None:
                    return [(b, default)]
        if ambiguous_candidates:
            raise ClarificationNeeded("account", "Sur quelle caisse ?", ambiguous_candidates)
        raise ClarificationNeeded("account", "Aucune caisse trouvee pour cette reference.")

    targets: list[tuple] = []
    for b in businesses:
        account, _ = resolve_account(db, actor, b.id)
        if account is not None:
            targets.append((b, account))
    if not targets:
        raise ClarificationNeeded("account", "Aucune caisse accessible pour le moment.")
    return targets
