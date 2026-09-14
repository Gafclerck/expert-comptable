"""Registre central : outils, types de champs (le port d'extensibilite), et
modules business (alias + indice de contexte). C'est le SEUL fichier qui
definit les contrats ; il ne connait le contenu d'aucun business ni d'aucun
type de champ concret.

Trois registres separes, tous remplis par auto-enregistrement au chargement
de app.modules.assistantv3.tools (voir ce sous-package) :
  - outils (ToolSpec)              : inchange dans l'esprit par rapport a v2
  - types de champs (FieldType)     : NOUVEAU, remplace les if/elif en dur de
    l'orchestrateur v2 sur les noms de champs ("contract", "account", ...)
  - modules business (BusinessModule) : NOUVEAU, porte les alias en langage
    naturel et un indice de contexte optionnel pour le system prompt, la ou
    v2 avait un dict BUSINESS_ALIASES partage et edite a la main.

Toute collision (nom d'outil, nom de type de champ, alias business) leve une
erreur explicite a l'enregistrement plutot que de se resoudre en silence :
deux business ecrits independamment qui se marchent dessus doivent le savoir
tout de suite, pas decouvrir un comportement bizarre en production.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from sqlalchemy.orm import Session


class ToolHandler(Protocol):
    def __call__(self, db: Session, actor, params: dict) -> tuple[dict, uuid.UUID | None, str]:
        """Execute l'outil et retourne (facts, target_id, static_text). `params`
        est deja materialise (types Python riches : Decimal, date...), voir
        orchestrator.py::_materialize_params."""
        ...


class FieldType(Protocol):
    """Le port : tout ce qu'un champ de tool doit savoir faire pour lui-meme.
    L'orchestrateur ne connait que cette interface, jamais un nom de champ.

    `is_entity_ref` distingue deux familles :
    - True (compte, categorie, contrat...) : la reussite se mesure a la
      presence de params[f"{field}_id"], etablie par `resolve()` qui interroge
      la base (lecture seule, jamais d'ecriture : resolve() s'execute avant la
      porte de confirmation, un effet de bord ici la contournerait).
    - False (montant, quantite, date, texte...) : la reussite se mesure par
      `validate()` sur la valeur brute JSON-safe, pas de requete necessaire.
    """

    is_entity_ref: bool
    # Noms de CHAMPS (pas de types) qui doivent apparaitre plus tot dans
    # spec.order pour que ce type fonctionne correctement (ex. 'payment_amount'
    # exige que 'contract' soit deja resolu pour son raccourci "reste").
    # Verifie a l'enregistrement de l'outil, pas au runtime : une dependance
    # non satisfaite doit etre une erreur de configuration decouverte tout de
    # suite, pas une fonctionnalite qui se desactive silencieusement en prod.
    requires_fields: list[str]

    def validate(self, raw: Any) -> bool:
        """Vrai si `raw` (une valeur JSON-safe) est semantiquement valide.
        Sans objet pour les types is_entity_ref=True (voir resolve())."""
        ...

    def coerce(self, raw: Any) -> Any:
        """Convertit une valeur JSON-safe vers le type Python riche utilise par
        le handler (Decimal, date...). Jamais appelee sur les is_entity_ref=True
        (les handlers convertissent eux-memes leur _id en uuid.UUID, comme en v2)."""
        ...

    def resolve(self, db: Session, actor, spec: "ToolSpec", step, field: str) -> None:
        """Pour is_entity_ref=True uniquement : mute step.params en resolvant
        une reference texte vers un id. Ne fait AUCUNE ecriture en base. Leve
        ClarificationNeeded (voir resolvers.py) si la reference manque ou est
        ambigue. No-op par defaut pour les types scalaires."""
        return None

    def fill(self, db: Session, actor, step, field: str, message: str, choices: list[dict]) -> bool:
        """Interprete la reponse de l'utilisateur a une question de
        clarification pour ce champ. Retourne False si le message ne permet
        pas de remplir le champ (on redemande)."""
        ...


class BaseFieldType:
    """Base commode : is_entity_ref=False et resolve() no-op par defaut, pour
    que les types scalaires n'aient a ecrire que validate/coerce/fill."""

    is_entity_ref = False
    requires_fields: list[str] = []

    def validate(self, raw: Any) -> bool:
        return raw not in (None, "")

    def coerce(self, raw: Any) -> Any:
        return raw

    def resolve(self, db: Session, actor, spec: "ToolSpec", step, field: str) -> None:
        return None

    def fill(self, db: Session, actor, step, field: str, message: str, choices: list[dict]) -> bool:
        raise NotImplementedError


@dataclass
class ToolSpec:
    name: str
    label: str
    example: str
    handler: ToolHandler
    parameters: dict  # {"properties": {...}, "required": [...]} format JSON schema
    business: str | None = None  # None = outil transverse
    order: list[str] = field(default_factory=list)
    questions: dict[str, str] = field(default_factory=dict)
    # Nom de champ -> nom de type de champ, quand ils different (ex. "premium"
    # se comporte comme le type "amount" ; "amount" de record_payment utilise
    # une variante "payment_amount" qui ajoute le raccourci "reste"). Un champ
    # absent de cette table utilise son propre nom comme nom de type.
    field_type_overrides: dict[str, str] = field(default_factory=dict)
    is_critical: bool = False
    confirmation_note: str | None = None
    is_read_only: bool = True


@dataclass
class BusinessModule:
    code: str
    aliases: set[str] = field(default_factory=set)
    context_hint: str | None = None


_TOOLS: dict[str, ToolSpec] = {}
_FIELD_TYPES: dict[str, FieldType] = {}
_BUSINESS_MODULES: dict[str, BusinessModule] = {}


def register(spec: ToolSpec) -> None:
    if spec.name in _TOOLS:
        raise ValueError(f"Outil deja enregistre: {spec.name}")
    for field_name in spec.order:
        type_name = spec.field_type_overrides.get(field_name, field_name)
        ftype = _FIELD_TYPES.get(type_name)
        if ftype is None:
            continue  # pas encore enregistre a cet instant : rien a verifier
        for required in getattr(ftype, "requires_fields", []):
            if required not in spec.order[: spec.order.index(field_name)]:
                raise ValueError(
                    f"L'outil '{spec.name}' utilise le type '{type_name}' pour le champ "
                    f"'{field_name}', qui exige que '{required}' apparaisse avant lui dans order."
                )
    _TOOLS[spec.name] = spec


def get(name: str) -> ToolSpec | None:
    return _TOOLS.get(name)


def all_tools() -> list[ToolSpec]:
    return list(_TOOLS.values())


def register_field_type(name: str, field_type: FieldType) -> None:
    if name in _FIELD_TYPES:
        raise ValueError(f"Type de champ deja enregistre: {name}")
    _FIELD_TYPES[name] = field_type


def get_field_type(name: str) -> FieldType | None:
    return _FIELD_TYPES.get(name)


def field_type_name_for(spec: ToolSpec, field_name: str) -> str:
    return spec.field_type_overrides.get(field_name, field_name)


def register_business(module: BusinessModule) -> None:
    if module.code in _BUSINESS_MODULES:
        raise ValueError(f"Business deja enregistre: {module.code}")
    all_known_aliases: dict[str, str] = {}
    for existing in _BUSINESS_MODULES.values():
        all_known_aliases[existing.code.casefold()] = existing.code
        for alias in existing.aliases:
            all_known_aliases[alias.casefold()] = existing.code
    if module.code.casefold() in all_known_aliases:
        raise ValueError(f"Code business '{module.code}' entre en collision avec {all_known_aliases[module.code.casefold()]}")
    for alias in module.aliases:
        owner = all_known_aliases.get(alias.casefold())
        if owner:
            raise ValueError(f"Alias '{alias}' deja utilise par le business '{owner}'")
    _BUSINESS_MODULES[module.code] = module


def all_businesses() -> list[BusinessModule]:
    return list(_BUSINESS_MODULES.values())


def get_business_module(code: str) -> BusinessModule | None:
    return _BUSINESS_MODULES.get(code)


def build_llm_tool_definitions(accessible_codes: set[str] | None = None) -> list[dict]:
    """`accessible_codes=None` signifie acces total (ex. super-admin), pas
    "aucun acces" : c'est la meme convention que get_business_ids_for_user."""
    defs = []
    for spec in _TOOLS.values():
        if accessible_codes is not None and spec.business is not None and spec.business not in accessible_codes:
            continue
        defs.append({
            "type": "function",
            "function": {
                "name": spec.name,
                "description": f"{spec.label}. Exemple : \"{spec.example}\"",
                "parameters": {
                    "type": "object",
                    "properties": spec.parameters.get("properties", {}),
                    "required": spec.parameters.get("required", []),
                },
            },
        })
    return defs


def business_context_hints(accessible_codes: set[str] | None = None) -> list[str]:
    hints = []
    for module in _BUSINESS_MODULES.values():
        if accessible_codes is not None and module.code not in accessible_codes:
            continue
        if module.context_hint:
            hints.append(f"{module.code} : {module.context_hint}")
    return hints


def reset_registry_for_tests() -> None:
    """Reserve aux tests : vide les trois registres."""
    _TOOLS.clear()
    _FIELD_TYPES.clear()
    _BUSINESS_MODULES.clear()
