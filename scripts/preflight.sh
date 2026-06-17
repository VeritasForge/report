#!/usr/bin/env bash
# report 셋업 진단 (read-only, 멱등). 모든 필수 항목 통과 시 exit 0, 아니면 1.
set -u
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 1

PASS="[OK]"; FAIL="[XX]"; WARN="[!!]"
fail=0
ok()   { printf "  %s %s\n" "$PASS" "$1"; }
bad()  { printf "  %s %s\n" "$FAIL" "$1"; fail=1; }
warn() { printf "  %s %s\n" "$WARN" "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

echo "report preflight  ($REPO_DIR)"
echo "-- 시스템 의존성 --"

if have uv; then ok "uv: $(uv --version 2>/dev/null)"; else bad "uv 없음 -> https://docs.astral.sh/uv 설치"; fi

if have uv && uv run python -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3,12) else 1)' >/dev/null 2>&1; then
  ok "python >=3.12 ($(uv run python -V 2>/dev/null))"
else
  bad "python >=3.12 아님 (pyproject requires-python>=3.12)"
fi

if have node; then ok "node: $(node -v 2>/dev/null)"; else bad "node 없음 -> claude CLI / sequential-thinking MCP에 필요"; fi

if have claude; then ok "claude: $(claude --version 2>/dev/null)"; else bad "claude CLI 없음 -> npm i -g @anthropic-ai/claude-code"; fi

if have mcp-atlassian || [ -x "$HOME/.local/bin/mcp-atlassian" ]; then ok "mcp-atlassian 설치됨"; else bad "mcp-atlassian 없음 -> uv tool install mcp-atlassian"; fi

echo "-- 설정 / 인증 --"
if [ -f .env ]; then
  ok ".env 존재"
  if grep -qE '^CONFLUENCE_SPACE_KEY=.+' .env; then ok "CONFLUENCE_SPACE_KEY 설정됨"; else bad "CONFLUENCE_SPACE_KEY 비어있음 (필수)"; fi
else
  bad ".env 없음 -> cp .env.example .env 후 값 입력"
fi

if have claude && claude auth status >/dev/null 2>&1; then ok "claude 인증됨"; else bad "claude 미인증 -> claude auth login (또는 claude setup-token)"; fi

if have claude; then
  mcp_out="$(claude mcp list 2>/dev/null)"
  if echo "$mcp_out" | grep -qi "mcp-atlassian"; then ok "mcp-atlassian 등록됨"; else bad "mcp-atlassian 미등록 -> make mcp-setup"; fi
  if echo "$mcp_out" | grep -qi "sequential-thinking"; then ok "sequential-thinking 등록됨"; else warn "sequential-thinking 미등록 (선택; make smoke로 필수여부 확정)"; fi
else
  warn "claude 없어 MCP 등록 확인 생략"
fi

echo ""
if [ "$fail" -eq 0 ]; then
  echo "PREFLIGHT: PASS  ->  make smoke 로 E2E 게이트 실행"; exit 0
else
  echo "PREFLIGHT: FAIL  ->  위 [XX] 항목 해결 (README의 Installation 참고)"; exit 1
fi
