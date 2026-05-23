from __future__ import annotations

from baize.core.models import ExecutionPlan, ExecutionReport, IntegrationKind, TaskStatus, TaskStep
from baize.integrations.mcp import MCPClientError, MCPExecutor
from baize.integrations.skill import SkillExecutionError, SkillExecutor


class LocalRuntime:
    def __init__(self, mcp_executor: MCPExecutor | None = None, skill_executor: SkillExecutor | None = None) -> None:
        self.mcp_executor = mcp_executor or MCPExecutor()
        self.skill_executor = skill_executor or SkillExecutor()

    def run(self, plan: ExecutionPlan, confirmed: bool = False) -> ExecutionReport:
        executed_steps = tuple(self._run_step(step, confirmed) for step in plan.steps)
        return ExecutionReport(plan=plan, steps=executed_steps)

    def _run_step(self, step: TaskStep, confirmed: bool) -> TaskStep:
        if step.requires_confirmation and not confirmed:
            return TaskStep(
                id=step.id,
                agent=step.agent,
                action=step.action,
                risk=step.risk,
                requires_confirmation=step.requires_confirmation,
                status=TaskStatus.BLOCKED,
                result="需要用户确认后才能执行",
                metadata=step.metadata,
            )
        try:
            result = self._execute_integration(step)
        except (MCPClientError, SkillExecutionError) as exc:
            result = f"执行失败: {exc}"
        return TaskStep(
            id=step.id,
            agent=step.agent,
            action=step.action,
            risk=step.risk,
            requires_confirmation=step.requires_confirmation,
            status=TaskStatus.COMPLETED,
            result=result,
            metadata=step.metadata,
        )

    def _execute_integration(self, step: TaskStep) -> str:
        integration = step.metadata.get("integration")
        if integration == IntegrationKind.MCP.value:
            return self.mcp_executor.run(step)
        if integration == IntegrationKind.SKILL.value:
            return self.skill_executor.run(step)
        return "已生成执行计划，当前最小版本不会直接操作系统或文件"
