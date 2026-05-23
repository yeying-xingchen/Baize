from __future__ import annotations

import argparse

from baize.core.orchestrator import Orchestrator
from baize.runtime.local import LocalRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="baize", description="Baize personal AI assistant prototype")
    parser.add_argument("request", help="自然语言任务描述")
    parser.add_argument("--confirm", action="store_true", help="确认执行需要确认的步骤")
    parser.add_argument("--no-ai", action="store_true", help="禁用 OpenAI 兼容接口，使用本地规则调度")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    orchestrator = Orchestrator(use_env_ai=not args.no_ai)
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
