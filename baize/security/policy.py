from __future__ import annotations

from baize.core.models import RiskLevel, TaskStep


class SafetyPolicy:
    dangerous_terms = (
        "delete",
        "remove",
        "overwrite",
        "format",
        "shutdown",
        "reboot",
        "rm -rf",
        "删除",
        "移除",
        "覆盖",
        "格式化",
        "关机",
        "重启",
    )

    sensitive_terms = (
        "desktop",
        "documents",
        "downloads",
        "home",
        "桌面",
        "文档",
        "下载",
        "隐私",
        "账号",
        "密码",
    )

    def classify_text(self, text: str, default: RiskLevel = RiskLevel.LOW) -> RiskLevel:
        normalized = text.lower()
        if any(term in normalized for term in self.dangerous_terms):
            return RiskLevel.DANGEROUS
        if any(term in normalized for term in self.sensitive_terms):
            return RiskLevel.SENSITIVE
        return default

    def apply(self, step: TaskStep, request_text: str) -> TaskStep:
        risk = self.classify_text(request_text, step.risk)
        requires_confirmation = risk in {RiskLevel.SENSITIVE, RiskLevel.DANGEROUS}
        return TaskStep(
            id=step.id,
            agent=step.agent,
            action=step.action,
            risk=risk,
            requires_confirmation=requires_confirmation,
            status=step.status,
            result=step.result,
            metadata=step.metadata,
        )
