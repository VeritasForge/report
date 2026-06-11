"""CLI 실행기.

ClaudeCLIExecutor — claude-agent-sdk 기반.
"""

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
