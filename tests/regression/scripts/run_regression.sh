#!/usr/bin/env bash
# Daily Report 회귀 테스트 실행 스크립트
# Sonnet 10회 + Haiku 10회 + Opus 3회 = 23회
#
# Usage:
#   ./tests/regression/scripts/run_regression.sh [DATE]
#
# Example:
#   ./tests/regression/scripts/run_regression.sh 2026-05-15
#   ./tests/regression/scripts/run_regression.sh         # uses today

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

DATE="${1:-}"
RUNS_DIR="tests/regression/runs/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RUNS_DIR"

echo "🏁 Regression test starting"
echo "   Repo:    $REPO_ROOT"
echo "   Output:  $RUNS_DIR"
echo "   Date:    ${DATE:-<today>}"
echo ""

DATE_ARG=""
if [[ -n "$DATE" ]]; then
  DATE_ARG="DATE=$DATE"
fi

run_model() {
  local model="$1"
  local count="$2"

  for i in $(seq -f "%03g" 1 "$count"); do
    local out_file="$RUNS_DIR/${model}-${i}.txt"
    local started_at
    started_at="$(date -u +%FT%TZ)"

    echo "▶ [${model}] run ${i}/${count} → ${out_file}"

    # shellcheck disable=SC2086
    if DRY_RUN=1 make run MODEL="$model" $DATE_ARG > "$out_file" 2>&1; then
      echo "  ✅ ok ($(wc -l < "$out_file" | tr -d ' ') lines)"
    else
      echo "  ❌ failed (see $out_file)"
    fi

    # metadata sidecar
    {
      echo "model=$model"
      echo "run_index=$i"
      echo "started_at=$started_at"
      echo "ended_at=$(date -u +%FT%TZ)"
      echo "date_arg=${DATE:-}"
    } > "${out_file%.txt}.meta"
  done
}

run_model "sonnet" 10
run_model "haiku" 10
run_model "opus" 3

echo ""
echo "✨ Regression runs complete"
echo "   Total: 23 outputs in $RUNS_DIR"
echo ""
echo "Next: run scoring with"
echo "  uv run python tests/regression/scripts/score_runs.py $RUNS_DIR"
