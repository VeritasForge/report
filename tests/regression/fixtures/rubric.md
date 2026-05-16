# Daily Report 정확도 평가 루브릭 (Ground Truth: 2026-05-15)

> All names, project IDs, and domain terms in this rubric are synthetic. Adapt to your organization's data before running regression.

각 항목 1점, 부분 점수 0.5점. 총 만점 = 15점.

## A. 항목 커버리지 (8점)

| ID | 검증 항목 | 만점 | 채점 기준 |
|----|---------|------|----------|
| A1 | Alice — PROJ-1001 Doing 포함 | 1 | "OrderItem 범위" 또는 "FeatureService" 표현으로 출력에 포함 |
| A2 | Alice — FeatureService 문서화 세부(FeatureRecord/SessionStatusHistory/처리 프로세스) 중 1개 이상 언급 | 1 | 0.5점: 문서화 언급, 1점: 세부 명사 1개 이상 |
| A3 | Bob — PROJ-1002 Done 포함 (`[ProductSim]` 카테고리) | 1 | "input-A/input-B" 표현 + 카테고리 정확 |
| A4 | Charlie — PROJ-1003 Done 포함 (`[ProductA v2.2.2-h1]` 카테고리) | 1 | "timezone" 표현 + hotfix 별도 카테고리 |
| A5 | Charlie — 권한 POC Doing 포함 + 세부(웹푸시/소속) 중 1개 이상 | 1 | 권한 POC 항목 출력 + 세부 명사 1개 이상 |
| A6 | David — PROJ-1004 Doing 포함 (`[ProductA v2.3.0]` 카테고리, helm 변경 명시) | 1 | PR 리뷰 + helm 변경 + 정확한 카테고리 |
| A7 | Eve — Trivy 처리 + moduleA + PoC 미팅 모두 Done 포함 | 1 | 0.33점 × 3 항목, 합산 후 반올림 |
| A8 | Eve — ModuleX 개발 ToDo 포함 (`_예정_` 섹션) | 1 | _예정_ 섹션 출력 + ModuleX 항목 포함 |

## B. 카테고리 분류 정확도 (3점)

| ID | 검증 항목 | 만점 | 채점 기준 |
|----|---------|------|----------|
| B1 | `[ProductA v2.2.2-h1]` hotfix 별도 카테고리 사용 | 1 | hotfix를 minor 버전과 분리 |
| B2 | `[ProductSim]` 별도 카테고리 (ProductA와 혼합 금지) | 1 | Bob 작업을 [ProductA]에 합치면 0점 |
| B3 | 권한 POC를 `[기술 리서치/문서화]`에 분류 (Charlie, Eve) | 1 | [ProductA] 또는 [기술 개선]에 분류 시 0점 |

## C. 환각/오류 (2점, 감점 방식)

| ID | 검증 항목 | 만점 | 채점 기준 |
|----|---------|------|----------|
| C1 | JIRA description 본문 인용 없음 (ReportService/Playwright 등 description 키워드 미출현) | 1 | 출현 시 0점 |
| C2 | Confluence 본문에 없고 JIRA에도 없는 작업 추가 없음 | 1 | 무중생유 환각 발견 시 0점 |

## D. 형식 (2점)

| ID | 검증 항목 | 만점 | 채점 기준 |
|----|---------|------|----------|
| D1 | `📊 일정 요약`으로 시작 + 슬랙 호환 형식 (테이블 미사용) | 1 | 위반 시 0점 |
| D2 | 카테고리 헤더 `*[제품명]*` 형식 + 구분선 사용 | 1 | 위반 시 0점 |

## 점수 해석

| 점수 | 등급 | 의미 |
|------|------|------|
| 14–15 | A | 운영 투입 가능 |
| 12–13.5 | B | 경미한 수정 필요 |
| 10–11.5 | C | 프롬프트 보강 필요 |
| < 10 | D | 신뢰 불가 |

## 채점 출력 형식 (LLM-as-Judge)

```json
{
  "run_id": "sonnet-001",
  "model": "sonnet",
  "scores": {
    "A1": 1, "A2": 0.5, "A3": 1, "A4": 1, "A5": 1, "A6": 1, "A7": 1, "A8": 0,
    "B1": 1, "B2": 1, "B3": 0,
    "C1": 1, "C2": 1,
    "D1": 1, "D2": 1
  },
  "total": 12.5,
  "grade": "B",
  "missing_items": ["Eve ModuleX ToDo"],
  "hallucinations": [],
  "category_errors": ["Charlie 권한 POC을 [ProductA]에 분류"]
}
```
