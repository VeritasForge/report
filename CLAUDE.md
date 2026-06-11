# CLAUDE.md

@README.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Weekly Report Generator - a Python application that automatically generates daily/weekly reports from Confluence pages using the Claude CLI (via claude-agent-sdk), then sends reports to Slack. The report generation logic is externalized to `.claude/commands/daily_report.md` (daily mode) and `.claude/commands/weekly_report.md` (weekly mode). The mode is controlled by `REPORT_MODE` env var (`daily` | `weekly` | `create_page`).

## Architecture

The application follows Clean Architecture with three layers:

```
src/
├── main.py                     # Composition Root (CLI factory, mode factories: build_report_use_case, run_create_page_mode)
├── domain/                     # Core business logic (no external dependencies)
│   ├── models.py               # DateRange, ReportConfig (space_key, team_name, team_prefix, mention_users), WeeklyPageConfig, CreatePageStatus
│   └── services.py             # Date calculation utilities, extract_report_content (report marker parsing)
├── application/                # Use cases (depends only on domain)
│   ├── ports.py                # Protocol interfaces (CLIExecutorPort, NotificationPort, ConfluencePort, PageTransformerPort)
│   ├── use_cases.py            # GenerateReportUseCase (daily/weekly 공용, title_suffix로 모드 구분)
│   └── create_page_use_case.py # CreateWeeklyPageUseCase (create_page mode)
└── infrastructure/             # External system adapters
    ├── config.py               # Environment variable loading (AppConfig incl. report_mode, slack_channel_weekly)
    └── adapters/
        ├── cli_executors.py    # ClaudeCLIExecutor (claude-agent-sdk, /daily_report or /weekly_report via command param)
        ├── slack_adapter.py    # Slack API integration
        ├── stdout_adapter.py   # Dry-run stdout output (NotificationPort)
        ├── confluence_adapter.py  # Confluence REST API (create_page mode)
        └── page_transformer.py # Weekly page HTML transformation (create_page mode)

.claude/
└── commands/
    ├── daily_report.md         # Daily report prompt (date calculation, Confluence search, formatting)
    └── weekly_report.md        # Weekly summary prompt (reads all daily pages, generates consolidated report)

Makefile                        # Build commands (install, run, test, coverage, etc.)
```

### Flow
`main.py` branches on `config.report_mode` (`daily` | `weekly` | `create_page`):

**Daily mode** (default):
1. `main.py` loads config and calls the `build_report_use_case(config, model, dry_run)` factory
2. The factory creates `ClaudeCLIExecutor(command="daily_report")` and a notifier (`SlackAdapter`, or `StdoutAdapter` when dry-run), then assembles `GenerateReportUseCase(cli_executor, notifier, title_suffix="Daily")`
3. `GenerateReportUseCase` executes `/daily_report SPACE_KEY "MENTION_USERS"` via the CLI executor
4. `daily_report.md` automatically calculates date range and searches Confluence page
5. `daily_report.md` extracts content, analyzes with sequential-thinking, formats report
6. `GenerateReportUseCase` extracts the final report with `extract_report_content` (domain service), builds title (e.g., `[BE][26.01.27_Daily]`) and sends it to the notifier
7. `SlackAdapter` posts title as main message, report content as thread reply

**Weekly mode** (`REPORT_MODE=weekly`):
1. `build_report_use_case` creates `ClaudeCLIExecutor(command="weekly_report")` and assembles `GenerateReportUseCase` with `title_suffix="Weekly"`
2. `SlackAdapter` is initialized with `slack_channel_weekly` (separate channel from daily)
3. `GenerateReportUseCase` executes `/weekly_report SPACE_KEY "MENTION_USERS"` via the CLI executor
4. `weekly_report.md` reads all daily pages from the week and generates a consolidated summary
5. `GenerateReportUseCase` builds title (e.g., `[BE][26.01.27_Weekly]`) and sends to Slack

**Create page mode** (`REPORT_MODE=create_page`):
1. `main.py` calls `run_create_page_mode(config, report_date)`, which assembles `ConfluenceAdapter`, `PageTransformer`, an optional `SlackAdapter`, and `CreateWeeklyPageUseCase`
2. `CreateWeeklyPageUseCase` copies the previous week's page into the new week's page and (optionally) notifies Slack

### CLI Plugin Architecture

The application uses a plugin architecture for CLI tools:

```
┌───────────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ GenerateReportUseCase │────▶│  CLIExecutorPort  │◀────│  ClaudeCLIExecutor   │
│ (daily/weekly 공용)    │     │    (Protocol)     │     │ (claude-agent-sdk)   │
└───────────────────────┘     └──────────────────┘     └─────────────────────┘
         │                                                       ▲
         │                                                       │
         ▼                                              ┌─────────────────┐
┌─────────────────────┐                                │ create_cli_     │
│ ReportConfig        │                                │ executor()      │
│ (space_key,         │                                │ (Factory)       │
│  team_prefix,       │                                └─────────────────┘
│  mention_users)     │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ .claude/commands/   │
│ daily_report.md     │
│ (Date calc + Report)│
└─────────────────────┘
```

**Components:**
- `CLIExecutorPort`: Protocol interface that all CLI executors must implement
- `ClaudeCLIExecutor`: Executes slash commands via claude-agent-sdk, switched by `command` constructor param (default: `"daily_report"`)
- `GenerateReportUseCase`: Orchestrates CLI execution and notification (daily/weekly 공용, `title_suffix`로 모드 구분)
- `ReportConfig`: Configuration containing `space_key`, `team_name`, `team_prefix`, `mention_users`
- `daily_report.md`: Daily report generation (date calculation, Confluence search, formatting)
- `weekly_report.md`: Weekly summary generation (reads all daily pages, consolidated report)
- `create_cli_executor()`: Factory function that creates the appropriate executor

**Switching command at runtime:**
- `ClaudeCLIExecutor(command="weekly_report")` makes the executor run `/weekly_report` instead of `/daily_report`

**Adding a new CLI executor:**
1. Create a new class in `cli_executors.py` implementing `execute(space_key: str, mention_users: str = "", report_date: date | None = None) -> str | None`
2. Accept `command: str = "daily_report"` in `__init__` for command switching
3. Add a branch for it in `create_cli_executor()` in `main.py` (and extend the supported `cli_type` values)

### External Dependencies
- **Claude CLI**: Must be installed separately and available in PATH (invoked via claude-agent-sdk). Executes `/daily_report` or `/weekly_report` command with Atlassian MCP
- **Slack SDK**: For posting reports to Slack channels

## Design Principles

### Clean Architecture (Inward Dependency)
의존성은 반드시 안쪽으로만 흘러야 합니다.

- **Domain (`src/domain`)**: 순수 Python 비즈니스 로직. 외부 의존성 없음.
- **Application (`src/application`)**: 유스케이스, 포트 인터페이스. Domain에만 의존.
- **Infrastructure (`src/infrastructure`)**: 외부 시스템 어댑터. Application과 Domain에 의존.

**금지 사항:**
- Domain 레이어에서 infrastructure 모듈 import 금지
- Domain 레이어에서 외부 라이브러리(slack_sdk 등) import 금지

### SOLID Principles
- **SRP**: 클래스/함수는 하나의 책임만 가짐
- **OCP**: 확장에는 열려있고, 수정에는 닫혀있음 (새 CLI 추가 시 기존 코드 수정 최소화)
- **DIP**: 고수준 모듈은 저수준 모듈에 의존하지 않음 (Protocol 인터페이스 사용)

### Clean Code Guidelines
- **의도를 드러내는 이름**: `days_since_creation` > `d`
- **작은 함수**: 하나의 일만 잘 수행
- **부수 효과 없음**: 숨겨진 상태 변경 금지
- **최소한의 주석**: 코드가 스스로 설명하도록, 주석은 "왜"를 설명

## Python Conventions

### Type Hints
Python 3.12+ 스타일 사용:
- `list[str]` (O) vs `List[str]` (X)
- `dict[str, int]` (O) vs `Dict[str, int]` (X)
- `str | None` (O) vs `Optional[str]` (X)

### Naming Conventions
- **변수/함수**: snake_case (`calculate_last_week_range`)
- **클래스**: PascalCase (`SlackAdapter`)
- **상수**: UPPER_SNAKE_CASE (`CLI_TYPE`)
- **프라이빗**: 언더스코어 접두사 (`_parse_output`)

## AI Interaction Guidelines

### Workflow
복잡한 작업 시 다음 워크플로우를 따릅니다:
1. **Plan**: 요구사항 분석 및 아키텍처 제안
2. **Chain of Thought**: Situation → Strategy → Plan → Verify
3. **Implement**: 최소한의 구현
4. **Refine**: 타입 안전성 및 규약 준수 확인

### External API Verification
외부 API(Confluence, Slack, JIRA 등) 호출 코드 작성 시, 구현 전에 반드시 Context7 또는 공식 문서로 request/response 스펙을 확인할 것. 가정으로 payload를 작성하지 않는다.

### Deep Thinking
복잡한 분석이 필요한 경우 `sequentialthinking` MCP 도구를 사용합니다.

### Clarification Protocol
- 모호하거나 불확실한 부분은 반드시 질문
- 가정하지 말고 사용자에게 확인
- 엣지 케이스와 에러 처리를 항상 고려

### Test Protection Protocol
코드 변경 시 기존 테스트 보호를 위한 워크플로우:

**변경 전:**
1. 테스트 파일 존재 여부 확인 (`tests/` 디렉토리)
2. 기존 테스트 실행하여 현재 상태 파악 (`uv run pytest`)
3. 모든 테스트가 통과하는지 확인

**변경 후:**
1. 전체 테스트 재실행
2. 테스트 실패 시 **즉시 개발자에게 안내**:
   - 어떤 테스트가 실패했는지
   - 예상되는 실패 원인
   - 의도된 변경인지 확인 요청
3. 개발자 확인 없이 실패한 테스트를 수정하지 않음

**Breaking Change 대응:**
- 기존 테스트 실패 = 기존 동작에 영향을 주는 변경
- AI가 임의로 테스트를 수정하거나 삭제하지 않음
- 개발자가 변경을 승인한 경우에만 테스트 업데이트 진행

### II. Strict TDD Protocol (Non-Negotiable)
Follow Robert C. Martin's 3 Rules of TDD:
1.  **Red**: Do not write production code unless it is to pass a failing unit test.
2.  **Green**: Do not write more code than is sufficient to pass the test.
3.  **Refactor**: Do not add functionality while refactoring.
*   **Test Layers**: Unit (10ms, Mocked Ports) -> Integration (DB/SQLModel) -> E2E (API/TestClient).

**Testing Strategy & Style Guide (Detailed):**
1.  **Given/When/Then Structure**: All tests MUST follow this structure, explicitly commented.
    -   *Example*: 'Given: User created -> And: Logged in -> When: Click button -> Then: Show modal'.
2.  **Single Concept**: Verify one concept per test function.
3.  **Parametrized Test**: Use 'pytest.mark.parametrize' for data-driven tests.
4.  **Descriptive Naming**: 'test_should_return_error_when_invalid_input()' over 'test_input()'.

**Test Coverage Categories (Mandatory):**

각 Task의 RED phase는 아래 **3개 카테고리에서 각각 최소 1개 이상의 테스트 케이스를 포함**해야 한다. Plan 문서나 PR description의 RED 섹션에서 카테고리별로 라벨링하여 명시한다.

| 카테고리 | 검증 대상 | 예시 |
|---------|---------|------|
| `[Happy]` | 정상 흐름 (정상 입력 → 정상 출력) | 유효 env var 로드, 정상 파라미터 전달, 정상 응답 누적 |
| `[Boundary]` | 경계값/엣지 케이스 | default 값, 빈 문자열(`""`), `None`, falsy 값(`0`, `false`), 빈 컬렉션, 대소문자 변종, 멀티라인, 유니코드 |
| `[Error]` | 예외/에러 케이스 | 외부 의존성 실패(`CLINotFoundError` 등), 잘못된 입력, 알려지지 않은 예외 정책(재발생/None 반환) |

**규칙:**
- Happy path만 테스트하고 GREEN phase로 진입 금지.
- 예외 케이스가 자연스럽게 부재하는 단순 보관 Task(파라미터만 저장하는 생성자 등)는 예외 허용하되, plan/PR에 **사유 명시 필수** (예: "외부 호출/IO 부재로 예외 케이스 없음").
- 경계 케이스는 *코드가 분기하는 모든 입력 영역*에서 1개 이상: truthy/falsy 분기, optional 인자의 `None`/실제 값, 컬렉션의 빈/단일/다수.
- 예외 케이스는 *명시적으로 잡는 모든 예외 타입* 각각에 1개 (`except (A, B, C):`이면 3개).

**테스트 실행:**
```bash
# 전체 테스트
uv run pytest

# 커버리지 포함
uv run pytest --cov=src --cov-report=term-missing

# 특정 레이어만
uv run pytest tests/unit/domain/
```

**테스트 구조:**
```
tests/
├── conftest.py              # 공유 픽스처
├── unit/                    # 단위 테스트 (Mocked, <10ms)
│   ├── domain/              # Domain 레이어 (Mock 불필요)
│   ├── application/         # Application 레이어 (Port Mock)
│   └── infrastructure/      # Infrastructure 레이어 (외부 의존성 Mock)
└── integration/             # 통합 테스트 (실제 의존성)
```
