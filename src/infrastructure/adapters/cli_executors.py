"""CLI 실행기.

ClaudeCLIExecutor — claude-agent-sdk 기반 (Task 6).
GeminiCLIExecutor — 별도 process 호출 유지 (본 PR 범위 밖).
"""

import subprocess
from datetime import date
from pathlib import Path

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    CLIJSONDecodeError,
    CLINotFoundError,
    ProcessError,
    TextBlock,
    query,
)

# Task 0 스파이크 결과로 채택. 변경 시 docs/sdk_spike_findings.md 참조.
_PERMISSION_MODE: str = "acceptEdits"
_DEFAULT_MODEL: str = "sonnet"


class ClaudeCLIExecutor:
    """Claude Agent SDK 기반 실행기 — `.claude/commands/<command>.md` 슬래시 커맨드 호출."""

    def __init__(self, command: str = "daily_report", model: str | None = None):
        self._command = command
        self._model = model

    def execute(
        self,
        space_key: str,
        mention_users: str = "",
        report_date: date | None = None,
    ) -> str | None:
        prompt = self._build_prompt(space_key, mention_users, report_date)
        try:
            return anyio.run(self._run_sdk, prompt)
        except (CLINotFoundError, ProcessError, CLIJSONDecodeError) as e:
            print(f"ERROR: claude SDK failed: {type(e).__name__}: {e}")
            return None

    def _build_prompt(
        self,
        space_key: str,
        mention_users: str,
        report_date: date | None,
    ) -> str:
        parts = [f"/{self._command}", space_key]
        if mention_users:
            parts.append(f'"{mention_users}"')
        if report_date:
            parts.append(f"--date {report_date.isoformat()}")
        return " ".join(parts)

    async def _run_sdk(self, prompt: str) -> str:
        parts: list[str] = []
        opts = ClaudeAgentOptions(
            model=self._model or _DEFAULT_MODEL,
            permission_mode=_PERMISSION_MODE,
            cwd=Path.cwd(),
        )
        async for msg in query(prompt=prompt, options=opts):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
        return "\n".join(parts).strip()


class GeminiCLIExecutor:
    """Gemini CLI 실행기 (subprocess 유지 — 본 PR 범위 밖)."""

    def __init__(self, command: str = "daily_report"):
        self._command = command

    def execute(
        self,
        space_key: str,
        mention_users: str = "",
        report_date: date | None = None,
    ) -> str | None:
        prompt = self._build_prompt(space_key, mention_users, report_date)
        cmd = ["gemini", "-p", prompt]
        return self._run_command(cmd, cli_name="gemini")

    def _build_prompt(
        self,
        space_key: str,
        mention_users: str,
        report_date: date | None,
    ) -> str:
        parts = [f"/{self._command}", space_key]
        if mention_users:
            parts.append(f'"{mention_users}"')
        if report_date:
            parts.append(f"--date {report_date.isoformat()}")
        return " ".join(parts)

    def _run_command(self, command: list[str], cli_name: str) -> str | None:
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                print(f"ERROR: {cli_name} CLI failed with exit code {process.returncode}.")
                print(f"ERROR: Stderr: {stderr.strip()}")
                return None
            return stdout.strip()
        except FileNotFoundError:
            print(
                f"ERROR: '{cli_name}' CLI not found. Please ensure it is installed and in your system's PATH."
            )
            return None
        except Exception as e:
            print(f"ERROR: An unexpected error occurred: {e}")
            return None
