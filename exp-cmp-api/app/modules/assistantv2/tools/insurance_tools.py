"""Outils de l'activite assurance. Chaque fonction a la signature
(db, actor, params) -> (facts, target_id, static_text), verifiee par
`registry.ToolHandler`. Portee depuis `assistant/executor.py` (v1), reorganisee
en un outil autonome par operation plutot qu'un if/elif unique.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.modules.assistantv2 import resolvers
from app.modules.assistantv2.registry import ToolSpec, register
from app.modules.identity.service import get_person_summary
from app.modules.insurance import service as insurance_service
from app.modules.ledger.models import CategoryType

BUSINESS_CODE = "assurance"
DEFAULT_CONTRACT_TYPE = "assurance-auto"


def create_client(db, actor, params: dict):
    full_name = " ".join(word.capitalize() for word in params["client"].split())
    client = insurance_service.create_client(
        db, actor, full_name=full_name, phone=params.get("phone"), client_number=params.get("client_number")
    )
    person = get_person_summary(db, client.person_id)
    facts = {"kind": "create_client", "client": person.full_name, "client_number": client.client_number}
    text = f"Client cree: {person.full_name} ({client.client_number})."
    return facts, client.id, text


def create_contract(db, actor, params: dict):
    client = insurance_service.find_client(db, actor, params["client"])
    person = get_person_summary(db, client.person_id)
    start = date.today()
    contract = insurance_service.create_contract(
        db, actor,
        client_id=client.id,
        matricule=params["matricule"],
        contract_type=DEFAULT_CONTRACT_TYPE,
        premium=params["premium"],
        start_date=start,
        end_date=start + timedelta(days=365),
    )
    remaining = insurance_service.remaining_amount(db, contract)
    facts = {
        "kind": "create_contract",
        "matricule": contract.matricule,
        "client": person.full_name,
        "premium": f"{resolvers.fmt_amount(contract.premium)} FCFA",
        "remaining": f"{resolvers.fmt_amount(remaining)} FCFA",
        "contract_type": contract.contract_type,
        "start_date": resolvers.fmt_date(contract.start_date),
        "end_date": resolvers.fmt_date(contract.end_date),
    }
    text = (
        f"Contrat cree: {contract.matricule} pour {person.full_name} - prime "
        f"{resolvers.fmt_amount(contract.premium)} FCFA, reste a payer {resolvers.fmt_amount(remaining)} FCFA "
        f"(type {contract.contract_type}, du {resolvers.fmt_date(contract.start_date)} au {resolvers.fmt_date(contract.end_date)})."
    )
    return facts, contract.id, text


def record_payment(db, actor, params: dict):
    contract_id = uuid.UUID(params["contract_id"])
    contract = insurance_service.get_contract(db, actor, contract_id)
    payment = insurance_service.create_payment(
        db, actor,
        contract_id=contract.id,
        amount=params["amount"],
        paid_at=None,
        account_id=uuid.UUID(params["account_id"]),
        category_id=uuid.UUID(params["category_id"]),
    )
    remaining = insurance_service.remaining_amount(db, contract)
    facts = {
        "kind": "record_payment",
        "amount": f"{resolvers.fmt_amount(payment.amount)} FCFA",
        "account": params["account_name"],
        "matricule": contract.matricule,
        "remaining": f"{resolvers.fmt_amount(remaining)} FCFA",
        "remaining_status": resolvers.remaining_status(remaining),
    }
    text = (
        f"Paiement encaisse: {resolvers.fmt_amount(payment.amount)} FCFA sur la caisse "
        f"\"{params['account_name']}\" pour le contrat {contract.matricule} - {resolvers.format_remaining(remaining)}."
    )
    return facts, payment.id, text


def _contract_from_params(db, actor, params: dict):
    if params.get("contract_id"):
        return insurance_service.get_contract(db, actor, uuid.UUID(params["contract_id"]))
    return resolvers.resolve_contract(db, actor, params["contract"])


def get_remaining(db, actor, params: dict):
    contract = _contract_from_params(db, actor, params)
    remaining = insurance_service.remaining_amount(db, contract)
    facts = {
        "kind": "get_remaining",
        "matricule": contract.matricule,
        "premium": f"{resolvers.fmt_amount(contract.premium)} FCFA",
        "remaining": f"{resolvers.fmt_amount(remaining)} FCFA",
        "remaining_status": resolvers.remaining_status(remaining),
    }
    text = f"{contract.matricule} - {resolvers.format_remaining(remaining)} (prime {resolvers.fmt_amount(contract.premium)} FCFA)."
    return facts, contract.id, text


def get_client_info(db, actor, params: dict):
    client = insurance_service.find_client(db, actor, params["client"])
    person = get_person_summary(db, client.person_id)
    contracts = insurance_service.list_contracts(db, actor, client_id=client.id)
    matricules = ", ".join(c.matricule for c in contracts) if contracts else "aucun"
    facts = {
        "kind": "get_client_info",
        "client": person.full_name,
        "client_number": client.client_number,
        "status": client.status.value,
        "phone": person.phone or "non renseigne",
        "contracts": matricules,
    }
    text = (
        f"Client {person.full_name} ({client.client_number}) - statut {client.status.value}, "
        f"telephone {person.phone or 'non renseigne'}. Contrats: {matricules}."
    )
    return facts, client.id, text


def get_contract_info(db, actor, params: dict):
    contract = _contract_from_params(db, actor, params)
    client = insurance_service.get_client(db, actor, contract.client_id)
    person = get_person_summary(db, client.person_id)
    payments = insurance_service.list_payments(db, actor, contract.id)
    total_paid = sum((p.amount for p in payments), start=Decimal("0"))
    remaining = insurance_service.remaining_amount(db, contract)
    facts = {
        "kind": "get_contract_info",
        "matricule": contract.matricule,
        "contract_type": contract.contract_type,
        "client": person.full_name,
        "premium": f"{resolvers.fmt_amount(contract.premium)} FCFA",
        "paid": f"{resolvers.fmt_amount(total_paid)} FCFA",
        "remaining": f"{resolvers.fmt_amount(remaining)} FCFA",
        "remaining_status": resolvers.remaining_status(remaining),
        "start_date": resolvers.fmt_date(contract.start_date),
        "end_date": resolvers.fmt_date(contract.end_date),
        "status": contract.status.value,
    }
    text = (
        f"Contrat {contract.matricule} ({contract.contract_type}) pour {person.full_name} - "
        f"prime {resolvers.fmt_amount(contract.premium)} FCFA, paye {resolvers.fmt_amount(total_paid)} FCFA, "
        f"{resolvers.format_remaining(remaining)}. Du {resolvers.fmt_date(contract.start_date)} au "
        f"{resolvers.fmt_date(contract.end_date)} - statut {contract.status.value}."
    )
    return facts, contract.id, text


def get_dues(db, actor, params: dict):
    contract = _contract_from_params(db, actor, params)
    dues = insurance_service.list_dues(db, actor, contract.id)
    if not dues:
        facts = {"kind": "get_dues", "matricule": contract.matricule, "dues": []}
        text = f"Aucune echeance programmee pour {contract.matricule}."
        return facts, contract.id, text
    lines = [f"- {resolvers.fmt_date(d.due_date)}: {resolvers.fmt_amount(d.amount_due)} FCFA ({d.status.value})" for d in dues]
    facts = {
        "kind": "get_dues",
        "matricule": contract.matricule,
        "dues": [
            {"date": resolvers.fmt_date(d.due_date), "amount": f"{resolvers.fmt_amount(d.amount_due)} FCFA", "status": d.status.value}
            for d in dues
        ],
    }
    text = f"Echeances de {contract.matricule}:\n" + "\n".join(lines)
    return facts, contract.id, text


def add_due(db, actor, params: dict):
    contract = _contract_from_params(db, actor, params)
    due = insurance_service.create_due(db, actor, contract_id=contract.id, due_date=params["due_date"], amount_due=params["amount"])
    facts = {
        "kind": "add_due",
        "matricule": contract.matricule,
        "amount": f"{resolvers.fmt_amount(due.amount_due)} FCFA",
        "due_date": resolvers.fmt_date(due.due_date),
    }
    text = f"Echeance ajoutee pour {contract.matricule}: {resolvers.fmt_amount(due.amount_due)} FCFA au {resolvers.fmt_date(due.due_date)}."
    return facts, due.id, text


def _register() -> None:
    register(ToolSpec(
        name="create_client",
        label="Creer un client",
        example="Creer un client Moussa Camara",
        handler=create_client,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "client": {"type": "string", "description": "Nom complet du client"},
                "phone": {"type": "string", "description": "Numero de telephone (optionnel)"},
                "client_number": {"type": "string", "description": "Numero de client existant (optionnel)"},
            },
            "required": ["client"],
        },
        order=["client"],
        questions={"client": "Quel client ? Indiquez le nom (ex. Moussa Camara)."},
        is_critical=False,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="create_contract",
        label="Creer un contrat",
        example="Nouveau contrat pour Tagoun, matricule MAT-100, prime 100 000",
        handler=create_contract,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "client": {"type": "string", "description": "Nom du client"},
                "matricule": {"type": "string", "description": "Matricule du contrat, ex. MAT-100"},
                "premium": {"type": "number", "description": "Montant total de la prime"},
            },
            "required": ["client", "matricule", "premium"],
        },
        order=["client", "matricule", "premium"],
        questions={
            "client": "Quel client ? Indiquez le nom (ex. Moussa Camara).",
            "matricule": "Quelle matricule ? (ex. MAT-001)",
            "premium": "Quel montant de prime ? (ex. 100 000)",
        },
        is_critical=True,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="record_payment",
        label="Encaisser une prime",
        example="Encaisser 40 000 de Tagoun pour le contrat MAT-E2E",
        handler=record_payment,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "contract": {"type": "string", "description": "Matricule du contrat ou nom du client"},
                "amount": {
                    "type": "number",
                    "description": "Montant encaisse. A omettre si le client paie tout ce qui reste.",
                },
                "account": {"type": "string", "description": "Nom de la caisse (optionnel s'il n'y en a qu'une)"},
                "category": {"type": "string", "description": "Categorie (optionnel s'il n'y en a qu'une)"},
            },
            "required": ["contract"],
        },
        order=["contract", "amount", "account", "category"],
        questions={
            "contract": "Pour quel contrat ? Indiquez la matricule (ex. MAT-001) ou le nom du client.",
            "amount": "Quel montant encaisser ? (ex. 40 000)",
            "account": "Sur quelle caisse ?",
            "category": "Sous quelle categorie ?",
        },
        category_type=CategoryType.CREDIT,
        is_critical=True,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="get_remaining",
        label="Reste a payer d'un contrat",
        example="Reste a payer du contrat MAT-E2E",
        handler=get_remaining,
        business=BUSINESS_CODE,
        parameters={"properties": {"contract": {"type": "string", "description": "Matricule du contrat ou nom du client"}}, "required": ["contract"]},
        order=["contract"],
        questions={"contract": "Pour quel contrat ? Indiquez la matricule (ex. MAT-001) ou le nom du client."},
    ))
    register(ToolSpec(
        name="get_client_info",
        label="Consulter les infos d'un client",
        example="Infos du client Tagoun",
        handler=get_client_info,
        business=BUSINESS_CODE,
        parameters={"properties": {"client": {"type": "string", "description": "Nom du client"}}, "required": ["client"]},
        order=["client"],
        questions={"client": "Quel client ? Indiquez le nom (ex. Moussa Camara)."},
    ))
    register(ToolSpec(
        name="get_contract_info",
        label="Consulter les infos d'un contrat",
        example="Infos du contrat MAT-E2E",
        handler=get_contract_info,
        business=BUSINESS_CODE,
        parameters={"properties": {"contract": {"type": "string", "description": "Matricule du contrat ou nom du client"}}, "required": ["contract"]},
        order=["contract"],
        questions={"contract": "Pour quel contrat ? Indiquez la matricule (ex. MAT-001) ou le nom du client."},
    ))
    register(ToolSpec(
        name="get_dues",
        label="Consulter les echeances",
        example="Echeances du contrat MAT-100",
        handler=get_dues,
        business=BUSINESS_CODE,
        parameters={"properties": {"contract": {"type": "string", "description": "Matricule du contrat ou nom du client"}}, "required": ["contract"]},
        order=["contract"],
        questions={"contract": "Pour quel contrat ? Indiquez la matricule (ex. MAT-001) ou le nom du client."},
    ))
    register(ToolSpec(
        name="add_due",
        label="Ajouter une echeance",
        example="Ajouter une echeance pour MAT-100 le 30/09 montant 20000",
        handler=add_due,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "contract": {"type": "string", "description": "Matricule du contrat ou nom du client"},
                "due_date": {"type": "string", "description": "Date de l'echeance, format ISO AAAA-MM-JJ"},
                "amount": {"type": "number", "description": "Montant prevu pour cette echeance"},
            },
            "required": ["contract", "due_date", "amount"],
        },
        order=["contract", "due_date", "amount"],
        questions={
            "contract": "Pour quel contrat ? Indiquez la matricule (ex. MAT-001) ou le nom du client.",
            "due_date": "Pour quelle date ? (ex. 30/09/2026)",
            "amount": "Quel montant prevoir pour cette echeance ?",
        },
        is_critical=False,
        is_read_only=False,
    ))


_register()
