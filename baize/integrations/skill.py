from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from baize.core.models import TaskStep


class SkillExecutionError(RuntimeError):
    pass


class SkillExecutor:
    def run(self, step: TaskStep) -> str:
        path_value = step.metadata.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            raise SkillExecutionError("Skill 接入缺少 path")
        path = Path(path_value).expanduser().resolve()
        if not path.is_file():
            raise SkillExecutionError(f"Skill 文件不存在: {path}")
        module = self._load_module(path)
        handler = getattr(module, "run", None)
        if not callable(handler):
            raise SkillExecutionError("Skill 文件必须暴露可调用的 run(step, metadata) 函数")
        result = handler(step, dict(step.metadata))
        return self._format_result(result)

    def _load_module(self, path: Path) -> Any:
        module_name = f"baize_skill_{path.stem}_{abs(hash(path))}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise SkillExecutionError("无法加载 Skill 模块")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _format_result(self, result: object) -> str:
        if result is None:
            return "Skill 执行完成"
        if isinstance(result, str):
            return result
        return repr(result)
