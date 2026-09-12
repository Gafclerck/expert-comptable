"""Registre unique des outils de l'assistant v2.

Remplace, en un seul endroit, ce qui etait duplique dans l'assistant v1 entre
`intents.py` (INTENTS, POULTRY_OPS/INSURANCE_OPS), `interpreter.py`
(_TOOL_PARAM_SCHEMAS) et `service.py` (_ORDER, _QUESTIONS).

Ce module ne connait AUCUN outil par son nom : chaque module metier
(voir tools/) s'enregistre lui-meme via `register()` au chargement de
`app.modules.assistantv2.tools`. Ajouter un business = ajouter un fichier
`tools/<business>_tools.py` + une ligne d'import dans `tools/__init__.py`,
sans toucher ce fichier.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable, Protocol

from sqlalchemy.orm import Session

from app.modules.ledger.models import CategoryType


class ToolHandler(Protocol):
    def __call__(self, db: Session, actor, params: dict) -> tuple[dict, uuid.UUID | None, str]:
        """Execute l'outil et retourne (facts, target_id, static_text), meme
        contrat que `execute()` dans l'assistant v1."""
        ...


@dataclass
class ToolSpec:
    name: str
    label: str
    example: str
    handler: ToolHandler
    parameters: dict  # {"properties": {...}, "required": [...]} format JSON schema
    # Activite proprietaire de l'outil. None = outil transverse, applicable a
    # toute activite (ex. get_balance, help).
    business: str | None = None
    # Ordre de remplissage des champs pour la clarification (memes noms que
    # dans `parameters`). Les champs "contract"/"account"/"category"/"driver"/
    # "vehicle" declenchent une resolution d'entite (voir resolvers.py) ; les
    # autres ne font l'objet que d'une verification de presence.
    order: list[str] = field(default_factory=list)
    questions: dict[str, str] = field(default_factory=dict)
    # Necessaire uniquement si "category" figure dans `order`.
    category_type: CategoryType | None = None
    # True : une confirmation utilisateur explicite est exigee avant execution,
    # verifiee cote orchestrateur (jamais laisse a la seule appreciation du LLM).
    is_critical: bool = False
    # Message additionnel affiche avec la demande de confirmation (ex. avertir
    # qu'une annulation de contrat n'entraine aucun remboursement automatique).
    # Reserve aux outils critiques ou l'action a une consequence non evidente.
    confirmation_note: str | None = None
    # True : outil sans effet de bord (lecture seule). Reserve pour une
    # parallelisation future ; l'execution reste sequentielle pour l'instant
    # (voir orchestrator.py).
    is_read_only: bool = True


_REGISTRY: dict[str, ToolSpec] = {}


def register(spec: ToolSpec) -> None:
    if spec.name in _REGISTRY:
        raise ValueError(f"Outil deja enregistre: {spec.name}")
    _REGISTRY[spec.name] = spec


def get(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)


def all_tools() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def build_llm_tool_definitions() -> list[dict]:
    """Definitions au format tool-calling (compatible OpenAI), pour tous les
    outils enregistres. Le LLM choisit librement parmi l'ensemble ; c'est lui
    qui decide si plusieurs outils sont necessaires pour une meme demande."""
    return [
        {
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
        }
        for spec in _REGISTRY.values()
    ]


def reset_registry_for_tests() -> None:
    """Reserve aux tests : vide le registre pour permettre un re-enregistrement
    propre entre deux imports (evite le "Outil deja enregistre")."""
    _REGISTRY.clear()
