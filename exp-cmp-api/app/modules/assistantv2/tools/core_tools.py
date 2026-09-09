"""Outils transverses : applicables a toute activite, pas rattaches a un
business precis (business=None dans le ToolSpec). Un nouveau business
beneficie automatiquement de ces outils des sa creation, sans aucune
modification ici.
"""
from app.modules.assistantv2 import registry, resolvers
from app.modules.assistantv2.registry import ToolSpec, register
from app.modules.ledger import service as ledger_service


def get_balance(db, actor, params: dict):
    """Sans reference : renvoie le solde de TOUTES les caisses accessibles
    (une par activite). Avec une reference ("account" et/ou "business") :
    cible une seule caisse, comme en v1. C'est ce comportement par defaut qui
    repond a « quels sont les soldes de mes comptes » sans que le LLM ait
    besoin d'appeler l'outil plusieurs fois."""
    targets = resolvers.resolve_balance_targets(db, actor, params.get("account"), params.get("business"))
    if len(targets) == 1:
        business, account = targets[0]
        balance = ledger_service.compute_balance(db, account)["balance"]
        facts = {"kind": "get_balance", "account": account.name, "balance": f"{resolvers.fmt_amount(balance)} FCFA"}
        text = f"Solde de la caisse \"{account.name}\": {resolvers.fmt_amount(balance)} FCFA."
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


def help_tool(db, actor, params: dict):
    lines = ["Voici ce que je peux faire:"]
    for spec in registry.all_tools():
        lines.append(f"- {spec.label} : {spec.example}")
    text = "\n".join(lines)
    return {"kind": "help"}, None, text


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


_register()
