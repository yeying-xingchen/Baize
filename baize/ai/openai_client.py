from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class AIClientError(Exception):
    pass


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout: float = 60.0

    @classmethod
    def from_env(cls) -> OpenAIConfig | None:
        api_key = os.getenv("BAIZE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        model = os.getenv("BAIZE_OPENAI_MODEL") or os.getenv("OPENAI_MODEL")
        if not api_key or not model:
            return None
        return cls(
            api_key=api_key,
            model=model,
            base_url=os.getenv("BAIZE_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL") or cls.base_url,
            timeout=float(os.getenv("BAIZE_OPENAI_TIMEOUT", "60")),
        )


class OpenAIChatClient:
    def __init__(self, config: OpenAIConfig) -> None:
        self.config = config

    def complete_json(self, messages: list[dict[str, str]], temperature: float = 0.2) -> dict[str, Any]:
        content = self.complete(messages=messages, temperature=temperature)
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIClientError("AI 返回内容不是合法 JSON") from exc
        if not isinstance(decoded, dict):
            raise AIClientError("AI 返回 JSON 顶层必须是对象")
        return decoded

    def complete(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AIClientError(f"OpenAI 兼容接口 HTTP 错误: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise AIClientError(f"OpenAI 兼容接口连接失败: {exc.reason}") from exc
        except TimeoutError as exc:
            raise AIClientError("OpenAI 兼容接口请求超时") from exc

        try:
            decoded = json.loads(body)
            content = decoded["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIClientError("OpenAI 兼容接口响应格式无效") from exc
        if not isinstance(content, str):
            raise AIClientError("OpenAI 兼容接口响应内容无效")
        return content
