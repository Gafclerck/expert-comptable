"""Resolution d'entites (client/contrat/caisse/categorie) a partir d'une
reference texte, et formatage des faits. Portee et consolidee depuis
`assistant/executor.py` (v1), qui dupliquait la table d'alias de business
avec `assistant/intents.py`. Ici : un seul endroit.

`ClarificationNeeded` est le mecanisme generique utilise par les outils et
l'orchestrateur pour signaler qu'une reponse utilisateur est necessaire
(champ manquant ou reference ambigue), que ce soit detecte a la validation
des parametres ou pendant l'execution d'un outil.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.identity.service import get_business_ids_for_user, get_person_summary, list_businesses
from app.modules.insurance import service as insurance_service
from app.modules.ledger import service as ledger_service
from app.modules.ledger.models import CategoryType

DEFAULT_ACCOUNT_NAME = "Caisse Principale"

# Alias en langage naturel vers un code d'activite existant. Ne couvre que le
# vocabulaire ; la liste des activites elle-meme vient de la base (Business).
# A terme, si la liste d'alias grossit beaucoup, elle a sa place comme colonne
# sur Business plutot qu'ici (pas fait maintenant : pas necessaire pour 3 a 4
# activites).
BUSINESS_ALIASES: dict[str, set[str]] = {
    "poulets": {"poulet", "poulailler", "poulaillers", "poules", "poule"},
    "vtc": {"vtc", "voiture", "chauffeur", "taxi", "uber", "transport"},
    "assurance": {"assurance", "assur"},
}


class ClarificationNeeded(Exception):
    """Leve par un resolveur ou un outil quand une reponse utilisateur est
    necessaire pour continuer. Capturee par l'orchestrateur, jamais par les
    appelants directs des services metier."""

    def __init__(self, field: str, question: str, choices: list[dict] | None = None):
        self.field = field
        self.question = question
        self.choices = choices or []
        super().__init__(question)


def normalize(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(ch) != "Mn"
    ).strip()


def _canonical_tokens(text: str) -> str:
    toks = text.split()
    out = []
    for tok in toks:
        replaced = tok
        for canonical, aliases in BUSINESS_ALIASES.items():
            if tok in aliases:
                replaced = canonical
                break
        out.append(replaced)
    return " ".join(out)


def name_match(name: str, ref: str) -> bool:
    norm_name = normalize(name)
    norm_ref = normalize(ref)
    if norm_name == norm_ref or norm_ref in norm_name or norm_name in norm_ref:
        return True
    canon_name = _canonical_tokens(norm_name)
    canon_ref = _canonical_tokens(norm_ref)
    return canon_name == canon_ref or canon_ref in canon_name or canon_name in canon_ref


def business_code_for(requested: str | None, default: str) -> str:
    """Ramene un alias libre (ex. « poulailler ») vers un code d'activite. Si
    aucun alias ne correspond, renvoie tel quel (pourra echouer plus loin, ce
    qui est correct : une activite inconnue doit etre signalee)."""
    if not requested:
        return default
    norm = requested.strip().casefold()
    for code, aliases in BUSINESS_ALIASES.items():
        if norm == code or norm in aliases:
            return code
    return requested


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
    """Matricule (ex. MAT-100) ou nom/numero de client -> contrat actif unique."""
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
    """Retourne (account, candidates). `account` est None si ambigu (plusieurs
    candidats, dans `candidates`) ou si aucune caisse n'existe."""
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
    """Activites accessibles a l'utilisateur, activite prioritaire en tete
    (utile pour le fallback multi-activite de get_balance)."""
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


def resolve_balance_targets(db: Session, actor, ref: str | None, business_hint: str | None) -> list[tuple]:
    """Coeur de get_balance (outil transverse). Retourne une liste de
    (business, account) a rapporter :
    - `ref` donne et resolu sans ambiguite -> une seule paire ;
    - rien de donne -> une paire par activite accessible ayant une caisse
      active (c'est ce qui repond a "soldes de toutes mes caisses") ;
    - `ref` donne mais ambigu -> ClarificationNeeded avec les candidats.
    """
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
