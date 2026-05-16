"""베이스라인과 신규 runs 디렉토리를 비교하여 변화량 리포트 생성.

Usage:
    uv run python tests/regression/scripts/compare_runs.py <baseline_dir> <new_dir>

Output:
    stdout: 모델별 점수 변동표 + 항목별 통과율 변동표
"""

from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def load_scores(scores_csv: Path) -> tuple[dict[str, list[float]], dict[str, dict[str, list[float]]]]:
    """모델별 총점, 모델/항목별 점수 반환."""
    totals_by_model: dict[str, list[float]] = defaultdict(list)
    item_by_model: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    with scores_csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            model = row["model"]
            totals_by_model[model].append(float(row["total"]))
            for key, val in row.items():
                if key in ("run_id", "model", "total"):
                    continue
                item_by_model[model][key].append(float(val))

    return totals_by_model, item_by_model


def avg(xs: list[float]) -> float:
    return round(statistics.mean(xs), 2) if xs else 0.0


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: uv run python tests/regression/scripts/compare_runs.py <baseline_dir> <new_dir>")
        return 2

    baseline = Path(sys.argv[1]) / "scores.csv"
    new = Path(sys.argv[2]) / "scores.csv"

    if not baseline.exists() or not new.exists():
        print(f"Missing scores.csv. Run score_runs.py first on:\n  {baseline.parent}\n  {new.parent}")
        return 1

    base_totals, base_items = load_scores(baseline)
    new_totals, new_items = load_scores(new)

    all_models = sorted(set(base_totals.keys()) | set(new_totals.keys()))

    print("# 회귀 비교: 베이스라인 → 신규\n")
    print(f"- Baseline: `{baseline.parent}`")
    print(f"- New:      `{new.parent}`\n")

    print("## 모델별 총점 비교\n")
    print("| 모델 | baseline 평균 | new 평균 | Δ | baseline runs | new runs |")
    print("|------|--------------|---------|---|--------------|---------|")
    for m in all_models:
        b_avg = avg(base_totals.get(m, []))
        n_avg = avg(new_totals.get(m, []))
        delta = round(n_avg - b_avg, 2)
        sign = "+" if delta >= 0 else ""
        print(f"| {m} | {b_avg} | {n_avg} | {sign}{delta} | {len(base_totals.get(m, []))} | {len(new_totals.get(m, []))} |")
    print()

    print("## 항목별 통과율 변동 (Δ가 큰 순)\n")
    print("| 항목 | 모델 | baseline | new | Δ |")
    print("|------|------|---------|-----|---|")
    rows = []
    for m in all_models:
        b_items = base_items.get(m, {})
        n_items = new_items.get(m, {})
        all_keys = sorted(set(b_items.keys()) | set(n_items.keys()))
        for key in all_keys:
            b = avg(b_items.get(key, [])) * 100
            n = avg(n_items.get(key, [])) * 100
            delta = round(n - b, 1)
            if abs(delta) >= 0.1:
                rows.append((abs(delta), key, m, b, n, delta))
    rows.sort(reverse=True)
    for _, key, m, b, n, delta in rows[:30]:
        sign = "+" if delta >= 0 else ""
        print(f"| {key} | {m} | {b}% | {n}% | {sign}{delta}% |")
    if not rows:
        print("| (변동 없음) | - | - | - | - |")

    return 0


if __name__ == "__main__":
    sys.exit(main())
