# Create Page Slack Notification — Design Spec

- **Date:** 2026-04-27
- **Author:** brainstorming session (superpowers:brainstorming)
- **Status:** Approved (post review v3 — awaiting implementation plan)
- **Review:**
  - v1 → ce-doc-review (15 findings)
  - v2 → /rl-verify Iteration 1 (12 new findings: 1 BLOCKER + 5 IMPORTANT + 3 MINOR + 3 FYI)

## 1. Background

`REPORT_MODE=create_page` 모드는 매주 월요일 07:00에 Cronicle로 실행되어, 이전 주 Confluence 페이지를 복사해서 새 주간 페이지를 만든다. 현재는 결과를 stdout에만 출력하므로 운영자가 매번 Cronicle 로그를 확인해야 한다.

이 설계는 페이지 생성 결과(성공/이미 존재/실패/예기치 않은 에러)를 별도의 Slack 채널로 푸시하여 운영 가시성을 높이는 것을 목적으로 한다. 기존 daily/weekly 보고서에서 사용하는 Slack 봇(`SLACK_TOKEN`)을 그대로 재사용하고, 채널만 분리한다.

## 2. Goals & Non-Goals

### Goals
- `create_page` 유스케이스 실행 시, **모든 결과**(성공/중복/명시적 실패/예기치 않은 예외)를 별도 Slack 채널로 알림 전송
- 케이스별로 시각적으로 구분되는 메시지 포맷 (✅ / ℹ️ / ❌)
- 알림 실패가 페이지 생성 결과를 오염시키지 않도록 격리 (try/except)
- **단일 페이지 작업당 최대 1개 Slack 알림** (double notification 금지)
- 환경변수 미설정 시 알림은 스킵하되, 페이지 생성은 정상 동작
- A/B 케이스 URL 형식 일치 (어댑터 내부에서 구성)

### Non-Goals
- 새 Slack 봇 추가 (기존 봇 재사용)
- 멘션 기능 (실패 케이스 포함, 모든 케이스에서 멘션 없음)
- daily/weekly 보고서 알림 흐름 변경 (현 동작 유지)
- pydantic 도입 (표준 `enum.Enum`만 사용)
- `WeeklyPageConfig` (Confluence 페이지 책임 모델)에 Slack-only 필드 추가 — domain layering 회피
- `page_transformer.py` 커버리지 fix는 본 spec 범위 외 — **별도 prerequisite commit**으로 처리 (M3)

## 3. Decisions Summary

| 항목 | 결정 | 비고 |
|---|---|---|
| 알림 시점 | 성공 + 이미 존재 + 명시적 실패 + 예기치 않은 예외 | I1 (v1) 반영: 모든 실패 가시화 |
| 메시지 형식 | 케이스별 분기, 메인+thread 구조 | |
| 환경변수 | `SLACK_CHANNEL_CREATE_PAGE`, 미설정 시 스킵 | |
| 멘션 | 없음 (모든 케이스) | |
| 구현 방식 | UseCase에 `NotificationPort` 주입 (방식 A) | I4 (v1) + FY1 (v2) 반영 |
| Status 표현 | semantic `Enum` (값: `'created'/'already_exists'/'failed'`) — domain 레이어 | M3 (v1) 반영 |
| Status label mapping | `STATUS_LABELS` dict — **application 레이어**에 위치 | **I1 (v2) 반영**: domain layer 침범 회피 |
| URL 추출 | **어댑터 내부에서만 구성**, `get_page_by_title`이 dict에 `'url'` 키 추가하여 반환 | **B1 (v2) 반영**: port 시그니처 안정화 |
| `team_prefix` 전달 | `execute()` 시그니처에 `notification_prefix: str = ""` 인자 추가 | B2 (v1) 반영 |
| 알림 중복 방지 | `_already_notified` 래치로 ✅ 이후 outer except의 ❌ 발송 차단 | **I2 (v2) 반영** |
| Skip guard | main.py가 primary 결정, SlackAdapter 내부 가드는 다른 호출자(테스트 등) 보호용 | **I3 (v2) 반영**: defense-in-depth 표현 제거 |
| Notifier 실패 시 디버깅 | `_notify` except에서 `traceback.format_exc()` stderr 출력 | **I4 (v2) 반영** |

### Approach 선택 Rationale (FY1 보강)

3가지 alternative 검토:

**Alternative A (채택)**: UseCase에 notifier 주입
- ✅ daily/weekly와 패턴 일관성
- ✅ status → title/body 매핑 로직이 use case 내부에 응집
- ⚠️ use case가 두 책임(페이지 생성 + 알림 디스패치)을 가짐 (단, 단일 stakeholder 관심사라 SRP 충족)

**Alternative B (기각)**: Result 타입 반환 후 main.py에서 알림
- ❌ main.py에 status별 title/body 분기 로직 중복 도입
- ❌ daily/weekly와 패턴 불일치
- ❌ Result enum/dataclass 추가 abstraction

**Alternative C (기각, FY1 추가)**: main.py가 알림 전체 소유, use case는 단순 boolean 반환
- ✅ use case 가장 단순
- ❌ main.py에 `STATUS_LABELS`, `_build_title`, `notification_prefix` 등 presentation 로직 침투
- ❌ exception → notification 변환 로직도 main.py에 → composition root 비대화
- ❌ 테스트 어려움 (main.py 통합 테스트 필요)

**결론**: Alternative A는 use case 내부 복잡도와 main.py 단순성을 균형있게 유지. C가 표면적으로 단순하지만 presentation 로직이 main.py로 침투하면 daily/weekly까지 일관 변경 압력 발생.

### NotificationPort 재사용 Rationale (I3 v1 보강)

`NotificationPort.send(message, thread_message)`의 두 인자는 의미적으로 daily/weekly의 "thread reply"가 아닌 일반 "title + body" 패턴. create_page에서도 `(title, URL or error)`로 자연스럽게 매핑됨. 향후 Slack blocks/buttons/attachments가 필요해지면 그때 별도 `RichNotificationPort`를 추가하여 `SlackAdapter`가 두 포트를 구현하도록 하면 됨. 현시점에서는 새 포트 도입이 over-engineering.

## 4. Architecture

### Data Flow

```
main.py (create_page 분기)
  ├─ ConfluenceAdapter
  │     └─ 내부에서 _build_page_url(page_id, space_key, title) 헬퍼로 URL 구성
  │     └─ get_page_by_title()는 'url' 키 포함하여 반환
  │     └─ create_page()는 그대로 URL 반환
  ├─ PageTransformer
  └─ SlackAdapter(token, channel=slack_channel_create_page)  ← Optional
        │
        ▼
  CreateWeeklyPageUseCase(confluence, transformer, notifier=Optional)
        │
        ├─ STATUS_LABELS (application 레이어 dict)
        │
        ├─ execute(config, target_date, notification_prefix="BE")
        │     │
        │     │ try:
        │     │   this_week 계산 (catch-all 안에서)
        │     │   ...페이지 작업...
        │     │
        │     ├─ [정상 생성]    self._notify(CREATED, ...)         → True
        │     ├─ [중복]         self._notify(ALREADY_EXISTS, ...)  → True
        │     ├─ [source 없음]  self._notify(FAILED, ..., body=err) → False
        │     │
        │     │ except Exception as e:
        │     │   if not self._already_notified:  ← 래치 (I2)
        │     │     self._notify(FAILED, ..., body=exc_msg)
        │     │   return False
        │
        ├─ self._notify는 try/except로 알림 격리
        │   └─ except 내부에서 traceback.format_exc() stderr 출력 (I4)
        │
        └─ self._already_notified = True 설정 (성공 알림 발송 직후)
```

### Files Changed

| 파일 | 변경 내용 |
|---|---|
| `src/domain/models.py` | `CreatePageStatus(str, Enum)` 추가 — 값은 semantic (`'created'`/`'already_exists'`/`'failed'`). **STATUS_LABELS는 여기에 두지 않음** |
| `src/application/create_page_use_case.py` | 모듈 레벨에 `STATUS_LABELS: dict[CreatePageStatus, str]` 정의. 생성자에 `notifier: NotificationPort \| None = None`, `execute()`에 `notification_prefix: str = ""` 인자 추가, 분기별 알림 호출 + outer try/except + `_already_notified` 래치 |
| `src/infrastructure/config.py` | `AppConfig.slack_channel_create_page: str = ""` 추가 + env 로딩 |
| `src/infrastructure/adapters/confluence_adapter.py` | (1) 내부 헬퍼 `_build_page_url(page_id, space_key, title)` 추가, (2) `get_page_by_title()` 반환 dict에 `'url'` 키 추가, (3) `create_page()`는 동일 헬퍼 사용 |
| `src/main.py` | `create_page` 분기에서 `SlackAdapter` 인스턴스화(env 미설정 시 None) + use case에 `notification_prefix=config.report.team_prefix` 전달 |
| `README.md` | 새 env var 문서화 |
| `tests/unit/domain/test_create_page_status.py` | **신규 파일** — Enum semantic 값 검증 |
| `tests/unit/application/test_create_page_use_case.py` | **기존 파일에 테스트 추가** — `STATUS_LABELS` mapping, 알림 호출/예외 격리/`_already_notified` 래치/`notification_prefix`/A·B URL 동일성/pre-try exception |
| `tests/unit/infrastructure/test_config.py` | **기존 파일에 테스트 추가** — `SLACK_CHANNEL_CREATE_PAGE` env 로딩 |

### Prerequisite (별도 작업, M3 반영)

`page_transformer.py` lines 23-26 (XML 표준 엔티티 보존 분기) 테스트 추가는 **본 spec 작업과 분리된 별도 prerequisite commit**으로 처리한다:

- 이유: 본 spec의 핵심(Slack 알림)과 무관한 coverage 갭 fix
- 처리: 본 spec 구현 시작 전 별도 PR/commit으로 100% 베이스라인 확보
- 메모리 의도(`project_coverage_100.md`) 유지

### ConfluencePort 변경 사항

```python
# src/application/ports.py
class ConfluencePort(Protocol):
    """Confluence 페이지 접근 추상 인터페이스"""

    def get_page_by_title(self, space_key: str, title: str) -> dict | None:
        """제목으로 페이지 조회. 없으면 None 반환.

        반환 dict는 'id', 'title', **'url'** 키를 포함한다.
        URL은 create_page() 반환과 동일한 형식.
        """
        ...

    def get_page_content(self, page_id: str) -> str: ...

    def create_page(self, space_key: str, title: str, content: str, parent_id: str) -> str:
        """새 페이지 생성. 생성된 페이지 URL 반환."""
        ...

    # ⛔ build_page_url 추가하지 않음 (B1 반영)
    #    URL 구성은 어댑터 내부 책임. port는 'URL 빌드 서비스'를 노출하지 않음.
```

### ConfluenceAdapter 변경 사항

```python
# src/infrastructure/adapters/confluence_adapter.py
class ConfluenceAdapter:
    # ... 기존 코드 ...

    def _build_page_url(self, page_id: str, space_key: str, title: str) -> str:
        """v2 API URL 형식으로 페이지 URL 구성 (private helper)"""
        return f"{self._v2_base_url}/spaces/{space_key}/pages/{page_id}/{title}"

    def get_page_by_title(self, space_key: str, title: str) -> dict | None:
        """제목으로 페이지 조회. 반환 dict에 'url' 키 추가."""
        page = self.client.get_page_by_title(space_key, title)
        if page is None:
            return None
        # 'url' 필드 추가하여 use case가 일관된 URL 형식 사용 가능
        page["url"] = self._build_page_url(page["id"], space_key, title)
        return page

    def create_page(self, space_key, title, content, parent_id) -> str:
        # ... 기존 로직 ...
        return self._build_page_url(page_id, space_key, title)
```

> **B1 해결 효과**: A 케이스(create)와 B 케이스(이미 존재) 모두 어댑터 내부의 `_build_page_url`을 통과하므로 형식 100% 동일. Use case는 dict의 `'url'` 또는 `create_page()` 반환을 그대로 사용. ConfluencePort 시그니처 변경 없음(메서드 추가/제거 없음).

### Core Principles

- **NotificationPort 재사용** — 새 포트 추가 없음
- **notifier는 Optional** — env var 미설정 시 main.py가 `None` 주입 → use case는 `if self._notifier:` 가드
- **알림 격리** — `try/except`로 알림 실패가 페이지 생성 결과를 오염시키지 않음
- **알림 중복 방지** — `_already_notified` 래치로 단일 execute() 호출당 최대 1개 알림
- **도메인-프레젠테이션 분리** — `CreatePageStatus`는 domain, `STATUS_LABELS`는 application
- **URL 구성은 인프라 책임** — port에 URL 빌드 서비스 노출 안 함
- **도메인 침범 금지** — `WeeklyPageConfig`에 Slack-only 필드 추가 안 함, `notification_prefix`는 `execute()` 인자

## 5. Message Format

### 공통

- 메인 메시지 = 제목 (한 줄)
- 스레드 메시지 = URL 또는 에러 사유
- 기존 `SlackAdapter.send(message, thread_message)` 시그니처 재사용
- `notification_prefix` 빈 문자열이면 `[BE]` 부분 생략

### 케이스별 포맷 (I5 반영, 모든 날짜 valid Mon-Fri)

> 예시 기준일: 2026-04-27 (월요일). `calculate_this_week_range`는 04.27(Mon) ~ 05.01(Fri) 반환.

**A. ✅ 새로 생성 성공 (`CreatePageStatus.CREATED`)**
```
메인:    [BE][26.04.27 ~ 05.01_WeeklyPage] ✅ 생성 완료
스레드:  https://your.atlassian.net/wiki/spaces/MAI/pages/1234567/2026.04.27%20~%2005.01
```

**B. ℹ️ 이미 존재 (`CreatePageStatus.ALREADY_EXISTS`)**
```
메인:    [BE][26.04.27 ~ 05.01_WeeklyPage] ℹ️ 이미 존재
스레드:  https://your.atlassian.net/wiki/spaces/MAI/pages/1234567/2026.04.27%20~%2005.01
```

> A와 B의 URL은 어댑터 내부 `_build_page_url`로 통일되므로 **byte-level 동일**.

**C. ❌ 실패 (`CreatePageStatus.FAILED`)**
```
메인:    [BE][26.04.27 ~ 05.01_WeeklyPage] ❌ 생성 실패
스레드:  이전 주 페이지를 찾을 수 없습니다: 2026.04.20 ~ 04.24
        # 또는 예외인 경우:
        Unexpected error: ConnectionError: HTTPSConnectionPool(...timeout...)
```

### Status Enum (domain) + Label Mapping (application, I1 반영)

```python
# src/domain/models.py
from enum import Enum

class CreatePageStatus(str, Enum):
    """create_page 유스케이스 실행 결과 (semantic identifier)"""
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"
    FAILED = "failed"
```

```python
# src/application/create_page_use_case.py
from ..domain.models import CreatePageStatus

# 모듈 레벨 상수 — application 레이어 (presentation은 use case가 책임)
STATUS_LABELS: dict[CreatePageStatus, str] = {
    CreatePageStatus.CREATED: "✅ 생성 완료",
    CreatePageStatus.ALREADY_EXISTS: "ℹ️ 이미 존재",
    CreatePageStatus.FAILED: "❌ 생성 실패",
}
```

> **Why application?** Korean+emoji 라벨은 presentation. domain은 의미만(`'created'` 등). 라벨 mapping은 use case가 _build_title에서 사용하는 곳에 colocate. SlackAdapter에 두지 않는 이유: 향후 다른 notifier(이메일, 대시보드)가 같은 라벨을 쓸 수 있도록 use case 레벨에서 공유.

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
| 1 | 정상 생성 | create OK | `CREATED` 알림 + `_already_notified=True` | `True` |
| 2 | 이미 존재 | skip | `ALREADY_EXISTS` 알림 + `_already_notified=True` | `True` |
| 3 | 이전 주 페이지 못 찾음 | abort | `FAILED` 알림 + `_already_notified=True` | `False` |
| 4 | confluence/transformer/네트워크 예외 (성공 알림 전) | use case가 catch | `FAILED` 알림 (사유: 예외 클래스 + 메시지) | `False` |
| 5 | **성공 알림 후 코드 raise** (예: `_build_title` KeyError 등 — 이론상) | 페이지는 생성됨 | `_already_notified=True`이므로 outer except는 알림 발송 **안 함** (래치) | `False` |
| 6 | notifier=None (env 미설정) | 정상 동작 | 알림 스킵 | 위 1/2/3/4 그대로 |
| 7 | notifier 호출 중 예외 | 이미 발생한 결과 그대로 | stderr 로그 + `traceback.format_exc()` 출력 | 위 1/2/3/4 그대로 |

### 알림 격리 패턴 (use case 내부, I4 반영)

```python
import traceback

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
        self._already_notified = True
    except Exception as e:
        # 알림 실패가 페이지 작업 결과를 오염시키지 않도록 격리.
        # debug 정보 보존을 위해 traceback을 stderr에 출력.
        print(
            f"WARNING: Slack notification failed (status={status.value}): {e}\n"
            f"{traceback.format_exc()}"
        )
```

### 예외 처리 패턴 (execute 메서드, I2 + M1 반영)

```python
def execute(
    self,
    config: WeeklyPageConfig,
    target_date: date | None = None,
    notification_prefix: str = "",
) -> bool:
    self._already_notified = False  # 매 호출 초기화
    this_week: DateRange | None = None  # except 가드용 fallback (M1)

    try:
        today = target_date or date.today()
        last_week = calculate_last_week_range(today)
        this_week = calculate_this_week_range(today)
        # ... 기존 페이지 조회/변환/생성 로직 ...
        # 케이스별로 _notify 호출하고 True/False 반환
        return result_bool
    except Exception as e:
        # 예기치 않은 예외 (네트워크/HTTP/transformer 에러 등)
        body = f"Unexpected error: {type(e).__name__}: {e}"
        print(f"ERROR: create_page unexpected exception: {body}")

        # I2: 이미 알림을 보냈다면 (성공 후 실패 등) 추가 알림 보내지 않음
        if not self._already_notified and this_week is not None:
            self._notify(CreatePageStatus.FAILED, notification_prefix, this_week, body)
        return False
```

> **Why catch all and return False (not raise)?**
> - 운영 가시성 (Goals): 모든 실패를 채널에서 보이게 함
> - Cronicle 잡 종료 코드: 현재 코드도 use case가 False 반환 시 main이 stderr 출력만 하고 정상 종료 → 변경 없음
> - 기존 동작과의 호환: caller(main.py)는 boolean만 보면 됨

> **Why `_already_notified` 래치?** 성공 알림(✅) 발송 후 다른 코드 경로에서 예외가 발생하면 outer except가 다시 ❌ FAILED 알림을 보낼 수 있음 → 단일 페이지에 대해 두 종류 알림 = 운영자 혼란. 래치로 차단.

> **Why `this_week is not None` 체크?** M1: 이론상 `calculate_this_week_range`가 raise하면 `this_week`가 None인 채로 except 진입. 이때 `_notify`를 호출하면 NPE 발생. fallback으로 알림 스킵 (단, stderr는 이미 출력됨).

### Skip Guard 책임 분리 (I3 반영)

defense-in-depth 표현 폐기. 명시적 책임 분리:

1. **main.py (composition root, primary)**: env 미설정 시 `notifier=None` 주입 → 정상 운영 흐름의 모든 'config 미설정' 케이스를 차단
2. **SlackAdapter (보조, 다른 호출자 보호)**: token/channel이 비어 있으면 stderr 경고 후 return → main.py를 우회한 호출(테스트, 디버깅 스크립트 등)에서도 안전망. 단, 운영 흐름에서는 이 분기에 도달하지 않음

> **차이점 (이전 v2와)**: "두 가드는 다른 threat를 막는다"고 주장하지 않음. SlackAdapter 가드는 main.py 가드의 fallback이며, 둘이 동시에 활성화될 가능성은 (테스트가 직접 SlackAdapter 인스턴스화하는 경우 외엔) 없음. 향후 SlackAdapter를 strict-by-construction(`__init__`에서 ValueError raise)으로 바꿀 수 있지만, daily/weekly 모드와의 일관성을 위해 현 거동 유지.

### Use case 내부 필드 명명

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
    self._already_notified: bool = False  # I2: 알림 중복 방지 래치
```

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

## 7. Testing Strategy (TDD)

기존 `tests/unit/{domain,application,infrastructure}/` 구조 활용. **변경 영향 파일 100% 커버리지** (page_transformer 갭은 별도 prerequisite commit).

### Domain 레이어
**`tests/unit/domain/test_create_page_status.py`** (신규):
- `CreatePageStatus.CREATED.value == "created"` 등 semantic 값 검증 (3개)
- `f"{status.value}"` 형식이 `"created"` 반환 검증 (FY2: Python 3.11 StrEnum 거동 lock-in)

### Application 레이어
**`tests/unit/application/test_create_page_use_case.py`** — 기존 파일에 추가:

| 테스트 | Given | When | Then |
|---|---|---|---|
| STATUS_LABELS 검증 | — | import | 3개 enum 값 모두 라벨 존재, 키 누락 없음 |
| 성공 시 알림 전송 | source 존재, target 미존재 | execute() | notifier.send() 호출, title=`✅ 생성 완료`, thread=URL |
| 중복 시 알림 전송 | source/target 모두 존재 | execute() | notifier.send() 호출, title=`ℹ️ 이미 존재`, thread=URL (`existing_page['url']` 사용 검증) |
| **A·B URL 동일성** (FY2 신규) | source/target 모두 존재 + create_page mock URL = "X" + existing_page url = "X" | execute() | A 케이스의 thread URL == B 케이스의 thread URL |
| source 없음 실패 알림 | source 미존재 | execute() | notifier.send() 호출, title=`❌ 생성 실패`, thread=사유 |
| 예외 발생 시 FAILED 알림 | confluence raise | execute() | notifier.send() 호출, title=`❌ 생성 실패`, thread=예외 메시지, return False |
| **알림 중복 방지 래치** (FY2 신규) | 성공 알림 후 _build_title raise (mock) | execute() | notifier.send() 호출 횟수 == 1 (성공만, FAILED 추가 안 됨) |
| **pre-try 예외 시 알림 스킵** (FY2 신규) | calculate_this_week_range mock raise | execute() | notifier.send() 호출 안 됨 (this_week=None), return False |
| notifier=None 알림 스킵 | notifier 미주입 | execute() | 어떤 알림도 호출되지 않음, 페이지 생성은 정상 |
| 알림 예외 격리 | notifier.send() raise | execute() | use case는 정상 boolean 반환, 예외 전파 X |
| notification_prefix 빈 값 | prefix="" | execute() | 제목에 `[BE]` 부분 생략 |
| notification_prefix 채워진 값 | prefix="BE" | execute() | 제목 시작이 `[BE]` |

### Infrastructure 레이어
**`tests/unit/infrastructure/test_config.py`** — 기존 파일에 추가:
- `SLACK_CHANNEL_CREATE_PAGE` env 설정 시 `slack_channel_create_page`가 채워짐
- 미설정 시 빈 문자열

### Note: ConfluenceAdapter 테스트
`pyproject.toml`에서 `confluence_adapter.py`는 coverage omit 대상 — `_build_page_url`/`get_page_by_title` url 키 추가도 동일 정책. 단위 테스트는 use case에서 mock으로 검증.

## 8. Completion Criteria

- [ ] `REPORT_MODE=create_page` 실행 시 `SLACK_CHANNEL_CREATE_PAGE` 채널에 케이스별 메시지 전송됨 (성공/중복/명시적 실패/예기치 않은 예외 모두 포함)
- [ ] **A/B 케이스 URL byte-level 동일** (어댑터 `_build_page_url` 단일 호출 경로)
- [ ] **단일 execute() 호출당 알림 최대 1개** (`_already_notified` 래치)
- [ ] `SLACK_CHANNEL_CREATE_PAGE` 미설정 시 알림 스킵, 페이지 생성은 정상 동작
- [ ] 알림 전송 실패 시 페이지 생성 결과의 boolean 반환값 변경되지 않음
- [ ] `_notify` 알림 실패 시 stderr에 `traceback` 출력
- [ ] 예기치 않은 예외 발생 시 use case가 catch하여 `FAILED` 알림 + False 반환
- [ ] `uv run pytest --cov=src --cov-report=term-missing` 통과
- [ ] **변경 파일 + 본 spec prerequisite(page_transformer.py 별도 commit) 모두 커버리지 100%**
- [ ] `STATUS_LABELS`는 `src/application/create_page_use_case.py`에 위치 (domain layer 아님)
- [ ] `ConfluencePort`에 새 메서드(`build_page_url` 등) 추가되지 않음
- [ ] `README.md`에 새 env var 문서화

## 9. Don'ts

- ❌ pydantic 도입 금지 → 표준 `Enum` 사용
- ❌ Domain 레이어에서 외부 라이브러리 import 금지 → `enum.Enum`만
- ❌ Domain 레이어에 presentation 문자열(emoji/Korean) 직접 노출 금지 → semantic 값만 + label은 application 레이어에 별도
- ❌ `WeeklyPageConfig`에 `team_prefix` 등 Slack-only 필드 추가 금지 → `execute()` 인자로 전달
- ❌ `NotificationPort` 외 새 포트 추가 금지 (현시점) → 기존 포트 재사용
- ❌ `ConfluencePort`에 URL 빌드 서비스 메서드 추가 금지 → 어댑터 내부에서 URL 구성, dict에 `'url'` 키 포함하여 반환
- ❌ `CreateWeeklyPageUseCase.execute()` 반환 타입 변경 금지 → boolean 유지, 알림은 부수효과
- ❌ 알림 예외를 raise 금지 → `try/except`로 흡수, stderr 로그 + traceback 출력
- ❌ **단일 페이지 작업당 알림 2개 이상 발송 금지** → `_already_notified` 래치로 차단
- ❌ daily/weekly 보고서 흐름에 영향 주는 변경 금지
- ❌ `confluence_url`을 use case에 직접 노출 금지 → 어댑터가 dict에 url 포함

## 10. Considerations

- **운영 가시성**: Cronicle 로그 확인 없이 채널만 봐도 매주 페이지 생성 상태 파악 가능 (모든 실패 모드 가시화)
- **Slack 자체 실패 trade-off (I4 반영)**: notifier 자체 실패는 stderr 로그(+ traceback)로만 기록되고 silent. Slack 토큰 만료/대량 rate limit 같은 systemic failure는 운영자가 daily/weekly 보고서 미수신으로도 결국 인지 — 별도 모니터링 추가는 별도 과제. 본 spec에서는 페이지 생성 정확성 > 알림 신뢰성을 명시적으로 채택. (개선 가능: notifier 자체 실패 시 Cronicle exit code를 non-zero로 변경하여 잡 실패 신호를 주는 방안. 본 spec 범위 외)
- **메시지 시각적 구분**: 이모지(✅/ℹ️/❌)로 케이스 즉시 식별 가능
- **URL 형식 통일 (B1 반영)**: A/B 케이스 모두 어댑터 `_build_page_url`을 통과 → 운영자가 클릭한 URL의 동작이 케이스별로 다르지 않음
- **알림 중복 방지 래치 (I2 반영)**: 단일 execute() 호출당 알림 최대 1개. 성공 알림 후 어떤 코드가 raise해도 outer except가 추가 알림 발송 안 함. 운영자에게 일관된 단일 신호 보장.
- **`notification_prefix` 확장 트리거 (M2 반영)**: `execute()`에 4번째 알림 관련 인자(예: `notification_mentions`, `notification_channel_override`)가 추가되는 시점에 `NotificationContext` value object 도입. 그 전까지 단일 `notification_prefix` 인자로 충분.
- **`page_transformer.py` 100% 분리 (M3 반영)**: 본 spec과 무관한 coverage 갭. 별도 prerequisite commit으로 처리하여 본 spec 작업 완료 시점과 분리.

## 11. Constraints

- 기존 Clean Architecture 의존성 방향 준수 (Domain → Application → Infrastructure)
- 기존 `@dataclass(frozen=True)` 패턴 일관성 유지 (`WeeklyPageConfig` 변경 없음)
- 기존 SlackAdapter 인터페이스 변경 금지 (`send(message, thread_message)`)
- 기존 NotificationPort 인터페이스 변경 금지
- `ConfluencePort` 메서드 추가/제거 없음 (반환 dict shape만 명시적 계약 추가)
- Python 3.12+ 타입 힌트 스타일 유지
- 기존 5개 `test_create_page_use_case.py` 테스트 회귀 없음 (fixture 변경 없음, 기본 인자만 추가)

## 12. Next Step

이 spec을 기반으로 `superpowers:writing-plans` 스킬로 구현 플랜을 작성한다. 플랜에는 CLAUDE.md 템플릿(완료조건/금지사항/고려사항/제약사항/스킬 검색/Task List)을 모두 포함한다.

**Task 순서 힌트** (writing-plans에서 상세화):
0. **(prerequisite, 별도 commit)** `page_transformer.py` lines 23-26 테스트 추가 — 100% 베이스라인 확보
1. `CreatePageStatus` Enum 추가 (domain)
2. `STATUS_LABELS` 추가 (application — `create_page_use_case.py` 모듈 레벨)
3. `AppConfig.slack_channel_create_page` + env 로딩 (infrastructure)
4. `ConfluenceAdapter._build_page_url` 헬퍼 + `get_page_by_title` 반환 dict에 `'url'` 키 추가 (adapter)
5. `CreateWeeklyPageUseCase` 시그니처 확장 + `_notify` + `_already_notified` 래치 + outer try/except + `_build_title` (application)
6. `main.py` 조립 + `notification_prefix` 전달
7. README 문서 갱신
8. 전체 회귀 + 변경 파일 100% 커버리지 검증

---

## Review History

- **v1 (2026-04-27)**: 초안. brainstorming 결과.
- **v2 (2026-04-27)**: ce-doc-review 15 findings 반영.
  - Status enum semantic 값으로 변경 + label mapping 분리
  - `team_prefix` → `notification_prefix` 인자 전달
  - 모든 예외를 use case가 catch하여 FAILED 알림
  - `ConfluencePort.build_page_url` 헬퍼로 URL 통일
  - page_transformer.py 선결 fix Task 100% 보장
- **v3 (2026-04-27)**: /rl-verify Iteration 1의 12개 신규 finding 반영.
  - **B1 (BLOCKER)**: `ConfluencePort.build_page_url` 제거 → 어댑터 내부 `_build_page_url` private 헬퍼 + `get_page_by_title` dict에 `'url'` 키 포함
  - **I1 (IMPORTANT)**: `STATUS_LABELS`을 application 레이어로 이동 (spec 자체 Don't 위배 해소)
  - **I2 (IMPORTANT)**: `_already_notified` 래치 추가 → ✅ 후 ❌ 중복 발송 차단
  - **I3 (IMPORTANT)**: defense-in-depth 표현 제거 → main.py primary + SlackAdapter는 보조 명시
  - **I4 (IMPORTANT)**: `_notify` except에서 `traceback.format_exc()` stderr 출력
  - **I5 (IMPORTANT)**: 샘플 날짜를 valid Mon-Fri로 수정 (`26.04.27 ~ 05.01`)
  - **M1 (MINOR)**: 날짜 계산을 try 안으로 이동 + `this_week is not None` 가드
  - **M2 (MINOR)**: §10에 `NotificationContext` 트리거 명시
  - **M3 (MINOR)**: page_transformer fix를 prerequisite (별도 commit)으로 명시 분리
  - **FY1**: Approach §3에 alternative C 검토 추가
  - **FY2**: A/B URL 동일성, 알림 래치, pre-try, `.value` 형식 테스트 추가
  - **FY3, FY4**: 변경 없음, 인지만
