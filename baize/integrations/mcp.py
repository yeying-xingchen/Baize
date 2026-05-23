from __future__ import annotations

import json
import subprocess
from typing import Any

from baize.core.models import TaskStep


class MCPClientError(RuntimeError):
    pass


class StdioMCPClient:
    def __init__(self, command: str, args: tuple[str, ...] = (), env: dict[str, str] | None = None) -> None:
        self.command = command
        self.args = args
        self.env = env
        self._next_id = 1

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> str:
        process = subprocess.Popen(
            (self.command, *self.args),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.env,
        )
        try:
            self._send(process, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "baize", "version": "0.1.0"}})
            initialize_response = self._receive(process)
            if "error" in initialize_response:
                raise MCPClientError(str(initialize_response["error"]))
            self._notify(process, "notifications/initialized")
            self._send(process, "tools/call", {"name": tool_name, "arguments": arguments or {}})
            response = self._receive(process)
            if "error" in response:
                raise MCPClientError(str(response["error"]))
            return self._format_result(response.get("result"))
        finally:
            self._close(process)

    def _send(self, process: subprocess.Popen[str], method: str, params: dict[str, Any]) -> None:
        message = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        self._next_id += 1
        self._write(process, message)

    def _notify(self, process: subprocess.Popen[str], method: str) -> None:
        self._write(process, {"jsonrpc": "2.0", "method": method})

    def _write(self, process: subprocess.Popen[str], message: dict[str, Any]) -> None:
        if process.stdin is None:
            raise MCPClientError("MCP 进程 stdin 不可用")
        process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        process.stdin.flush()

    def _receive(self, process: subprocess.Popen[str]) -> dict[str, Any]:
        if process.stdout is None:
            raise MCPClientError("MCP 进程 stdout 不可用")
        line = process.stdout.readline()
        if not line:
            stderr = process.stderr.read() if process.stderr is not None else ""
            raise MCPClientError(stderr.strip() or "MCP 进程没有返回响应")
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MCPClientError("MCP 响应不是有效 JSON") from exc
        if not isinstance(response, dict):
            raise MCPClientError("MCP 响应必须是 JSON 对象")
        return response

    def _format_result(self, result: object) -> str:
        if isinstance(result, dict) and isinstance(result.get("content"), list):
            values = []
            for item in result["content"]:
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                    values.append(item["text"])
            if values:
                return "\n".join(values)
        return json.dumps(result, ensure_ascii=False)

    def _close(self, process: subprocess.Popen[str]) -> None:
        if process.stdin is not None:
            process.stdin.close()
        try:
            process.terminate()
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()


class MCPExecutor:
    def run(self, step: TaskStep) -> str:
        command = step.metadata.get("command")
        tool = step.metadata.get("tool")
        if not isinstance(command, str) or not command.strip():
            raise MCPClientError("MCP 接入缺少 command")
        if not isinstance(tool, str) or not tool.strip():
            raise MCPClientError("MCP 接入缺少 tool")
        args = step.metadata.get("args", ())
        arguments = step.metadata.get("arguments", {})
        if isinstance(args, str):
            args = tuple(arg for arg in args.split(" ") if arg)
        if not isinstance(args, tuple):
            args = tuple(args) if isinstance(args, list) else ()
        if not isinstance(arguments, dict):
            arguments = {}
        return StdioMCPClient(command=command, args=args).call_tool(tool, arguments)
