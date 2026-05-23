import sys
import tempfile
import unittest
from pathlib import Path

from baize.ai.openai_client import AIClientError
from baize.config import BaizeConfig
from baize.core.models import AgentIntegration, IntegrationKind, RiskLevel, TaskStatus, TaskStep
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

    def test_mcp_integration_routes_to_mcp_agent(self) -> None:
        integration = AgentIntegration(
            kind=IntegrationKind.MCP,
            name="filesystem",
            description="本地文件 MCP Server",
            metadata={"keywords": ("filesystem", "mcp")},
        )
        plan = Orchestrator(integrations=(integration,), use_env_ai=False).create_plan("通过 filesystem MCP 查找资料")

        self.assertTrue(any(step.agent == "mcp" for step in plan.steps))
        mcp_step = next(step for step in plan.steps if step.agent == "mcp")
        self.assertEqual(mcp_step.metadata["integration"], "mcp")
        self.assertEqual(mcp_step.metadata["name"], "filesystem")
        self.assertTrue(mcp_step.requires_confirmation)

    def test_skill_integration_routes_to_skill_agent(self) -> None:
        integration = AgentIntegration(
            kind=IntegrationKind.SKILL,
            name="pdf-summary",
            description="PDF 摘要 Skill",
            metadata={"keywords": ("pdf-summary", "摘要技能")},
        )
        plan = Orchestrator(integrations=(integration,), use_env_ai=False).create_plan("用 pdf-summary Skill 总结报告")

        self.assertTrue(any(step.agent == "skill" for step in plan.steps))
        skill_step = next(step for step in plan.steps if step.agent == "skill")
        self.assertEqual(skill_step.metadata["integration"], "skill")
        self.assertEqual(skill_step.metadata["name"], "pdf-summary")
        self.assertTrue(skill_step.requires_confirmation)

    def test_runtime_executes_mcp_step_after_confirmation(self) -> None:
        server_path = Path(__file__).with_name("fake_mcp_server.py")
        integration = AgentIntegration(
            kind=IntegrationKind.MCP,
            name="fake-mcp",
            description="测试 MCP Server",
            metadata={"keywords": ("fake-mcp",), "command": sys.executable, "args": (str(server_path),), "tool": "echo"},
        )
        plan = Orchestrator(integrations=(integration,), use_env_ai=False).create_plan("调用 fake-mcp")
        report = LocalRuntime().run(plan, confirmed=True)
        mcp_step = next(step for step in report.steps if step.agent == "mcp")

        self.assertEqual(mcp_step.status, TaskStatus.COMPLETED)
        self.assertEqual(mcp_step.result, "called echo")

    def test_runtime_executes_skill_step_after_confirmation(self) -> None:
        skill_path = Path(__file__).with_name("fake_skill.py")
        integration = AgentIntegration(
            kind=IntegrationKind.SKILL,
            name="fake-skill",
            description="测试 Skill",
            metadata={"keywords": ("fake-skill",), "path": str(skill_path)},
        )
        plan = Orchestrator(integrations=(integration,), use_env_ai=False).create_plan("调用 fake-skill")
        report = LocalRuntime().run(plan, confirmed=True)
        skill_step = next(step for step in report.steps if step.agent == "skill")

        self.assertEqual(skill_step.status, TaskStatus.COMPLETED)
        self.assertEqual(skill_step.result, f"skill fake-skill handled {skill_step.id}")

    def test_config_loads_mcp_and_skill_integrations(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as config_file:
            config_file.write(
                """
                {
                  "mcp": [
                    {
                      "name": "fake-mcp",
                      "description": "测试 MCP",
                      "command": "python3",
                      "args": ["tests/fake_mcp_server.py"],
                      "tool": "echo",
                      "arguments": {"message": "hello"},
                      "keywords": ["fake-mcp", "mcp"]
                    }
                  ],
                  "skills": [
                    {
                      "name": "fake-skill",
                      "description": "测试 Skill",
                      "path": "tests/fake_skill.py",
                      "keywords": ["fake-skill", "skill"]
                    }
                  ]
                }
                """
            )
            config_file.flush()
            config = BaizeConfig.load(config_file.name)

        self.assertEqual(len(config.integrations), 2)
        self.assertEqual(config.integrations[0].kind, IntegrationKind.MCP)
        self.assertEqual(config.integrations[0].metadata["args"], ("tests/fake_mcp_server.py",))
        self.assertEqual(config.integrations[0].metadata["arguments"], {"message": "hello"})
        self.assertEqual(config.integrations[1].kind, IntegrationKind.SKILL)
        self.assertEqual(config.integrations[1].metadata["path"], "tests/fake_skill.py")


if __name__ == "__main__":
    unittest.main()
