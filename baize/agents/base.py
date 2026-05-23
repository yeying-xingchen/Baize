from __future__ import annotations

from abc import ABC, abstractmethod

from baize.core.models import AgentIntegration, RiskLevel, TaskStep, UserRequest


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


class IntegrationAgent(Agent):
    def __init__(self, integration: AgentIntegration) -> None:
        self.integration = integration
        self.name = integration.kind.value

    def can_handle(self, request: UserRequest) -> bool:
        text = request.text.lower()
        terms = (self.integration.name, self.integration.kind.value, *self.integration.metadata.get("keywords", ()))
        return any(str(term).lower() in text for term in terms if str(term).strip())

    def plan(self, request: UserRequest, step_id: str) -> TaskStep:
        return TaskStep(
            id=step_id,
            agent=self.name,
            action=f"调用 {self.integration.name}：{self.integration.description}",
            risk=RiskLevel.SENSITIVE,
            metadata={
                "integration": self.integration.kind.value,
                "name": self.integration.name,
                **self.integration.metadata,
            },
        )
