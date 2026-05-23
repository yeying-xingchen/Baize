from __future__ import annotations

from baize.agents.base import Agent
from baize.agents.specialized import (
    ApplicationAgent,
    FileAgent,
    GeneralAgent,
    SearchAgent,
    SystemAgent,
)
from baize.ai.openai_client import AIClientError
from baize.ai.planner import AIPlanner, OpenAIPlanner
from baize.core.models import ExecutionPlan, UserRequest
from baize.security.policy import SafetyPolicy


class Orchestrator:
    def __init__(
        self,
        agents: tuple[Agent, ...] | None = None,
        safety_policy: SafetyPolicy | None = None,
        ai_planner: AIPlanner | None = None,
        use_env_ai: bool = True,
    ) -> None:
        self.agents = agents or (
            FileAgent(),
            SystemAgent(),
            ApplicationAgent(),
            SearchAgent(),
        )
        self.fallback_agent = GeneralAgent()
        self.safety_policy = safety_policy or SafetyPolicy()
        self.ai_planner = ai_planner if ai_planner is not None else OpenAIPlanner.from_env() if use_env_ai else None

    def create_plan(self, text: str) -> ExecutionPlan:
        request = UserRequest(text=text.strip())
        steps = self._create_ai_steps(request) or self._create_rule_steps(request)
        return ExecutionPlan(request=request, steps=steps)

    def _create_ai_steps(self, request: UserRequest) -> tuple:
        if self.ai_planner is None:
            return ()
        try:
            return tuple(self.safety_policy.apply(step, request.text) for step in self.ai_planner.plan(request))
        except AIClientError:
            return ()

    def _create_rule_steps(self, request: UserRequest) -> tuple:
        selected_agents = tuple(agent for agent in self.agents if agent.can_handle(request))
        if not selected_agents:
            selected_agents = (self.fallback_agent,)

        return tuple(
            self.safety_policy.apply(agent.plan(request, f"step-{index}"), request.text)
            for index, agent in enumerate(selected_agents, start=1)
        )
