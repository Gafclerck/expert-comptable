"""Outils transverses (business=None) : disponibles a toute activite sans
qu'un business ait quoi que ce soit a declarer. Ne registre aucun business
module (pas d'alias, pas de hint) : ce fichier n'EST pas un business, c'est le
framework lui-meme.
"""
from datetime import date

from fastapi import HTTPException

from app.modules.assistantv3 import parsing, registry, resolvers
from app.modules.assistantv3.registry import ToolSpec, register
from app.modules.identity.service import get_business_by_code
from app.modules.ledger import service as ledger_service


def get_balance(db, actor, params: dict):
    """Sans reference : solde de TOUTES les caisses accessibles (une par
    activite). Avec reference ('account' et/ou 'business') : une seule
    caisse. Inclut encaisse/depense cumules pour la caisse ciblee."""
    targets = resolvers.resolve_balance_targets(db, actor, params.get("account"), params.get("business"))
    if len(targets) == 1:
        business, account = targets[0]
        detail = ledger_service.compute_balance(db, account)
        facts = {
            "kind": "get_balance",
            "account": account.name,
            "balance": f"{resolvers.fmt_amount(detail['balance'])} FCFA",
            "inflows": f"{resolvers.fmt_amount(detail['inflows'])} FCFA",
            "outflows": f"{resolvers.fmt_amount(detail['outflows'])} FCFA",
        }
        text = (
            f"Solde de la caisse \"{account.name}\": {resolvers.fmt_amount(detail['balance'])} FCFA "
            f"(encaisse: {resolvers.fmt_amount(detail['inflows'])} FCFA, depense: {resolvers.fmt_amount(detail['outflows'])} FCFA)."
        )
        return facts, account.id, text

    rows = []
    lines = []
    for business, account in targets:
        balance = ledger_service.compute_balance(db, account)["balance"]
        rows.append({"business": business.name, "account": account.name, "balance": f"{resolvers.fmt_amount(balance)} FCFA"})
        lines.append(f"- {business.name} ({account.name}): {resolvers.fmt_amount(balance)} FCFA")
    facts = {"kind": "get_balance", "balances": rows}
    text = "Soldes de vos caisses:\n" + "\n".join(lines)
    return facts, None, text


def list_transactions(db, actor, params: dict):
    business_id = None
    business_label = None
    ref = params.get("business")
    if ref:
        code = resolvers.business_code_for(ref, ref)
        try:
            business = get_business_by_code(db, code)
        except HTTPException:
            business = None
        if business is not None:
            business_id = business.id
            business_label = business.name

    transactions = ledger_service.list_transactions(db, actor, business_id=business_id, limit=20)
    if not transactions:
        text = f"Aucune transaction pour {business_label}." if business_label else "Aucune transaction enregistree."
        return {"kind": "list_transactions", "transactions": []}, None, text

    rows = []
    lines = []
    for t in transactions:
        row = {
            "date": t.occurred_at.strftime("%d/%m/%Y"),
            "type": t.type.value,
            "amount": f"{resolvers.fmt_amount(t.amount)} FCFA",
            "description": t.description or "",
        }
        rows.append(row)
        suffix = f" - {t.description}" if t.description else ""
        lines.append(f"- {row['date']} [{row['type']}] {row['amount']}{suffix}")
    facts = {"kind": "list_transactions", "transactions": rows}
    header = f"Dernieres transactions ({business_label}) :" if business_label else "Dernieres transactions (toutes activites) :"
    text = header + "\n" + "\n".join(lines)
    return facts, None, text


def get_period_summary(db, actor, params: dict):
    parsed = parsing.parse_period(params.get("period") or "")
    if parsed is None:
        start, end, label = date.today().replace(day=1), date.today(), "ce mois"
    else:
        start, end, label = parsed

    ref = params.get("business")
    businesses = None
    if ref:
        code = resolvers.business_code_for(ref, ref)
        try:
            businesses = [get_business_by_code(db, code)]
        except HTTPException:
            businesses = None
    if businesses is None:
        businesses = resolvers.accessible_businesses(db, actor)

    rows = []
    lines = []
    for business in businesses:
        detail = ledger_service.compute_period_totals(db, actor, business.id, start, end)
        rows.append({
            "business": business.name,
            "inflows": f"{resolvers.fmt_amount(detail['inflows'])} FCFA",
            "outflows": f"{resolvers.fmt_amount(detail['outflows'])} FCFA",
            "net": f"{resolvers.fmt_amount(detail['net'])} FCFA",
        })
        lines.append(
            f"- {business.name} : encaisse {resolvers.fmt_amount(detail['inflows'])} FCFA, "
            f"depense {resolvers.fmt_amount(detail['outflows'])} FCFA, net {resolvers.fmt_amount(detail['net'])} FCFA"
        )
    facts = {
        "kind": "get_period_summary",
        "period": label,
        "period_start": resolvers.fmt_date(start),
        "period_end": resolvers.fmt_date(end),
        "totals": rows,
    }
    text = f"Resume {label} (du {resolvers.fmt_date(start)} au {resolvers.fmt_date(end)}) :\n" + "\n".join(lines)
    return facts, None, text


def help_tool(db, actor, params: dict):
    lines = ["Voici ce que je peux faire:"]
    for spec in registry.all_tools():
        lines.append(f"- {spec.label} : {spec.example}")
    return {"kind": "help"}, None, "\n".join(lines)


def _register() -> None:
    register(ToolSpec(
        name="get_balance",
        label="Consulter le solde d'une ou toutes les caisses",
        example="Solde de la caisse, ou : quels sont les soldes de mes caisses",
        handler=get_balance,
        business=None,
        parameters={
            "properties": {
                "account": {"type": "string", "description": "Nom de la caisse (optionnel)"},
                "business": {"type": "string", "description": "Activite concernee (optionnel, ex. assurance, poulets)"},
            },
            "required": [],
        },
        order=[],
        is_critical=False,
        is_read_only=True,
    ))
    register(ToolSpec(
        name="help",
        label="Aide",
        example="aide",
        handler=help_tool,
        business=None,
        parameters={"properties": {}, "required": []},
        order=[],
    ))
    register(ToolSpec(
        name="list_transactions",
        label="Consulter l'historique des transactions",
        example="Quelles sont mes dernieres transactions ? ou : historique de la caisse poulets",
        handler=list_transactions,
        business=None,
        parameters={
            "properties": {"business": {"type": "string", "description": "Activite concernee (optionnel, sinon toutes)"}},
            "required": [],
        },
        order=[],
        is_critical=False,
        is_read_only=True,
    ))
    register(ToolSpec(
        name="get_period_summary",
        label="Resume des encaissements et depenses sur une periode",
        example="Combien j'ai encaisse ce mois ? ou : depenses de la semaine derniere",
        handler=get_period_summary,
        business=None,
        parameters={
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Periode en langage naturel : aujourd'hui, hier, cette semaine, la semaine derniere, ce mois, le mois dernier, cette annee. Par defaut : ce mois.",
                },
                "business": {"type": "string", "description": "Activite concernee (optionnel, sinon toutes)"},
            },
            "required": [],
        },
        order=[],
        is_critical=False,
        is_read_only=True,
    ))


_register()
