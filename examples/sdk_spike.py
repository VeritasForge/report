"""Claude Agent SDK 스파이크 — Task 0 검증 (plan: rustling-honking-squirrel.md)

검증 항목:
  (a) .claude/commands/*.md 자동 로드 여부
  (b) MCP 서버 자동 로드 여부 (Atlassian MCP는 글로벌 ~/.claude 설정 추정)
  (c) model="sonnet" short alias 수용 여부
  (d) permission_mode 비교: auto / acceptEdits / bypassPermissions
  (e) total_cost_usd (캐싱 확인)
"""

from pathlib import Path

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)


META_PROMPT = (
    "List the slash commands defined in this project (look in .claude/commands/) "
    "and the MCP tools you have access to (especially Atlassian Confluence/Jira). "
    "Reply briefly in this exact format and nothing else:\n"
    "SLASH_COMMANDS: <comma-separated list, or 'none'>\n"
    "MCP_TOOLS: <comma-separated list, or 'none'>\n"
    "DONE"
)


async def run_with_mode(mode: str, model: str = "sonnet") -> dict:
    header = f"permission_mode='{mode}', model='{model}'"
    print(f"\n{'=' * 60}\nTesting {header}\n{'=' * 60}")
    result: dict = {
        "mode": mode,
        "model": model,
        "model_accepted": False,
        "slash_commands_seen": "",
        "mcp_tools_seen": "",
        "cost_usd": None,
        "error": None,
        "text_output": "",
    }
    try:
        opts = ClaudeAgentOptions(
            model=model,
            permission_mode=mode,
            cwd=Path.cwd(),
        )
        async for msg in query(prompt=META_PROMPT, options=opts):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        result["text_output"] += block.text
            elif isinstance(msg, ResultMessage):
                result["cost_usd"] = getattr(msg, "total_cost_usd", None)
        result["model_accepted"] = True
        for line in result["text_output"].splitlines():
            if line.startswith("SLASH_COMMANDS:"):
                result["slash_commands_seen"] = line.split(":", 1)[1].strip()
            elif line.startswith("MCP_TOOLS:"):
                result["mcp_tools_seen"] = line.split(":", 1)[1].strip()
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        print(f"FAILED: {result['error']}")

    print(f"text_output (truncated):\n{result['text_output'][:800]}")
    print(f"cost_usd: {result['cost_usd']}")
    print(f"error: {result['error']}")
    return result


async def main() -> None:
    modes = ["auto", "acceptEdits", "bypassPermissions"]
    results = []
    for mode in modes:
        r = await run_with_mode(mode)
        results.append(r)

    print(f"\n{'=' * 60}\nSUMMARY\n{'=' * 60}")
    for r in results:
        daily_seen = "daily_report" in r["slash_commands_seen"]
        mcp_seen = bool(r["mcp_tools_seen"]) and r["mcp_tools_seen"].lower() != "none"
        print(f"\nmode={r['mode']}")
        print(f"  model_accepted (sonnet alias): {r['model_accepted']}")
        print(f"  daily_report.md detected:     {daily_seen}")
        print(f"  mcp tools detected:           {mcp_seen}")
        print(f"  slash_commands_raw:           {r['slash_commands_seen'][:200]}")
        print(f"  mcp_tools_raw:                {r['mcp_tools_seen'][:200]}")
        print(f"  cost_usd:                     {r['cost_usd']}")
        print(f"  error:                        {r['error']}")


if __name__ == "__main__":
    anyio.run(main)
