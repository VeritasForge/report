---
name: prompt-regression-testing
description: Use when LLM 프롬프트(slash command, system prompt 등)를 변경한 뒤 정확도 회귀를 정량 측정해야 할 때, 또는 sonnet/haiku/opus 등 모델 간 정확도·일관성·비용을 비교하여 운영 모델을 결정해야 할 때. 단일 dry-run 비교만으로는 LLM 비결정성 때문에 신뢰할 수 없으므로 반복 실행 + 자동 채점 + 베이스라인 비교가 필요한 경우.
---

# Prompt Regression Testing

## Overview

**프롬프트 회귀 테스트는 코드 회귀 테스트의 LLM 버전이다.** 프롬프트는 코드와 같지만 출력이 비결정적이므로, 같은 입력으로 N회 실행한 통계적 분포를 ground truth + rubric으로 채점하고, 이전 베이스라인과 비교하여 변화량(Δ)을 정량화한다.

핵심 원칙: **단일 dry-run 비교는 신뢰할 수 없다.** 모델별 5-10회 + 자동 채점 + 베이스라인 비교가 최소 조건.

## When to Use

- 프롬프트(`.claude/commands/*.md`, system prompt 파일) 수정 후 회귀 여부 확인
- 모델 변경 결정 (sonnet → haiku, opus → sonnet 등) 시 정량 근거 필요
- "환각인지 vs 정답인지" 의심 발생 시 ground truth 대조 필요
- 모델 출력의 변동성/일관성(표준편차) 측정 필요
- LLM 비결정성으로 1회 실행 결과를 신뢰할 수 없을 때

## When NOT to Use

- 일회성 실험 (재현 의도 없음) → 그냥 dry-run 1회로 충분
- Ground truth 자체가 불확실한 작업 (창작, 브레인스토밍 등) → LLM-as-Judge가 더 적합
- 비용 제약으로 5회 미만만 가능 → 통계적 의미 부족, 정성 평가로 대체
- 검증 대상 프롬프트가 변경 빈도 낮음 (분기/년 1회) → ROI 부족

## Core Components (3개 동기화 필수)

```
fixtures/                    scripts/
├── ground_truth.json   ─┐   ├── run_regression.sh   (반복 실행)
└── rubric.md           ─┤   ├── score_runs.py       (자동 채점)
                         │   └── compare_runs.py     (베이스라인 비교)
                         │
                         └─→ 키워드 일관성이 깨지면 채점 신뢰성 0
```

**Iron Rule**: ground_truth.json의 `expected_*` 필드, rubric.md의 검증 항목, score_runs.py의 `RUBRIC_CHECKS` 정규식 — 이 3개의 키워드는 항상 동기화해야 한다. 한 곳만 바꾸면 다른 곳이 silently 망가진다.

## Workflow: RED → GREEN → REFACTOR (코드 TDD와 동일)

### RED: 베이스라인 측정
1. 현재 프롬프트로 baseline 디렉토리에 N회 dry-run 저장
2. ground_truth + rubric으로 채점
3. 시스템적 누락 패턴 식별 (예: "A2 항목이 90% 누락")

### GREEN: 프롬프트 패치 + 재회귀
1. 베이스라인 누락 패턴에 맞춰 프롬프트 패치 (예시: "특정 명사 보존 규칙 추가")
2. 새 timestamp 디렉토리에 동일 N회 dry-run
3. `compare_runs.py`로 베이스라인 ↔ 신규 변동표 출력
4. 목표 점수 달성 시 GREEN, 미달 시 추가 패치

### REFACTOR: 모델 결정 + 운영 반영
1. 모델별 평균 + 표준편차 → 운영 모델 결정
2. `.env`의 `CLI_MODEL` 또는 system config에 반영
3. 베이스라인 디렉토리 보존 (다음 패치 비교용)

## Step-by-Step (신규 프로젝트에 셋업)

1. **디렉토리 구조 생성**
   ```bash
   mkdir -p tests/regression/{fixtures,scripts,runs}
   cp <skill_dir>/templates/* tests/regression/scripts/  # 5개 템플릿
   cp <skill_dir>/templates/ground_truth.example.json tests/regression/fixtures/ground_truth_YYYY_MM_DD.json
   cp <skill_dir>/templates/rubric.example.md tests/regression/fixtures/rubric.md
   ```

2. **`.gitignore`에 `tests/regression/runs/` 추가** (회귀 결과는 큰 텍스트 파일 + 잦은 추가 → commit 부적합)

3. **Ground truth 작성** — 실제 대상 입력(예: 특정 날짜의 Confluence 페이지)에 대해 기대 출력의 핵심 명사·카테고리를 명시
   - 회사 정보가 포함되면 별도 `ground_truth_*.local.json`으로 분리하고 `.gitignore`에 추가

4. **Rubric 정의** — 검증 항목을 A/B/C/D 카테고리로 구조화
   - A: 항목 커버리지 (필수 출력 사실들)
   - B: 카테고리 분류 정확도
   - C: 환각/오류 (감점)
   - D: 형식 (슬랙 호환, 헤더 등)

5. **Scorer 동기화** — `score_runs.py`의 `RUBRIC_CHECKS` 정규식이 rubric.md와 일치하는지 확인

6. **첫 회귀 실행 (baseline)**
   ```bash
   make regression-run DATE=YYYY-MM-DD   # 또는 ./scripts/run_regression.sh
   make regression-score RUNS_DIR=<dir>
   ```

7. **베이스라인 디렉토리 명명** — `runs/baseline_v1_pre_patch/`처럼 의도 표현 (timestamp만 쓰면 어떤 라운드인지 헷갈림)

8. **프롬프트 패치 → 재회귀 → 비교**
   ```bash
   make regression DATE=YYYY-MM-DD   # 새 timestamp dir 생성
   make regression-compare BASE=runs/baseline_v1_pre_patch NEW=runs/<new_timestamp>
   ```

## Cost & Time Budget (실측 기준)

| 모델 | 1회 소요 | 권장 반복 | 비용 (relative) | 비고 |
|------|---------|----------|----------------|------|
| Haiku | 1.5분 | 10회 | 1× | 변동성 ↑, 비용 절감 우선일 때만 |
| **Sonnet** | **2분** | **10회** | ≈8× | **운영 권장 (가성비 sweet spot)** |
| Opus | 4분 | 3회 | ≈40× | 비싼 baseline + 1/3 인프라 실패 관측 |

**전체 23회(Sonnet 10 + Haiku 10 + Opus 3) 실행 시간 ≈ 60분.** 30초/회로 추정하지 말 것.

비용 절감: 1차 패치 결과 본 뒤 Sonnet 만점이면 Opus 생략 가능.

## Common Mistakes (Reality)

| 실수 | 결과 | 회피 방법 |
|------|------|----------|
| 단일 dry-run으로 모델 결정 | LLM 비결정성 무시 → 잘못된 결정 | 최소 5회, 권장 10회 반복 |
| "환각"으로 즉시 단정 | JIRA/외부 시스템 본문 충실 반영을 환각으로 오판 (70% 케이스) | ground truth에 JIRA summary 필드 포함 + 환각 판정 전 본문 1회 조회 |
| Rubric 정규식이 컨텍스트-blind | `[A]` 카테고리 안에 잘못 분류해도 키워드만 있으면 통과 | `category_block_check` 같은 블록 단위 매칭 패턴 사용 |
| 모델 실패 vs 인프라 실패 혼동 | Opus rate limit → 점수 0점 → 모델 약점으로 오해 | output 크기 < 100 bytes면 인프라 실패로 마크 + 통계 제외 |
| fixture/rubric/scorer 동기화 누락 | 한 곳 수정 후 다른 곳 silently 망가짐 | 3개 파일을 동시 수정. 변경 시 한 묶음 commit |
| `runs/`를 commit | 큰 텍스트 파일 + 잦은 추가로 repo 비대 | `.gitignore`에 `tests/regression/runs/` 추가 |
| 회사 정보를 fixture에 직접 작성 | GitHub push 차단 | example fixture(공유용) + .local fixture(운영용) 분리 |
| 패치 1회로 결정 종료 | 다음 라운드에서 더 큰 개선 가능성 무시 | RED → GREEN → REFACTOR 2-3 라운드 반복 |
| 시간 30초/회 추정 | 사용자에게 잘못된 ETA 안내 | 실측 평균 2분/회 사용 |

## Red Flags (Stop and Reconsider)

- "1회 실행 결과가 명확하니 결론 내리자" → 비결정성 무시
- "이건 환각이다" (ground truth 미대조) → JIRA/외부 시스템 본문 미확인 가능성
- "이 항목은 채점 통과지만 출력은 잘못됐다" → 정규식 너무 관대 (refactor 필요)
- "Opus가 약하네" (실패 1회 후) → 인프라 실패 vs 모델 약점 구분 안 됨

## Generalization Pattern (회사 정보 분리)

GitHub 공유와 운영 사용을 동시에 만족시키는 패턴:

```
tests/regression/fixtures/
├── ground_truth.example.json    ← Git 커밋 (가상 데이터: Alice/ProductA/PROJ-XXX)
└── ground_truth.local.json      ← .gitignore (실제 운영 데이터)
```

`.gitignore`:
```
tests/regression/runs/
tests/regression/fixtures/*.local.json
tests/regression/fixtures/*.local.md
```

운영 시: `score_runs.py`의 `RUBRIC_CHECKS` 정규식만 회사 키워드로 갈아끼우면 동작. 가상 example 패턴은 그대로 유지하여 새 사람도 즉시 셋업 가능.

## Quick Reference

```bash
# 1차 회귀 (베이스라인)
make regression-run DATE=YYYY-MM-DD
mv tests/regression/runs/YYYYMMDD_HHMMSS tests/regression/runs/baseline_v1
make regression-score RUNS_DIR=tests/regression/runs/baseline_v1

# 프롬프트 패치 → 재회귀 → 비교
# (.claude/commands/*.md 수정 후)
make regression DATE=YYYY-MM-DD   # 새 dir 자동 생성
make regression-compare BASE=tests/regression/runs/baseline_v1 NEW=tests/regression/runs/<new>

# 인프라 실패 출력 식별 (크기 < 100 bytes)
find tests/regression/runs/<dir>/ -name "*.txt" -size -100c
```

## Templates

`templates/` 디렉토리 5개 파일을 그대로 복사하면 셋업 가능:

| 파일 | 역할 | 대상 위치 |
|------|------|----------|
| `ground_truth.example.json` | Ground truth fixture 예시 | `tests/regression/fixtures/ground_truth_YYYY_MM_DD.json` |
| `rubric.example.md` | 평가 루브릭 예시 (15점 만점) | `tests/regression/fixtures/rubric.md` |
| `run_regression.sh` | N회 dry-run 자동화 | `tests/regression/scripts/run_regression.sh` |
| `score_runs.py` | 자동 채점기 (rule-based regex) | `tests/regression/scripts/score_runs.py` |
| `compare_runs.py` | 베이스라인 ↔ 신규 비교 | `tests/regression/scripts/compare_runs.py` |

각 템플릿은 가상 데이터(Alice/Bob/ProductA/PROJ-XXX)로 작성되어 있으며, 실제 환경에 맞춰 키워드와 항목을 조정하여 사용한다.

## Real-World Impact

이 워크플로우로 본 프로젝트의 daily_report 프롬프트를 검증한 결과:
- Sonnet 베이스라인 **12.5/15** → P1~P4 패치 후 **15.0/15 (10회 모두 만점, stdev 0)**
- Haiku 베이스라인 **7.17/15** → 패치 후 **12.14/15**
- "환각으로 보였던" 출력의 70%가 사실은 JIRA summary 충실 반영으로 판명
- Opus의 1/3 일관된 실패는 모델 약점이 아닌 CLI 인프라 실패로 판명
- 운영 모델 결정: Opus → Sonnet (비용 1/5, 동급 정확도)
