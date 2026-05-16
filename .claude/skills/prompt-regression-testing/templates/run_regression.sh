#!/usr/bin/env bash
# Prompt Regression Test Runner
# Runs the same dry-run multiple times across models to capture LLM non-determinism.
#
# Default: Sonnet x10 + Haiku x10 + Opus x3 = 23 runs (~60 min, see SKILL.md cost table).
#
# Setup (adapt to your project):
#   1. Copy this script to <your_repo>/tests/regression/scripts/run_regression.sh
#   2. Edit RUN_COMMAND below to match your dry-run invocation
#   3. (Optional) Adjust ITERATIONS_* counts based on your cost budget
#
# Usage:
#   ./tests/regression/scripts/run_regression.sh [DATE]
#
# Example:
#   ./tests/regression/scripts/run_regression.sh 2026-05-15
#   ./tests/regression/scripts/run_regression.sh         # uses today

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────
# Required: command template that produces ONE dry-run output to stdout.
# Available variables in template: {MODEL}, {DATE_ARG} (empty if no DATE)
# Examples:
#   make run-style:    'DRY_RUN=1 make run MODEL={MODEL} {DATE_ARG}'
#   direct python:     'uv run python -m src.main --dry-run --model {MODEL} {DATE_ARG}'
#   custom CLI:        'my-cli --model {MODEL} --date {DATE_ARG} --dry'
RUN_COMMAND_TEMPLATE="${RUN_COMMAND_TEMPLATE:-DRY_RUN=1 make run MODEL={MODEL} {DATE_ARG}}"

# Iteration counts per model. Adjust based on cost budget and statistical needs.
ITERATIONS_SONNET="${ITERATIONS_SONNET:-10}"
ITERATIONS_HAIKU="${ITERATIONS_HAIKU:-10}"
ITERATIONS_OPUS="${ITERATIONS_OPUS:-3}"

# Models to run (comment out a line to skip a model)
MODELS=("sonnet:$ITERATIONS_SONNET" "haiku:$ITERATIONS_HAIKU" "opus:$ITERATIONS_OPUS")

# Output directory pattern (timestamp-based by default)
RUNS_DIR_BASE="${RUNS_DIR_BASE:-tests/regression/runs}"
# ──────────────────────────────────────────────────────────────

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

DATE="${1:-}"
RUNS_DIR="${RUNS_DIR_BASE}/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RUNS_DIR"

echo "🏁 Regression test starting"
echo "   Repo:    $REPO_ROOT"
echo "   Output:  $RUNS_DIR"
echo "   Date:    ${DATE:-<today>}"
echo "   Command: $RUN_COMMAND_TEMPLATE"
echo ""

DATE_ARG=""
if [[ -n "$DATE" ]]; then
  # Adapt to your CLI; some accept `DATE=...` env, others accept `--date ...`
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

    # Substitute template variables
    local cmd="${RUN_COMMAND_TEMPLATE//\{MODEL\}/$model}"
    cmd="${cmd//\{DATE_ARG\}/$DATE_ARG}"

    if eval "$cmd" > "$out_file" 2>&1; then
      local size
      size=$(wc -c < "$out_file" | tr -d ' ')
      if [[ "$size" -lt 100 ]]; then
        echo "  ⚠️  suspiciously small ($size bytes) — likely infrastructure failure"
      else
        echo "  ✅ ok ($(wc -l < "$out_file" | tr -d ' ') lines)"
      fi
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

for entry in "${MODELS[@]}"; do
  model="${entry%%:*}"
  count="${entry##*:}"
  run_model "$model" "$count"
done

total=0
for entry in "${MODELS[@]}"; do
  total=$((total + ${entry##*:}))
done

echo ""
echo "✨ Regression runs complete"
echo "   Total: $total outputs in $RUNS_DIR"
echo ""
echo "Next steps:"
echo "  1. Score:    uv run python tests/regression/scripts/score_runs.py $RUNS_DIR"
echo "  2. Compare:  uv run python tests/regression/scripts/compare_runs.py <baseline_dir> $RUNS_DIR"
echo ""
echo "Tip: Rename this dir to something meaningful (e.g. 'baseline_v1') for future comparisons:"
echo "  mv $RUNS_DIR ${RUNS_DIR_BASE}/baseline_v1"
