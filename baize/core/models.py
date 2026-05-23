from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "low"
    SENSITIVE = "sensitive"
    DANGEROUS = "dangerous"


class TaskStatus(str, Enum):
    PLANNED = "planned"
    BLOCKED = "blocked"
    COMPLETED = "completed"


@dataclass(frozen=True)
class UserRequest:
    text: str


@dataclass(frozen=True)
class TaskStep:
    id: str
    agent: str
    action: str
    risk: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    status: TaskStatus = TaskStatus.PLANNED
    result: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlan:
    request: UserRequest
    steps: tuple[TaskStep, ...]


@dataclass(frozen=True)
class ExecutionReport:
    plan: ExecutionPlan
    steps: tuple[TaskStep, ...]

    @property
    def blocked(self) -> bool:
        return any(step.status == TaskStatus.BLOCKED for step in self.steps)
