import unittest

from baize.ai.openai_client import AIClientError
from baize.core.models import RiskLevel, TaskStatus, TaskStep
from baize.core.orchestrator import Orchestrator
from baize.runtime.local import LocalRuntime


class FakeAIPlanner:
    def __init__(self, steps: tuple[TaskStep, ...] | None = None, error: Exception | None = None) -> None:
        self.steps = steps or ()
        self.error = error

    def plan(self, request):
        if self.error is not None:
            raise self.error
        return self.steps


class OrchestratorTestCase(unittest.TestCase):
    def test_file_request_routes_to_file_agent(self) -> None:
        plan = Orchestrator(use_env_ai=False).create_plan("帮我查找上个月的项目预算表格")

        self.assertTrue(any(step.agent == "file" for step in plan.steps))

    def test_system_request_routes_to_system_agent(self) -> None:
        plan = Orchestrator(use_env_ai=False).create_plan("查看当前电脑配置")

        self.assertTrue(any(step.agent == "system" for step in plan.steps))

    def test_dangerous_request_requires_confirmation(self) -> None:
        plan = Orchestrator(use_env_ai=False).create_plan("删除桌面上的重复文件")

        self.assertTrue(any(step.risk == RiskLevel.DANGEROUS for step in plan.steps))
        self.assertTrue(all(step.requires_confirmation for step in plan.steps))

    def test_runtime_blocks_unconfirmed_sensitive_steps(self) -> None:
        plan = Orchestrator(use_env_ai=False).create_plan("整理桌面上的 PDF")
        report = LocalRuntime().run(plan)

        self.assertTrue(report.blocked)
        self.assertTrue(all(step.status == TaskStatus.BLOCKED for step in report.steps))

    def test_runtime_completes_confirmed_steps(self) -> None:
        plan = Orchestrator(use_env_ai=False).create_plan("整理桌面上的 PDF")
        report = LocalRuntime().run(plan, confirmed=True)

        self.assertFalse(report.blocked)
        self.assertTrue(all(step.status == TaskStatus.COMPLETED for step in report.steps))

    def test_ai_planner_steps_are_used(self) -> None:
        ai_step = TaskStep(id="step-1", agent="search", action="搜索并总结 AI 新闻", risk=RiskLevel.LOW)
        plan = Orchestrator(ai_planner=FakeAIPlanner((ai_step,)), use_env_ai=False).create_plan("今天 AI 新闻")

        self.assertEqual(plan.steps[0].agent, "search")
        self.assertEqual(plan.steps[0].metadata, {"planner": "openai"} if plan.steps[0].metadata else {})

    def test_ai_planner_failure_falls_back_to_rules(self) -> None:
        planner = FakeAIPlanner(error=AIClientError("failed"))
        plan = Orchestrator(ai_planner=planner, use_env_ai=False).create_plan("查看当前电脑配置")

        self.assertTrue(any(step.agent == "system" for step in plan.steps))


if __name__ == "__main__":
    unittest.main()
