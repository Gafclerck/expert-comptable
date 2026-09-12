"""Outils de l'activite VTC (chauffeurs, vehicules, affectations,
versements, depenses, indisponibilites). Meme contrat que les autres modules
d'outils : chaque fonction (db, actor, params) -> (facts, target_id,
static_text). La resolution chauffeur/vehicule passe par resolvers.py
(depend uniquement de la facade `vtc.service`).
"""
import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException

from app.modules.assistantv2 import parsing, resolvers
from app.modules.assistantv2.registry import ToolSpec, register
from app.modules.ledger.models import CategoryType
from app.modules.vtc.models import AffectationStatut, TypeDepenseVehicule
from app.modules.vtc import service as vtc_service

BUSINESS_CODE = "vtc"

_EXPENSE_TYPE_ALIASES = {
    "fuel": {"fuel", "carburant", "essence", "gazole", "gasoil"},
    "maintenance": {"maintenance", "entretien"},
    "repair": {"repair", "reparation", "reparations", "mecanique"},
    "tires": {"tires", "pneus", "pneu"},
    "insurance": {"insurance", "assurance"},
    "registration": {"registration", "immatriculation", "carte grise"},
    "misc": {"misc", "divers", "autre"},
}


def _resolve_expense_type(ref: str) -> TypeDepenseVehicule:
    norm = resolvers.normalize(ref)
    for code, aliases in _EXPENSE_TYPE_ALIASES.items():
        if norm in aliases or norm == code:
            return TypeDepenseVehicule(code)
    raise resolvers.ClarificationNeeded(
        "expense_type",
        "Type de depense inconnu. Options : carburant, entretien, reparation, pneus, assurance, immatriculation, divers.",
    )


def _money(value) -> str:
    return f"{resolvers.fmt_amount(Decimal(str(value)))} FCFA"


def create_chauffeur(db, actor, params: dict):
    if not params.get("driver"):
        raise resolvers.ClarificationNeeded("driver", "Quel est le nom du chauffeur ?")
    full_name = " ".join(word.capitalize() for word in params["driver"].split())
    chauffeur = vtc_service.create_chauffeur(
        db, actor, full_name=full_name, phone=params.get("phone"), license_number=params.get("license_number")
    )
    facts = {"kind": "create_chauffeur", "driver": full_name, "status": chauffeur.status.value}
    text = f"Chauffeur cree: {full_name}."
    return facts, chauffeur.id, text


def create_vehicule(db, actor, params: dict):
    year = int(params["year"]) if params.get("year") else None
    vehicule = vtc_service.create_vehicule(
        db, actor,
        make=params["make"],
        model=params["model"],
        year=year,
        registration=params["registration"],
        acquisition_cost=params.get("acquisition_cost") or Decimal("0"),
    )
    facts = {
        "kind": "create_vehicule",
        "make": vehicule.make,
        "model": vehicule.model,
        "registration": vehicule.registration,
        "status": vehicule.status.value,
    }
    text = f"Vehicule cree: {vehicule.make} {vehicule.model} ({vehicule.registration})."
    return facts, vehicule.id, text


def create_affectation(db, actor, params: dict):
    affectation = vtc_service.create_affectation(
        db, actor,
        driver_id=uuid.UUID(params["driver_id"]),
        vehicle_id=uuid.UUID(params["vehicle_id"]),
        start_date=params.get("start_date") or date.today(),
        end_date=params.get("end_date"),
        expected_amount=params["expected_amount"],
        terms=params.get("terms"),
    )
    out = vtc_service.to_affectation_out(db, affectation)
    facts = {
        "kind": "create_affectation",
        "driver": out["driver_name"],
        "vehicle": out["vehicle_registration"],
        "expected_amount": _money(out["expected_amount"]),
        "start_date": out["start_date"],
        "status": out["status"],
    }
    text = (
        f"Affectation creee: {out['driver_name']} sur {out['vehicle_registration']} - "
        f"montant attendu {_money(out['expected_amount'])} (debut {out['start_date']})."
    )
    return facts, affectation.id, text


def record_versement(db, actor, params: dict):
    versement = vtc_service.create_versement(
        db, actor,
        driver_id=uuid.UUID(params["driver_id"]),
        vehicle_id=uuid.UUID(params["vehicle_id"]),
        amount=params["amount"],
        account_id=uuid.UUID(params["account_id"]),
        category_id=uuid.UUID(params["category_id"]),
    )
    sold = vtc_service.statut_paiement_chauffeur(db, actor, uuid.UUID(params["driver_id"]))
    remaining = sold["total_remaining"]
    facts = {
        "kind": "record_versement",
        "amount": _money(versement.amount),
        "account": params["account_name"],
        "driver": params["driver_name"],
        "vehicle": params["vehicle_label"],
        "remaining": _money(remaining),
    }
    text = (
        f"Versement enregistre: {_money(versement.amount)} de {params['driver_name']} "
        f"sur la caisse \"{params['account_name']}\" pour {params['vehicle_label']}. "
        f"Reste a payer sur l'affectation en cours: {_money(remaining)}."
    )
    return facts, versement.id, text


def record_depense(db, actor, params: dict):
    expense_type = _resolve_expense_type(params["expense_type"])
    quantity = Decimal(str(params["quantity"])) if params.get("quantity") is not None else None
    depense = vtc_service.create_depense(
        db, actor,
        vehicle_id=uuid.UUID(params["vehicle_id"]),
        expense_type=expense_type,
        amount=params["amount"],
        quantity=quantity,
        unit=params.get("unit"),
        description=params.get("description"),
        account_id=uuid.UUID(params["account_id"]),
        category_id=uuid.UUID(params["category_id"]),
    )
    facts = {
        "kind": "record_depense",
        "vehicle": params["vehicle_label"],
        "expense_type": depense.expense_type.value,
        "amount": _money(depense.amount),
        "account": params["account_name"],
    }
    text = (
        f"Depense enregistree ({depense.expense_type.value}): {_money(depense.amount)} "
        f"sur {params['vehicle_label']}, caisse \"{params['account_name']}\"."
    )
    return facts, depense.id, text


def declare_indisponibilite(db, actor, params: dict):
    indispo = vtc_service.create_indisponibilite(
        db, actor,
        vehicle_id=uuid.UUID(params["vehicle_id"]),
        start_date=params.get("start_date") or date.today(),
        end_date=params.get("end_date"),
        reason=params.get("reason"),
    )
    facts = {
        "kind": "declare_indisponibilite",
        "vehicle": params["vehicle_label"],
        "start_date": resolvers.fmt_date(indispo.start_date),
        "end_date": resolvers.fmt_date(indispo.end_date),
    }
    text = f"Indisponibilite declaree pour {params['vehicle_label']} a partir du {resolvers.fmt_date(indispo.start_date)}."
    return facts, indispo.id, text


def end_affectation(db, actor, params: dict):
    actives = vtc_service.list_affectations(
        db, actor,
        driver_id=uuid.UUID(params["driver_id"]),
        vehicle_id=uuid.UUID(params["vehicle_id"]),
        status=AffectationStatut.ACTIVE,
    )
    if params.get("affectation_id"):
        actives = [
            a for a in actives if str(a["id"]) == str(params["affectation_id"])
        ] or actives
    if not actives:
        raise HTTPException(status_code=400, detail="Aucune affectation active pour ce chauffeur/vehicule")
    if len(actives) > 1:
        raise resolvers.ClarificationNeeded(
            "affectation",
            "Plusieurs affectations actives, laquelle ?",
            [
                {"name": f"Debut {a['start_date']} - attendu {_money(a['expected_amount'])}", "id": str(a["id"])}
                for a in actives
            ],
        )
    ended = vtc_service.end_affectation(db, actor, actives[0]["id"], end_date=params.get("end_date"))
    out = vtc_service.to_affectation_out(db, ended)
    facts = {
        "kind": "end_affectation",
        "driver": out["driver_name"],
        "vehicle": out["vehicle_registration"],
        "end_date": out["end_date"],
        "status": out["status"],
    }
    text = f"Affectation terminee: {out['driver_name']} / {out['vehicle_registration']} (cloturee le {out['end_date']})."
    return facts, ended.id, text


def list_chauffeurs(db, actor, params: dict):
    chauffeurs = vtc_service.list_chauffeurs(db, actor)
    if not chauffeurs:
        return {"kind": "list_chauffeurs", "chauffeurs": []}, None, "Aucun chauffeur enregistre."
    rows = [{"name": c["full_name"], "phone": c["phone"] or "", "status": c["status"]} for c in chauffeurs]
    lines = []
    for r in rows:
        phone = f" - {r['phone']}" if r["phone"] else ""
        lines.append(f"- {r['name']} ({r['status']}){phone}")
    facts = {"kind": "list_chauffeurs", "count": str(len(chauffeurs)), "chauffeurs": rows}
    text = f"Chauffeurs ({len(chauffeurs)}) :\n" + "\n".join(lines)
    return facts, None, text


def list_vehicules(db, actor, params: dict):
    vehicules = vtc_service.list_vehicules(db, actor)
    if not vehicules:
        return {"kind": "list_vehicules", "vehicules": []}, None, "Aucun vehicule enregistre."
    rows = [
        {
            "make": v.make,
            "model": v.model,
            "registration": v.registration,
            "year": str(v.year) if v.year else "",
            "status": v.status.value,
        }
        for v in vehicules
    ]
    lines = [f"- {r['make']} {r['model']} ({r['registration']}) - {r['status']}" for r in rows]
    facts = {"kind": "list_vehicules", "count": str(len(vehicules)), "vehicules": rows}
    text = f"Vehicules ({len(vehicules)}) :\n" + "\n".join(lines)
    return facts, None, text


def list_affectations(db, actor, params: dict):
    driver_id = None
    if params.get("driver"):
        driver_id = uuid.UUID(resolvers.resolve_driver(db, actor, params["driver"])["id"])
    vehicle_id = None
    if params.get("vehicle"):
        vehicle_id = resolvers.resolve_vehicle(db, actor, params["vehicle"]).id
    affectations = vtc_service.list_affectations(db, actor, driver_id=driver_id, vehicle_id=vehicle_id)
    if not affectations:
        return {"kind": "list_affectations", "affectations": []}, None, "Aucune affectation trouvee."
    rows = []
    lines = []
    for a in affectations:
        rows.append({
            "driver": a["driver_name"],
            "vehicle": a["vehicle_registration"],
            "expected_amount": _money(a["expected_amount"]),
            "paid_amount": _money(a["paid_amount"]),
            "remaining_amount": _money(a["remaining_amount"]),
            "status": a["status"],
        })
        lines.append(
            f"- {a['driver_name']} / {a['vehicle_registration']}: attendu {_money(a['expected_amount'])}, "
            f"paye {_money(a['paid_amount'])}, reste {_money(a['remaining_amount'])} ({a['status']})"
        )
    facts = {"kind": "list_affectations", "count": str(len(affectations)), "affectations": rows}
    text = f"Affectations ({len(affectations)}) :\n" + "\n".join(lines)
    return facts, None, text


def get_chauffeur_sold(db, actor, params: dict):
    sold = vtc_service.statut_paiement_chauffeur(db, actor, uuid.UUID(params["driver_id"]))
    facts = {
        "kind": "get_chauffeur_sold",
        "driver": params["driver_name"],
        "total_expected": _money(sold["total_expected"]),
        "total_paid": _money(sold["total_paid"]),
        "total_remaining": _money(sold["total_remaining"]),
    }
    text = (
        f"Chauffeur {params['driver_name']}: attendu {_money(sold['total_expected'])}, "
        f"paye {_money(sold['total_paid'])}, reste a payer {_money(sold['total_remaining'])}."
    )
    return facts, uuid.UUID(params["driver_id"]), text


def get_vehicle_stats(db, actor, params: dict):
    stats = vtc_service.statistiques_vehicule(db, actor, uuid.UUID(params["vehicle_id"]))
    facts = {
        "kind": "get_vehicle_stats",
        "vehicle": params["vehicle_label"],
        "versements": _money(stats["versements"]),
        "depenses": _money(stats["depenses"]),
        "rentabilite": _money(stats["rentabilite"]),
        "cout_acquisition": _money(stats["cout_acquisition"]),
        "depenses_par_type": {k: _money(v) for k, v in stats["depenses_par_type"].items()},
    }
    text = (
        f"{params['vehicle_label']}: versements {_money(stats['versements'])}, "
        f"depenses {_money(stats['depenses'])}, rentabilite {_money(stats['rentabilite'])}."
    )
    return facts, uuid.UUID(params["vehicle_id"]), text


def list_depenses(db, actor, params: dict):
    vehicle_id = None
    if params.get("vehicle"):
        vehicle_id = resolvers.resolve_vehicle(db, actor, params["vehicle"]).id
    depenses = vtc_service.list_depenses(db, actor, vehicle_id=vehicle_id)
    if not depenses:
        return {"kind": "list_depenses", "depenses": []}, None, "Aucune depense enregistree."
    rows = [{
        "date": resolvers.fmt_date(d.occurred_at.date()),
        "expense_type": d.expense_type.value,
        "amount": _money(d.amount),
    } for d in depenses]
    lines = [f"- {r['date']} [{r['expense_type']}] {r['amount']}" for r in rows]
    facts = {"kind": "list_depenses", "count": str(len(depenses)), "depenses": rows}
    text = f"Depenses ({len(depenses)}) :\n" + "\n".join(lines)
    return facts, None, text


def get_resume_financier(db, actor, params: dict):
    parsed = parsing.parse_period(params.get("period") or "")
    if parsed:
        start, end, label = parsed
    else:
        start, end, label = None, None, "toutes periodes"
    resume = vtc_service.resume_financier(db, actor, start=start, end=end)
    t = resume["totals"]
    facts = {
        "kind": "get_resume_financier",
        "period": label,
        "versements": _money(t["versements"]),
        "depenses": _money(t["depenses"]),
        "net": _money(t["net"]),
        "per_vehicle": [
            {
                "make": v["make"],
                "model": v["model"],
                "registration": v["registration"],
                "versements": _money(v["versements"]),
                "depenses": _money(v["depenses"]),
                "net": _money(v["net"]),
            }
            for v in resume["per_vehicle"]
        ],
    }
    lines = [
        f"- {v['make']} {v['model']} ({v['registration']}): versements {_money(v['versements'])}, "
        f"depenses {_money(v['depenses'])}, net {_money(v['net'])}"
        for v in resume["per_vehicle"]
    ]
    header = f"Resume financier VTC ({label}): encaisse {_money(t['versements'])}, depense {_money(t['depenses'])}, net {_money(t['net'])}."
    text = (header + "\n" + "\n".join(lines)) if lines else header
    return facts, None, text


def _register() -> None:
    register(ToolSpec(
        name="create_chauffeur",
        label="Creer un chauffeur",
        example="Nouveau chauffeur Moussa Fall",
        handler=create_chauffeur,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "driver": {"type": "string", "description": "Nom complet du chauffeur"},
                "phone": {"type": "string", "description": "Numero de telephone (optionnel)"},
                "license_number": {"type": "string", "description": "Numero de permis (optionnel)"},
            },
            "required": ["driver"],
        },
        # "driver" est un nouveau nom, pas une reference a un chauffeur existant
        # : on ne le met pas dans `order` (sinon _RESOLVABLE_FIELDS tenterait de
        # le resoudre) ; le handler signale lui-meme le champ manquant.
        order=[],
        questions={},
        is_critical=False,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="create_vehicule",
        label="Enregistrer un vehicule",
        example="Nouveau vehicule Toyota Corolla, immatriculation DK-1234-AB",
        handler=create_vehicule,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "make": {"type": "string", "description": "Marque"},
                "model": {"type": "string", "description": "Modele"},
                "registration": {"type": "string", "description": "Immatriculation unique, ex. DK-1234-AB"},
                "year": {"type": "integer", "description": "Annee (optionnel)"},
                "acquisition_cost": {"type": "number", "description": "Cout d'acquisition en FCFA (optionnel)"},
            },
            "required": ["make", "model", "registration"],
        },
        order=["make", "model", "registration"],
        questions={
            "make": "Quelle marque ?",
            "model": "Quel modele ?",
            "registration": "Quelle immatriculation ? (ex. DK-1234-AB)",
        },
        is_critical=False,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="create_affectation",
        label="Affecter un chauffeur a un vehicule",
        example="Affecter Moussa Fall au vehicule DK-1234-AB pour 50 000",
        handler=create_affectation,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "driver": {"type": "string", "description": "Nom du chauffeur"},
                "vehicle": {"type": "string", "description": "Immatriculation du vehicule"},
                "expected_amount": {"type": "number", "description": "Montant attendu pour cette affectation"},
                "start_date": {"type": "string", "description": "Date de debut (AAAA-MM-JJ, optionnel)"},
                "end_date": {"type": "string", "description": "Date de fin (AAAA-MM-JJ, optionnel)"},
                "terms": {"type": "string", "description": "Conditions (optionnel)"},
            },
            "required": ["driver", "vehicle", "expected_amount"],
        },
        order=["driver", "vehicle", "expected_amount"],
        questions={
            "driver": "Quel chauffeur ?",
            "vehicle": "Quel vehicule ?",
            "expected_amount": "Quel montant attendu ?",
        },
        is_critical=True,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="record_versement",
        label="Enregistrer un versement de chauffeur",
        example="Moussa Fall a verse 25 000 sur la caisse pour DK-1234-AB",
        handler=record_versement,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "driver": {"type": "string", "description": "Nom du chauffeur"},
                "vehicle": {"type": "string", "description": "Immatriculation du vehicule"},
                "amount": {"type": "number", "description": "Montant verse"},
                "account": {"type": "string", "description": "Nom de la caisse (optionnel)"},
                "category": {"type": "string", "description": "Categorie (optionnel)"},
            },
            "required": ["driver", "vehicle", "amount"],
        },
        order=["driver", "vehicle", "amount", "account", "category"],
        questions={
            "driver": "Quel chauffeur ?",
            "vehicle": "Quel vehicule ?",
            "amount": "Quel montant verse ?",
            "account": "Sur quelle caisse ?",
            "category": "Sous quelle categorie ?",
        },
        category_type=CategoryType.CREDIT,
        is_critical=True,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="record_depense",
        label="Enregistrer une depense vehicule",
        example="Depense de carburant 15 000 sur DK-1234-AB",
        handler=record_depense,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "vehicle": {"type": "string", "description": "Immatriculation du vehicule"},
                "expense_type": {"type": "string", "description": "Type de depense: fuel, maintenance, repair, tires, insurance, registration, misc"},
                "amount": {"type": "number", "description": "Montant de la depense"},
                "account": {"type": "string", "description": "Nom de la caisse (optionnel)"},
                "category": {"type": "string", "description": "Categorie (optionnel)"},
                "quantity": {"type": "number", "description": "Quantite (carburant en litres, optionnel)"},
                "unit": {"type": "string", "description": "Unite, ex. litre (optionnel)"},
                "description": {"type": "string", "description": "Description libre (optionnel)"},
            },
            "required": ["vehicle", "expense_type", "amount"],
        },
        order=["vehicle", "expense_type", "amount", "account", "category"],
        questions={
            "vehicle": "Quel vehicule ?",
            "expense_type": "Quel type de depense ? (carburant, entretien, reparation, pneus, assurance, immatriculation, divers)",
            "amount": "Quel montant ?",
            "account": "Sur quelle caisse ?",
            "category": "Sous quelle categorie ?",
        },
        category_type=CategoryType.DEBIT,
        is_critical=True,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="declare_indisponibilite",
        label="Declarer l'indisponibilite d'un vehicule",
        example="DK-1234-AB est en panne a partir d'aujourd'hui",
        handler=declare_indisponibilite,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "vehicle": {"type": "string", "description": "Immatriculation du vehicule"},
                "start_date": {"type": "string", "description": "Date de debut (AAAA-MM-JJ, optionnel)"},
                "end_date": {"type": "string", "description": "Date de fin (AAAA-MM-JJ, optionnel)"},
                "reason": {"type": "string", "description": "Motif (optionnel)"},
            },
            "required": ["vehicle"],
        },
        order=["vehicle"],
        questions={"vehicle": "Quel vehicule ?"},
        is_critical=False,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="end_affectation",
        label="Cloturer une affectation chauffeur/vehicule",
        example="Cloturer l'affectation de Moussa Fall sur DK-1234-AB",
        handler=end_affectation,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "driver": {"type": "string", "description": "Nom du chauffeur"},
                "vehicle": {"type": "string", "description": "Immatriculation du vehicule"},
                "end_date": {"type": "string", "description": "Date de cloture (AAAA-MM-JJ, optionnel)"},
            },
            "required": ["driver", "vehicle"],
        },
        order=["driver", "vehicle"],
        questions={
            "driver": "Quel chauffeur ?",
            "vehicle": "Quel vehicule ?",
        },
        is_critical=True,
        is_read_only=False,
    ))
    register(ToolSpec(
        name="list_chauffeurs",
        label="Lister les chauffeurs",
        example="Quels sont mes chauffeurs ?",
        handler=list_chauffeurs,
        business=BUSINESS_CODE,
        parameters={"properties": {}, "required": []},
        order=[],
    ))
    register(ToolSpec(
        name="list_vehicules",
        label="Lister les vehicules",
        example="Quels sont mes vehicules ?",
        handler=list_vehicules,
        business=BUSINESS_CODE,
        parameters={"properties": {}, "required": []},
        order=[],
    ))
    register(ToolSpec(
        name="list_affectations",
        label="Lister les affectations chauffeur/vehicule",
        example="Quelles sont mes affectations ? ou : affectations de Moussa Fall",
        handler=list_affectations,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "driver": {"type": "string", "description": "Nom du chauffeur (optionnel, sinon toutes)"},
                "vehicle": {"type": "string", "description": "Immatriculation du vehicule (optionnel, sinon toutes)"},
            },
            "required": [],
        },
        order=[],
    ))
    register(ToolSpec(
        name="get_chauffeur_sold",
        label="Reste a payer d'un chauffeur",
        example="Reste a payer de Moussa Fall",
        handler=get_chauffeur_sold,
        business=BUSINESS_CODE,
        parameters={"properties": {"driver": {"type": "string", "description": "Nom du chauffeur"}}, "required": ["driver"]},
        order=["driver"],
        questions={"driver": "Quel chauffeur ?"},
    ))
    register(ToolSpec(
        name="get_vehicle_stats",
        label="Statistiques de rentabilite d'un vehicule",
        example="Rentabilite du vehicule DK-1234-AB",
        handler=get_vehicle_stats,
        business=BUSINESS_CODE,
        parameters={"properties": {"vehicle": {"type": "string", "description": "Immatriculation du vehicule"}}, "required": ["vehicle"]},
        order=["vehicle"],
        questions={"vehicle": "Quel vehicule ?"},
    ))
    register(ToolSpec(
        name="list_depenses",
        label="Lister les depenses vehicule",
        example="Historique des depenses du vehicule DK-1234-AB",
        handler=list_depenses,
        business=BUSINESS_CODE,
        parameters={
            "properties": {"vehicle": {"type": "string", "description": "Immatriculation du vehicule (optionnel, sinon toutes)"}},
            "required": [],
        },
        order=[],
    ))
    register(ToolSpec(
        name="get_resume_financier",
        label="Resume financier VTC (versements, depenses, net)",
        example="Resume financier du VTC ce mois",
        handler=get_resume_financier,
        business=BUSINESS_CODE,
        parameters={
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Periode en langage naturel (aujourd'hui, cette semaine, ce mois, le mois dernier, cette annee). Par defaut : toutes periodes.",
                }
            },
            "required": [],
        },
        order=[],
    ))


_register()