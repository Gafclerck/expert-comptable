"""Types de champs communs ("core") : fournis par le framework, disponibles a
tout business sans rien enregistrer de plus. Un business ne cree son propre
FieldType que pour un concept qui lui est vraiment propre (ex. ContractType
dans insurance_tools.py, qui interroge insurance_service).

Auto-enregistres a l'import de ce module (voir _register_core_field_types en
bas). Importe par tools/__init__.py avant les modules business, pour que ces
types soient disponibles quand les business s'enregistrent.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from app.modules.assistantv3 import parsing, resolvers
from app.modules.assistantv3.registry import BaseFieldType, register_field_type
from app.modules.identity.service import get_business_by_code
from app.modules.ledger.models import CategoryType


class PersonNameFieldType(BaseFieldType):
    """Nom d'une personne extrait de texte libre (ex. \"client\"). Generique :
    n'importe quel business qui a besoin d'un nom de personne peut reutiliser
    ce type tel quel."""

    def fill(self, db, actor, step, field: str, message: str, choices: list[dict]) -> bool:
        name = parsing.extract_client_name(message) or parsing.clean_free_text(message)
        if not name:
            return False
        step.params[field] = name
        return True


class CodeFieldType(BaseFieldType):
    """Code court style \"XXX-999\" (matricule de contrat, immatriculation de
    vehicule...). Generique, pas specifique a l'assurance."""

    def fill(self, db, actor, step, field: str, message: str, choices: list[dict]) -> bool:
        code = parsing.parse_matricule(message)
        if not code:
            return False
        step.params[field] = code
        return True


class AmountFieldType(BaseFieldType):
    """Montant strictement positif. `validate`/`coerce` travaillent sur la
    valeur JSON-safe deja presente dans params (fournie par le LLM ou par
    fill()) ; `fill` interprete une reponse de clarification en texte libre."""

    def validate(self, raw) -> bool:
        if raw in (None, ""):
            return False
        try:
            return Decimal(str(raw)) > 0
        except Exception:
            return False

    def coerce(self, raw) -> Decimal:
        return Decimal(str(raw))

    def fill(self, db, actor, step, field: str, message: str, choices: list[dict]) -> bool:
        amount = parsing.parse_amount(message)
        if amount is None or amount <= 0:
            return False
        step.params[field] = str(amount)
        return True


class QuantityFieldType(BaseFieldType):
    """Entier strictement positif. C'est ce type qui empeche la ZeroDivisionError
    trouvee en v2 : une quantite a zero echoue `validate`, donc ne peut jamais
    atteindre un handler. `validate` rejette aussi une valeur non entiere
    (24.7) plutot que de la tronquer silencieusement en 24."""

    def validate(self, raw) -> bool:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return False
        return value.is_integer() and int(value) > 0

    def coerce(self, raw) -> int:
        return int(raw)

    def fill(self, db, actor, step, field: str, message: str, choices: list[dict]) -> bool:
        text = message.strip()
        quantity = parsing.parse_quantity(message) or (int(text) if text.isdigit() else None)
        if not quantity or quantity <= 0:
            return False
        step.params[field] = quantity
        return True


class DateFieldType(BaseFieldType):
    def validate(self, raw) -> bool:
        if not raw:
            return False
        try:
            from datetime import date as _date
            _date.fromisoformat(str(raw)[:10])
            return True
        except ValueError:
            return False

    def coerce(self, raw):
        from datetime import date as _date
        return _date.fromisoformat(str(raw)[:10])

    def fill(self, db, actor, step, field: str, message: str, choices: list[dict]) -> bool:
        parsed = parsing.parse_due_date(message)
        if not parsed:
            return False
        step.params[field] = parsed.isoformat()
        return True


def _choose_index(message: str, items: list[dict]) -> int | None:
    text = parsing.normalize(message).strip()
    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(items):
            return index
    words = {"1": 0, "premier": 0, "premiere": 0, "2": 1, "deuxieme": 1, "3": 2, "troisieme": 2, "4": 3}
    if text in words and words[text] < len(items):
        return words[text]
    return None


class AccountFieldType(BaseFieldType):
    """Reference une caisse de l'activite du tool (spec.business). Type
    is_entity_ref=True : la reussite se mesure a params[f'{field}_id']."""

    is_entity_ref = True

    def resolve(self, db, actor, spec, step, field: str) -> None:
        id_key = f"{field}_id"
        if step.params.get(id_key):
            return
        business = get_business_by_code(db, spec.business)
        account, candidates = resolvers.resolve_account(db, actor, business.id, step.params.get(field))
        if account is not None:
            step.params[id_key] = str(account.id)
            step.params[f"{field}_name"] = account.name
        elif candidates:
            raise resolvers.ClarificationNeeded(
                field, "Sur quelle caisse ?", [{"name": a.name, "id": str(a.id)} for a in candidates]
            )
        else:
            raise resolvers.ClarificationNeeded(field, "Aucune caisse pour cette activite.")

    def fill(self, db, actor, step, field: str, message: str, choices: list[dict]) -> bool:
        index = _choose_index(message, choices)
        if index is not None:
            step.params[f"{field}_id"] = choices[index]["id"]
            step.params[f"{field}_name"] = choices[index]["name"]
            return True
        step.params[field] = message.strip(".,")
        return True


class CategoryFieldType(BaseFieldType):
    """Reference une categorie d'un type donne (debit/credit), fixe a la
    construction : voir les deux instances enregistrees plus bas
    ('category_debit' / 'category_credit'). Un tool y accede via
    field_type_overrides={'category': 'category_debit'} par exemple."""

    is_entity_ref = True

    def __init__(self, category_type: CategoryType):
        self._category_type = category_type

    def resolve(self, db, actor, spec, step, field: str) -> None:
        id_key = f"{field}_id"
        if step.params.get(id_key):
            return
        category, candidates = resolvers.resolve_category(db, self._category_type, step.params.get(field))
        if category is not None:
            step.params[id_key] = str(category.id)
        elif candidates:
            raise resolvers.ClarificationNeeded(
                field, "Sous quelle categorie ?", [{"name": c.name, "id": str(c.id)} for c in candidates]
            )
        else:
            raise resolvers.ClarificationNeeded(field, "Aucune categorie de ce type.")

    def fill(self, db, actor, step, field: str, message: str, choices: list[dict]) -> bool:
        index = _choose_index(message, choices)
        if index is not None:
            step.params[f"{field}_id"] = choices[index]["id"]
            return True
        step.params[field] = message.strip(".,")
        return True


def _register_core_field_types() -> None:
    register_field_type("client", PersonNameFieldType())
    register_field_type("matricule", CodeFieldType())
    register_field_type("amount", AmountFieldType())
    register_field_type("premium", AmountFieldType())
    register_field_type("quantity", QuantityFieldType())
    register_field_type("due_date", DateFieldType())
    register_field_type("account", AccountFieldType())
    register_field_type("category_debit", CategoryFieldType(CategoryType.DEBIT))
    register_field_type("category_credit", CategoryFieldType(CategoryType.CREDIT))


_register_core_field_types()
