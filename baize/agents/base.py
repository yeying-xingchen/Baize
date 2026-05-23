from __future__ import annotations

from abc import ABC, abstractmethod

from baize.core.models import RiskLevel, TaskStep, UserRequest


class Agent(ABC):
    name: str

    @abstractmethod
    def can_handle(self, request: UserRequest) -> bool:
        raise NotImplementedError

    @abstractmethod
    def plan(self, request: UserRequest, step_id: str) -> TaskStep:
        raise NotImplementedError


class KeywordAgent(Agent):
    keywords: tuple[str, ...]
    action: str
    risk: RiskLevel = RiskLevel.LOW

    def can_handle(self, request: UserRequest) -> bool:
        text = request.text.lower()
        return any(keyword in text for keyword in self.keywords)

    def plan(self, request: UserRequest, step_id: str) -> TaskStep:
        return TaskStep(
            id=step_id,
            agent=self.name,
            action=self.action,
            risk=self.risk,
        )
