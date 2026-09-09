"""Modele de donnees du plan d'execution : remplace le dict `draft` ad hoc de
l'assistant v1 (`SESSIONS: dict[str, dict]`). Un Plan porte une liste ordonnee
de PlanStep (un par tool call), plus l'etat de la conversation en cours
(en attente de clarification, de confirmation, ou termine).

Serialise en JSON pour la persistance Redis (voir session_store.py) : aucune
dependance a SQLAlchemy ou a des objets non serialisables ici.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.modules.assistantv2 import parsing


class StepStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class PlanStatus(str, Enum):
    RUNNING = "running"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    DONE = "done"


@dataclass
class PlanStep:
    tool: str
    params: dict
    status: StepStatus = StepStatus.PENDING
    result: dict | None = None
    static_text: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "params": self.params,
            "status": self.status.value,
            "result": self.result,
            "static_text": self.static_text,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlanStep":
        return cls(
            tool=data["tool"],
            params=parsing.coerce_params(data.get("params") or {}),
            status=StepStatus(data.get("status", "pending")),
            result=data.get("result"),
            static_text=data.get("static_text"),
            error=data.get("error"),
        )


@dataclass
class Plan:
    session_id: str
    status: PlanStatus = PlanStatus.RUNNING
    steps: list[PlanStep] = field(default_factory=list)
    # Champ de clarification en attente de reponse utilisateur (None si aucun).
    pending_field: str | None = None
    pending_question: str | None = None
    pending_choices: list[dict] = field(default_factory=list)
    # Index (dans `steps`) du step concerne par la clarification/confirmation en cours.
    pending_step_index: int | None = None
    user_message: str = ""
    iterations: int = 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "pending_field": self.pending_field,
            "pending_question": self.pending_question,
            "pending_choices": self.pending_choices,
            "pending_step_index": self.pending_step_index,
            "user_message": self.user_message,
            "iterations": self.iterations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Plan":
        return cls(
            session_id=data["session_id"],
            status=PlanStatus(data.get("status", "running")),
            steps=[PlanStep.from_dict(s) for s in data.get("steps", [])],
            pending_field=data.get("pending_field"),
            pending_question=data.get("pending_question"),
            pending_choices=data.get("pending_choices") or [],
            pending_step_index=data.get("pending_step_index"),
            user_message=data.get("user_message", ""),
            iterations=data.get("iterations", 0),
        )
