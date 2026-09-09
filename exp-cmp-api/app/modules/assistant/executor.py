import re
import unicodedata
import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.assistant.interpreter import parse_amount
from app.modules.assistant.intents import business_code_for
from app.modules.identity.service import get_business_by_code, get_person_summary
from app.modules.insurance import service as insurance_service
from app.modules.ledger import service as ledger_service
from app.modules.ledger.models import CategoryType
from app.modules.poultry import service as poultry_service

ASSURANCE_BUSINESS_CODE = "assurance"
DEFAULT_CONTRACT_TYPE = "assurance-auto"
DEFAULT_ACCOUNT_NAME = "Caisse Principale"

_BUSINESS_ALIASES = {
    "poulets": {"poulet", "poulailler", "poulaillers", "poules", "poule"},
    "vtc": {"vtc", "voiture", "chauffeur", "taxi", "uber"},
    "assurance": {"assurance", "assur"},
}


def _canonical_tokens(text: str) -> str:
    toks = text.split()
    canonical_toks = []
    for tok in toks:
        replaced = tok
        for canonical, aliases in _BUSINESS_ALIASES.items():
            if tok in aliases:
                replaced = canonical
                break
        canonical_toks.append(replaced)
    return " ".join(canonical_toks)


def _normalize(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(ch) != "Mn"
    ).strip()


def fmt_amount(amount: Decimal) -> str:
    value = amount.quantize(Decimal("0.01"))
    if value == value.to_integral_value():
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def fmt_date(value: date | None) -> str:
    if value is None:
        return "sans date de fin"
    return value.strftime("%d/%m/%Y")


def _format_remaining(remaining: Decimal) -> str:
    if remaining > 0:
        return f"reste a payer: {fmt_amount(remaining)} FCFA"
    if remaining < 0:
        return f"reste a payer: 0 FCFA (avance de {fmt_amount(-remaining)} FCFA)"
    return "reste a payer: 0 FCFA (solde)"


def _business(db: Session, code: str):
    return get_business_by_code(db, code)


def _name_match(name: str, ref: str) -> bool:
    norm_name = _normalize(name)
    norm_ref = _normalize(ref)
    if norm_name == norm_ref or norm_ref in norm_name or norm_name in norm_ref:
        return True
    canon_name = _canonical_tokens(norm_name)
    canon_ref = _canonical_tokens(norm_ref)
    if canon_name == canon_ref or canon_ref in canon_name or canon_name in canon_ref:
        return True
    return False


def resolve_contract(db: Session, user, ref: str):
    if re.fullmatch(r"(?!CLI-)[A-Z]{2,5}-[A-Z0-9]+", ref.upper()):
        return insurance_service.get_active_contract_by_matricule(db, user, ref)
    client = insurance_service.find_client(db, user, ref)
    contracts = insurance_service.list_contracts(db, user, client_id=client.id)
    if not contracts:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun contrat pour le client {get_person_summary(db, client.person_id).full_name}",
        )
    if len(contracts) == 1:
        return contracts[0]
    matricules = ", ".join(c.matricule for c in contracts)
    raise HTTPException(
        status_code=400,
        detail=f"Plusieurs contrats pour ce client: {matricules}. Precisez la matricule.",
    )


def resolve_account(db: Session, user, business_id: uuid.UUID, ref: str | None = None):
    accounts = [a for a in ledger_service.list_accounts(db, user, business_id) if a.active]
    if not accounts:
        raise HTTPException(
            status_code=400,
            detail="Aucune caisse pour cette activite. Creez d'abord un compte via /api/ledger/accounts",
        )
    if ref:
        matches = [a for a in accounts if _name_match(a.name, ref)]
        if len(matches) == 1:
            return matches[0], []
        raise HTTPException(status_code=400, detail="Caisse introuvable ou nom ambigu")
    if len(accounts) == 1:
        return accounts[0], []
    default = next(
        (a for a in accounts if _normalize(a.name) == _normalize(DEFAULT_ACCOUNT_NAME)),
        None,
    )
    if default is not None:
        return default, []
    return None, accounts


def resolve_category(db: Session, ctype: CategoryType, ref: str | None = None):
    categories = [c for c in ledger_service.list_categories(db) if c.type == ctype]
    if not categories:
        raise HTTPException(
            status_code=400,
            detail="Aucune categorie de ce type. Creez-la via /api/ledger/categories",
        )
    if ref:
        matches = [c for c in categories if _name_match(c.name, ref) or _name_match(c.code, ref)]
        if len(matches) == 1:
            return matches[0], []
        raise HTTPException(status_code=400, detail="Categorie introuvable ou nom ambigu")
    if len(categories) == 1:
        return categories[0], []
    return None, categories


def _contract_from_params(db: Session, actor, params: dict):
    if params.get("contract_id"):
        return insurance_service.get_contract(db, actor, uuid.UUID(params["contract_id"]))
    return resolve_contract(db, actor, params["contract"])


def _remaining_status(remaining: Decimal) -> str:
    if remaining > 0:
        return "reste a payer"
    if remaining < 0:
        return "avance (trop paye)"
    return "solde"


def execute(db: Session, actor, operation: str, params: dict) -> tuple[dict, uuid.UUID | None, str]:
    """Execute l'operation et retourne (result, target_id, static_text) :
    `result` est un dictionnaire de faits STRING deja formates (montants, dates,
    matricules) recopiable tel quel par le Formulator LLM ; `static_text` est la
    reponse redressa actuelle utilisee comme repli si aucune formulation LLM.
    """
    business = _business(db, business_code_for(operation, params.get("business")))
    if operation == "create_client":
        full_name = " ".join(word.capitalize() for word in params["client"].split())
        client = insurance_service.create_client(
            db,
            actor,
            full_name=full_name,
            phone=params.get("phone"),
            client_number=params.get("client_number"),
        )
        person = get_person_summary(db, client.person_id)
        result = {
            "kind": "create_client",
            "client": person.full_name,
            "client_number": client.client_number,
        }
        text = f"Client cree: {person.full_name} ({client.client_number})."
        return result, client.id, text
    if operation == "create_contract":
        client = insurance_service.find_client(db, actor, params["client"])
        person = get_person_summary(db, client.person_id)
        start = date.today()
        contract = insurance_service.create_contract(
            db,
            actor,
            client_id=client.id,
            matricule=params["matricule"],
            contract_type=DEFAULT_CONTRACT_TYPE,
            premium=params["premium"],
            start_date=start,
            end_date=start + timedelta(days=365),
        )
        result = {
            "kind": "create_contract",
            "matricule": contract.matricule,
            "client": person.full_name,
            "premium": f"{fmt_amount(contract.premium)} FCFA",
            "remaining": f"{fmt_amount(insurance_service.remaining_amount(db, contract))} FCFA",
            "contract_type": contract.contract_type,
            "start_date": fmt_date(contract.start_date),
            "end_date": fmt_date(contract.end_date),
        }
        text = (
            f"Contrat cree: {contract.matricule} pour {person.full_name} — prime "
            f"{fmt_amount(contract.premium)} FCFA, reste a payer "
            f"{fmt_amount(insurance_service.remaining_amount(db, contract))} FCFA "
            f"(type {contract.contract_type}, du {fmt_date(contract.start_date)} au {fmt_date(contract.end_date)})."
        )
        return result, contract.id, text
    if operation == "record_payment":
        contract_id = uuid.UUID(params["contract_id"])
        contract = insurance_service.get_contract(db, actor, contract_id)
        payment = insurance_service.create_payment(
            db,
            actor,
            contract_id=contract.id,
            amount=params["amount"],
            paid_at=None,
            account_id=uuid.UUID(params["account_id"]),
            category_id=uuid.UUID(params["category_id"]),
        )
        remaining = insurance_service.remaining_amount(db, contract)
        result = {
            "kind": "record_payment",
            "amount": f"{fmt_amount(payment.amount)} FCFA",
            "account": params["account_name"],
            "matricule": contract.matricule,
            "remaining": f"{fmt_amount(remaining)} FCFA",
            "remaining_status": _remaining_status(remaining),
        }
        text = (
            f"Paiement encaisse: {fmt_amount(payment.amount)} FCFA sur la caisse "
            f"\"{params['account_name']}\" pour le contrat {contract.matricule} — "
            f"{_format_remaining(remaining)}."
        )
        return result, payment.id, text
    if operation == "get_balance":
        if params.get("account_id"):
            account = ledger_service.get_account(db, uuid.UUID(params["account_id"]), actor)
        else:
            bid = uuid.UUID(params["business_id"]) if params.get("business_id") else business.id
            account, _ = resolve_account(db, actor, bid, params.get("account"))
        balance = ledger_service.compute_balance(db, account)["balance"]
        result = {
            "kind": "get_balance",
            "account": account.name,
            "balance": f"{fmt_amount(balance)} FCFA",
        }
        text = f"Solde de la caisse \"{account.name}\": {fmt_amount(balance)} FCFA."
        return result, account.id, text
    if operation == "get_remaining":
        contract = _contract_from_params(db, actor, params)
        remaining = insurance_service.remaining_amount(db, contract)
        result = {
            "kind": "get_remaining",
            "matricule": contract.matricule,
            "premium": f"{fmt_amount(contract.premium)} FCFA",
            "remaining": f"{fmt_amount(remaining)} FCFA",
            "remaining_status": _remaining_status(remaining),
        }
        text = (
            f"{contract.matricule} — {_format_remaining(remaining)} "
            f"(prime {fmt_amount(contract.premium)} FCFA)."
        )
        return result, contract.id, text
    if operation == "get_client_info":
        client = insurance_service.find_client(db, actor, params["client"])
        person = get_person_summary(db, client.person_id)
        contracts = insurance_service.list_contracts(db, actor, client_id=client.id)
        matricules = ", ".join(c.matricule for c in contracts) if contracts else "aucun"
        result = {
            "kind": "get_client_info",
            "client": person.full_name,
            "client_number": client.client_number,
            "status": client.status.value,
            "phone": person.phone or "non renseigne",
            "contracts": matricules or "aucun",
        }
        text = (
            f"Client {person.full_name} ({client.client_number}) — statut {client.status.value}, "
            f"telephone {person.phone or 'non renseigne'}. Contrats: {matricules}."
        )
        return result, client.id, text
    if operation == "get_contract_info":
        contract = _contract_from_params(db, actor, params)
        client = insurance_service.get_client(db, actor, contract.client_id)
        person = get_person_summary(db, client.person_id)
        payments = insurance_service.list_payments(db, actor, contract.id)
        total_paid = sum((p.amount for p in payments), start=Decimal("0"))
        remaining = insurance_service.remaining_amount(db, contract)
        result = {
            "kind": "get_contract_info",
            "matricule": contract.matricule,
            "contract_type": contract.contract_type,
            "client": person.full_name,
            "premium": f"{fmt_amount(contract.premium)} FCFA",
            "paid": f"{fmt_amount(total_paid)} FCFA",
            "remaining": f"{fmt_amount(remaining)} FCFA",
            "remaining_status": _remaining_status(remaining),
            "start_date": fmt_date(contract.start_date),
            "end_date": fmt_date(contract.end_date),
            "status": contract.status.value,
        }
        text = (
            f"Contrat {contract.matricule} ({contract.contract_type}) pour {person.full_name} — "
            f"prime {fmt_amount(contract.premium)} FCFA, paye {fmt_amount(total_paid)} FCFA, "
            f"{_format_remaining(remaining)}. "
            f"Du {fmt_date(contract.start_date)} au {fmt_date(contract.end_date)} — statut {contract.status.value}."
        )
        return result, contract.id, text
    if operation == "get_dues":
        contract = _contract_from_params(db, actor, params)
        dues = insurance_service.list_dues(db, actor, contract.id)
        if not dues:
            result = {"kind": "get_dues", "matricule": contract.matricule, "dues": []}
            text = f"Aucune echeance programmee pour {contract.matricule}."
        else:
            lines = [
                f"- {fmt_date(d.due_date)}: {fmt_amount(d.amount_due)} FCFA ({d.status.value})"
                for d in dues
            ]
            result = {
                "kind": "get_dues",
                "matricule": contract.matricule,
                "dues": [
                    {
                        "date": fmt_date(d.due_date),
                        "amount": f"{fmt_amount(d.amount_due)} FCFA",
                        "status": d.status.value,
                    }
                    for d in dues
                ],
            }
            text = f"Echeances de {contract.matricule}:\n" + "\n".join(lines)
        return result, contract.id, text
    if operation == "add_due":
        contract = _contract_from_params(db, actor, params)
        due = insurance_service.create_due(
            db,
            actor,
            contract_id=contract.id,
            due_date=params["due_date"],
            amount_due=params["amount"],
        )
        result = {
            "kind": "add_due",
            "matricule": contract.matricule,
            "amount": f"{fmt_amount(due.amount_due)} FCFA",
            "due_date": fmt_date(due.due_date),
        }
        text = (
            f"Echeance ajoutee pour {contract.matricule}: {fmt_amount(due.amount_due)} FCFA "
            f"au {fmt_date(due.due_date)}."
        )
        return result, due.id, text
    if operation == "add_purchase":
        quantity = params["quantity"]
        total_amount = params["amount"]
        unit_price = (total_amount / quantity).quantize(Decimal("0.01"))
        appro = poultry_service.create_approvisionnement(
            db,
            actor,
            quantity=quantity,
            unit_price=unit_price,
            note=params.get("note"),
            account_id=uuid.UUID(params["account_id"]),
            category_id=uuid.UUID(params["category_id"]),
        )
        result = {
            "kind": "add_purchase",
            "quantity": str(quantity),
            "amount": f"{fmt_amount(total_amount)} FCFA",
            "account": params["account_name"],
        }
        text = (
            f"Achat enregistre: {quantity} poulets pour {fmt_amount(total_amount)} FCFA "
            f"sur la caisse \"{params['account_name']}\" ({quantity} poulets ajoutes au stock)."
        )
        return result, appro.id, text
    if operation == "add_sale":
        quantity = params["quantity"]
        total_amount = params["amount"]
        unit_price = (total_amount / quantity).quantize(Decimal("0.01"))
        sale = poultry_service.create_vente(
            db,
            actor,
            quantity=quantity,
            unit_price=unit_price,
            account_id=uuid.UUID(params["account_id"]),
            category_id=uuid.UUID(params["category_id"]),
        )
        result = {
            "kind": "add_sale",
            "quantity": str(quantity),
            "amount": f"{fmt_amount(total_amount)} FCFA",
            "account": params["account_name"],
        }
        text = (
            f"Vente enregistree: {quantity} poulets pour {fmt_amount(total_amount)} FCFA "
            f"sur la caisse \"{params['account_name']}\"."
        )
        return result, sale.id, text
    if operation == "get_stock":
        total = poultry_service.get_stock_total(db, actor)
        result = {"kind": "get_stock", "quantity": str(total)}
        text = f"Stock disponible: {total} poulet(s)."
        return result, None, text
    raise HTTPException(status_code=400, detail=f"Operation inconnue: {operation}")


def amount_from_text(text: str) -> Decimal | None:
    return parse_amount(text)