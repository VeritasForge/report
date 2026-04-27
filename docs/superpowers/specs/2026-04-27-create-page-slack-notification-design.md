# Create Page Slack Notification — Design Spec

- **Date:** 2026-04-27
- **Author:** brainstorming session (superpowers:brainstorming)
- **Status:** Approved (post review v2 — awaiting implementation plan)
- **Review:** ce-doc-review v1 → 15 findings 반영하여 v2로 갱신

## 1. Background

`REPORT_MODE=create_page` 모드는 매주 월요일 07:00에 Cronicle로 실행되어, 이전 주 Confluence 페이지를 복사해서 새 주간 페이지를 만든다. 현재는 결과를 stdout에만 출력하므로 운영자가 매번 Cronicle 로그를 확인해야 한다.

이 설계는 페이지 생성 결과(성공/이미 존재/실패/예기치 않은 에러)를 별도의 Slack 채널로 푸시하여 운영 가시성을 높이는 것을 목적으로 한다. 기존 daily/weekly 보고서에서 사용하는 Slack 봇(`SLACK_TOKEN`)을 그대로 재사용하고, 채널만 분리한다.

## 2. Goals & Non-Goals

### Goals
- `create_page` 유스케이스 실행 시, **모든 결과**(성공/중복/명시적 실패/예기치 않은 예외)를 별도 Slack 채널로 알림 전송
- 케이스별로 시각적으로 구분되는 메시지 포맷 (✅ / ℹ️ / ❌)
- 알림 실패가 페이지 생성 결과를 오염시키지 않도록 격리 (try/except)
- 환경변수 미설정 시 알림은 스킵하되, 페이지 생성은 정상 동작
- A/B 케이스 URL 형식 일치 (어댑터 헬퍼로 통일)

### Non-Goals
- 새 Slack 봇 추가 (기존 봇 재사용)
- 멘션 기능 (실패 케이스 포함, 모든 케이스에서 멘션 없음)
- daily/weekly 보고서 알림 흐름 변경 (현 동작 유지)
- pydantic 도입 (표준 `enum.Enum`만 사용)
- `WeeklyPageConfig` (Confluence 페이지 책임 모델)에 Slack-only 필드 추가 — domain layering 회피

## 3. Decisions Summary

| 항목 | 결정 | 비고 |
|---|---|---|
| 알림 시점 | 성공 + 이미 존재 + 명시적 실패 + **예기치 않은 예외** | I1 반영: 모든 실패를 가시화 |
| 메시지 형식 | 케이스별 분기, 메인+thread 구조 | |
| 환경변수 | `SLACK_CHANNEL_CREATE_PAGE`, 미설정 시 스킵 | |
| 멘션 | 없음 (모든 케이스) | |
| 구현 방식 | UseCase에 `NotificationPort` 주입 (방식 A) | I4 반영: rationale 보강 |
| Status 표현 | semantic `Enum` (값: `'created'/'already_exists'/'failed'`), label은 별도 mapping | M3 반영: 도메인-프레젠테이션 분리 |
| `team_prefix` 전달 | `execute()` 시그니처에 `notification_prefix: str = ""` 인자 추가 (모델 변경 없음) | B2 반영: domain 침범 회피 |
| URL 추출 | `ConfluencePort.build_page_url(page_id)` 헬퍼 추가, A/B 모두 동일 형식 | I2 반영 |
| Skip guard | main.py에서 `notifier=None` 결정 (composition root) + SlackAdapter 내부 가드 (defense-in-depth) | M1 반영: 두 단계 의도된 중복 |

### Approach A 선택 Rationale (I4 보강)

> "UseCase에 notifier 주입" vs "Result 타입 반환 후 main.py에서 알림" 중 A를 선택.

- **A 채택 이유 (실질)**:
  1. `GenerateWeeklyReportUseCase`/`GenerateWeeklySummaryUseCase`가 모두 동일 패턴(use case가 notifier 주입받음)을 사용 중 → 일관성으로 인지 부담 감소
  2. main.py에 status 매핑/포맷팅 로직 중복 도입 회피 (Result 타입 반환 시 main.py가 status별 title/body 분기 필요)
  3. 알림은 use case 결과의 부수효과로 자연스러움 (use case가 결과를 직접 알고 있음)
- **B(Result 타입)를 다시 검토할 시점**: 향후 mode가 추가되어 동일 알림 패턴이 3회 이상 반복될 때, 또는 use case가 여러 notifier에 분기 알림을 보내야 할 때. 현시점에서는 over-engineering.

### NotificationPort 재사용 Rationale (I3 보강)

`NotificationPort.send(message, thread_message)`의 두 인자는 의미적으로 daily/weekly의 "thread reply"가 아닌 일반 "title + body" 패턴. create_page에서도 `(title, URL or error)`로 자연스럽게 매핑됨. 향후 Slack blocks/buttons/attachments가 필요해지면 그때 별도 `RichNotificationPort`를 추가하여 `SlackAdapter`가 두 포트를 구현하도록 하면 됨. 현시점에서는 새 포트 도입이 over-engineering.

## 4. Architecture

### Data Flow

```
main.py (create_page 분기)
  ├─ ConfluenceAdapter
  ├─ PageTransformer
  └─ SlackAdapter(token, channel=slack_channel_create_page)  ← Optional
        │
        ▼
  CreateWeeklyPageUseCase(confluence, transformer, notifier=Optional)
        │
        ├─ execute(config, target_date, notification_prefix="BE")
        │     │
        │     ├─ [정상 생성]    self._notify(CREATED, prefix, week, body=url)         → True
        │     ├─ [중복]         self._notify(ALREADY_EXISTS, prefix, week, body=url)  → True
        │     ├─ [source 없음]  self._notify(FAILED, prefix, week, body=err_msg)      → False
        │     └─ [예외 catch]   self._notify(FAILED, prefix, week, body=exc_msg)      → False
        │
        └─ self._notify는 try/except로 알림 격리 (실패 시 stderr 로그만)
```

### Files Changed

| 파일 | 변경 내용 |
|---|---|
| `src/domain/models.py` | `CreatePageStatus(str, Enum)` 추가 — 값은 semantic (`'created'`/`'already_exists'`/`'failed'`) |
| `src/application/ports.py` | `ConfluencePort`에 `build_page_url(page_id: str) -> str` 메서드 추가 |
| `src/application/create_page_use_case.py` | 생성자에 `notifier: NotificationPort \| None = None`, `execute()`에 `notification_prefix: str = ""` 인자 추가, 분기별 알림 호출 + 예외 catch 래핑 |
| `src/infrastructure/config.py` | `AppConfig.slack_channel_create_page: str = ""` 추가 + env 로딩 |
| `src/infrastructure/adapters/confluence_adapter.py` | `build_page_url(page_id: str) -> str` 메서드 추가 (A/B 케이스 통일) |
| `src/infrastructure/adapters/page_transformer.py` | **(선결 fix)** lines 23-26 (XML 표준 엔티티 보존 분기) 테스트 케이스 추가하여 100% 달성 |
| `src/main.py` | `create_page` 분기에서 `SlackAdapter` 인스턴스화(env 미설정 시 None) + use case에 `notification_prefix=config.report.team_prefix` 전달 |
| `README.md` | 새 env var 문서화 |
| `tests/unit/domain/test_create_page_status.py` | **신규 파일** — Enum 값 검증 |
| `tests/unit/application/test_create_page_use_case.py` | **기존 파일에 테스트 추가** — 알림 호출/예외 격리/notification_prefix |
| `tests/unit/infrastructure/test_config.py` | **기존 파일에 테스트 추가** — `SLACK_CHANNEL_CREATE_PAGE` env 로딩 |
| `tests/unit/infrastructure/test_page_transformer.py` | **기존 파일에 테스트 추가** — `_unescape_html_entities`의 XML 엔티티 보존 분기 (선결 100% 달성용) |

### Core Principles

- **NotificationPort 재사용** — 새 포트 추가 없음 (현 시그니처로 충분, I3 참조)
- **notifier는 Optional** — env var 미설정 시 main.py가 `None` 주입 → use case는 `if self._notifier:` 가드
- **알림 격리** — `try/except`로 알림 실패가 페이지 생성 결과를 오염시키지 않음
- **도메인 침범 금지** — `WeeklyPageConfig`에 Slack-only 필드 추가 안 함, `notification_prefix`는 `execute()` 인자
- **URL 형식 통일** — A/B 모두 `ConfluenceAdapter.build_page_url()` 사용

## 5. Message Format

### 공통

- 메인 메시지 = 제목 (한 줄)
- 스레드 메시지 = URL 또는 에러 사유
- 기존 `SlackAdapter.send(message, thread_message)` 시그니처 재사용
- `notification_prefix` 빈 문자열이면 `[BE]` 부분 생략

### 케이스별 포맷

**A. ✅ 새로 생성 성공 (`CreatePageStatus.CREATED`)**
```
메인:    [BE][26.04.28 ~ 05.02_WeeklyPage] ✅ 생성 완료
스레드:  https://your.atlassian.net/wiki/spaces/MAI/pages/1234567/...
```

**B. ℹ️ 이미 존재 (`CreatePageStatus.ALREADY_EXISTS`)**
```
메인:    [BE][26.04.28 ~ 05.02_WeeklyPage] ℹ️ 이미 존재
스레드:  https://your.atlassian.net/wiki/spaces/MAI/pages/1234567/...
```

**C. ❌ 실패 (`CreatePageStatus.FAILED`)** — 이전 주 페이지 미존재 OR 예기치 않은 예외
```
메인:    [BE][26.04.28 ~ 05.02_WeeklyPage] ❌ 생성 실패
스레드:  이전 주 페이지를 찾을 수 없습니다: 2026.04.21 ~ 04.25
        # 또는 예외인 경우:
        Unexpected error: ConnectionError: HTTPSConnectionPool(...timeout...)
```

### Status Enum (semantic 값 + 별도 label mapping)

```python
# src/domain/models.py
from enum import Enum

class CreatePageStatus(str, Enum):
    """create_page 유스케이스 실행 결과 (semantic identifier)"""
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"
    FAILED = "failed"


# Status별 표시 라벨 (presentation 분리)
STATUS_LABELS: dict[CreatePageStatus, str] = {
    CreatePageStatus.CREATED: "✅ 생성 완료",
    CreatePageStatus.ALREADY_EXISTS: "ℹ️ 이미 존재",
    CreatePageStatus.FAILED: "❌ 생성 실패",
}
```

> **Why semantic + label mapping?** Domain layer는 의미만 표현하고, Korean+emoji 같은 presentation 문자열은 별도 mapping으로 분리. 향후 다국어/다른 채널 포맷 대응이 가능하고, 도메인 모델이 UI 변경에 영향받지 않음.

### Title Builder (use case 내부)

```python
def _build_title(
    self,
    prefix: str,
    this_week: DateRange,
    status: CreatePageStatus,
) -> str:
    start = this_week.start.strftime('%y.%m.%d')
    end = this_week.end.strftime('%m.%d')
    bracket = f"[{prefix}]" if prefix else ""
    label = STATUS_LABELS[status]
    return f"{bracket}[{start} ~ {end}_WeeklyPage] {label}"
```

## 6. Error Handling & Edge Cases

| # | 시나리오 | 페이지 동작 | 알림 동작 | use_case 반환 |
|---|---|---|---|---|
| 1 | 정상 생성 | create OK | `CREATED` 알림 | `True` |
| 2 | 이미 존재 | skip | `ALREADY_EXISTS` 알림 | `True` |
| 3 | 이전 주 페이지 못 찾음 | abort | `FAILED` 알림 (사유: "이전 주 페이지를 찾을 수 없습니다: …") | `False` |
| 4 | confluence/transformer/네트워크 예외 | use case가 catch | `FAILED` 알림 (사유: 예외 클래스 + 메시지) | `False` |
| 5 | notifier=None (env 미설정) | 정상 동작 | 알림 스킵 | 위 1/2/3/4 그대로 |
| 6 | notifier 호출 중 예외 | 이미 발생한 결과 그대로 | stderr 로그만 출력 | 위 1/2/3/4 그대로 |

### 알림 격리 패턴 (use case 내부)

```python
def _notify(
    self,
    status: CreatePageStatus,
    prefix: str,
    this_week: DateRange,
    body: str,
) -> None:
    if self._notifier is None:
        return
    title = self._build_title(prefix, this_week, status)
    try:
        self._notifier.send(title, body)
    except Exception as e:
        # 알림 실패가 페이지 작업 결과를 오염시키지 않도록 격리.
        # status는 semantic identifier (e.g. "failed") — 운영자에게 보이는 라벨이 아님.
        print(f"WARNING: Slack notification failed (status={status.value}): {e}")
```

> **`status.value` 사용** — `(str, Enum)`이므로 `.value` 또는 `str(status)`가 semantic identifier 반환. 사용자 라벨은 `STATUS_LABELS[status]`로 별도.

### 예외 처리 패턴 (execute 메서드)

```python
def execute(
    self,
    config: WeeklyPageConfig,
    target_date: date | None = None,
    notification_prefix: str = "",
) -> bool:
    today = target_date or date.today()
    last_week = calculate_last_week_range(today)
    this_week = calculate_this_week_range(today)

    try:
        # ... 기존 페이지 조회/변환/생성 로직
        # 케이스별로 _notify 호출하고 True/False 반환
        return result_bool
    except Exception as e:
        # 예기치 않은 예외 (네트워크/HTTP/transformer 에러 등)
        # → FAILED 알림 보내고 False 반환 (raise 안 함 — Cronicle 잡은 종료 코드 0)
        body = f"Unexpected error: {type(e).__name__}: {e}"
        print(f"ERROR: create_page unexpected exception: {body}")
        self._notify(CreatePageStatus.FAILED, notification_prefix, this_week, body)
        return False
```

> **Why catch all and return False?** 
> - 운영 가시성 (Goals): 모든 실패를 채널에서 보이게 함
> - Cronicle 잡 종료 코드: 현재 코드도 use case가 False 반환 시 main이 stderr 출력만 하고 정상 종료 → 변경 없음
> - 기존 동작과의 호환: caller(main.py)는 boolean만 보면 됨

### Skip Guard (defense-in-depth, M1 명시)

두 단계 가드를 의도적으로 유지:

1. **main.py (composition root)**: env 미설정 시 `notifier=None` 주입 → use case가 알림 호출 자체를 스킵
2. **SlackAdapter (보조)**: token/channel이 비어 있으면 stderr 경고 후 return → 직접 호출 시(테스트, 다른 호출자)에도 안전

> 이는 의도된 중복임. 서로 다른 boundary에서 방어하므로 한쪽이 변경/제거되어도 다른 쪽이 fallback 역할. 단, 테스트 시 main.py 가드와 SlackAdapter 내부 가드를 별도 케이스로 검증.

### B-case URL 추출 (I2 반영)

`ConfluencePort.build_page_url(page_id: str) -> str` 헬퍼를 추가:

```python
# src/infrastructure/adapters/confluence_adapter.py
def build_page_url(self, page_id: str) -> str:
    """page_id로 Confluence 페이지 URL 빌드 (create/조회 일관)"""
    return f"{self._v2_base_url}/spaces/{...}/pages/{page_id}"
    # 정확한 형식은 create_page 반환값과 동일하게 맞춤
```

A 케이스(생성)는 `create_page()` 반환 URL 사용, B 케이스(중복)는 `build_page_url(existing_page['id'])` 사용 → **두 케이스 URL 형식 동일**.

> **세부 구현 시 결정**: `space_key`/`title`도 URL에 포함해야 한다면 `build_page_url(page_id, space_key, title)` 형태로 시그니처 확장. 단, B 케이스에서 use case는 `space_key`(`config.space_key`)와 `title`(`new_title`)을 모두 가지고 있으므로 인자 전달 가능.

### Use case 내부 필드 명명

생성자 인자 `notifier`는 **`self._notifier`** (private 언더스코어 프리픽스)로 저장. Python convention 따름.

```python
def __init__(
    self,
    confluence: ConfluencePort,
    transformer: PageTransformerPort,
    notifier: NotificationPort | None = None,
):
    self.confluence = confluence
    self.transformer = transformer
    self._notifier = notifier  # private — 내부 격리 헬퍼에서만 사용
```

> 기존 `confluence`/`transformer`는 외부에서 직접 접근 가능한 dependency, `_notifier`는 부수효과 전용 internal collaborator. 명명 차이가 곧 의도 차이.

### main.py 인스턴스화

```python
# create_page 분기 안
notifier = (
    SlackAdapter(token=config.slack_token, channel=config.slack_channel_create_page)
    if config.slack_channel_create_page and config.slack_token
    else None
)
use_case = CreateWeeklyPageUseCase(
    confluence=confluence,
    transformer=transformer,
    notifier=notifier,
)
success = use_case.execute(
    weekly_page_config,
    target_date=report_date,
    notification_prefix=config.report.team_prefix,
)
```

> **`config.report.team_prefix`를 명시적으로 전달**. `WeeklyPageConfig`에는 추가하지 않음 (Slack-only 정보가 Confluence 페이지 책임 모델에 침투하지 않도록).

## 7. Testing Strategy (TDD)

기존 `tests/unit/{domain,application,infrastructure}/` 구조 활용. **변경 영향 파일 + page_transformer.py 갭 모두 100% 커버리지**.

### Domain 레이어
**`tests/unit/domain/test_create_page_status.py`** (신규) — Enum 값/label 검증
- `CreatePageStatus.CREATED.value == "created"` 등 semantic 값 검증
- `STATUS_LABELS[CreatePageStatus.CREATED] == "✅ 생성 완료"` 등 label mapping 검증

### Application 레이어
**`tests/unit/application/test_create_page_use_case.py`** — 기존 파일에 테스트 케이스 추가:

| 테스트 | Given | When | Then |
|---|---|---|---|
| 성공 시 알림 전송 | source 존재, target 미존재, mock notifier | execute() | notifier.send() 호출, title에 `✅ 생성 완료` + thread에 URL |
| 중복 시 알림 전송 | source/target 모두 존재 | execute() | notifier.send() 호출, title에 `ℹ️ 이미 존재` + thread에 URL (build_page_url 호출 검증) |
| source 없음 실패 알림 | source 미존재 | execute() | notifier.send() 호출, title에 `❌ 생성 실패` + thread에 사유 |
| 예외 발생 시 FAILED 알림 | confluence가 raise | execute() | notifier.send() 호출, title에 `❌ 생성 실패` + thread에 예외 메시지, return False |
| notifier=None 알림 스킵 | notifier 미주입 | execute() | 어떤 알림도 호출되지 않음, 페이지 생성은 정상 |
| 알림 예외 격리 | notifier.send() raise | execute() | use case는 정상 boolean 반환, 예외 전파 X |
| notification_prefix 빈 값 | prefix="" | execute() | 제목에 `[BE]` 부분 생략 |
| notification_prefix 채워진 값 | prefix="BE" | execute() | 제목 시작이 `[BE]` |

### Infrastructure 레이어
**`tests/unit/infrastructure/test_config.py`** — 기존 파일에 추가:
- `SLACK_CHANNEL_CREATE_PAGE` env 설정 시 `slack_channel_create_page`가 채워짐
- 미설정 시 빈 문자열

**`tests/unit/infrastructure/test_page_transformer.py`** (선결 fix) — 기존 파일에 추가:
- `_unescape_html_entities`가 XML 표준 엔티티(`&amp;`, `&lt;`, `&gt;`, `&quot;`, `&apos;`)를 보존하고, 일반 HTML 엔티티(`&rarr;`, `&nbsp;`)는 유니코드로 변환하는 분기 검증 (lines 23-26)

### Note: ConfluenceAdapter 테스트
`pyproject.toml`에서 `confluence_adapter.py`는 coverage omit 대상 (실제 외부 API 호출, 테스트 어려움). `build_page_url` 추가도 동일 정책 적용 — 단위 테스트는 use case에서 mock으로 검증.

## 8. Completion Criteria

- [ ] `REPORT_MODE=create_page` 실행 시 `SLACK_CHANNEL_CREATE_PAGE` 채널에 케이스별 메시지 전송됨 (성공/중복/명시적 실패/예기치 않은 예외 모두 포함)
- [ ] A/B 케이스가 동일한 URL 형식으로 표시됨 (build_page_url 헬퍼 통일)
- [ ] `SLACK_CHANNEL_CREATE_PAGE` 미설정 시 알림 스킵, 페이지 생성은 정상 동작
- [ ] 알림 전송 실패 시 페이지 생성 결과의 boolean 반환값 변경되지 않음
- [ ] 예기치 않은 예외 발생 시 use case가 catch하여 `FAILED` 알림 + False 반환
- [ ] `uv run pytest --cov=src --cov-report=term-missing` 통과
- [ ] **전체 커버리지 100%** — 변경 파일 + 선결 fix(`page_transformer.py`) 포함
- [ ] `README.md`에 새 env var 문서화

## 9. Don'ts

- ❌ pydantic 도입 금지 → 표준 `Enum` 사용
- ❌ Domain 레이어에서 외부 라이브러리 import 금지 → `enum.Enum`만
- ❌ Domain 레이어에 presentation 문자열(emoji/Korean) 직접 노출 금지 → semantic 값 + 별도 label mapping
- ❌ `WeeklyPageConfig`에 `team_prefix` 등 Slack-only 필드 추가 금지 → `execute()` 인자로 전달
- ❌ `NotificationPort` 외 새 포트 추가 금지 (현시점) → 기존 포트 재사용
- ❌ `CreateWeeklyPageUseCase.execute()` 반환 타입 변경 금지 → boolean 유지, 알림은 부수효과
- ❌ 알림 예외를 raise 금지 → `try/except`로 흡수, stderr 로그만
- ❌ daily/weekly 보고서 흐름에 영향 주는 변경 금지
- ❌ `confluence_url`을 use case에 직접 노출 금지 → 어댑터 헬퍼 사용

## 10. Considerations

- **운영 가시성**: Cronicle 로그 확인 없이 채널만 봐도 매주 페이지 생성 상태 파악 가능 (모든 실패 모드 가시화)
- **Slack 토큰 만료 trade-off (M2)**: notifier 자체 실패는 stderr 로그로만 기록되고 silent. Slack 토큰 만료/대량 rate limit 같은 systemic failure는 운영자가 daily/weekly 보고서 미수신으로도 결국 인지 — 별도 모니터링 추가는 별도 과제. 본 spec에서는 페이지 생성 정확성 > 알림 신뢰성을 명시적으로 채택.
- **메시지 시각적 구분**: 이모지(✅/ℹ️/❌)로 케이스 즉시 식별 가능
- **URL 형식 통일**: A/B 케이스 모두 `build_page_url()` 사용 → 운영자가 클릭한 URL의 동작이 케이스별로 다르지 않음
- **두 단계 skip guard**: composition root + adapter 두 곳에서 방어 → 의도된 defense-in-depth, 둘 모두 단위 테스트로 검증
- **page_transformer.py 선결 fix**: lines 23-26 (XML 엔티티 보존 분기) 테스트 추가는 본 spec 작업의 일부로 수행 — 프로젝트 메모리(`project_coverage_100.md`) 의도에 맞춰 전체 100% 유지

## 11. Constraints

- 기존 Clean Architecture 의존성 방향 준수 (Domain → Application → Infrastructure)
- 기존 `@dataclass(frozen=True)` 패턴 일관성 유지 (`WeeklyPageConfig` 변경 없음)
- 기존 SlackAdapter 인터페이스 변경 금지 (`send(message, thread_message)`)
- 기존 NotificationPort 인터페이스 변경 금지
- Python 3.12+ 타입 힌트 스타일 유지
- 기존 5개 `test_create_page_use_case.py` 테스트 회귀 없음 (fixture 변경 없음)
- ConfluencePort에 `build_page_url` 추가는 인터페이스 확장이므로 기존 호출자 영향 없음 (default 메서드 아님)

## 12. Next Step

이 spec을 기반으로 `superpowers:writing-plans` 스킬로 구현 플랜을 작성한다. 플랜에는 CLAUDE.md 템플릿(완료조건/금지사항/고려사항/제약사항/스킬 검색/Task List)을 모두 포함한다.

**Task 순서 힌트** (writing-plans에서 상세화):
1. `page_transformer.py` lines 23-26 테스트 추가 (선결 fix, 100% 베이스라인 확보)
2. `CreatePageStatus` Enum + `STATUS_LABELS` 추가 (domain)
3. `ConfluencePort.build_page_url` 추가 + `ConfluenceAdapter` 구현 (인프라)
4. `AppConfig.slack_channel_create_page` + env 로딩
5. `CreateWeeklyPageUseCase` 시그니처 확장 + 예외 처리/알림 로직
6. `main.py` 조립 + `notification_prefix` 전달
7. README 문서 갱신
8. 전체 회귀 + 커버리지 100% 검증

---

## Review History

- **v1 (2026-04-27)**: 초안. brainstorming 결과.
- **v2 (2026-04-27)**: ce-doc-review 15 findings 반영. 주요 변경:
  - Status enum semantic 값으로 변경 + label mapping 분리 (B1, M3)
  - `team_prefix` → `notification_prefix` 인자 전달, `WeeklyPageConfig` 변경 안 함 (B2, B3)
  - 모든 예외를 use case가 catch하여 FAILED 알림 (I1)
  - `ConfluencePort.build_page_url` 헬퍼로 URL 통일 (I2)
  - page_transformer.py 선결 fix Task로 100% 보장 (B4)
  - Approach A / NotificationPort 재사용 rationale 보강 (I3, I4)
  - 두 단계 skip guard / swallow trade-off 명시 (M1, M2)
  - `self._notifier` 명명, 다이어그램 보강, 테스트 파일 신규/추가 명시 (F1-F4)
