from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from baize.core.models import AgentIntegration, IntegrationKind


class ConfigError(ValueError):
    pass


class BaizeConfig:
    def __init__(self, integrations: tuple[AgentIntegration, ...] = ()) -> None:
        self.integrations = integrations

    @classmethod
    def load(cls, path: str | Path) -> BaizeConfig:
        config_path = Path(path).expanduser()
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigError(f"无法读取配置文件: {config_path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"配置文件不是有效 JSON: {config_path}") from exc
        if not isinstance(data, dict):
            raise ConfigError("配置文件根节点必须是 JSON 对象")
        return cls(integrations=parse_integrations(data))


def parse_integrations(data: dict[str, Any]) -> tuple[AgentIntegration, ...]:
    integrations: list[AgentIntegration] = []
    integrations.extend(parse_mcp_items(data.get("mcp", ())))
    integrations.extend(parse_skill_items(data.get("skills", ())))
    return tuple(integrations)


def parse_mcp_items(value: object) -> tuple[AgentIntegration, ...]:
    items = require_list(value, "mcp")
    integrations = []
    for item in items:
        entry = require_dict(item, "mcp 项")
        name = require_string(entry, "name")
        command = require_string(entry, "command")
        tool = require_string(entry, "tool")
        description = optional_string(entry, "description", f"{command} -> {tool}")
        metadata = dict(entry.get("metadata", {})) if isinstance(entry.get("metadata", {}), dict) else {}
        metadata.update(
            {
                "keywords": parse_keywords(entry, name),
                "command": command,
                "args": parse_args(entry.get("args", ())),
                "tool": tool,
                "arguments": parse_arguments(entry.get("arguments", {})),
            }
        )
        integrations.append(AgentIntegration(kind=IntegrationKind.MCP, name=name, description=description, metadata=metadata))
    return tuple(integrations)


def parse_skill_items(value: object) -> tuple[AgentIntegration, ...]:
    items = require_list(value, "skills")
    integrations = []
    for item in items:
        entry = require_dict(item, "skill 项")
        name = require_string(entry, "name")
        path = require_string(entry, "path")
        description = optional_string(entry, "description", path)
        metadata = dict(entry.get("metadata", {})) if isinstance(entry.get("metadata", {}), dict) else {}
        metadata.update({"keywords": parse_keywords(entry, name), "path": path})
        integrations.append(AgentIntegration(kind=IntegrationKind.SKILL, name=name, description=description, metadata=metadata))
    return tuple(integrations)


def require_list(value: object, field: str) -> list[object]:
    if value in (None, ()):
        return []
    if not isinstance(value, list):
        raise ConfigError(f"{field} 必须是数组")
    return value


def require_dict(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{field} 必须是对象")
    return value


def require_string(value: dict[str, Any], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise ConfigError(f"{field} 必须是非空字符串")
    return item.strip()


def optional_string(value: dict[str, Any], field: str, default: str) -> str:
    item = value.get(field, default)
    if not isinstance(item, str) or not item.strip():
        raise ConfigError(f"{field} 必须是非空字符串")
    return item.strip()


def parse_keywords(value: dict[str, Any], name: str) -> tuple[str, ...]:
    keywords = value.get("keywords", (name,))
    if not isinstance(keywords, list | tuple):
        raise ConfigError("keywords 必须是字符串数组")
    parsed = tuple(str(keyword).strip() for keyword in keywords if str(keyword).strip())
    return parsed or (name,)


def parse_args(value: object) -> tuple[str, ...]:
    if value in (None, ()):
        return ()
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, list | tuple):
        raise ConfigError("args 必须是字符串数组")
    return tuple(str(item) for item in value)


def parse_arguments(value: object) -> dict[str, Any]:
    if value in (None, ()):
        return {}
    if not isinstance(value, dict):
        raise ConfigError("arguments 必须是对象")
    return value
