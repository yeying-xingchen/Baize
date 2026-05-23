from __future__ import annotations

from baize.core.models import ExecutionPlan, ExecutionReport, TaskStatus, TaskStep


class LocalRuntime:
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
        return TaskStep(
            id=step.id,
            agent=step.agent,
            action=step.action,
            risk=step.risk,
            requires_confirmation=step.requires_confirmation,
            status=TaskStatus.COMPLETED,
            result="已生成执行计划，当前最小版本不会直接操作系统或文件",
            metadata=step.metadata,
        )
