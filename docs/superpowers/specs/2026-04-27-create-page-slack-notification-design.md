# Create Page Slack Notification — Design Spec

- **Date:** 2026-04-27
- **Author:** brainstorming session (superpowers:brainstorming)
- **Status:** Approved (awaiting implementation plan)

## 1. Background

`REPORT_MODE=create_page` 모드는 매주 월요일 07:00에 Cronicle로 실행되어, 이전 주 Confluence 페이지를 복사해서 새 주간 페이지를 만든다. 현재는 결과를 stdout에만 출력하므로 운영자가 매번 Cronicle 로그를 확인해야 한다.

이 설계는 페이지 생성 결과(성공/이미 존재/실패)를 별도의 Slack 채널로 푸시하여 운영 가시성을 높이는 것을 목적으로 한다. 기존 daily/weekly 보고서에서 사용하는 Slack 봇(`SLACK_TOKEN`)을 그대로 재사용하고, 채널만 분리한다.

## 2. Goals & Non-Goals

### Goals
- `create_page` 유스케이스 실행 시, 결과를 별도 Slack 채널로 알림 전송
- 케이스별로 시각적으로 구분되는 메시지 포맷 (✅ / ℹ️ / ❌)
- 알림 실패가 페이지 생성 결과를 오염시키지 않도록 격리
- 환경변수 미설정 시 알림은 스킵하되, 페이지 생성은 정상 동작

### Non-Goals
- 새 Slack 봇 추가 (기존 봇 재사용)
- 멘션 기능 (실패 케이스 포함, 모든 케이스에서 멘션 없음)
- daily/weekly 보고서 알림 흐름 변경 (현 동작 유지)
- pydantic 도입 (표준 `enum.Enum`만 사용)

## 3. Decisions Summary

| 항목 | 결정 |
|---|---|
| 알림 시점 | 성공(A) + 이미 존재(B) + 실패(C) 모두 |
| 메시지 형식 | 케이스별 분기, 메인+thread 구조 |
| 환경변수 | `SLACK_CHANNEL_CREATE_PAGE`, 미설정 시 스킵 |
| 멘션 | 없음 (모든 케이스) |
| 구현 방식 | UseCase에 `NotificationPort` 주입 (방식 A) |
| Status 표현 | 표준 `enum.Enum` (pydantic 미도입) |
| `team_prefix` 전달 | `WeeklyPageConfig`에 필드 추가 (모델 변경) |

## 4. Architecture

### Data Flow

```
main.py (create_page 분기)
  ├─ ConfluenceAdapter
  ├─ PageTransformer
  └─ SlackAdapter(token, channel=slack_channel_create_page)  ← NEW (Optional)
        │
        ▼
  CreateWeeklyPageUseCase(confluence, transformer, notifier=Optional)
        │
        ├─ [성공]   notifier.send("[BE]...✅ 생성 완료", url)
        ├─ [중복]   notifier.send("[BE]...ℹ️ 이미 존재", url)
        └─ [실패]   notifier.send("[BE]...❌ 생성 실패", error_msg)
```

### Files Changed

| 파일 | 변경 내용 |
|---|---|
| `src/domain/models.py` | `CreatePageStatus` Enum 추가, `WeeklyPageConfig`에 `team_prefix` 필드 추가 |
| `src/infrastructure/config.py` | `AppConfig.slack_channel_create_page: str = ""` 추가 + env 로딩 |
| `src/application/create_page_use_case.py` | 생성자에 `notifier: NotificationPort \| None` 추가, 분기별 알림 호출 |
| `src/main.py` | `create_page` 분기에서 `SlackAdapter` 인스턴스화 후 use_case에 주입 |
| `README.md` | 새 env var 문서화 |
| `tests/unit/domain/test_create_page_status.py` | Enum 값 검증 |
| `tests/unit/domain/test_models.py` | `WeeklyPageConfig.team_prefix` 검증 |
| `tests/unit/application/test_create_page_use_case.py` | 알림 호출 검증 (성공/중복/실패/스킵/예외 격리) |
| `tests/unit/infrastructure/test_config.py` | env 로딩 검증 |

### Core Principles

- **NotificationPort 재사용** — 새 포트 추가 없음
- **notifier는 Optional** — env var 미설정 시 `None` 주입 → use case는 `if self._notifier:` 가드
- **알림 격리** — `try/except`로 알림 실패가 페이지 생성 결과를 오염시키지 않음

## 5. Message Format

### 공통

- 메인 메시지 = 제목 (한 줄)
- 스레드 메시지 = URL 또는 에러 사유
- 기존 `SlackAdapter.send(message, thread_message)` 시그니처 재사용
- `team_prefix` 빈 문자열이면 `[BE]` 부분 생략

### 케이스별 포맷

**A. ✅ 새로 생성 성공**
```
메인:    [BE][26.04.28 ~ 05.02_WeeklyPage] ✅ 생성 완료
스레드:  https://your.atlassian.net/wiki/spaces/MAI/pages/1234567
```

**B. ℹ️ 이미 존재 (skip)**
```
메인:    [BE][26.04.28 ~ 05.02_WeeklyPage] ℹ️ 이미 존재
스레드:  https://your.atlassian.net/wiki/spaces/MAI/pages/1234567
```

**C. ❌ 실패 (이전 주 페이지 못 찾음)**
```
메인:    [BE][26.04.28 ~ 05.02_WeeklyPage] ❌ 생성 실패
스레드:  이전 주 페이지를 찾을 수 없습니다: 2026.04.21 ~ 04.25
```

### Status Enum

```python
# src/domain/models.py
from enum import Enum

class CreatePageStatus(str, Enum):
    """create_page 유스케이스 실행 결과"""
    CREATED = "✅ 생성 완료"
    ALREADY_EXISTS = "ℹ️ 이미 존재"
    FAILED = "❌ 생성 실패"
```

### Title Builder

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
    return f"{bracket}[{start} ~ {end}_WeeklyPage] {status.value}"
```

## 6. Error Handling & Edge Cases

| # | 시나리오 | 페이지 동작 | 알림 동작 | use_case 반환 |
|---|---|---|---|---|
| 1 | 정상 생성 | create OK | `CREATED` 알림 시도 | `True` |
| 2 | 이미 존재 | skip | `ALREADY_EXISTS` 알림 시도 | `True` |
| 3 | 이전 주 페이지 못 찾음 | abort | `FAILED` 알림 시도 | `False` |
| 4 | `confluence.create_page` 예외 | (예외 전파) | 알림 안 함 (기존 동작 유지) | (예외 전파) |
| 5 | notifier=None (env 미설정) | 정상 동작 | 알림 스킵 | 위 1/2/3 그대로 |
| 6 | notifier 호출 중 예외 | 이미 발생한 결과 그대로 | 로그만 출력 | 위 1/2/3 그대로 |

### 알림 격리 패턴

```python
def _try_notify(self, status: CreatePageStatus, title: str, body: str) -> None:
    if self._notifier is None:
        return
    try:
        self._notifier.send(title, body)
    except Exception as e:
        print(f"WARNING: Slack notification failed ({status.name}): {e}")
```

### B 케이스 URL 추출

`existing_page` (현재 `confluence.get_page_by_title()` 반환 dict)에서 URL 키 확인 필요. 어댑터 코드 검토 후:
- 키가 있으면 직접 사용
- 없으면 `f"{confluence_url}/wiki/spaces/{space_key}/pages/{existing_page['id']}"`로 빌드 (필요 시 `ConfluenceAdapter.build_page_url(page_id)` 헬퍼 추가)

### main.py 인스턴스화

```python
# create_page 분기 안
notifier = (
    SlackAdapter(token=config.slack_token, channel=config.slack_channel_create_page)
    if config.slack_channel_create_page and config.slack_token
    else None
)
use_case = CreateWeeklyPageUseCase(confluence, transformer, notifier=notifier)
```

## 7. Testing Strategy (TDD)

기존 `tests/unit/{domain,application,infrastructure}/` 구조 활용. **커버리지 100% 유지**.

### Domain 레이어
- `test_create_page_status.py` — Enum 값 3개 검증
- `test_models.py` — `WeeklyPageConfig.team_prefix` 필드 검증

### Application 레이어
`test_create_page_use_case.py` 추가 케이스:

| 테스트 | Given | When | Then |
|---|---|---|---|
| 성공 시 알림 전송 | source 존재, target 미존재 | execute() | notifier.send() 호출, 메시지에 `✅ 생성 완료` + URL 포함 |
| 중복 시 알림 전송 | source/target 모두 존재 | execute() | notifier.send() 호출, 메시지에 `ℹ️ 이미 존재` + URL 포함 |
| 실패 시 알림 전송 | source 미존재 | execute() | notifier.send() 호출, 메시지에 `❌ 생성 실패` + 에러 메시지 |
| notifier=None 알림 스킵 | notifier 미주입 | execute() | 어떤 알림도 호출되지 않음 |
| 알림 예외 격리 | notifier.send() raise | execute() | use case는 정상 반환, 예외 전파 X |
| team_prefix 빈 값 처리 | prefix="" | execute() | 제목에 `[BE]` 부분 생략 |

### Infrastructure 레이어
- `test_config.py` — `SLACK_CHANNEL_CREATE_PAGE` env 설정/미설정 케이스

## 8. Completion Criteria

- [ ] `REPORT_MODE=create_page` 실행 시 `SLACK_CHANNEL_CREATE_PAGE` 채널에 케이스별 메시지 전송됨
- [ ] `SLACK_CHANNEL_CREATE_PAGE` 미설정 시 알림 스킵, 페이지 생성은 정상 동작
- [ ] 알림 전송 실패 시 페이지 생성 결과의 boolean 반환값 변경되지 않음
- [ ] `uv run pytest --cov=src --cov-report=term-missing` 통과 + **커버리지 100%**
- [ ] `README.md`에 새 env var 문서화

## 9. Don'ts

- ❌ pydantic 도입 금지 → 표준 `Enum` 사용
- ❌ Domain 레이어에서 외부 라이브러리 import 금지 → `enum.Enum`만
- ❌ `NotificationPort` 외 새 포트 추가 금지 → 기존 포트 재사용
- ❌ `CreateWeeklyPageUseCase.execute()` 반환 타입 변경 금지 → 알림은 부수효과로 격리
- ❌ 알림 실패를 raise 금지 → `try/except`로 흡수, 로그만 출력
- ❌ daily/weekly 보고서 흐름에 영향 주는 변경 금지

## 10. Considerations

- **운영 가시성**: Cronicle 로그 확인 없이 채널만 봐도 매주 페이지 생성 상태 파악 가능
- **Slack 토큰 만료 위험**: 기존 토큰을 재사용하므로 별도 토큰 만료 대응 불필요
- **메시지 시각적 구분**: 이모지(✅/ℹ️/❌)로 케이스 즉시 식별 가능
- **B 케이스 URL 추출 시 어댑터 변경 가능성**: `get_page_by_title` 반환 dict 키 확인 후 결정

## 11. Constraints

- 기존 Clean Architecture 의존성 방향 준수 (Domain → Application → Infrastructure)
- 기존 dataclass 패턴 일관성 유지
- 기존 SlackAdapter 인터페이스 변경 금지
- Python 3.12+ 타입 힌트 스타일 유지

## 12. Next Step

이 spec을 기반으로 `superpowers:writing-plans` 스킬로 구현 플랜을 작성한다. 플랜에는 CLAUDE.md 템플릿(완료조건/금지사항/고려사항/제약사항/스킬 검색/Task List)을 모두 포함한다.
