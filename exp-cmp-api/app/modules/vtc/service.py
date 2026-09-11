import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.events import publish
from app.modules.identity.service import (
    create_person,
    get_business_by_code,
    get_business_ids_for_user,
    get_person_summary,
)
from app.modules.ledger.service import compute_balance, list_accounts, record_expense, record_revenue
from app.modules.vtc.models import (
    Affectation,
    AffectationStatut,
    Chauffeur,
    ChauffeurStatut,
    DepenseVehicule,
    IndisponibiliteVehicule,
    TypeDepenseVehicule,
    Vehicule,
    VehiculeStatut,
    VersementChauffeur,
)

VTC_BUSINESS_CODE = "vtc"


def _vtc_business(db: Session):
    return get_business_by_code(db, VTC_BUSINESS_CODE)


def _ensure_vtc_access(db: Session, user, business) -> None:
    allowed = get_business_ids_for_user(db, user)
    if allowed is not None and business.id not in allowed:
        raise HTTPException(status_code=403, detail="Acces refuse a l'activite vtc")


# ---------------------------------------------------------------------------
# Chauffeur
# ---------------------------------------------------------------------------


def create_chauffeur(
    db: Session,
    actor,
    *,
    full_name: str,
    phone: str | None = None,
    license_number: str | None = None,
) -> Chauffeur:
    """Cree un chauffeur : Person + Chauffeur (sans compte bancaire)."""
    business = _vtc_business(db)
    _ensure_vtc_access(db, actor, business)

    person = create_person(db, actor, full_name, phone=phone)
    chauffeur = Chauffeur(person_id=person.id, license_number=license_number)
    db.add(chauffeur)
    db.commit()
    db.refresh(chauffeur)
    publish(
        "vtc.chauffeur.created",
        actor_id=str(actor.id),
        entity_id=str(chauffeur.id),
        new_values={"person_id": str(person.id), "full_name": full_name},
    )
    return chauffeur


def list_chauffeurs(db: Session, user, *, status: ChauffeurStatut | None = None) -> list[dict]:
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)
    q = db.query(Chauffeur).order_by(Chauffeur.created_at)
    if status is not None:
        q = q.filter(Chauffeur.status == status)
    chauffeurs = q.all()
    result = []
    for ch in chauffeurs:
        person = get_person_summary(db, ch.person_id)
        result.append(
            {
                "id": ch.id,
                "person_id": ch.person_id,
                "full_name": person.full_name,
                "phone": person.phone,
                "license_number": ch.license_number,
                "status": ch.status.value,
                "created_at": ch.created_at,
            }
        )
    return result


def get_chauffeur(db: Session, user, chauffeur_id: uuid.UUID) -> dict:
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)
    chauffeur = db.get(Chauffeur, chauffeur_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")
    person = get_person_summary(db, chauffeur.person_id)
    return {
        "id": chauffeur.id,
        "person_id": chauffeur.person_id,
        "full_name": person.full_name,
        "phone": person.phone,
        "license_number": chauffeur.license_number,
        "status": chauffeur.status.value,
        "created_at": chauffeur.created_at,
    }


def update_chauffeur_status(
    db: Session,
    actor,
    chauffeur_id: uuid.UUID,
    *,
    status: ChauffeurStatut,
) -> Chauffeur:
    business = _vtc_business(db)
    _ensure_vtc_access(db, actor, business)
    chauffeur = db.get(Chauffeur, chauffeur_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")
    old_status = chauffeur.status.value
    chauffeur.status = status
    db.commit()
    db.refresh(chauffeur)
    publish(
        "vtc.chauffeur.updated",
        actor_id=str(actor.id),
        entity_id=str(chauffeur.id),
        old_values={"status": old_status},
        new_values={"status": status.value},
    )
    return chauffeur


# ---------------------------------------------------------------------------
# Vehicule
# ---------------------------------------------------------------------------


def create_vehicule(
    db: Session,
    actor,
    *,
    make: str,
    model: str,
    year: int | None = None,
    registration: str,
    acquisition_cost: Decimal = Decimal("0"),
) -> Vehicule:
    business = _vtc_business(db)
    _ensure_vtc_access(db, actor, business)

    vehicule = Vehicule(
        business_id=business.id,
        make=make,
        model=model,
        year=year,
        registration=registration,
        acquisition_cost=acquisition_cost.quantize(Decimal("0.01")),
    )
    db.add(vehicule)
    db.commit()
    db.refresh(vehicule)
    publish(
        "vtc.vehicule.created",
        actor_id=str(actor.id),
        entity_id=str(vehicule.id),
        new_values={
            "business_id": str(business.id),
            "make": make,
            "model": model,
            "registration": registration,
        },
    )
    return vehicule


def list_vehicules(db: Session, user, *, status: VehiculeStatut | None = None) -> list[Vehicule]:
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)
    q = db.query(Vehicule).filter(Vehicule.business_id == business.id).order_by(Vehicule.created_at)
    if status is not None:
        q = q.filter(Vehicule.status == status)
    return q.all()


def get_vehicule(db: Session, user, vehicule_id: uuid.UUID) -> Vehicule:
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)
    vehicule = db.get(Vehicule, vehicule_id)
    if not vehicule:
        raise HTTPException(status_code=404, detail="Vehicule introuvable")
    if vehicule.business_id != business.id:
        raise HTTPException(status_code=403, detail="Vehicule n'appartient pas a l'activite vtc")
    return vehicule


def update_vehicule(
    db: Session,
    actor,
    vehicule_id: uuid.UUID,
    *,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    registration: str | None = None,
    acquisition_cost: Decimal | None = None,
) -> Vehicule:
    vehicule = get_vehicule(db, actor, vehicule_id)
    updates = {}
    if make is not None:
        updates["make"] = make
    if model is not None:
        updates["model"] = model
    if year is not None:
        updates["year"] = year
    if registration is not None:
        updates["registration"] = registration
    if acquisition_cost is not None:
        updates["acquisition_cost"] = acquisition_cost.quantize(Decimal("0.01"))
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ a modifier")
    for field, value in updates.items():
        setattr(vehicule, field, value)
    db.commit()
    db.refresh(vehicule)
    publish(
        "vtc.vehicule.updated",
        actor_id=str(actor.id),
        entity_id=str(vehicule.id),
        new_values={k: str(v) for k, v in updates.items()},
    )
    return vehicule


def update_vehicule_status(
    db: Session,
    actor,
    vehicule_id: uuid.UUID,
    *,
    status: VehiculeStatut,
) -> Vehicule:
    vehicule = get_vehicule(db, actor, vehicule_id)
    old_status = vehicule.status.value
    vehicule.status = status
    db.commit()
    db.refresh(vehicule)
    publish(
        "vtc.vehicule.updated",
        actor_id=str(actor.id),
        entity_id=str(vehicule.id),
        old_values={"status": old_status},
        new_values={"status": status.value},
    )
    return vehicule


# ---------------------------------------------------------------------------
# Affectation
# ---------------------------------------------------------------------------


def _check_no_overlap_assignment(db: Session, driver_id: uuid.UUID, vehicle_id: uuid.UUID,
                                  start_date: date, end_date: date | None,
                                  exclude_id: uuid.UUID | None = None) -> None:
    effective_end = end_date or date.max
    q = db.query(Affectation).filter(
        Affectation.vehicle_id == vehicle_id,
        Affectation.status == AffectationStatut.ACTIVE,
        Affectation.start_date <= effective_end,
        or_(Affectation.end_date.is_(None), Affectation.end_date >= start_date),
    )
    if exclude_id is not None:
        q = q.filter(Affectation.id != exclude_id)
    if q.first():
        raise HTTPException(status_code=400, detail="Chevauchement d'affectation sur ce vehicule")


def _check_no_downtime(db: Session, vehicle_id: uuid.UUID, on_date: date) -> None:
    q = db.query(IndisponibiliteVehicule).filter(
        IndisponibiliteVehicule.vehicle_id == vehicle_id,
        IndisponibiliteVehicule.start_date <= on_date,
        or_(IndisponibiliteVehicule.end_date.is_(None), IndisponibiliteVehicule.end_date >= on_date),
    )
    if q.first():
        raise HTTPException(status_code=400, detail="Le vehicule est en indisponibilite a cette date")


def create_affectation(
    db: Session,
    actor,
    *,
    driver_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    start_date: date,
    end_date: date | None = None,
    expected_amount: Decimal,
    terms: str | None = None,
) -> Affectation:
    business = _vtc_business(db)
    _ensure_vtc_access(db, actor, business)

    chauffeur = db.get(Chauffeur, driver_id)
    if not chauffeur or chauffeur.status != ChauffeurStatut.ACTIVE:
        raise HTTPException(status_code=400, detail="Chauffeur introuvable ou inactif")

    vehicule = get_vehicule(db, actor, vehicle_id)
    if vehicule.status != VehiculeStatut.ACTIVE:
        raise HTTPException(status_code=400, detail="Le vehicule n'est pas actif")

    if end_date is not None and end_date < start_date:
        raise HTTPException(status_code=400, detail="La date de fin ne peut preceder la date de debut")

    _check_no_overlap_assignment(db, driver_id, vehicle_id, start_date, end_date)
    _check_no_downtime(db, vehicle_id, start_date)

    affectation = Affectation(
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        start_date=start_date,
        end_date=end_date,
        expected_amount=expected_amount.quantize(Decimal("0.01")),
        terms=terms,
    )
    db.add(affectation)
    db.commit()
    db.refresh(affectation)
    publish(
        "vtc.affectation.created",
        actor_id=str(actor.id),
        entity_id=str(affectation.id),
        new_values={
            "driver_id": str(driver_id),
            "vehicle_id": str(vehicle_id),
            "expected_amount": str(expected_amount),
        },
    )
    return affectation


def _sum_versements(db: Session, assignment_id: uuid.UUID) -> Decimal:
    return (
        db.query(func.coalesce(func.sum(VersementChauffeur.amount), Decimal("0")))
        .filter(VersementChauffeur.assignment_id == assignment_id)
        .scalar()
        or Decimal("0")
    )


def to_affectation_out(db: Session, af: Affectation) -> dict:
    vehicle = db.get(Vehicule, af.vehicle_id)
    chauffeur = db.get(Chauffeur, af.driver_id)
    person = get_person_summary(db, chauffeur.person_id) if chauffeur else None
    paid = _sum_versements(db, af.id)
    return {
        "id": af.id,
        "driver_id": af.driver_id,
        "vehicle_id": af.vehicle_id,
        "driver_name": person.full_name if person else None,
        "vehicle_registration": vehicle.registration if vehicle else None,
        "start_date": af.start_date.isoformat(),
        "end_date": af.end_date.isoformat() if af.end_date else None,
        "expected_amount": af.expected_amount,
        "paid_amount": paid,
        "remaining_amount": af.expected_amount - paid,
        "terms": af.terms,
        "status": af.status.value,
        "created_at": af.created_at,
    }


def list_affectations(
    db: Session,
    user,
    *,
    driver_id: uuid.UUID | None = None,
    vehicle_id: uuid.UUID | None = None,
    status: AffectationStatut | None = None,
) -> list[dict]:
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)
    q = db.query(Affectation)
    if driver_id is not None:
        q = q.filter(Affectation.driver_id == driver_id)
    if vehicle_id is not None:
        q = q.filter(Affectation.vehicle_id == vehicle_id)
    if status is not None:
        q = q.filter(Affectation.status == status)
    q = q.order_by(Affectation.start_date.desc())
    return [to_affectation_out(db, af) for af in q.all()]


def get_affectation(db: Session, user, affectation_id: uuid.UUID) -> dict:
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)
    af = db.get(Affectation, affectation_id)
    if not af:
        raise HTTPException(status_code=404, detail="Affectation introuvable")
    vehicule = db.get(Vehicule, af.vehicle_id)
    if vehicule.business_id != business.id:
        raise HTTPException(status_code=403, detail="Affectation hors de l'activite vtc")
    return to_affectation_out(db, af)


def end_affectation(
    db: Session,
    actor,
    affectation_id: uuid.UUID,
    *,
    end_date: date | None = None,
) -> Affectation:
    business = _vtc_business(db)
    _ensure_vtc_access(db, actor, business)
    af = db.get(Affectation, affectation_id)
    if not af:
        raise HTTPException(status_code=404, detail="Affectation introuvable")
    vehicule = db.get(Vehicule, af.vehicle_id)
    if vehicule.business_id != business.id:
        raise HTTPException(status_code=403, detail="Affectation hors de l'activite vtc")
    if af.status == AffectationStatut.ENDED:
        raise HTTPException(status_code=400, detail="Affectation deja terminee")
    effective_end = end_date or date.today()
    if effective_end < af.start_date:
        raise HTTPException(status_code=400, detail="La date de fin ne peut preceder la date de debut")
    paid = _sum_versements(db, af.id)
    if paid > af.expected_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de cloturer : les versements ({paid}) depassent le montant attendu ({af.expected_amount})",
        )
    af.end_date = effective_end
    af.status = AffectationStatut.ENDED
    db.commit()
    db.refresh(af)
    publish(
        "vtc.affectation.ended",
        actor_id=str(actor.id),
        entity_id=str(af.id),
        new_values={"end_date": effective_end.isoformat(), "paid_amount": str(paid)},
    )
    return af


# ---------------------------------------------------------------------------
# Versement chauffeur
# ---------------------------------------------------------------------------


def _find_active_assignment(db: Session, driver_id: uuid.UUID, vehicle_id: uuid.UUID, on_date: date) -> Affectation | None:
    return (
        db.query(Affectation)
        .filter(
            Affectation.driver_id == driver_id,
            Affectation.vehicle_id == vehicle_id,
            Affectation.status == AffectationStatut.ACTIVE,
            Affectation.start_date <= on_date,
            or_(Affectation.end_date.is_(None), Affectation.end_date >= on_date),
        )
        .first()
    )


def create_versement(
    db: Session,
    actor,
    *,
    driver_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    amount: Decimal,
    account_id: uuid.UUID,
    category_id: uuid.UUID,
    occurred_at: datetime | None = None,
) -> VersementChauffeur:
    """Le chauffeur verse l'argent : debite sa dette, credite la caisse."""
    business = _vtc_business(db)
    _ensure_vtc_access(db, actor, business)

    vehicule = get_vehicule(db, actor, vehicle_id)
    paid_on = (occurred_at or datetime.now(timezone.utc)).date()

    _check_no_downtime(db, vehicle_id, paid_on)

    chauffeur = db.get(Chauffeur, driver_id)
    if not chauffeur or chauffeur.status != ChauffeurStatut.ACTIVE:
        raise HTTPException(status_code=400, detail="Chauffeur introuvable ou inactif")

    assignment = _find_active_assignment(db, driver_id, vehicle_id, paid_on)
    if not assignment:
        raise HTTPException(status_code=400, detail="Aucune affectation active pour ce chauffeur/vehicule a cette date")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Le montant du versement doit etre positif")

    amount = amount.quantize(Decimal("0.01"))
    transaction = record_revenue(
        db,
        actor,
        business_id=business.id,
        account_id=account_id,
        amount=amount,
        description=f"Versement chauffeur {chauffeur.id}",
        occurred_at=occurred_at,
        category_id=category_id,
        commit=False,
    )

    versement = VersementChauffeur(
        assignment_id=assignment.id,
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        amount=amount,
        paid_at=occurred_at or datetime.now(timezone.utc),
        transaction_id=transaction.id,
        created_by=actor.id if hasattr(actor, "id") else None,
    )
    db.add(versement)
    db.commit()
    db.refresh(versement)

    paid_total = _sum_versements(db, assignment.id)
    remaining = assignment.expected_amount - paid_total

    publish(
        "ledger.transaction.posted",
        actor_id=str(actor.id),
        entity_id=str(transaction.id),
        new_values={
            "business_id": str(business.id),
            "account_id": str(account_id),
            "type": "revenue",
            "amount": str(amount),
        },
    )
    publish(
        "vtc.remittance.created",
        actor_id=str(actor.id),
        entity_id=str(versement.id),
        new_values={
            "assignment_id": str(assignment.id),
            "amount": str(amount),
            "paid_total": str(paid_total),
            "remaining_amount": str(remaining),
        },
    )
    return versement


def list_versements(
    db: Session,
    user,
    *,
    driver_id: uuid.UUID | None = None,
    vehicle_id: uuid.UUID | None = None,
) -> list[VersementChauffeur]:
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)
    vehicle_ids = [v.id for v in db.query(Vehicule.id).filter(Vehicule.business_id == business.id)]
    q = db.query(VersementChauffeur).filter(VersementChauffeur.vehicle_id.in_(vehicle_ids))
    if driver_id is not None:
        q = q.filter(VersementChauffeur.driver_id == driver_id)
    if vehicle_id is not None:
        q = q.filter(VersementChauffeur.vehicle_id == vehicle_id)
    return q.order_by(VersementChauffeur.paid_at.desc()).all()


# ---------------------------------------------------------------------------
# Depense vehicule
# ---------------------------------------------------------------------------

_DEPENSE_DESCRIPTIONS = {
    TypeDepenseVehicule.FUEL: "Achat carburant",
    TypeDepenseVehicule.MAINTENANCE: "Entretien",
    TypeDepenseVehicule.REPAIR: "Reparation",
    TypeDepenseVehicule.TIRES: "Achat pneus",
    TypeDepenseVehicule.INSURANCE: "Assurance vehicule",
    TypeDepenseVehicule.REGISTRATION: "Immatriculation",
    TypeDepenseVehicule.MISC: "Depense diverse",
}


def create_depense(
    db: Session,
    actor,
    *,
    vehicle_id: uuid.UUID,
    expense_type: TypeDepenseVehicule,
    amount: Decimal,
    quantity: Decimal | None = None,
    unit: str | None = None,
    description: str | None = None,
    account_id: uuid.UUID,
    category_id: uuid.UUID,
    occurred_at: datetime | None = None,
) -> DepenseVehicule:
    business = _vtc_business(db)
    _ensure_vtc_access(db, actor, business)

    vehicule = get_vehicule(db, actor, vehicle_id)

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Le montant de la depense doit etre positif")

    amount = amount.quantize(Decimal("0.01"))
    effective_occurred = occurred_at or datetime.now(timezone.utc)
    desc = description or _DEPENSE_DESCRIPTIONS.get(expense_type, "Depense vehicule")
    if expense_type == TypeDepenseVehicule.FUEL and quantity is not None:
        desc = f"{desc} ({quantity} {unit or 'l'})"

    transaction = record_expense(
        db,
        actor,
        business_id=business.id,
        account_id=account_id,
        amount=amount,
        description=desc,
        occurred_at=occurred_at,
        category_id=category_id,
        commit=False,
    )

    depense = DepenseVehicule(
        vehicle_id=vehicle_id,
        expense_type=expense_type,
        amount=amount,
        quantity=quantity,
        unit=unit,
        description=desc,
        occurred_at=effective_occurred,
        transaction_id=transaction.id,
        created_by=actor.id if hasattr(actor, "id") else None,
    )
    db.add(depense)
    db.commit()
    db.refresh(depense)

    publish(
        "ledger.transaction.posted",
        actor_id=str(actor.id),
        entity_id=str(transaction.id),
        new_values={
            "business_id": str(business.id),
            "account_id": str(account_id),
            "type": "expense",
            "amount": str(amount),
        },
    )
    publish(
        "vtc.expense.created",
        actor_id=str(actor.id),
        entity_id=str(depense.id),
        new_values={
            "vehicle_id": str(vehicle_id),
            "expense_type": expense_type.value,
            "amount": str(amount),
        },
    )
    return depense


def list_depenses(
    db: Session,
    user,
    *,
    vehicle_id: uuid.UUID | None = None,
    expense_type: TypeDepenseVehicule | None = None,
) -> list[DepenseVehicule]:
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)
    vehicle_ids = [v.id for v in db.query(Vehicule.id).filter(Vehicule.business_id == business.id)]
    q = db.query(DepenseVehicule).filter(DepenseVehicule.vehicle_id.in_(vehicle_ids))
    if vehicle_id is not None:
        q = q.filter(DepenseVehicule.vehicle_id == vehicle_id)
    if expense_type is not None:
        q = q.filter(DepenseVehicule.expense_type == expense_type)
    return q.order_by(DepenseVehicule.occurred_at.desc()).all()


# ---------------------------------------------------------------------------
# Indisponibilite vehicule
# ---------------------------------------------------------------------------


def create_indisponibilite(
    db: Session,
    actor,
    *,
    vehicle_id: uuid.UUID,
    start_date: date,
    end_date: date | None = None,
    reason: str | None = None,
) -> IndisponibiliteVehicule:
    business = _vtc_business(db)
    _ensure_vtc_access(db, actor, business)

    vehicule = get_vehicule(db, actor, vehicle_id)

    if end_date is not None and end_date < start_date:
        raise HTTPException(status_code=400, detail="La date de fin ne peut preceder la date de debut")

    _check_no_downtime(db, vehicle_id, start_date)

    active_assignments = db.query(Affectation).filter(
        Affectation.vehicle_id == vehicle_id,
        Affectation.status == AffectationStatut.ACTIVE,
        Affectation.start_date <= (end_date or date.max),
        or_(Affectation.end_date.is_(None), Affectation.end_date >= start_date),
    ).all()
    if active_assignments:
        raise HTTPException(status_code=400, detail="Impossible de declarer une indisponibilite : affectation(s) active(s)")

    indispo = IndisponibiliteVehicule(
        vehicle_id=vehicle_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
    )
    db.add(indispo)
    db.commit()
    db.refresh(indispo)
    publish(
        "vtc.downtime.created",
        actor_id=str(actor.id),
        entity_id=str(indispo.id),
        new_values={
            "vehicle_id": str(vehicle_id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat() if end_date else None,
        },
    )
    return indispo


def close_indisponibilite(
    db: Session,
    actor,
    indisponibilite_id: uuid.UUID,
    *,
    end_date: date | None = None,
) -> IndisponibiliteVehicule:
    business = _vtc_business(db)
    _ensure_vtc_access(db, actor, business)
    indispo = db.get(IndisponibiliteVehicule, indisponibilite_id)
    if not indispo:
        raise HTTPException(status_code=404, detail="Indisponibilite introuvable")
    vehicule = db.get(Vehicule, indispo.vehicle_id)
    if vehicule.business_id != business.id:
        raise HTTPException(status_code=403, detail="Indisponibilite hors de l'activite vtc")
    if indispo.end_date is not None:
        raise HTTPException(status_code=400, detail="Indisponibilite deja cloturee")
    effective_end = end_date or date.today()
    if effective_end < indispo.start_date:
        raise HTTPException(status_code=400, detail="La date de fin ne peut preceder la date de debut")
    indispo.end_date = effective_end
    db.commit()
    db.refresh(indispo)
    publish(
        "vtc.downtime.closed",
        actor_id=str(actor.id),
        entity_id=str(indispo.id),
        new_values={"end_date": effective_end.isoformat()},
    )
    return indispo


def list_indisponibilites(
    db: Session,
    user,
    *,
    vehicle_id: uuid.UUID | None = None,
) -> list[IndisponibiliteVehicule]:
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)
    vehicle_ids = [v.id for v in db.query(Vehicule.id).filter(Vehicule.business_id == business.id)]
    q = db.query(IndisponibiliteVehicule).filter(IndisponibiliteVehicule.vehicle_id.in_(vehicle_ids))
    if vehicle_id is not None:
        q = q.filter(IndisponibiliteVehicule.vehicle_id == vehicle_id)
    return q.order_by(IndisponibiliteVehicule.start_date.desc()).all()


# ---------------------------------------------------------------------------
# Indicateurs financiers
# ---------------------------------------------------------------------------


def _sum_versements_vehicule(db: Session, vehicle_id: uuid.UUID) -> Decimal:
    return (
        db.query(func.coalesce(func.sum(VersementChauffeur.amount), Decimal("0")))
        .filter(VersementChauffeur.vehicle_id == vehicle_id)
        .scalar()
        or Decimal("0")
    )


def _sum_depenses_vehicule(db: Session, vehicle_id: uuid.UUID) -> Decimal:
    return (
        db.query(func.coalesce(func.sum(DepenseVehicule.amount), Decimal("0")))
        .filter(DepenseVehicule.vehicle_id == vehicle_id)
        .scalar()
        or Decimal("0")
    )


def _depenses_vehicule_par_type(db: Session, vehicle_id: uuid.UUID) -> dict[str, Decimal]:
    rows = (
        db.query(DepenseVehicule.expense_type, func.coalesce(func.sum(DepenseVehicule.amount), Decimal("0")))
        .filter(DepenseVehicule.vehicle_id == vehicle_id)
        .group_by(DepenseVehicule.expense_type)
        .all()
    )
    return {t.value: total for t, total in rows}


def statut_paiement_chauffeur(db: Session, user, driver_id: uuid.UUID) -> dict:
    """Resume des paiements d'un chauffeur sur toutes ses affectations."""
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)

    chauffeur = db.get(Chauffeur, driver_id)
    if not chauffeur:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable")

    assignments = (
        db.query(Affectation)
        .filter(Affectation.driver_id == driver_id)
        .order_by(Affectation.start_date.desc())
        .all()
    )

    breakdown = []
    total_expected = Decimal("0")
    total_paid = Decimal("0")
    for af in assignments:
        paid = _sum_versements(db, af.id)
        remaining = af.expected_amount - paid
        total_expected += af.expected_amount
        total_paid += paid
        breakdown.append(
            {
                "assignment_id": af.id,
                "expected_amount": af.expected_amount,
                "paid_amount": paid,
                "remaining_amount": remaining,
                "status": af.status.value,
                "start_date": af.start_date.isoformat(),
                "end_date": af.end_date.isoformat() if af.end_date else None,
            }
        )

    return {
        "driver_id": driver_id,
        "total_expected": total_expected,
        "total_paid": total_paid,
        "total_remaining": total_expected - total_paid,
        "assignments": breakdown,
    }


def statistiques_vehicule(db: Session, user, vehicule_id: uuid.UUID) -> dict:
    vehicule = get_vehicule(db, user, vehicule_id)
    verses = _sum_versements_vehicule(db, vehicule.id)
    depenses = _sum_depenses_vehicule(db, vehicule.id)
    par_type = _depenses_vehicule_par_type(db, vehicule.id)

    return {
        "vehicle_id": vehicule.id,
        "make": vehicule.make,
        "model": vehicule.model,
        "registration": vehicule.registration,
        "versements": verses,
        "depenses": depenses,
        "rentabilite": verses - depenses,
        "depenses_par_type": par_type,
        "cout_acquisition": vehicule.acquisition_cost,
    }


def resume_financier(
    db: Session,
    user,
    *,
    start: date | None = None,
    end: date | None = None,
) -> dict:
    """Resume financier global VTC sur une periode (toutes caisses)."""
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)

    vehicle_ids = [v.id for v in db.query(Vehicule.id).filter(Vehicule.business_id == business.id)]
    if not vehicle_ids:
        return {
            "business_id": business.id,
            "totals": {"versements": Decimal("0"), "depenses": Decimal("0"), "net": Decimal("0")},
            "per_vehicle": [],
            "counts": {"vehicules_actifs": 0, "chauffeurs_actifs": 0, "affectations_actives": 0},
        }

    def _date_to_dt(d: date, is_start: bool) -> datetime:
        if is_start:
            return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
        return datetime.combine(d, datetime.max.time(), tzinfo=timezone.utc)

    q_verse = db.query(VersementChauffeur).filter(VersementChauffeur.vehicle_id.in_(vehicle_ids))
    q_depense = db.query(DepenseVehicule).filter(DepenseVehicule.vehicle_id.in_(vehicle_ids))
    if start is not None:
        q_verse = q_verse.filter(VersementChauffeur.paid_at >= _date_to_dt(start, True))
        q_depense = q_depense.filter(DepenseVehicule.occurred_at >= _date_to_dt(start, True))
    if end is not None:
        q_verse = q_verse.filter(VersementChauffeur.paid_at <= _date_to_dt(end, False))
        q_depense = q_depense.filter(DepenseVehicule.occurred_at <= _date_to_dt(end, False))

    verses_total = q_verse.with_entities(func.coalesce(func.sum(VersementChauffeur.amount), Decimal("0"))).scalar() or Decimal("0")
    depenses_total = q_depense.with_entities(func.coalesce(func.sum(DepenseVehicule.amount), Decimal("0"))).scalar() or Decimal("0")

    vehicles = (
        db.query(Vehicule)
        .filter(Vehicule.business_id == business.id, Vehicule.status != VehiculeStatut.SOLD)
        .order_by(Vehicule.created_at)
        .all()
    )
    per_vehicle = []
    for v in vehicles:
        v_verse = _sum_versements_vehicule(db, v.id)
        v_dep = _sum_depenses_vehicule(db, v.id)
        per_vehicle.append(
            {
                "vehicle_id": v.id,
                "make": v.make,
                "model": v.model,
                "registration": v.registration,
                "versements": v_verse,
                "depenses": v_dep,
                "net": v_verse - v_dep,
            }
        )

    counts = {
        "vehicules_actifs": db.query(func.count(Vehicule.id))
            .filter(Vehicule.business_id == business.id, Vehicule.status == VehiculeStatut.ACTIVE)
            .scalar() or 0,
        "chauffeurs_actifs": db.query(func.count(Chauffeur.id))
            .filter(Chauffeur.status == ChauffeurStatut.ACTIVE)
            .scalar() or 0,
        "affectations_actives": db.query(func.count(Affectation.id))
            .filter(Affectation.status == AffectationStatut.ACTIVE)
            .scalar() or 0,
    }

    return {
        "business_id": business.id,
        "totals": {"versements": verses_total, "depenses": depenses_total, "net": verses_total - depenses_total},
        "per_vehicle": per_vehicle,
        "counts": counts,
    }


def soldes_caisses(db: Session, user) -> dict:
    """Soldes de toutes les caisses de l'activite VTC (grand livre)."""
    business = _vtc_business(db)
    _ensure_vtc_access(db, user, business)
    accounts = list_accounts(db, user, business.id)
    rows = [compute_balance(db, a) for a in accounts]
    total = sum((Decimal(r["balance"]) for r in rows), Decimal("0"))
    return {"business_id": business.id, "accounts": rows, "total": total}
