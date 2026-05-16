"""Prompt Regression Test Scorer (template).

Rule-based, deterministic scoring of LLM dry-run outputs against a rubric.

# How to adapt for your project
1. Edit `RUBRIC_CHECKS` below to match your fixture's `expected_*` keywords
   and your rubric.md items. Keep all 3 files (ground_truth, rubric, scorer)
   synchronized — if you rename an expected category, change it everywhere.
2. Pattern primitives supported:
   - patterns_all     : ALL regex must match (AND)
   - patterns_any     : at least ONE regex must match (OR)
   - patterns_none    : NONE may match (block list, e.g. description-quote bans)
   - patterns_each    : partial credit per regex (sum / count)
   - patterns_any_bonus : after all/any pass, require ≥1 of these for full credit
   - category_block_check : extract `*[Category]*` block, require keyword in it
3. Common pitfalls:
   - patterns_any with bare keywords is too lenient (context-blind).
     Use category_block_check if you need to verify the keyword appears
     inside a specific category block.
   - Korean text: use re.IGNORECASE freely; the matcher already applies it.

Usage:
    uv run python tests/regression/scripts/score_runs.py <runs_dir>

Output:
    <runs_dir>/scores.csv     - per-run, per-item scores
    <runs_dir>/summary.md     - per-model stats + top-N missing/hallucination patterns
"""

from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# 각 검증 항목별 패턴(regex). True면 통과, False면 실패.
#
# Adapt these patterns to match your own organization's domain. The structure
# below corresponds to fixtures/rubric.md and fixtures/ground_truth_*.json which
# use synthetic data (Alice, Bob, ProductA, PROJ-XXXX, etc.) for illustration.
RUBRIC_CHECKS: dict[str, dict] = {
    "A1": {
        "label": "Alice — PROJ-1001 Doing 포함",
        "patterns_any": [r"OrderItem.*범위", r"범위.*처리", r"FeatureService"],
        "weight": 1.0,
    },
    "A2": {
        "label": "Alice — FeatureService 문서화 세부",
        "patterns_any": [r"FeatureRecord", r"SessionStatusHistory", r"처리\s*프로세스"],
        "weight": 1.0,
    },
    "A3": {
        "label": "Bob — PROJ-1002 Done + [ProductSim] 카테고리",
        "patterns_all": [r"input-A|input-B", r"\[ProductSim\]"],
        "weight": 1.0,
    },
    "A4": {
        "label": "Charlie — PROJ-1003 + [ProductA v2.2.2-h1] 카테고리",
        "patterns_all": [r"timezone", r"\[ProductA\s*v?2\.2\.2-h1\]"],
        "weight": 1.0,
    },
    "A5": {
        "label": "Charlie — 권한 POC 세부(웹푸시/소속)",
        "patterns_all": [r"권한", r"POC|PoC"],
        "patterns_any_bonus": [r"웹푸시", r"소속.*프리셋", r"커스텀.*확장"],
        "weight": 1.0,
    },
    "A6": {
        "label": "David — PROJ-1004 + [ProductA v2.3.0] + helm",
        "patterns_all": [r"\[ProductA\s*v?2\.3\.0\]", r"helm"],
        "weight": 1.0,
    },
    "A7": {
        "label": "Eve — Trivy + moduleA + PoC 미팅",
        "patterns_each": [r"Trivy", r"moduleA|dependabot", r"권한.*미팅|PoC.*미팅|상위기획"],
        "weight": 1.0,
    },
    "A8": {
        "label": "Eve — ModuleX 개발 ToDo + _예정_ 섹션",
        "patterns_all": [r"ModuleX", r"_예정_"],
        "weight": 1.0,
    },
    "B1": {
        "label": "[ProductA v2.2.2-h1] hotfix 별도 카테고리",
        "patterns_any": [r"\[ProductA\s*v?2\.2\.2-h1\]"],
        "weight": 1.0,
    },
    "B2": {
        "label": "[ProductSim] 별도 카테고리",
        "patterns_any": [r"\[ProductSim\]"],
        "weight": 1.0,
    },
    "B3": {
        "label": "권한 POC를 [기술 리서치/문서화] 분류",
        "category_block_check": {
            "expected_category": "기술 리서치/문서화",
            "keyword_in_block": "권한",
        },
        "weight": 1.0,
    },
    "C1": {
        "label": "JIRA description 본문 인용 없음 (감점)",
        "patterns_none": [r"ReportService", r"Playwright", r"AS-IS", r"TO-BE", r"FastAPI"],
        "weight": 1.0,
    },
    "C2": {
        "label": "환각 없음 (Confluence/JIRA 미존재 작업 추가)",
        "patterns_none": [
            r"Slack.*알림.*개발",
            r"신규.*기능.*개발",
        ],
        "weight": 1.0,
    },
    "D1": {
        "label": "📊 일정 요약 시작 + 슬랙 호환",
        "patterns_all": [r"📊\s*일정\s*요약"],
        "patterns_none": [r"^\|[^|]+\|[^|]+\|"],  # 마크다운 테이블 행 금지
        "weight": 1.0,
    },
    "D2": {
        "label": "카테고리 헤더 *[제품명]* 형식 + 구분선",
        "patterns_all": [r"\*\[.+\]\*", r"───"],
        "weight": 1.0,
    },
}


@dataclass
class RunScore:
    run_id: str
    model: str
    scores: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    missing: list[str] = field(default_factory=list)
    hallucinations: list[str] = field(default_factory=list)


def extract_category_block(text: str, category_name: str) -> str | None:
    """`*[카테고리]*` 헤더 뒤부터 다음 `*[...]*` 또는 EOF까지의 본문을 반환."""
    pattern = rf"\*\[{re.escape(category_name)}\]\*"
    match = re.search(pattern, text)
    if not match:
        return None
    start = match.end()
    next_header = re.search(r"\*\[[^\]]+\]\*", text[start:])
    end = start + next_header.start() if next_header else len(text)
    return text[start:end]


def check_item(text: str, rule: dict) -> float:
    """단일 rubric 항목 채점. 1.0/0.5/0.0 반환."""
    score = 0.0

    patterns_all = rule.get("patterns_all")
    patterns_any = rule.get("patterns_any")
    patterns_none = rule.get("patterns_none")
    patterns_each = rule.get("patterns_each")
    patterns_any_bonus = rule.get("patterns_any_bonus")
    category_block_check = rule.get("category_block_check")

    if category_block_check:
        # 카테고리 블록 내에 특정 키워드가 있어야 통과
        cat_name = category_block_check["expected_category"]
        keyword = category_block_check["keyword_in_block"]
        block = extract_category_block(text, cat_name)
        if block and re.search(keyword, block, re.IGNORECASE):
            return 1.0
        return 0.0

    if patterns_each:
        # 각 패턴별 부분 점수
        hits = sum(1 for p in patterns_each if re.search(p, text, re.IGNORECASE))
        total = len(patterns_each)
        score = round(hits / total, 2)
        return score

    passed = True

    if patterns_all:
        if not all(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in patterns_all):
            passed = False

    if patterns_any:
        if not any(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in patterns_any):
            passed = False

    if patterns_none:
        if any(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in patterns_none):
            passed = False

    if passed:
        score = 1.0

    # any_bonus는 patterns_all/any 충족 후 세부 보강 점수
    if score == 1.0 and patterns_any_bonus:
        if not any(re.search(p, text, re.IGNORECASE) for p in patterns_any_bonus):
            score = 0.5

    return score


def score_run(text: str, run_id: str, model: str) -> RunScore:
    scores: dict[str, float] = {}
    missing: list[str] = []
    hallucinations: list[str] = []

    for item_id, rule in RUBRIC_CHECKS.items():
        item_score = check_item(text, rule)
        scores[item_id] = item_score

        if item_id.startswith("A") and item_score < 1.0:
            missing.append(f"{item_id}: {rule['label']}")
        if item_id.startswith("C") and item_score < 1.0:
            hallucinations.append(f"{item_id}: {rule['label']}")

    total = round(sum(scores.values()), 2)
    return RunScore(run_id=run_id, model=model, scores=scores, total=total, missing=missing, hallucinations=hallucinations)


def parse_run_file(path: Path) -> tuple[str, str]:
    """파일명에서 model 추출, 본문 반환."""
    name = path.stem  # e.g., sonnet-001
    model = name.split("-")[0]
    text = path.read_text(encoding="utf-8")
    return model, text


def write_csv(scores: list[RunScore], out_path: Path) -> None:
    header = ["run_id", "model"] + list(RUBRIC_CHECKS.keys()) + ["total"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for s in scores:
            row = [s.run_id, s.model] + [s.scores.get(k, 0) for k in RUBRIC_CHECKS] + [s.total]
            writer.writerow(row)


def write_summary(scores: list[RunScore], out_path: Path) -> None:
    by_model: dict[str, list[RunScore]] = {}
    for s in scores:
        by_model.setdefault(s.model, []).append(s)

    lines: list[str] = ["# Regression Test Summary\n"]
    lines.append(f"- Total runs: {len(scores)}")
    lines.append(f"- Models: {sorted(by_model.keys())}\n")

    lines.append("## 모델별 통계 (만점 15)\n")
    lines.append("| 모델 | runs | 평균 | 표준편차 | 최저 | 최고 |")
    lines.append("|------|------|------|---------|------|------|")
    for model, runs in sorted(by_model.items()):
        totals = [r.total for r in runs]
        avg = round(statistics.mean(totals), 2)
        stdev = round(statistics.stdev(totals), 2) if len(totals) > 1 else 0.0
        lines.append(f"| {model} | {len(runs)} | {avg} | {stdev} | {min(totals)} | {max(totals)} |")
    lines.append("")

    lines.append("## 누락 Top-10 (전체 합산)\n")
    missing_counter: Counter = Counter()
    for s in scores:
        for m in s.missing:
            missing_counter[m] += 1
    for label, cnt in missing_counter.most_common(10):
        lines.append(f"- ({cnt}회) {label}")
    lines.append("")

    lines.append("## 환각 Top-10 (전체 합산)\n")
    hal_counter: Counter = Counter()
    for s in scores:
        for h in s.hallucinations:
            hal_counter[h] += 1
    if not hal_counter:
        lines.append("- (없음)")
    for label, cnt in hal_counter.most_common(10):
        lines.append(f"- ({cnt}회) {label}")
    lines.append("")

    lines.append("## 항목별 통과율 (모델별)\n")
    item_ids = list(RUBRIC_CHECKS.keys())
    header = "| 항목 | " + " | ".join(sorted(by_model.keys())) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(by_model) + 1))
    for item_id in item_ids:
        row = [f"{item_id} {RUBRIC_CHECKS[item_id]['label']}"]
        for model in sorted(by_model.keys()):
            runs = by_model[model]
            pass_rate = round(sum(r.scores.get(item_id, 0) for r in runs) / len(runs) * 100, 1)
            row.append(f"{pass_rate}%")
        lines.append("| " + " | ".join(row) + " |")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: uv run python tests/regression/scripts/score_runs.py <runs_dir>")
        return 2

    runs_dir = Path(sys.argv[1])
    if not runs_dir.exists():
        print(f"Error: {runs_dir} does not exist")
        return 1

    run_files = sorted(runs_dir.glob("*.txt"))
    if not run_files:
        print(f"Error: no .txt run files in {runs_dir}")
        return 1

    scores: list[RunScore] = []
    for path in run_files:
        model, text = parse_run_file(path)
        scores.append(score_run(text, run_id=path.stem, model=model))

    write_csv(scores, runs_dir / "scores.csv")
    write_summary(scores, runs_dir / "summary.md")

    print(f"✅ Scored {len(scores)} runs")
    print(f"   CSV:     {runs_dir / 'scores.csv'}")
    print(f"   Summary: {runs_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
