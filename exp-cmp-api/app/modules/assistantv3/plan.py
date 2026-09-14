"""Modele de donnees du plan d'execution.

Difference cle avec assistantv2 : `PlanStep.params` ne contient JAMAIS que des
valeurs JSON-safe (str/int/float/bool/None), y compris pendant l'execution en
memoire. La conversion vers les types Python "riches" (Decimal, date) est
faite a la volee juste avant d'appeler le handler d'un outil (voir
orchestrator.py::_materialize_params), jamais stockee. Ca supprime par
construction le bug trouve en v2 ou un Decimal/date pouvait perdre son type
apres un aller-retour Redis (clarification/confirmation) : ici il n'y a
jamais rien a reconvertir, `from_dict` est un json.loads direct.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


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
    params: dict  # JSON-safe uniquement : str/int/float/bool/None
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
            params=data.get("params") or {},
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
    pending_field: str | None = None
    pending_question: str | None = None
    pending_choices: list[dict] = field(default_factory=list)
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
