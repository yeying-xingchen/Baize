from __future__ import annotations

import argparse

from baize.config import BaizeConfig, ConfigError
from baize.core.models import AgentIntegration, IntegrationKind
from baize.core.orchestrator import Orchestrator
from baize.runtime.local import LocalRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="baize", description="Baize personal AI assistant prototype")
    parser.add_argument("request", help="自然语言任务描述")
    parser.add_argument("--config", help="加载 MCP 和 Skill 接入配置文件")
    parser.add_argument("--confirm", action="store_true", help="确认执行需要确认的步骤")
    parser.add_argument("--mcp", action="append", default=(), metavar="NAME:COMMAND:TOOL", help="接入 stdio MCP Server 并指定默认工具")
    parser.add_argument("--skill", action="append", default=(), metavar="NAME:PATH", help="接入 Python Skill 文件")
    parser.add_argument("--no-ai", action="store_true", help="禁用 OpenAI 兼容接口，使用本地规则调度")
    return parser


def parse_integration(value: str, kind: IntegrationKind) -> AgentIntegration:
    if kind == IntegrationKind.MCP:
        name, command, tool = parse_parts(value, 3, "MCP 接入格式必须是 NAME:COMMAND:TOOL")
        return AgentIntegration(
            kind=kind,
            name=name,
            description=f"{command} -> {tool}",
            metadata={"keywords": (name,), "command": command, "tool": tool},
        )
    name, path = parse_parts(value, 2, "Skill 接入格式必须是 NAME:PATH")
    return AgentIntegration(
        kind=kind,
        name=name,
        description=path,
        metadata={"keywords": (name,), "path": path},
    )


def parse_parts(value: str, count: int, error: str) -> tuple[str, ...]:
    parts = tuple(part.strip() for part in value.split(":", count - 1))
    if len(parts) != count or any(not part for part in parts):
        raise argparse.ArgumentTypeError(error)
    return parts


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config_integrations = ()
    if args.config:
        try:
            config_integrations = BaizeConfig.load(args.config).integrations
        except ConfigError as exc:
            parser.error(str(exc))
    integrations = config_integrations + tuple(
        parse_integration(value, kind)
        for kind, values in ((IntegrationKind.MCP, args.mcp), (IntegrationKind.SKILL, args.skill))
        for value in values
    )
    orchestrator = Orchestrator(integrations=integrations, use_env_ai=not args.no_ai)
    runtime = LocalRuntime()
    plan = orchestrator.create_plan(args.request)
    report = runtime.run(plan, confirmed=args.confirm)

    print(f"请求: {report.plan.request.text}")
    for step in report.steps:
        confirmation = "需要确认" if step.requires_confirmation else "无需确认"
        print(f"- {step.id} [{step.agent}] {step.status.value} {step.risk.value} {confirmation}: {step.action}")
        if step.result:
            print(f"  结果: {step.result}")


if __name__ == "__main__":
    main()
