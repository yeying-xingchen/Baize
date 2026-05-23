from __future__ import annotations

from typing import Protocol

from baize.ai.openai_client import AIClientError, OpenAIChatClient, OpenAIConfig
from baize.core.models import RiskLevel, TaskStep, UserRequest


class AIPlanner(Protocol):
    def plan(self, request: UserRequest) -> tuple[TaskStep, ...]:
        raise NotImplementedError


class OpenAIPlanner:
    allowed_agents = {"file", "system", "application", "search", "general"}

    def __init__(self, client: OpenAIChatClient) -> None:
        self.client = client

    @classmethod
    def from_env(cls) -> OpenAIPlanner | None:
        config = OpenAIConfig.from_env()
        if config is None:
            return None
        return cls(OpenAIChatClient(config))

    def plan(self, request: UserRequest) -> tuple[TaskStep, ...]:
        response = self.client.complete_json(self._messages(request))
        steps = response.get("steps")
        if not isinstance(steps, list) or not steps:
            raise AIClientError("AI 计划必须包含非空 steps 数组")
        return tuple(self._decode_step(index, step) for index, step in enumerate(steps, start=1))

    def _messages(self, request: UserRequest) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "你是白泽 Baize 的主控 Agent。"
                    "你的任务是把用户自然语言请求拆解为可执行计划。"
                    "只能返回 JSON 对象，不要返回 Markdown。"
                    "JSON 格式必须为 {\"steps\":[{\"agent\":\"file|system|application|search|general\",\"action\":\"中文动作描述\",\"risk\":\"low|sensitive|dangerous\"}]}。"
                    "涉及删除、覆盖、格式化、系统设置修改、账号密码、隐私目录、支付资金的任务必须标记为 sensitive 或 dangerous。"
                    "当前阶段只规划，不真实执行系统、文件或应用操作。"
                ),
            },
            {"role": "user", "content": request.text},
        ]

    def _decode_step(self, index: int, value: object) -> TaskStep:
        if not isinstance(value, dict):
            raise AIClientError("AI 计划步骤必须是对象")
        agent = value.get("agent")
        action = value.get("action")
        risk_value = value.get("risk", RiskLevel.LOW.value)
        if agent not in self.allowed_agents:
            raise AIClientError("AI 计划包含未知 Agent")
        if not isinstance(action, str) or not action.strip():
            raise AIClientError("AI 计划步骤缺少 action")
        try:
            risk = RiskLevel(str(risk_value))
        except ValueError as exc:
            raise AIClientError("AI 计划包含未知风险级别") from exc
        return TaskStep(
            id=f"step-{index}",
            agent=str(agent),
            action=action.strip(),
            risk=risk,
            metadata={"planner": "openai"},
        )
