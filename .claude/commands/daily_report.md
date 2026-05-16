Confluence 주간 데일리 페이지를 읽고 C-Level 보고용 형식으로 정리합니다.

## 입력 파라미터
- `$ARGUMENTS`: `SPACE_KEY "MENTION_USERS" [--date YYYY-MM-DD]` 형식
  - SPACE_KEY: Confluence 스페이스 키 (기본값: MAI)
  - MENTION_USERS: 지연/보류 시 멘션할 사용자 (선택)
  - --date YYYY-MM-DD: 리포트 대상 날짜 (선택). 지정하면 해당 날짜 기준으로 작업 내용을 추출합니다. 미지정 시 오늘 날짜 사용.
  - 예: `MAI "@홍길동 @김철수"` 또는 `MAI` 또는 `MAI "@홍길동" --date 2026-04-06`

## 실행 단계

### 1. 날짜 범위 계산 및 Confluence 페이지 읽기

**기준 날짜를 확인하고 이번 주 월요일~금요일 범위를 계산합니다:**
1. 기준 날짜 확인: `$ARGUMENTS`에 `--date YYYY-MM-DD`가 있으면 해당 날짜, 없으면 오늘 날짜 사용 (예: 2026-01-27, 월요일)
2. 이번 주 월요일 날짜 계산 (오늘이 월요일이면 오늘, 아니면 이번 주 월요일)
3. 이번 주 금요일 날짜 계산 (월요일 + 4일)
4. 페이지 제목 형식으로 변환:
   - 형식: `YYYY.MM.DD ~ MM.DD` (항상 MM.DD)
   - 예: 2026-01-27 ~ 2026-01-31 → `2026.01.27 ~ 01.31`
   - 예: 2026-03-30 ~ 2026-04-03 → `2026.03.30 ~ 04.03`

**`mcp__mcp-atlassian__confluence_get_page` 도구를 사용하여 페이지를 검색합니다:**
- `space_key`: $ARGUMENTS의 첫 번째 값 또는 기본값 `MAI`
- `title`: 위에서 계산한 페이지 제목 (예: "2026.01.27 ~ 31")
- `include_metadata`: true
- `convert_to_markdown`: true

### 2. 오늘 날짜 기준 작업 내용 추출
페이지 내용에서 **기준 날짜**(1단계에서 결정한 날짜, 예: 2026.01.27)에 해당하는 각 팀원별 작업 내용을 추출합니다:
- Done (완료)
- Doing (진행 중)
- ToDo (예정)
- 기타 (휴가, 반차 등) - **오늘 날짜에 해당하는 항목만** 포함. 휴가/반차 날짜가 오늘이 아닌 항목은 제외합니다.

**누락 금지 원칙 (Mandatory Coverage):**
- Confluence 본문에 기재된 모든 팀원의 모든 Done/Doing/ToDo 항목을 빠짐없이 추출합니다.
- 단일 티켓이거나 한 줄짜리 항목이라도 절대 누락하지 않습니다 (예: 단독 JIRA 티켓, 단일 ToDo 항목).
- "비즈니스 임팩트 중심" 지시는 표현 방식에만 적용하며, 항목 자체를 임의로 생략하는 근거가 되지 않습니다.

### 3. 제품/버전 식별

작업 항목을 제품별로 분류할 때 아래 우선순위를 따릅니다.

**1순위: Confluence 본문에서 제품-버전 태그 추출**
페이지 본문에 다음 형식이 있으면 해당 제품/버전으로 분류합니다:
- 리스트 헤더 형식: `* producta-v2.2.2` 또는 `* productb-v1.0.0` (하위 항목이 해당 제품/버전에 속함)
- 인라인 태그 형식: `[producta-v2.2.0] 작업 내용` 또는 `[productb-v1.0.0] 작업 내용`
- 제품명은 소문자, 버전은 `v` 접두사 포함 (예: `producta-v2.2.2`, `productb-v1.0.0`)

**2순위: JIRA 티켓 fix versions 조회 (1순위로 식별 안 된 항목만)**
Confluence 본문에 제품-버전 태그가 없는 작업 항목 중 JIRA 티켓이 언급된 경우:
- PROJ 스페이스의 티켓 → `ProductA` 제품, 티켓의 fix versions로 버전 확인
- SECONDARY 스페이스의 티켓 → `ProductB` 제품, 티켓의 fix versions로 버전 확인
- fix versions가 1개면 그대로 사용
- fix versions가 2개 이상이면: alpha/beta/rc 등 프리릴리즈 태그를 제외한 정식 버전 중 가장 높은 버전 사용. 정식 버전이 없으면 첫 번째 항목 사용
- 예: fix versions가 `2.2.2, 2.2.2-alpha1`이면 → `producta-v2.2.2` 사용 (정식 버전 우선)

**Hotfix 버전 분리 규칙:**
- fix versions에 `-h1`, `-h2` 등 hotfix 접미사가 있으면 **별도 카테고리**로 분리합니다.
- 예: `2.2.2-h1` → `producta-v2.2.2-h1` 카테고리 (운영 hotfix 가시성 확보 목적, minor 버전과 합치지 않음)
- 표기: `*[VC v2.2.2-h1]*`

**제품 독립 분리 규칙 (Strict Product Isolation):**
서로 다른 제품은 **절대 같은 카테고리로 묶지 않습니다**. 각 제품은 독립된 `*[제품명]*` 카테고리 블록을 가집니다.

| 제품 | 카테고리 | 설명 |
|------|---------|------|
| ProductA (main backend) | `*[ProductA]*`, `*[ProductA v2.x.x]*` | PROJ JIRA 스페이스 + JIRA summary prefix `[ProductA]`, `[ProductA-BE]` |
| ProductSim (Simulator) | `*[ProductSim]*` | JIRA summary prefix `[ProductSim]` |
| ProductB (Secondary product) | `*[ProductB]*`, `*[ProductB v1.x.x]*` | SECONDARY JIRA 스페이스 + JIRA summary prefix `[ProductB]` |

> **Adapt to your environment**: replace product names (ProductA/Sim/B), JIRA spaces (PROJ/SECONDARY), and prefix patterns to match your organization.

**금지 사례 (절대 합치지 않음):**
- ❌ `*[ProductA]*` 카테고리 안에 ProductSim 작업을 넣음
- ❌ `*[ProductA]*` 카테고리 안에 ProductB 작업을 넣음
- ❌ 한 카테고리 블록에 두 제품의 _완료_ 항목 혼재

**올바른 출력 예시:**
```
*[ProductA]*
_진행 중_
• ... (ProductA 작업만)
───────────────────
*[ProductSim]*
_완료_
• ... (ProductSim 작업만)
```

**판정 기준:**
- 한 제품의 작업이 다른 제품 카테고리 안에 포함되면 카테고리 오류로 본다.
- ProductSim 작업이 1건이라도 있으면 `*[ProductSim]*` 카테고리 블록을 반드시 별도로 출력.

**3순위: 키워드 기반 분류 (위 두 방법으로 식별 안 된 항목)**
제품/버전 태그도 없고 JIRA 티켓도 없는 항목은 작업 내용의 키워드로 분류합니다:
- 운영 키워드 (배포, 모니터링, 장애, 핫픽스, 서버, 인프라, CS, 문의 대응, 점검) → `[운영]`
- 리서치/문서 키워드 (리서치, 조사, PoC, POC, 문서화, 위키, 스터디, 세미나, 컨퍼런스, 상위기획) → `[기술 리서치/문서화]`
- 기술 개선 키워드 (리팩토링, 테스트, 성능 개선, 마이그레이션, 업그레이드, CI/CD, 의존성, dependabot, 보안 취약점, Trivy) → `[기술 개선]`
- 위 키워드에 해당하지 않으면 → `[기타]`

**카테고리 판정 우선순위 (혼합 키워드 처리):**
- 한 항목이 여러 키워드에 매칭되면, 다음 우선순위로 단일 카테고리에 배정합니다: `제품/버전 > 운영 > 기술 개선 > 기술 리서치/문서화 > 기타`
- 예: "Trivy PoC 미팅" → `[기술 개선]` (Trivy 우선)
- 예: "권한 설정 PoC 미팅" → `[기술 리서치/문서화]` (PoC + 기획 단계)
- 예: "권한 설정 정책 구현 POC" → 코드 변경/구현 단계면 해당 제품 카테고리, 기획/탐색 단계면 `[기술 리서치/문서화]`

**제품명 표기 규칙:**
- 리포트에서 제품명은 대문자로 표기: `[ProductA v2.2.2]`, `[ProductB v1.0.0]`
- 예시: `*[ProductA v2.2.2]*`, `*[ProductB v1.0.0]*`, `*[운영]*`, `*[기타]*`

### 4. sequential-thinking MCP를 활용한 분석
`mcp__sequential-thinking__sequentialthinking` 도구를 사용하여 다음을 분석합니다:
- 위 3단계에서 식별한 제품/버전별로 작업 항목 분류
- 일정 지연 여부 판단
- 담당자별 작업 매핑
- 리스크/이슈 식별

### 5. C-Level 보고용 형식으로 정리 (슬랙 호환)
다음 형식으로 최종 보고서를 작성합니다.
**중요: 슬랙에 복붙할 수 있도록 마크다운 테이블 사용 금지. 리스트 형태로만 작성.**

```
*📊 일정 요약*

• ✅ [작업 내용] - [담당자명]
• 🔄 [작업 내용] - [담당자명]
• ⚠️ [작업 내용] - [담당자명] (지연 사유: [사유])
───────────────────
*📋 금일 업무 요약*

*[제품명]*

_완료_
• [작업 내용] - [담당자명]

_진행 중_
• [작업 내용] - [담당자명]
───────────────────
*[제품명]*

_완료_
• [작업 내용] - [담당자명]

_진행 중_
• [작업 내용] - [담당자명]
───────────────────
*📌 기타*
• 🏖️ [휴가/반차 유형] - [담당자명]
───────────────────
⚠️ 지연/보류 항목이 있어 공유드립니다.
[MENTION_USERS]
```

**참고**:
- 지연(⚠️) 또는 보류/대기(⏸️) 항목이 없는 경우 마지막 멘션 섹션은 생략합니다.
- `[MENTION_USERS]`는 $ARGUMENTS의 두 번째 값으로 대체합니다. (예: "@홍길동 @김철수")
- 멘션 사용자가 제공되지 않은 경우 멘션 섹션 전체를 생략합니다.

## 포맷 규칙

### 상태 이모티콘 (판단 기준)

아래 순서대로 첫 번째로 매칭되는 상태를 적용합니다:

1. 🏖️ 휴가/반차 — Confluence에 휴가/반차로 명시된 경우
2. ⏸️ 보류/대기 — Confluence에 "보류", "대기", "블로커" 등으로 명시된 경우
3. ✅ 완료 — Confluence 상태가 Done인 항목만. Doing/ToDo 항목에 절대 사용 금지
4. ⚠️ 지연 — Confluence 또는 JIRA에 명시된 마감일을 초과한 경우만
5. 🔄 진행 중 — 위 어디에도 해당하지 않는 모든 Doing/ToDo 항목

**중요**: 마감일이 Confluence/JIRA에 명시되지 않은 항목은 절대 ⚠️로 판단하지 않습니다. 마감일 없음 = 🔄 진행 중.

### 제품명 표기
- 제품명은 반드시 *[제품명]* 형식으로 표기 (Bold + 대괄호)
- 제품/버전이 식별된 경우: *[VC v2.2.2]*, *[ER v1.0.0]* (대문자 제품명 + 버전)
- 기타 분류: *[운영]*, *[기술 리서치/문서화]*, *[기타]*

### 구분선
- 섹션 구분은 `───────────────────` 사용

## 출력 규칙
- **최종 보고서만 출력하세요.** 중간 분석 과정, 데이터 정리 테이블, 상태 메시지(예: "JIRA 티켓 정보를 확인했습니다", "분석하겠습니다") 등은 절대 출력하지 마세요.
- 출력은 반드시 `📊 일정 요약`으로 시작해야 합니다. 그 앞에 어떤 텍스트도 포함하지 마세요.

### _예정_ 섹션 출력 규칙 (Mandatory Future-Section)
ToDo 항목 처리 정책을 엄격히 적용합니다.

**필수 출력 원칙:**
- Confluence 본문에 **ToDo 항목이 1건이라도 존재**하면, 해당 카테고리 블록에 `_예정_` 서브섹션을 **반드시 출력**합니다.
- 단순히 "C-Level은 디테일 불필요" 라는 이유로 _예정_ 섹션을 통째로 생략하면 안 됩니다.
- ToDo가 정말로 0건일 때만 _예정_ 서브섹션을 생략합니다.

**출력 형식:**
```
*[카테고리]*

_완료_
• ...

_진행 중_
• ...

_예정_
• [작업 내용] - [담당자명]
```

**판정 기준:**
- Confluence 본문에 명시된 ToDo 항목이 출력에 없으면 누락으로 본다.
- 예: Eve ToDo에 `ModuleX 개발`이 있으면 → 출력에 `_예정_` 섹션 + `ModuleX 개발 - Eve` 필수.
- 카테고리 분류는 ToDo도 동일하게 적용 (ModuleX은 키워드상 `[기타]` 또는 `[기술 개선]`).

## 주의사항
- C-Level이 볼 문서이므로 디테일한 내용보다 **작업 내용, 일정, 담당자, 지연 여부**에 집중
- 일정 요약을 **가장 먼저** 표시하여 한눈에 상태 파악 가능하도록 함
- **슬랙 호환 필수**: 마크다운 테이블(|---|) 사용 금지, 리스트(•) 형태로만 작성
- 슬랙 굵은 글씨는 *텍스트*, 기울임은 _텍스트_ 형식 사용
- **지연/보류 알림**: ⚠️, ⏸️ 상태 항목이 있고 멘션 사용자가 제공된 경우, 리포트 하단에 해당 사용자 멘션 추가

### JIRA 티켓 표현 규칙 (Source-of-Truth Policy)
모델별 표현 편차를 막기 위해 아래 규칙을 엄격히 따릅니다.

**허용 (DO):**
- JIRA 티켓 번호 자체(PROJ-XXXX)는 출력에서 생략
- JIRA **summary 필드**의 핵심 명사구만 사용. 대괄호 prefix(`[ProductA]`, `[ProductSim]`, `[ProductA-BE]`)는 제거
- summary가 길면 **한 줄 ≤ 60자**로 압축. 핵심 동작·대상만 남김
  - 예: `[ProductA] OrderItem이 삭제 또는 변경되어 범위 처리에 포함되지 않는 경우...` → `OrderItem 범위 처리 개선`
  - 예: `[ProductA-BE] report 생성 기능 개선` → `Report 생성 기능 개선`
  - 예: `[ProductSim] input-A, input-B 입력 리팩토링` → `input-A/input-B 입력 리팩토링`

**금지 (DON'T):**
- JIRA **description** 본문(AS-IS / TO-BE / 브랜치명 등) 인용 금지
- summary에 없는 기술 스택, 구현 방식, 브랜치명을 임의로 추가 금지
- Confluence 본문에 없고 JIRA에도 없는 작업은 **절대 추가 금지** (환각 방지)

**구체적 금지 키워드 (Description Block List):**
JIRA description의 다음 표현은 **출력에 절대 포함하지 않습니다**. 이들은 description 본문에서 가져온 것임이 명백한 흔적입니다.

| 카테고리 | 금지 키워드 (예시) |
|---------|------------|
| 서비스/모듈 분리명 | `ReportService`, `ReportServiceClient` 등 별도 서비스 이름 (단, Confluence 본문에 직접 명시되면 예외) |
| 구현 스택 | `Playwright`, `Chromium`, `FastAPI`, `asyncio`, `background_tasks` 등 description에만 등장하는 기술 스택 |
| 구조 키워드 | `AS-IS`, `TO-BE`, `feature/*` 브랜치명, `app-backend`, `monorepo` 등 |
| 인프라/배포 | `Docker 이미지 크기`, `CPU/메모리 점유`, `리소스 점유` 등 description의 비교 문구 |

> Adapt the block list to your project: list keywords that appear in JIRA descriptions but not in Confluence daily reports.

**판정 기준:**
- 위 키워드가 출력에 1개라도 등장하면 description 인용으로 본다 (C1 0점).
- 단, **해당 키워드가 Confluence 본문에 직접 명시**되어 있으면 인용이 아닌 정상 활용 (예외 허용).
- 예: David의 Confluence sub-bullet에 `helm`이 있으면 → `helm` 출력 가능. 하지만 `ReportService`는 Confluence에 없고 JIRA description에만 있으므로 → 출력 금지.

**모호한 경우:**
- summary가 너무 짧아 의미 전달이 부족하면 Confluence 본문의 sub-bullet 내용을 1줄로 압축해 보완 가능
  - 예: Confluence에 "예외케이스 통과, 테스트코드 추가" 라고 명시된 경우 그대로 활용

### Confluence Sub-bullet 고유명사 보존 규칙 (Mandatory Preservation)
60자 압축 규칙에도 불구하고 **아래 종류의 고유명사는 반드시 원문 그대로 보존**합니다.

**보존 대상:**
- 클래스/엔티티/모듈명: `FeatureRecord`, `SessionStatusHistory`, `OrderItem` 등 CamelCase 식별자
- 처리 프로세스명, 도메인 개념명: `처리 프로세스`, `범위 처리` 등 Confluence에 명시된 도메인 용어
- 기술 키워드: `웹푸시 알람`, `소속 프리셋`, `helm` 등 작업 맥락에 핵심인 명사구
- PR/이슈 ID 또는 수량: `PR 4건`, `(#6625, #6624, #6623, #6617)` 등

**보존 방법:**
- 60자 압축 시 동사·조사·중복 형용사만 제거하고, 위 고유명사는 그대로 유지
- 압축으로 인해 클래스명이 잘리거나 누락되면 **압축을 포기하고** 풀어쓴다 (60자 초과 허용)
- 예: Alice의 Confluence sub-bullet에 `FeatureRecord, SessionStatusHistory, 처리 프로세스`가 명시되면 → 모두 출력에 포함
  - GOOD: `FeatureService 문서화 (FeatureRecord, SessionStatusHistory, 처리 프로세스)`
  - BAD: `FeatureService 문서화` (세부 누락 → 0점)

**판정 기준:**
- Confluence 본문의 sub-bullet에 명시된 고유명사 중 **하나라도 출력에 빠지면 누락**으로 본다.
- "C-Level은 디테일 불필요"라는 지시는 **장황한 설명 제거**에 적용하고, **고유명사 제거**에는 적용하지 않는다.
