"""Outils de l'activite poulets (poulailler)."""
import uuid
from decimal import Decimal

from app.modules.assistantv2 import resolvers
from app.modules.assistantv2.registry import ToolSpec, register
from app.modules.ledger.models import CategoryType
from app.modules.poultry import service as poultry_service

BUSINESS_CODE = "poulets"


def add_purchase(db, actor, params: dict):
    quantity = params["quantity"]
    total_amount = params["amount"]
    unit_price = (total_amount / quantity).quantize(Decimal("0.01"))
    appro = poultry_service.create_approvisionnement(
        db, actor,
        quantity=quantity,
        unit_price=unit_price,
        note=params.get("note"),
        account_id=uuid.UUID(params["account_id"]),
        category_id=uuid.UUID(params["category_id"]),
    )
    facts = {
        "kind": "add_purchase",
        "quantity": str(quantity),
        "amount": f"{resolvers.fmt_amount(total_amount)} FCFA",
        "account": params["account_name"],
    }
    text = (
        f"Achat enregistre: {quantity} poulets pour {resolvers.fmt_amount(total_amount)} FCFA "
        f"sur la caisse \"{params['account_name']}\" ({quantity} poulets ajoutes au stock)."
    )
    return facts, appro.id, text


def add_sale(db, actor, params: dict):
    quantity = params["quantity"]
    total_amount = params["amount"]
    unit_price = (total_amount / quantity).quantize(Decimal("0.01"))
    sale = poultry_service.create_vente(
        db, actor,
        quantity=quantity,
        unit_price=unit_price,
        account_id=uuid.UUID(params["account_id"]),
        category_id=uuid.UUID(params["category_id"]),
    )
    facts = {
        "kind": "add_sale",
        "quantity": str(quantity),
        "amount": f"{resolvers.fmt_amount(total_amount)} FCFA",
        "account": params["account_name"],
    }
    text = (
        f"Vente enregistree: {quantity} poulets pour {resolvers.fmt_amount(total_amount)} FCFA "
        f"sur la caisse \"{params['account_name']}\"."
    )
    return facts, sale.id, text


def get_stock(db, actor, params: dict):
    total = poultry_service.get_stock_total(db, actor)
    facts = {"kind": "get_stock", "quantity": str(total)}
    text = f"Stock disponible: {total} poulet(s)."
    return facts, None, text


def list_purchases(db, actor, params: dict):
    purchases = poultry_service.list_approvisionnements(db, actor, limit=50)
    if not purchases:
        return {"kind": "list_purchases", "purchases": []}, None, "Aucun achat enregistre."
    rows = []
    lines = []
    for p in purchases:
        amount = (p.unit_price * p.quantity).quantize(Decimal("0.01"))
        rows.append({
            "date": resolvers.fmt_date(p.created_at.date()),
            "quantity": str(p.quantity),
            "amount": f"{resolvers.fmt_amount(amount)} FCFA",
        })
        lines.append(f"- {rows[-1]['date']} : {p.quantity} poulets pour {rows[-1]['amount']}")
    facts = {"kind": "list_purchases", "purchases": rows}
    text = "Achats recents :\n" + "\n".join(lines)
    return facts, None, text


def list_sales(db, actor, params: dict):
    sales = poultry_service.list_ventes(db, actor, limit=50)
    if not sales:
        return {"kind": "list_sales", "sales": []}, None, "Aucune vente enregistree."
    rows = []
    lines = []
    for s in sales:
        amount = (s.unit_price * s.quantity).quantize(Decimal("0.01"))
        rows.append({
            "date": resolvers.fmt_date(s.created_at.date()),
            "quantity": str(s.quantity),
            "amount": f"{resolvers.fmt_amount(amount)} FCFA",
        })
        lines.append(f"- {rows[-1]['date']} : {s.quantity} poulets pour {rows[-1]['amount']}")
    facts = {"kind": "list_sales", "sales": rows}
    text = "Ventes recentes :\n" + "\n".join(lines)
    return facts, None, text


def _register() -> None:
    register(ToolSpec(
        name="add_purchase",
        label="Enregistrer un approvisionnement (poulailler)",
        example="J'ai achete 24 poulets a 120000",
        handler=add_purchase,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "quantity": {"type": "integer", "description": "Nombre de poulets achetes"},
                "amount": {"type": "number", "description": "Montant total paye pour cet achat"},
                "account": {"type": "string", "description": "Nom de la caisse (optionnel)"},
                "category": {"type": "string", "description": "Categorie (optionnel)"},
                "note": {"type": "string", "description": "Note libre, ex. provenance (optionnel)"},
            },
            "required": ["quantity", "amount"],
        },
        order=["quantity", "amount", "account", "category"],
        questions={
            "quantity": "Combien de poulets ?",
            "amount": "Pour quel montant total ?",
            "account": "Sur quelle caisse ?",
            "category": "Sous quelle categorie ?",
        },
        category_type=CategoryType.DEBIT,
        is_critical=True,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="add_sale",
        label="Enregistrer une vente (poulailler)",
        example="J'ai vendu 8 poulets pour 60000",
        handler=add_sale,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "quantity": {"type": "integer", "description": "Nombre de poulets vendus"},
                "amount": {"type": "number", "description": "Montant total encaisse pour cette vente"},
                "account": {"type": "string", "description": "Nom de la caisse (optionnel)"},
                "category": {"type": "string", "description": "Categorie (optionnel)"},
            },
            "required": ["quantity", "amount"],
        },
        order=["quantity", "amount", "account", "category"],
        questions={
            "quantity": "Combien de poulets ?",
            "amount": "Pour quel montant total ?",
            "account": "Sur quelle caisse ?",
            "category": "Sous quelle categorie ?",
        },
        category_type=CategoryType.CREDIT,
        is_critical=True,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="get_stock",
        label="Consulter le stock de poulets",
        example="Combien de poulets me reste-t-il ?",
        handler=get_stock,
        business=BUSINESS_CODE,
        parameters={"properties": {}, "required": []},
        order=[],
    ))
    register(ToolSpec(
        name="list_purchases",
        label="Lister les achats de poulets",
        example="Historique de mes achats de poulets",
        handler=list_purchases,
        business=BUSINESS_CODE,
        parameters={"properties": {}, "required": []},
        order=[],
    ))
    register(ToolSpec(
        name="list_sales",
        label="Lister les ventes de poulets",
        example="Historique de mes ventes de poulets",
        handler=list_sales,
        business=BUSINESS_CODE,
        parameters={"properties": {}, "required": []},
        order=[],
    ))


_register()
