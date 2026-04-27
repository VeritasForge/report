# Create Page Slack Notification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `REPORT_MODE=create_page` 실행 시 페이지 생성 결과(성공/중복/명시적 실패/예기치 않은 예외)를 별도 Slack 채널(`SLACK_CHANNEL_CREATE_PAGE`)로 단일 알림 발송.

**Architecture:** `CreateWeeklyPageUseCase`에 Optional `NotificationPort` 주입 (방식 A). status는 domain `Enum`(semantic) + application `STATUS_LABELS`(presentation) 분리. URL은 `ConfluenceAdapter` 내부 `_build_page_url` 헬퍼로 통일하여 A/B 케이스 byte-level 동일. `_already_notified` 래치로 단일 execute() 호출당 알림 1개 보장. outer try/except로 모든 예외를 `FAILED` 알림으로 변환.

**Tech Stack:** Python 3.12+, `slack_sdk`, `atlassian-python-api`, `pytest`, `uv`, Clean Architecture (Domain → Application → Infrastructure).

**Spec Reference:** `docs/superpowers/specs/2026-04-27-create-page-slack-notification-design.md` (v3)

---

## 완료조건 (Plan-level Completion Criteria)

- [ ] `REPORT_MODE=create_page` + `SLACK_CHANNEL_CREATE_PAGE` 설정 후 실행 시 채널에 케이스별 메시지 전송됨
- [ ] A/B 케이스 thread URL이 byte-level 동일 (`_build_page_url` 단일 호출 경로)
- [ ] 단일 `execute()` 호출당 notifier.send 호출 횟수 ≤ 1 (`_already_notified` 래치)
- [ ] `SLACK_CHANNEL_CREATE_PAGE` 미설정 시 알림 스킵, 페이지 생성은 정상 동작
- [ ] 알림 전송 실패 시 페이지 생성 결과 boolean 반환값 변경되지 않음, stderr에 traceback 출력
- [ ] 예기치 않은 예외 발생 시 `FAILED` 알림 + `False` 반환 (raise 안 함)
- [ ] `STATUS_LABELS`는 `src/application/create_page_use_case.py`에 위치 (domain layer 아님)
- [ ] `ConfluencePort`에 새 메서드(`build_page_url` 등) 추가되지 않음
- [ ] `uv run pytest --cov=src --cov-report=term-missing` 통과 + **변경 영향 파일 100% 커버리지** (page_transformer.py 갭은 prerequisite로 분리 처리)
- [ ] 기존 5개 `test_create_page_use_case.py` 테스트 회귀 없음
- [ ] `README.md`에 `SLACK_CHANNEL_CREATE_PAGE` 문서화

## 금지사항 (Don'ts)

- ❌ pydantic 도입 금지 → 표준 `enum.Enum`만 사용
- ❌ Domain 레이어에서 외부 라이브러리 import 금지 → `enum.Enum`만
- ❌ Domain 레이어에 presentation 문자열(emoji/Korean) 직접 노출 금지 → `STATUS_LABELS`는 application 레이어
- ❌ `WeeklyPageConfig`에 Slack-only 필드 추가 금지 → `execute()` 인자로 전달
- ❌ `NotificationPort` 외 새 포트 추가 금지 → 기존 포트 재사용
- ❌ `ConfluencePort`에 URL 빌드 서비스 메서드 추가 금지 → 어댑터 내부에서 URL 구성
- ❌ `CreateWeeklyPageUseCase.execute()` 반환 타입 변경 금지 → boolean 유지
- ❌ 알림 예외를 raise 금지 → `try/except`로 흡수, stderr + traceback 출력
- ❌ 단일 페이지 작업당 알림 2개 이상 발송 금지 → `_already_notified` 래치 사용
- ❌ daily/weekly 보고서 흐름에 영향 주는 변경 금지
- ❌ `confluence_url`을 use case에 직접 노출 금지 → 어댑터가 dict에 url 포함
- ❌ "defense-in-depth" 표현으로 두 단계 가드 정당화 금지 → main.py primary, SlackAdapter는 보조
- ❌ 검증 명령 결과 확인 없이 "통과" 주장 금지 (verification-before-completion 원칙)

## 고려사항 (Considerations)

- **운영 가시성**: 모든 실패 모드(source missing / 예외)가 가시화됨. 단, notifier 자체 실패는 stderr 로그만 → systemic Slack failure는 daily/weekly 미수신으로 간접 인지 (trade-off 채택)
- **알림 중복 방지**: `_already_notified` 래치는 매 `execute()` 호출 시작에 `False`로 초기화. 성공 알림 발송 직후 `True` 설정. outer except는 래치 확인.
- **pre-try 안전망**: `this_week`를 try 외부에서 `None`으로 초기화. except에서 `this_week is None`이면 `_notify` 스킵 (가드).
- **테스트 어려움 분리**: `confluence_adapter.py`는 `pyproject.toml` coverage omit. `_build_page_url` 단위 테스트는 use case 레벨 mock으로 검증.
- **기존 5개 테스트 호환성**: `WeeklyPageConfig`는 변경하지 않음, 새 인자는 모두 default 값 → 기존 fixture/호출 그대로 동작.

## 제약사항 (Constraints)

- Clean Architecture 의존성 방향 준수 (Domain → Application → Infrastructure)
- 기존 `@dataclass(frozen=True)` 패턴 유지 (`WeeklyPageConfig` 변경 없음)
- 기존 `SlackAdapter.send(message, thread_message)` 시그니처 변경 금지
- 기존 `NotificationPort.send` Protocol 시그니처 변경 금지
- `ConfluencePort` 메서드 추가/제거 없음 (반환 dict shape 계약만 docstring으로 명시)
- Python 3.12+ 타입 힌트 스타일 (`str | None`, `list[str]` 등)
- 모든 코드 변경은 TDD: Red → Green → Refactor → Commit

## 스킬 검색 (Skill Discovery)

Memory(`MEMORY.md`)에 스킬 매핑 테이블 없음 → fresh 검색.

| 스킬/Agent | 용도 | 적용 Task |
|---|---|---|
| `superpowers:test-driven-development` | TDD Red-Green-Refactor 사이클 강제 | 모든 코드 변경 Task (1-7) |
| `superpowers:verification-before-completion` | "통과" 주장 전 실제 명령 결과 확인 | 모든 Task의 마지막 step |
| `superpowers:systematic-debugging` | 테스트/구현 실패 시 root cause 추적 | 디버깅 필요 시 |
| `superpowers:subagent-driven-development` | Fresh subagent per task + two-stage review | 플랜 실행 (선택) |
| `superpowers:executing-plans` | Inline batch execution + checkpoints | 플랜 실행 (선택) |
| `/rl` (slash command) | Task별 검증 — `.claude/ralph-loop.local.md` 단일 상태 파일 사용 | 각 Task 완료 후, 플랜 최종 검증 |
| Memory 저장 | 다음 Task에서 매핑 재사용 | 플랜 완료 후 사용자 확인 |

> **CLAUDE.md 규칙**: Task는 순차 실행 (병렬 금지, /rl 파일 충돌). 각 Task 완료 후 `/rl`로 검증.

---

## File Structure

| 파일 | 역할 | 변경 유형 |
|---|---|---|
| `src/domain/models.py` | `CreatePageStatus(str, Enum)` 추가 | Modify |
| `src/application/create_page_use_case.py` | `STATUS_LABELS` + `_notify` + `_already_notified` 래치 + outer try/except + `_build_title` | Modify |
| `src/application/ports.py` | `ConfluencePort.get_page_by_title` docstring 갱신 (반환 dict에 `'url'` 키 명시) | Modify (주석만) |
| `src/infrastructure/config.py` | `AppConfig.slack_channel_create_page` 필드 + env 로딩 | Modify |
| `src/infrastructure/adapters/confluence_adapter.py` | `_build_page_url` 헬퍼 + `get_page_by_title` 반환 dict에 `'url'` 키 추가 | Modify |
| `src/main.py` | `create_page` 분기에서 `SlackAdapter` 인스턴스화 + `notification_prefix` 전달 | Modify |
| `README.md` | `SLACK_CHANNEL_CREATE_PAGE` 환경변수 문서화 | Modify |
| `tests/unit/domain/test_create_page_status.py` | Enum semantic 값 검증 | Create |
| `tests/unit/application/test_create_page_use_case.py` | `STATUS_LABELS`, 알림 호출, 래치, pre-try, prefix 케이스 추가 | Modify |
| `tests/unit/infrastructure/test_config.py` | `SLACK_CHANNEL_CREATE_PAGE` env 로딩 케이스 추가 | Modify |
| `tests/unit/infrastructure/test_page_transformer.py` | XML 표준 엔티티 보존 분기 (선결, 별도 commit) | Modify |

---

## Task 0 (Prerequisite, 별도 commit): page_transformer.py 100% 베이스라인 확보

> **Skill mapping**: TDD, verification-before-completion. **완료조건**: `page_transformer.py` 커버리지 100%, 전체 99% → 100%.

본 spec 작업과 무관한 coverage 갭. 별도 commit으로 본 spec 시작 전 베이스라인 확보.

**Files:**
- Modify: `tests/unit/infrastructure/test_page_transformer.py`

- [ ] **Step 1: 현재 갭 확인**

Run: `uv run pytest --cov=src --cov-report=term-missing 2>&1 | grep "page_transformer.py"`
Expected: `... 121      4     50      0    96%   23-26`

- [ ] **Step 2: XML 엔티티 보존 테스트 추가 (Red)**

Find the existing test file. If `tests/unit/infrastructure/test_page_transformer.py` doesn't exist, create it. Add this test in the appropriate test class (or create one):

```python
"""PageTransformer XML entity preservation 테스트"""
from src.infrastructure.adapters.page_transformer import _unescape_html_entities


class TestUnescapeHtmlEntities:
    """HTML 엔티티 변환 — XML 표준 엔티티는 보존, 그 외는 unicode 변환"""

    def test_should_preserve_xml_standard_entities(self):
        # Given: XML 표준 엔티티 5개 (amp, lt, gt, quot, apos)
        text = "&amp;&lt;&gt;&quot;&apos;"

        # When: 변환하면
        result = _unescape_html_entities(text)

        # Then: 그대로 보존된다 (XML 파싱 깨지지 않게)
        assert result == "&amp;&lt;&gt;&quot;&apos;"

    def test_should_unescape_non_xml_html_entities(self):
        # Given: 일반 HTML 엔티티
        text = "&rarr;&nbsp;&copy;"

        # When: 변환하면
        result = _unescape_html_entities(text)

        # Then: 유니코드로 변환된다
        assert result == "→\xa0©"

    def test_should_handle_mixed_entities(self):
        # Given: XML 표준 + 일반 HTML 엔티티 혼합
        text = "&amp; and &rarr; and &lt;"

        # When: 변환하면
        result = _unescape_html_entities(text)

        # Then: XML은 보존, 일반은 변환
        assert result == "&amp; and → and &lt;"
```

- [ ] **Step 3: 테스트 실행 (이미 import 가능하므로 PASS 예상)**

Run: `uv run pytest tests/unit/infrastructure/test_page_transformer.py::TestUnescapeHtmlEntities -v`
Expected: 3 PASS (구현은 이미 존재; 테스트가 missing branch를 cover)

- [ ] **Step 4: 커버리지 100% 확인 (Green)**

Run: `uv run pytest --cov=src --cov-report=term-missing 2>&1 | tail -25`
Expected: `page_transformer.py ... 100%`, `TOTAL ... 100%`

- [ ] **Step 5: Commit**

```bash
git add tests/unit/infrastructure/test_page_transformer.py
git commit -m "$(cat <<'EOF'
test(infra): cover XML entity preservation branch in page_transformer

_unescape_html_entities의 XML 표준 엔티티(&amp;, &lt;, &gt;, &quot;, &apos;)
보존 분기(lines 23-26)에 대한 테스트 추가. 전체 커버리지 99% → 100%.

prerequisite for create_page slack notification feature.
EOF
)"
```

- [ ] **Step 6: /rl로 Task 검증**

Run: `/rl Task 0 완료조건: page_transformer.py 커버리지 100%, 전체 100%`

---

## Task 1: `CreatePageStatus` Enum (domain)

> **Skill mapping**: TDD. **완료조건**: `CreatePageStatus.CREATED.value == "created"` 등 3개 값 검증, semantic-only (no presentation).

**Files:**
- Modify: `src/domain/models.py`
- Create: `tests/unit/domain/test_create_page_status.py`

- [ ] **Step 1: 실패 테스트 작성 (Red)**

Create `tests/unit/domain/test_create_page_status.py`:

```python
"""CreatePageStatus Enum 테스트 — semantic 값 검증, presentation 문자열 부재 검증"""
from src.domain.models import CreatePageStatus


class TestCreatePageStatus:
    """create_page 유스케이스 결과 enum"""

    def test_created_value_is_semantic_identifier(self):
        # Given/When/Then: enum value는 semantic identifier (Korean/emoji 아님)
        assert CreatePageStatus.CREATED.value == "created"

    def test_already_exists_value_is_semantic_identifier(self):
        # Given/When/Then
        assert CreatePageStatus.ALREADY_EXISTS.value == "already_exists"

    def test_failed_value_is_semantic_identifier(self):
        # Given/When/Then
        assert CreatePageStatus.FAILED.value == "failed"

    def test_should_be_str_enum(self):
        # Given/When: str mixin enum이어야 dict key/log 사용 시 안정적
        # Then
        assert isinstance(CreatePageStatus.CREATED, str)
        assert CreatePageStatus.CREATED == "created"

    def test_value_format_is_lockable(self):
        # Given: f-string 포맷 시 .value 사용
        # When/Then: f"{status.value}"가 'created' 반환 (Python 3.11 StrEnum 거동 lock-in)
        status = CreatePageStatus.CREATED
        assert f"{status.value}" == "created"
```

- [ ] **Step 2: 테스트 실행 (Red 확인)**

Run: `uv run pytest tests/unit/domain/test_create_page_status.py -v`
Expected: FAIL (`ImportError: cannot import name 'CreatePageStatus'`)

- [ ] **Step 3: 최소 구현 (Green)**

Edit `src/domain/models.py`. Append at the end of the file (after existing dataclasses):

```python
from enum import Enum


class CreatePageStatus(str, Enum):
    """create_page 유스케이스 실행 결과 (semantic identifier)

    값은 Korean/emoji가 아닌 semantic identifier. 사용자에게 보이는 라벨은
    application 레이어의 STATUS_LABELS dict에 mapping된다 (Clean Architecture
    의 도메인-프레젠테이션 분리 준수).
    """
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"
    FAILED = "failed"
```

> **주의**: 파일 상단에 이미 `from dataclasses import dataclass`가 있을 것. `from enum import Enum`도 상단에 추가하거나 파일 맨 위에 import 모음에 추가.

- [ ] **Step 4: 테스트 실행 (Green 확인)**

Run: `uv run pytest tests/unit/domain/test_create_page_status.py -v`
Expected: 5 PASS

- [ ] **Step 5: 회귀 확인**

Run: `uv run pytest tests/unit/domain/ -v`
Expected: 모든 domain 테스트 PASS (기존 + 새 5개)

- [ ] **Step 6: Commit**

```bash
git add src/domain/models.py tests/unit/domain/test_create_page_status.py
git commit -m "$(cat <<'EOF'
feat(domain): add CreatePageStatus enum

create_page 유스케이스 결과를 semantic identifier(created/already_exists/
failed)로 표현. presentation 문자열은 application 레이어 STATUS_LABELS에
별도 분리.

Spec: docs/superpowers/specs/2026-04-27-create-page-slack-notification-design.md §5
EOF
)"
```

- [ ] **Step 7: /rl로 Task 검증**

Run: `/rl Task 1 완료조건: CreatePageStatus enum이 domain에 추가됨, 3개 값(created/already_exists/failed) semantic, str mixin, 5개 테스트 통과`

---

## Task 2: `STATUS_LABELS` (application 레이어)

> **Skill mapping**: TDD. **완료조건**: `STATUS_LABELS`가 application 레이어에 존재, 3개 enum 값 모두 매핑.

**Files:**
- Modify: `src/application/create_page_use_case.py`
- Modify: `tests/unit/application/test_create_page_use_case.py`

- [ ] **Step 1: 실패 테스트 작성 (Red)**

Edit `tests/unit/application/test_create_page_use_case.py`. Add at the top, after existing imports:

```python
from src.application.create_page_use_case import STATUS_LABELS
from src.domain.models import CreatePageStatus
```

Add a new test class (after the existing `TestCreateWeeklyPageUseCase` class):

```python
class TestStatusLabels:
    """STATUS_LABELS — application 레이어 presentation mapping"""

    def test_created_label_is_korean_with_emoji(self):
        # Given/When/Then
        assert STATUS_LABELS[CreatePageStatus.CREATED] == "✅ 생성 완료"

    def test_already_exists_label_is_korean_with_emoji(self):
        # Given/When/Then
        assert STATUS_LABELS[CreatePageStatus.ALREADY_EXISTS] == "ℹ️ 이미 존재"

    def test_failed_label_is_korean_with_emoji(self):
        # Given/When/Then
        assert STATUS_LABELS[CreatePageStatus.FAILED] == "❌ 생성 실패"

    def test_all_enum_values_have_labels(self):
        # Given: 모든 enum 값
        # When/Then: STATUS_LABELS에 키 누락 없음 (KeyError 방지)
        for status in CreatePageStatus:
            assert status in STATUS_LABELS
            assert isinstance(STATUS_LABELS[status], str)
            assert len(STATUS_LABELS[status]) > 0
```

- [ ] **Step 2: 테스트 실행 (Red 확인)**

Run: `uv run pytest tests/unit/application/test_create_page_use_case.py::TestStatusLabels -v`
Expected: FAIL (`ImportError: cannot import name 'STATUS_LABELS'`)

- [ ] **Step 3: 최소 구현 (Green)**

Edit `src/application/create_page_use_case.py`. Add `CreatePageStatus` import and `STATUS_LABELS` dict at module level (above the class):

```python
"""주간 페이지 자동 생성 유스케이스"""

from datetime import date, timedelta

from ..domain.models import CreatePageStatus, WeeklyPageConfig
from ..domain.services import (
    calculate_last_week_range,
    calculate_this_week_range,
    format_confluence_page_title,
)
from .ports import ConfluencePort, PageTransformerPort


# 모듈 레벨 — application 레이어 (presentation mapping은 use case가 책임)
STATUS_LABELS: dict[CreatePageStatus, str] = {
    CreatePageStatus.CREATED: "✅ 생성 완료",
    CreatePageStatus.ALREADY_EXISTS: "ℹ️ 이미 존재",
    CreatePageStatus.FAILED: "❌ 생성 실패",
}


class CreateWeeklyPageUseCase:
    """이전 주 Confluence 페이지를 복사하여 새 주간 페이지 생성"""
    # ... 기존 본문 그대로 ...
```

> **주의**: 기존 `from ..domain.models import WeeklyPageConfig` 라인을 위처럼 `CreatePageStatus, WeeklyPageConfig`로 합치기. 기존 `class CreateWeeklyPageUseCase:` 본문은 변경하지 말 것.

- [ ] **Step 4: 테스트 실행 (Green 확인)**

Run: `uv run pytest tests/unit/application/test_create_page_use_case.py::TestStatusLabels -v`
Expected: 4 PASS

- [ ] **Step 5: 회귀 확인 (기존 5개 테스트도 통과해야 함)**

Run: `uv run pytest tests/unit/application/test_create_page_use_case.py -v`
Expected: 9 PASS (5 기존 + 4 신규)

- [ ] **Step 6: Commit**

```bash
git add src/application/create_page_use_case.py tests/unit/application/test_create_page_use_case.py
git commit -m "$(cat <<'EOF'
feat(application): add STATUS_LABELS mapping for CreatePageStatus

CreatePageStatus → presentation 라벨 매핑을 application 레이어에 위치.
domain 레이어에 Korean/emoji 노출 금지(spec Don't #3) 준수.

Spec: docs/superpowers/specs/2026-04-27-create-page-slack-notification-design.md §5
EOF
)"
```

- [ ] **Step 7: /rl로 Task 검증**

Run: `/rl Task 2 완료조건: STATUS_LABELS가 src/application/create_page_use_case.py 모듈 레벨에 위치, 3개 enum 값 모두 매핑, 9개 테스트 통과`

---

## Task 3: `AppConfig.slack_channel_create_page` env 로딩

> **Skill mapping**: TDD. **완료조건**: `SLACK_CHANNEL_CREATE_PAGE` env 설정 시 `slack_channel_create_page` 채워짐, 미설정 시 빈 문자열.

**Files:**
- Modify: `src/infrastructure/config.py`
- Modify: `tests/unit/infrastructure/test_config.py`

- [ ] **Step 1: 실패 테스트 작성 (Red)**

Edit `tests/unit/infrastructure/test_config.py`. Find the existing test class (likely `TestLoadConfigFromEnv`) and add new tests. If unsure about exact structure, place at the end of the file:

```python
class TestLoadConfigFromEnvCreatePageNotification:
    """SLACK_CHANNEL_CREATE_PAGE env 로딩"""

    def test_should_load_slack_channel_create_page_when_set(self, monkeypatch):
        # Given: env 변수 설정
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.setenv("SLACK_CHANNEL_CREATE_PAGE", "C12345CREATE")

        # When: 설정 로드
        from src.infrastructure.config import load_config_from_env
        config = load_config_from_env()

        # Then: slack_channel_create_page 필드에 채워진다
        assert config is not None
        assert config.slack_channel_create_page == "C12345CREATE"

    def test_should_default_slack_channel_create_page_to_empty_when_unset(self, monkeypatch):
        # Given: SLACK_CHANNEL_CREATE_PAGE 미설정
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.delenv("SLACK_CHANNEL_CREATE_PAGE", raising=False)

        # When: 설정 로드
        from src.infrastructure.config import load_config_from_env
        config = load_config_from_env()

        # Then: 빈 문자열 (None 아님 — dataclass default)
        assert config is not None
        assert config.slack_channel_create_page == ""
```

- [ ] **Step 2: 테스트 실행 (Red 확인)**

Run: `uv run pytest tests/unit/infrastructure/test_config.py::TestLoadConfigFromEnvCreatePageNotification -v`
Expected: FAIL (`AttributeError: 'AppConfig' object has no attribute 'slack_channel_create_page'`)

- [ ] **Step 3: 최소 구현 (Green)**

Edit `src/infrastructure/config.py`. Add `slack_channel_create_page` field to `AppConfig` (alphabetical/logical placement near other slack fields):

```python
@dataclass
class AppConfig:
    """애플리케이션 전체 설정"""
    report: ReportConfig
    slack_token: str
    slack_channel: str
    cli_type: str
    report_mode: str = "daily"
    slack_channel_weekly: str = ""
    slack_channel_create_page: str = ""  # 추가
    confluence_url: str = ""
    confluence_user: str = ""
    confluence_token: str = ""
    parent_page_id: str = ""
```

In `load_config_from_env`, add the env loading line in the `AppConfig(...)` construction:

```python
return AppConfig(
    report=report_config,
    slack_token=os.environ.get("SLACK_TOKEN", ""),
    slack_channel=os.environ.get("SLACK_CHANNEL", ""),
    slack_channel_weekly=os.environ.get("SLACK_CHANNEL_WEEKLY", ""),
    slack_channel_create_page=os.environ.get("SLACK_CHANNEL_CREATE_PAGE", ""),  # 추가
    cli_type=cli_type,
    report_mode=report_mode,
    confluence_url=os.environ.get("CONFLUENCE_URL", ""),
    confluence_user=os.environ.get("CONFLUENCE_USER", ""),
    confluence_token=os.environ.get("CONFLUENCE_TOKEN", ""),
    parent_page_id=os.environ.get("PARENT_PAGE_ID", ""),
)
```

- [ ] **Step 4: 테스트 실행 (Green 확인)**

Run: `uv run pytest tests/unit/infrastructure/test_config.py -v`
Expected: 모든 기존 + 신규 2개 PASS

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/config.py tests/unit/infrastructure/test_config.py
git commit -m "$(cat <<'EOF'
feat(infra): add SLACK_CHANNEL_CREATE_PAGE env loading

AppConfig에 slack_channel_create_page 필드 추가. 미설정 시 빈 문자열
(main.py가 None notifier 결정에 사용).

Spec: docs/superpowers/specs/2026-04-27-create-page-slack-notification-design.md §4
EOF
)"
```

- [ ] **Step 6: /rl로 Task 검증**

Run: `/rl Task 3 완료조건: AppConfig.slack_channel_create_page 필드 추가, env 로딩 동작, 2개 신규 테스트 통과`

---

## Task 4: `ConfluenceAdapter._build_page_url` 헬퍼 + `get_page_by_title` URL 키

> **Skill mapping**: TDD (단, ConfluenceAdapter는 coverage omit이므로 단위 테스트는 use case 레벨에서 mock으로). **완료조건**: A/B 케이스에서 사용되는 URL이 단일 헬퍼 함수를 통해 byte-level 동일 형식 출력.

**Files:**
- Modify: `src/infrastructure/adapters/confluence_adapter.py`
- Modify: `src/application/ports.py` (docstring만)

> **주의**: `confluence_adapter.py`는 `pyproject.toml`의 coverage `omit`에 포함됨. 직접 단위 테스트 추가하지 않고, use case 레벨 mock 테스트(Task 6)에서 행위 검증.

- [ ] **Step 1: ConfluencePort docstring 갱신**

Edit `src/application/ports.py`. Update `get_page_by_title` docstring:

```python
class ConfluencePort(Protocol):
    """Confluence 페이지 접근 추상 인터페이스"""

    def get_page_by_title(self, space_key: str, title: str) -> dict | None:
        """제목으로 페이지 조회. 없으면 None 반환.

        반환 dict는 'id', 'title', 'url' 키를 포함한다.
        URL은 create_page() 반환과 동일한 형식 (어댑터 내부 _build_page_url로 통일).
        """
        ...

    def get_page_content(self, page_id: str) -> str:
        """페이지의 storage format HTML 조회"""
        ...

    def create_page(self, space_key: str, title: str, content: str, parent_id: str) -> str:
        """새 페이지 생성. 생성된 페이지 URL 반환."""
        ...
```

> **주의**: 메서드 추가/제거 없음. docstring만 변경.

- [ ] **Step 2: ConfluenceAdapter 변경 (Green)**

Edit `src/infrastructure/adapters/confluence_adapter.py`:

```python
"""Confluence REST API 어댑터"""

import requests
from atlassian import Confluence


class ConfluenceAdapter:
    """atlassian-python-api + REST API v2를 사용한 Confluence 페이지 접근"""

    def __init__(self, url: str, user: str, token: str):
        self.client = Confluence(url=url, username=user, password=token)
        base = url.rstrip("/")
        self._v2_base_url = base if base.endswith("/wiki") else f"{base}/wiki"
        self._auth = (user, token)

    def _build_page_url(self, page_id: str, space_key: str, title: str) -> str:
        """v2 API URL 형식으로 페이지 URL 구성 (private helper).

        A 케이스(create_page)와 B 케이스(get_page_by_title)가 동일 형식을 갖도록
        단일 진입점으로 사용.
        """
        return f"{self._v2_base_url}/spaces/{space_key}/pages/{page_id}/{title}"

    def get_page_by_title(self, space_key: str, title: str) -> dict | None:
        """제목으로 페이지 조회. 반환 dict에 'url' 키 추가."""
        page = self.client.get_page_by_title(space_key, title)
        if page is None:
            return None
        # use case가 일관된 URL 형식 사용 가능하도록 'url' 필드 추가
        page["url"] = self._build_page_url(page["id"], space_key, title)
        return page

    def get_page_content(self, page_id: str) -> str:
        """페이지의 storage format HTML 조회"""
        page = self.client.get_page_by_id(page_id, expand="body.storage")
        return page["body"]["storage"]["value"]

    def get_space_id(self, space_key: str) -> str:
        """space key로 space ID(숫자) 조회 (v2 API용)"""
        resp = requests.get(
            f"{self._v2_base_url}/api/v2/spaces?keys={space_key}",
            auth=self._auth,
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            raise ValueError(f"Space not found: {space_key}")
        return results[0]["id"]

    def create_page(
        self, space_key: str, title: str, content: str, parent_id: str
    ) -> str:
        """Live Page로 새 페이지 생성 (v2 API). 생성된 페이지 URL 반환."""
        space_id = self.get_space_id(space_key)

        payload = {
            "spaceId": space_id,
            "title": title,
            "parentId": parent_id,
            "status": "current",
            "subtype": "live",
            "body": {
                "representation": "storage",
                "value": content,
            },
        }

        resp = requests.post(
            f"{self._v2_base_url}/api/v2/pages",
            json=payload,
            auth=self._auth,
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        page_id = result["id"]
        return self._build_page_url(page_id, space_key, title)
```

> **변경 핵심**: (1) `_build_page_url` 헬퍼 추가, (2) `get_page_by_title`이 `'url'` 키 포함하여 반환, (3) `create_page`의 마지막 라인이 헬퍼 호출로 변경.

- [ ] **Step 3: 회귀 테스트 실행**

Run: `uv run pytest tests/unit/ -v`
Expected: 모든 기존 테스트 PASS (ConfluenceAdapter는 coverage omit이지만 다른 테스트가 의존하지 않으므로 영향 없음)

- [ ] **Step 4: Commit**

```bash
git add src/infrastructure/adapters/confluence_adapter.py src/application/ports.py
git commit -m "$(cat <<'EOF'
refactor(infra): unify confluence page URL via _build_page_url helper

(1) ConfluenceAdapter에 _build_page_url(page_id, space_key, title) private
헬퍼 추가, (2) get_page_by_title 반환 dict에 'url' 키 추가, (3) create_page도
동일 헬퍼 사용. A/B 케이스 URL byte-level 동일 보장.

ConfluencePort 메서드 시그니처 변경 없음 (docstring만 갱신하여 'url' 키 계약 명시).

Spec: docs/superpowers/specs/2026-04-27-create-page-slack-notification-design.md §4
EOF
)"
```

- [ ] **Step 5: /rl로 Task 검증**

Run: `/rl Task 4 완료조건: _build_page_url 헬퍼 추가, get_page_by_title이 'url' 키 반환, create_page도 동일 헬퍼 사용, ConfluencePort 메서드 변경 없음, 모든 테스트 통과`

---

## Task 5: `_build_title` + `_notify` + 생성자 확장 (notifier 인프라)

> **Skill mapping**: TDD. **완료조건**: notifier 주입 가능, `_build_title`이 spec 형식 출력, `_notify`가 알림 + 격리 동작, `_already_notified` 래치 초기화.

**Files:**
- Modify: `src/application/create_page_use_case.py`
- Modify: `tests/unit/application/test_create_page_use_case.py`

- [ ] **Step 1: 실패 테스트 작성 (Red) — `_build_title`**

Edit `tests/unit/application/test_create_page_use_case.py`. Add a new fixture and test class (after existing test classes):

```python
from datetime import date as _date
from unittest.mock import MagicMock as _MagicMock
from src.application.create_page_use_case import CreateWeeklyPageUseCase as _UseCase
from src.domain.models import CreatePageStatus as _Status, DateRange as _DateRange


@pytest.fixture
def mock_notifier():
    return MagicMock()


@pytest.fixture
def use_case_with_notifier(mock_confluence, mock_transformer, mock_notifier):
    return CreateWeeklyPageUseCase(
        confluence=mock_confluence,
        transformer=mock_transformer,
        notifier=mock_notifier,
    )


class TestBuildTitle:
    """_build_title 헬퍼 — Slack 알림 제목 생성"""

    def test_should_build_title_with_prefix(self, use_case_with_notifier):
        # Given: 2026-04-27(월) ~ 2026-05-01(금) 주간
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When: prefix='BE', status=CREATED로 제목 생성
        title = use_case_with_notifier._build_title(
            "BE", this_week, _Status.CREATED
        )

        # Then: spec §5 형식
        assert title == "[BE][26.04.27 ~ 05.01_WeeklyPage] ✅ 생성 완료"

    def test_should_build_title_without_prefix_when_empty(self, use_case_with_notifier):
        # Given: prefix 빈 문자열
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When
        title = use_case_with_notifier._build_title(
            "", this_week, _Status.ALREADY_EXISTS
        )

        # Then: [BE] 부분 생략
        assert title == "[26.04.27 ~ 05.01_WeeklyPage] ℹ️ 이미 존재"

    def test_should_use_failed_label(self, use_case_with_notifier):
        # Given
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When
        title = use_case_with_notifier._build_title("BE", this_week, _Status.FAILED)

        # Then
        assert title == "[BE][26.04.27 ~ 05.01_WeeklyPage] ❌ 생성 실패"


class TestNotify:
    """_notify — 알림 전송 + 격리"""

    def test_should_skip_when_notifier_is_none(self, mock_confluence, mock_transformer):
        # Given: notifier 없는 use case
        use_case = _UseCase(confluence=mock_confluence, transformer=mock_transformer)
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When: _notify 호출 (notifier=None)
        use_case._notify(_Status.CREATED, "BE", this_week, "url")

        # Then: 어떤 send도 호출되지 않음 (예외도 X)
        # (mock이 아예 없으므로 검증은 예외 미발생으로 충분)

    def test_should_send_notification_when_notifier_set(
        self, use_case_with_notifier, mock_notifier
    ):
        # Given: notifier 주입된 use case
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When: _notify 호출
        use_case_with_notifier._notify(_Status.CREATED, "BE", this_week, "https://...")

        # Then: notifier.send 호출됨, _already_notified=True 설정
        mock_notifier.send.assert_called_once()
        call_args = mock_notifier.send.call_args
        assert call_args[0][0] == "[BE][26.04.27 ~ 05.01_WeeklyPage] ✅ 생성 완료"
        assert call_args[0][1] == "https://..."
        assert use_case_with_notifier._already_notified is True

    def test_should_swallow_notifier_exception(
        self, use_case_with_notifier, mock_notifier
    ):
        # Given: notifier.send가 예외 발생
        mock_notifier.send.side_effect = RuntimeError("Slack down")
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When: _notify 호출
        # Then: 예외 전파되지 않음
        try:
            use_case_with_notifier._notify(
                _Status.FAILED, "BE", this_week, "error body"
            )
        except RuntimeError:
            pytest.fail("_notify should swallow notifier exceptions")

        # 그리고 _already_notified는 False 유지 (실패한 알림은 latch 트리거 안 함)
        assert use_case_with_notifier._already_notified is False
```

- [ ] **Step 2: 테스트 실행 (Red 확인)**

Run: `uv run pytest tests/unit/application/test_create_page_use_case.py::TestBuildTitle tests/unit/application/test_create_page_use_case.py::TestNotify -v`
Expected: FAIL (notifier 인자 미지원, `_build_title`/`_notify` 미구현, `_already_notified` 미존재)

- [ ] **Step 3: 최소 구현 (Green)**

Edit `src/application/create_page_use_case.py`. Add imports at top:

```python
"""주간 페이지 자동 생성 유스케이스"""

import traceback
from datetime import date, timedelta

from ..domain.models import CreatePageStatus, DateRange, WeeklyPageConfig
from ..domain.services import (
    calculate_last_week_range,
    calculate_this_week_range,
    format_confluence_page_title,
)
from .ports import ConfluencePort, NotificationPort, PageTransformerPort
```

Update the class — extend `__init__` and add `_build_title` + `_notify` (place them as methods of `CreateWeeklyPageUseCase`):

```python
class CreateWeeklyPageUseCase:
    """이전 주 Confluence 페이지를 복사하여 새 주간 페이지 생성"""

    def __init__(
        self,
        confluence: ConfluencePort,
        transformer: PageTransformerPort,
        notifier: NotificationPort | None = None,
    ):
        self.confluence = confluence
        self.transformer = transformer
        self._notifier = notifier
        self._already_notified: bool = False

    # ... 기존 execute() 본문 그대로 ... (Task 6에서 수정)

    def _build_title(
        self,
        prefix: str,
        this_week: DateRange,
        status: CreatePageStatus,
    ) -> str:
        """Slack 알림 제목 생성"""
        start = this_week.start.strftime('%y.%m.%d')
        end = this_week.end.strftime('%m.%d')
        bracket = f"[{prefix}]" if prefix else ""
        label = STATUS_LABELS[status]
        return f"{bracket}[{start} ~ {end}_WeeklyPage] {label}"

    def _notify(
        self,
        status: CreatePageStatus,
        prefix: str,
        this_week: DateRange,
        body: str,
    ) -> None:
        """알림 전송 (격리됨, notifier=None이면 스킵, 예외 swallow)"""
        if self._notifier is None:
            return
        title = self._build_title(prefix, this_week, status)
        try:
            self._notifier.send(title, body)
            self._already_notified = True
        except Exception as e:
            print(
                f"WARNING: Slack notification failed (status={status.value}): {e}\n"
                f"{traceback.format_exc()}"
            )

    def _generate_date_strings(self, monday: date, friday: date) -> list[str]:
        # ... 기존 그대로 ...
```

> **주의**: 기존 `execute()` 본문은 이 Task에서 수정하지 않음 (Task 6에서). 생성자만 확장 + 새 메서드 추가.

- [ ] **Step 4: 테스트 실행 (Green 확인)**

Run: `uv run pytest tests/unit/application/test_create_page_use_case.py -v`
Expected: 기존 5 + 4(STATUS_LABELS) + 3(_build_title) + 3(_notify) = 15 PASS

- [ ] **Step 5: Commit**

```bash
git add src/application/create_page_use_case.py tests/unit/application/test_create_page_use_case.py
git commit -m "$(cat <<'EOF'
feat(application): add notifier infrastructure to CreateWeeklyPageUseCase

(1) 생성자에 Optional NotificationPort 주입, (2) _already_notified latch
초기화, (3) _build_title 메서드(Slack 제목 생성), (4) _notify 메서드
(알림 전송 + 격리 + traceback stderr 출력).

execute() 흐름은 다음 commit에서 통합.

Spec: docs/superpowers/specs/2026-04-27-create-page-slack-notification-design.md §6
EOF
)"
```

- [ ] **Step 6: /rl로 Task 검증**

Run: `/rl Task 5 완료조건: __init__에 notifier=None, _already_notified=False 초기화, _build_title이 spec 형식 출력, _notify가 send 호출+래치 설정+예외 격리, 15개 테스트 통과`

---

## Task 6: `execute()` 확장 (notification_prefix + 케이스별 알림 + outer try/except + 래치)

> **Skill mapping**: TDD. **완료조건**: 4개 케이스 분기에 알림 호출, outer try/except로 모든 예외 catch → FAILED 알림, 래치로 중복 방지, pre-try 가드.

**Files:**
- Modify: `src/application/create_page_use_case.py`
- Modify: `tests/unit/application/test_create_page_use_case.py`

- [ ] **Step 1: 실패 테스트 작성 (Red) — execute 알림 통합**

Edit `tests/unit/application/test_create_page_use_case.py`. Add a new test class:

```python
class TestExecuteNotificationIntegration:
    """execute()에 알림 호출 통합 — 케이스별 알림, 래치, 예외 격리"""

    def test_should_send_created_notification_on_success(
        self, use_case_with_notifier, mock_confluence, mock_transformer, mock_notifier, config
    ):
        # Given: 정상 생성 경로
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123", "title": "2026.04.20 ~ 04.24"},  # 이전 주 존재
            None,  # 새 주 미존재
        ]
        mock_confluence.get_page_content.return_value = "<table>old</table>"
        mock_transformer.transform.return_value = "<table>new</table>"
        mock_confluence.create_page.return_value = "https://wiki/spaces/MAI/pages/456/title"

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: True + CREATED 알림 1회
        assert result is True
        assert mock_notifier.send.call_count == 1
        call_args = mock_notifier.send.call_args
        assert "✅ 생성 완료" in call_args[0][0]
        assert call_args[0][1] == "https://wiki/spaces/MAI/pages/456/title"

    def test_should_send_already_exists_notification_with_url_from_dict(
        self, use_case_with_notifier, mock_confluence, mock_notifier, config
    ):
        # Given: 새 주 페이지가 이미 존재 — get_page_by_title이 'url' 키 포함
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123", "url": "https://wiki/spaces/MAI/pages/123/old"},  # 이전 주
            {"id": "456", "url": "https://wiki/spaces/MAI/pages/456/new"},  # 새 주 (이미 존재)
        ]

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: True (스킵) + ALREADY_EXISTS 알림 with existing_page['url']
        assert result is True
        assert mock_notifier.send.call_count == 1
        call_args = mock_notifier.send.call_args
        assert "ℹ️ 이미 존재" in call_args[0][0]
        assert call_args[0][1] == "https://wiki/spaces/MAI/pages/456/new"

    def test_should_send_failed_notification_when_source_not_found(
        self, use_case_with_notifier, mock_confluence, mock_notifier, config
    ):
        # Given: 이전 주 페이지 없음
        mock_confluence.get_page_by_title.return_value = None

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: False + FAILED 알림 (사유 포함)
        assert result is False
        assert mock_notifier.send.call_count == 1
        call_args = mock_notifier.send.call_args
        assert "❌ 생성 실패" in call_args[0][0]
        assert "이전 주 페이지를 찾을 수 없습니다" in call_args[0][1]

    def test_should_send_failed_notification_on_unexpected_exception(
        self, use_case_with_notifier, mock_confluence, mock_notifier, config
    ):
        # Given: confluence 호출이 예외 발생
        mock_confluence.get_page_by_title.side_effect = RuntimeError("Network timeout")

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: False + FAILED 알림 (예외 메시지 포함)
        assert result is False
        assert mock_notifier.send.call_count == 1
        call_args = mock_notifier.send.call_args
        assert "❌ 생성 실패" in call_args[0][0]
        assert "Unexpected error" in call_args[0][1]
        assert "Network timeout" in call_args[0][1]

    def test_should_not_double_notify_when_post_success_code_raises(
        self, use_case_with_notifier, mock_confluence, mock_transformer, mock_notifier, config, monkeypatch
    ):
        # Given: 정상 생성 후 추가 코드가 raise하는 시나리오
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123"},
            None,
        ]
        mock_confluence.get_page_content.return_value = "<table>old</table>"
        mock_transformer.transform.return_value = "<table>new</table>"
        mock_confluence.create_page.return_value = "https://wiki/url"

        # 성공 알림은 발송됨 → _already_notified=True
        # 그 후 다른 코드가 raise (예: 가상 시나리오 위해 _notify를 monkeypatch)
        original_notify = use_case_with_notifier._notify
        call_log = []

        def notify_then_raise(status, prefix, week, body):
            original_notify(status, prefix, week, body)
            call_log.append(status)
            if status == _Status.CREATED:
                # 성공 알림 후 raise 가정
                raise RuntimeError("Simulated post-success failure")

        monkeypatch.setattr(use_case_with_notifier, "_notify", notify_then_raise)

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: outer except는 _already_notified=True를 보고 추가 알림 발송 안 함
        # → notifier.send 호출은 정확히 1회 (성공 알림만)
        assert result is False  # outer except가 False 반환
        assert mock_notifier.send.call_count == 1  # CREATED만, FAILED 추가 발송 안 됨

    def test_should_skip_notification_when_pre_try_fails(
        self, use_case_with_notifier, mock_notifier, config, monkeypatch
    ):
        # Given: calculate_this_week_range 자체가 raise (this_week=None 가드 검증)
        from src.application import create_page_use_case as cpuc_mod

        def boom(today):
            raise RuntimeError("date calc failed")

        monkeypatch.setattr(cpuc_mod, "calculate_this_week_range", boom)

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: False, 알림 호출 안 됨 (this_week is None 가드)
        assert result is False
        assert mock_notifier.send.call_count == 0

    def test_should_pass_correct_url_in_a_b_cases_consistently(
        self, use_case_with_notifier, mock_confluence, mock_transformer, mock_notifier, config
    ):
        # Given: A 케이스용 mock — 동일한 URL 형식
        SAME_URL = "https://wiki/spaces/MAI/pages/456/title"

        # B 케이스 시나리오: get_page_by_title이 'url' 키로 같은 URL 반환
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123", "url": "https://wiki/spaces/MAI/pages/123/old"},
            {"id": "456", "url": SAME_URL},
        ]

        # When: B 케이스 실행
        use_case_with_notifier.execute(config, target_date=date(2026, 4, 27))

        # Then: 알림 thread에 'url' 키 값이 그대로 전달
        call_args = mock_notifier.send.call_args
        assert call_args[0][1] == SAME_URL


class TestExecuteWithoutNotifier:
    """notifier=None 일 때 실행 — 알림 스킵, 페이지 동작 정상"""

    def test_should_run_normally_when_notifier_is_none(
        self, use_case, mock_confluence, mock_transformer, config
    ):
        # Given: notifier 없음 (use_case 픽스처 사용)
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123"},
            None,
        ]
        mock_confluence.get_page_content.return_value = "<table>old</table>"
        mock_transformer.transform.return_value = "<table>new</table>"
        mock_confluence.create_page.return_value = "url"

        # When
        result = use_case.execute(config, target_date=date(2026, 4, 27))

        # Then: 페이지 생성 정상, 어떤 알림도 시도되지 않음 (notifier=None이라 호출 자체가 안 일어남)
        assert result is True
        mock_confluence.create_page.assert_called_once()
```

- [ ] **Step 2: 테스트 실행 (Red 확인)**

Run: `uv run pytest tests/unit/application/test_create_page_use_case.py::TestExecuteNotificationIntegration tests/unit/application/test_create_page_use_case.py::TestExecuteWithoutNotifier -v`
Expected: FAIL (execute()가 아직 알림 호출 안 함, notification_prefix 인자 미지원)

- [ ] **Step 3: 최소 구현 (Green)**

Edit `src/application/create_page_use_case.py`. Replace the `execute()` method with the integrated version:

```python
    def execute(
        self,
        config: WeeklyPageConfig,
        target_date: date | None = None,
        notification_prefix: str = "",
    ) -> bool:
        """
        새 주간 페이지 생성 + Slack 알림.
        Returns: True (성공/스킵), False (실패).
        알림은 부수효과 — boolean 결과를 오염시키지 않음.
        """
        self._already_notified = False
        this_week: DateRange | None = None

        try:
            today = target_date or date.today()

            # 1. 날짜 계산
            last_week = calculate_last_week_range(today)
            this_week = calculate_this_week_range(today)
            old_title = format_confluence_page_title(last_week)
            new_title = format_confluence_page_title(this_week)

            print(f"Source page: {old_title}")
            print(f"Target page: {new_title}")

            # 2. 이전 주 페이지 조회
            source_page = self.confluence.get_page_by_title(config.space_key, old_title)
            if source_page is None:
                err = f"이전 주 페이지를 찾을 수 없습니다: {old_title}"
                print(f"ERROR: {err}")
                self._notify(CreatePageStatus.FAILED, notification_prefix, this_week, err)
                return False

            # 3. 새 주 페이지 중복 확인
            existing_page = self.confluence.get_page_by_title(config.space_key, new_title)
            if existing_page is not None:
                print(f"Page already exists: {new_title} — skipping.")
                self._notify(
                    CreatePageStatus.ALREADY_EXISTS,
                    notification_prefix,
                    this_week,
                    existing_page["url"],
                )
                return True

            # 4. 이전 페이지 HTML 가져오기
            html = self.confluence.get_page_content(source_page["id"])

            # 5. HTML 변환
            old_dates = self._generate_date_strings(last_week.start, last_week.end)
            new_dates = self._generate_date_strings(this_week.start, this_week.end)
            new_html = self.transformer.transform(html, old_dates, new_dates)

            # 6. 새 페이지 생성
            url = self.confluence.create_page(
                space_key=config.space_key,
                title=new_title,
                content=new_html,
                parent_id=config.parent_page_id,
            )
            print(f"Created: {url}")
            self._notify(CreatePageStatus.CREATED, notification_prefix, this_week, url)
            return True

        except Exception as e:
            body = f"Unexpected error: {type(e).__name__}: {e}"
            print(f"ERROR: create_page unexpected exception: {body}")
            # I2 래치: 이미 알림 보냈으면 추가 알림 안 보냄
            # M1 가드: pre-try에서 this_week가 None일 수 있음
            if not self._already_notified and this_week is not None:
                self._notify(
                    CreatePageStatus.FAILED, notification_prefix, this_week, body
                )
            return False
```

> **변경 핵심**: (1) 시그니처에 `notification_prefix: str = ""` 추가, (2) 매 호출 시작에 `_already_notified=False` 초기화, (3) `this_week: DateRange | None = None` pre-try 초기화, (4) 본문 try/except로 감쌈, (5) 케이스별 `_notify` 호출 추가, (6) outer except에 래치+가드 적용.

- [ ] **Step 4: 테스트 실행 (Green 확인)**

Run: `uv run pytest tests/unit/application/test_create_page_use_case.py -v`
Expected: 기존 5 + STATUS_LABELS 4 + _build_title 3 + _notify 3 + Integration 7 + WithoutNotifier 1 = 23 PASS

> 일부 기존 테스트가 시그니처 변경으로 영향받을 수 있음. 만약 실패하면:
> - `test_should_skip_when_page_already_exists` 등에서 `existing_page` mock에 `'url'` 키 추가 필요. 예: `{"id": "456", "url": "fake-url"}`. 단, 이 테스트는 `mock_confluence.get_page_by_title.side_effect = [{"id": "123"}, {"id": "456"}]` 형식이므로 `'url'` 누락 → KeyError 발생 가능.
> - 해결: 기존 테스트의 `existing_page` mock에 `"url": "..."` 추가하거나, 테스트가 `existing_page['url']` 접근에 도달하지 않으면 그대로.

- [ ] **Step 5: 기존 테스트 회귀 fix (필요 시)**

If `test_should_skip_when_page_already_exists` fails with `KeyError: 'url'`, edit it to include `'url'`:

Find:
```python
mock_confluence.get_page_by_title.side_effect = [
    {"id": "123"},  # 이전 주 존재
    {"id": "456"},  # 새 주도 존재
]
```

Replace with:
```python
mock_confluence.get_page_by_title.side_effect = [
    {"id": "123"},  # 이전 주 존재 (url 미사용 — get_page_content으로만 접근)
    {"id": "456", "url": "https://fake.url/456"},  # 새 주도 존재 (url 키 필요)
]
```

Run again: `uv run pytest tests/unit/application/test_create_page_use_case.py -v`
Expected: All 23 PASS.

- [ ] **Step 6: Commit**

```bash
git add src/application/create_page_use_case.py tests/unit/application/test_create_page_use_case.py
git commit -m "$(cat <<'EOF'
feat(application): integrate slack notifications into execute()

(1) notification_prefix 인자 추가, (2) 케이스별 _notify 호출
(CREATED/ALREADY_EXISTS/FAILED), (3) outer try/except로 모든 예외를 FAILED
알림으로 변환, (4) _already_notified 래치로 단일 호출당 알림 1개 보장,
(5) pre-try this_week=None 가드.

기존 테스트 회귀: existing_page mock에 'url' 키 추가 (B 케이스에서 dict
key 접근).

Spec: docs/superpowers/specs/2026-04-27-create-page-slack-notification-design.md §6
EOF
)"
```

- [ ] **Step 7: /rl로 Task 검증**

Run: `/rl Task 6 완료조건: execute()에 notification_prefix 인자, 4개 케이스 분기 알림, outer try/except + 래치 + pre-try 가드, 단일 호출당 send ≤ 1회, 23개 테스트 통과`

---

## Task 7: `main.py` 조립

> **Skill mapping**: 통합 — main.py는 단위 테스트 어려움(composition root). 변경 후 수동 검증 + 기존 테스트 회귀 확인. **완료조건**: `create_page` 분기에서 SlackAdapter 인스턴스화 + use case에 `notification_prefix` 전달.

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: main.py 변경**

Edit `src/main.py`. Find the `create_page` branch (currently around lines 53-78) and update:

```python
    if config.report_mode == "create_page":
        from .infrastructure.adapters.confluence_adapter import ConfluenceAdapter
        from .infrastructure.adapters.page_transformer import PageTransformer
        from .application.create_page_use_case import CreateWeeklyPageUseCase
        from .domain.models import WeeklyPageConfig

        if not config.confluence_url or not config.confluence_user or not config.confluence_token:
            print("ERROR: CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_TOKEN must be set.")
            return

        confluence = ConfluenceAdapter(
            url=config.confluence_url,
            user=config.confluence_user,
            token=config.confluence_token,
        )
        transformer = PageTransformer()

        # SlackAdapter 인스턴스화 (env 미설정 시 None — main.py가 primary 가드)
        notifier = (
            SlackAdapter(
                token=config.slack_token,
                channel=config.slack_channel_create_page,
            )
            if config.slack_channel_create_page and config.slack_token
            else None
        )

        use_case = CreateWeeklyPageUseCase(
            confluence=confluence,
            transformer=transformer,
            notifier=notifier,
        )

        weekly_page_config = WeeklyPageConfig(
            space_key=config.report.space_key,
            parent_page_id=config.parent_page_id,
        )
        success = use_case.execute(
            weekly_page_config,
            target_date=report_date,
            notification_prefix=config.report.team_prefix,
        )
        if not success:
            print("ERROR: Failed to create weekly page.")
        return
```

> **변경 핵심**: (1) `SlackAdapter` 인스턴스화 추가 (env 미설정 시 `None`), (2) `CreateWeeklyPageUseCase` 생성자에 `notifier=notifier` 전달, (3) `use_case.execute(...)`에 `notification_prefix=config.report.team_prefix` 전달.

- [ ] **Step 2: 회귀 테스트 실행**

Run: `uv run pytest -v`
Expected: 모든 테스트 PASS (main.py 변경은 기존 테스트에 영향 없음 — main.py는 통합 진입점이라 단위 테스트가 거의 없음)

- [ ] **Step 3: 수동 검증 (smoke test, dry run)**

Run: `uv run python -c "from src.main import main; print('import OK')"`
Expected: `import OK` (import-time error 없음)

> **참고**: 실제 동작 검증은 Task 9의 통합 검증에서 (env 변수 설정 후 `REPORT_MODE=create_page` 실행).

- [ ] **Step 4: Commit**

```bash
git add src/main.py
git commit -m "$(cat <<'EOF'
feat(main): wire SlackAdapter into create_page mode

create_page 분기에서 SLACK_CHANNEL_CREATE_PAGE env가 설정되어 있으면
SlackAdapter 인스턴스화하여 use case에 주입. 미설정 시 None — use case가
notifier=None 가드로 알림 스킵.

notification_prefix=config.report.team_prefix 전달하여 Slack 제목에 [BE] 등
prefix 노출.

Spec: docs/superpowers/specs/2026-04-27-create-page-slack-notification-design.md §6
EOF
)"
```

- [ ] **Step 5: /rl로 Task 검증**

Run: `/rl Task 7 완료조건: main.py create_page 분기에 SlackAdapter 인스턴스화, notifier 주입, notification_prefix 전달, 모든 테스트 회귀 없이 통과`

---

## Task 8: README 문서화

> **Skill mapping**: 문서. **완료조건**: `SLACK_CHANNEL_CREATE_PAGE` env 변수가 README의 환경변수 표/리스트에 등재됨.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 현재 README의 env 변수 섹션 확인**

Run: `grep -n "SLACK_CHANNEL" README.md`
Expected: 기존 `SLACK_CHANNEL`, `SLACK_CHANNEL_WEEKLY` 라인 위치 확인

- [ ] **Step 2: README 변경**

Edit `README.md`. Find the env variable list (around the `Set Environment Variables` section). Add `SLACK_CHANNEL_CREATE_PAGE` near the other Slack channel entries:

In the `.env` example block — find:
```
SLACK_CHANNEL_WEEKLY="YOUR_WEEKLY_SLACK_CHANNEL_ID"  # Optional, separate channel for weekly reports
```

Add immediately after:
```
SLACK_CHANNEL_CREATE_PAGE="YOUR_CREATE_PAGE_SLACK_CHANNEL_ID"  # Optional, separate channel for create_page mode notifications
```

In the descriptions list — find:
```
*   `SLACK_CHANNEL_WEEKLY`: (Optional) The ID of the Slack channel for weekly reports. If not set, weekly reports are skipped (empty channel).
```

Add immediately after:
```
*   `SLACK_CHANNEL_CREATE_PAGE`: (Optional) The ID of the Slack channel for `create_page` mode notifications (success/already-exists/failure). If not set, notifications are skipped — page creation continues normally.
```

- [ ] **Step 3: 변경 확인**

Run: `grep -A 0 "SLACK_CHANNEL_CREATE_PAGE" README.md`
Expected: 2 lines (env 예시 + 설명)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs(readme): document SLACK_CHANNEL_CREATE_PAGE env variable

create_page 모드 실행 결과 알림용 Slack 채널 ID. 미설정 시 알림 스킵,
페이지 생성은 정상 동작.

Spec: docs/superpowers/specs/2026-04-27-create-page-slack-notification-design.md
EOF
)"
```

- [ ] **Step 5: /rl로 Task 검증**

Run: `/rl Task 8 완료조건: README.md에 SLACK_CHANNEL_CREATE_PAGE env 변수 (예시 + 설명) 추가됨`

---

## Task 9: 통합 검증 + 커버리지 100%

> **Skill mapping**: verification-before-completion. **완료조건**: 변경 영향 파일 모두 100% 커버리지 + 전체 100%, 기존 테스트 회귀 0건.

**Files:** (검증만, 변경 없음)

- [ ] **Step 1: 전체 테스트 + 커버리지 실행**

Run: `uv run pytest --cov=src --cov-report=term-missing 2>&1 | tail -30`
Expected:
- 모든 테스트 PASS (이전 168 + 새로 추가된 ~18 = ~186)
- `TOTAL ... 100%`
- `models.py 100%`, `create_page_use_case.py 100%`, `config.py 100%`, `main.py 100%`, `page_transformer.py 100%`

- [ ] **Step 2: 변경 파일별 커버리지 확인**

Run: `uv run pytest --cov=src --cov-report=term-missing 2>&1 | grep -E "(models|create_page_use_case|config|main|page_transformer)\.py"`
Expected: 위 파일들 모두 `100%` 표시 (Missing 컬럼 비어있음)

> **`confluence_adapter.py`는 omit이므로 표시되지 않음** — 이는 정상.

- [ ] **Step 3: 만약 커버리지 갭이 있다면**

If any file is below 100%:
1. `--cov-report=term-missing`의 `Missing` 컬럼에서 누락 라인 확인
2. 해당 라인을 cover하는 테스트를 작성
3. Step 1 다시 실행

> 예상되는 누락 케이스:
> - `_notify`에서 notifier=None 분기를 cover하는 테스트가 빠지면 → `TestNotify.test_should_skip_when_notifier_is_none`이 cover (이미 작성됨)
> - `execute()`의 except 분기 일부 → `TestExecuteNotificationIntegration` 테스트들이 cover

- [ ] **Step 4: 수동 통합 검증 (선택, env 설정된 경우)**

> 실제 Slack/Confluence env가 로컬에 있다면:

```bash
# 정상 케이스 (이미 페이지가 있을 가능성 → ALREADY_EXISTS)
REPORT_MODE=create_page uv run python -m src.main
```

Expected: stdout에 `Page already exists` 또는 `Created: ...` 로그, Slack 채널에 ✅/ℹ️ 메시지.

> env 미설정 환경에서는 import-only smoke test로 충분 (Task 7 Step 3).

- [ ] **Step 5: 최종 plan-level 검증**

Run: `/rl 플랜 완료조건 전체 검증:
- REPORT_MODE=create_page + SLACK_CHANNEL_CREATE_PAGE 채널에 케이스별 메시지
- A/B URL byte-level 동일
- 단일 execute()당 send ≤ 1회 (래치)
- env 미설정 시 알림 스킵 + 페이지 정상
- 알림 실패 시 boolean 영향 없음 + traceback stderr
- 예외 시 FAILED 알림 + False
- STATUS_LABELS는 application 레이어
- ConfluencePort 메서드 변경 없음
- 변경 파일 100% 커버리지
- 기존 5개 테스트 회귀 없음
- README 문서화`

If any criterion fails: 보완 Task를 Task List 끝에 추가하고 동일 형식(완료조건+스킬 매핑)으로 처리.

- [ ] **Step 6: 검증 commit (코드 변경 없음, 검증 로그용)**

```bash
git log --oneline -10
# 8 commits expected: prereq + 7 task commits
```

(별도 commit 없음 — 검증만)

---

## Memory 저장 (사용자 확인)

플랜 완료 후, 위 스킬 매핑 테이블을 Memory에 저장할지 사용자에게 확인 (CLAUDE.md 가이드).

저장 시: `~/.claude/projects/-Users-cjynim-lab-report/memory/skill_mapping_implementation_plans.md`

---

## Self-Review 결과

(플랜 작성자 self-check)

**1. Spec coverage**:
- §3 Decisions Summary 12개 항목 → Task 1-7에 모두 매핑됨 ✓
- §4 Files Changed 9개 → Task 1-7 + Task 8 README ✓
- §5 Message Format → Task 5 (`_build_title`) + Task 6 (case branches) ✓
- §6 Error Handling 7개 시나리오 → Task 6 테스트 케이스에 모두 등장 ✓
- §7 Testing Strategy → Task 1-6 각 Task 내 테스트 ✓
- §8 Completion Criteria 11개 → 플랜 완료조건 11개 일치 ✓
- §9 Don'ts → 플랜 Don'ts 13개 ✓
- §10/§11 Considerations/Constraints → 플랜 동일 섹션 ✓

**2. Placeholder scan**:
- "TBD"/"TODO"/"적절히" 검색 → 없음 ✓
- 모든 코드 블록 완전 ✓

**3. Type consistency**:
- `CreatePageStatus` 모든 Task에서 동일 import 경로 ✓
- `STATUS_LABELS` Task 2 정의, Task 5 사용 — 모두 application 레이어 ✓
- `_build_title(prefix, this_week, status)` 시그니처 Task 5 정의, Task 6 호출 — 일치 ✓
- `_notify(status, prefix, this_week, body)` 시그니처 Task 5 정의, Task 6 호출 — 일치 ✓

---

## Execution Handoff

플랜 작성 완료, `docs/superpowers/plans/2026-04-27-create-page-slack-notification.md`에 저장됨.

두 가지 실행 옵션:

**1. Subagent-Driven (recommended)** — 매 Task당 fresh subagent, two-stage review, 빠른 iteration. CLAUDE.md의 "각 Task별 /rl 검증" 규칙과 잘 맞음.

**2. Inline Execution** — 현재 세션에서 batch 실행 + checkpoints.

어느 쪽으로 진행할까요?
