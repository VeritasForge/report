# CLAUDE.md

@README.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Weekly Report Generator - a Python application that automatically generates weekly reports by summarizing Confluence pages and associated JIRA tickets using a pluggable CLI (Claude or Gemini), then sends reports to Slack.

## Architecture

The application follows Clean Architecture with three layers:

```
src/
├── main.py                     # Composition Root (dependency injection, CLI factory)
├── domain/                     # Core business logic (no external dependencies)
│   ├── models.py               # DateRange, ReportConfig, Report
│   └── services.py             # Date calculation, markdown conversion, prompt builder
├── application/                # Use cases (depends only on domain)
│   ├── ports.py                # Protocol interfaces (CLIExecutorPort, ReportGeneratorPort, NotificationPort)
│   └── use_cases.py            # GenerateWeeklyReportUseCase
└── infrastructure/             # External system adapters
    ├── config.py               # Environment variable loading
    └── adapters/
        ├── cli_executors.py    # CLI executors (Claude, Gemini)
        ├── report_generator.py # Report generation orchestrator
        └── slack_adapter.py    # Slack API integration
```

### Flow
1. `main.py` loads config and assembles dependencies using factory pattern
2. `create_cli_executor()` creates the appropriate CLI executor based on `CLI_TYPE`
3. `ReportGenerator` orchestrates prompt building and CLI execution
4. `GenerateWeeklyReportUseCase` coordinates the report generation workflow
5. `SlackAdapter` posts the report to Slack

### CLI Plugin Architecture

The application uses a plugin architecture for CLI tools:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  ReportGenerator │────▶│  CLIExecutorPort  │◀────│  ClaudeCLIExecutor │
│  (Orchestrator)  │     │    (Protocol)     │     │  GeminiCLIExecutor │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                                                 ▲
         │                                                 │
         ▼                                                 │
┌─────────────────┐                              ┌─────────────────┐
│ build_report_   │                              │ create_cli_     │
│ prompt()        │                              │ executor()      │
│ (Domain Service)│                              │ (Factory)       │
└─────────────────┘                              └─────────────────┘
```

**Components:**
- `CLIExecutorPort`: Protocol interface that all CLI executors must implement
- `ClaudeCLIExecutor` / `GeminiCLIExecutor`: Concrete implementations for each CLI
- `ReportGenerator`: Orchestrates prompt building and CLI execution
- `build_report_prompt()`: Domain service that generates the prompt (CLI-agnostic)
- `create_cli_executor()`: Factory function that creates the appropriate executor

**Adding a new CLI executor:**
1. Create a new class in `cli_executors.py` implementing `execute(prompt: str) -> str | None`
2. Register it in the `executors` dict in `create_cli_executor()` in `main.py`

### External Dependencies
- **Claude CLI** or **Gemini CLI**: Must be installed separately and available in PATH. Used to read Confluence pages via Atlassian MCP and summarize content
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
- **클래스**: PascalCase (`ReportGenerator`)
- **상수**: UPPER_SNAKE_CASE (`CLI_TYPE`)
- **프라이빗**: 언더스코어 접두사 (`_parse_output`)

## AI Interaction Guidelines

### Workflow
복잡한 작업 시 다음 워크플로우를 따릅니다:
1. **Plan**: 요구사항 분석 및 아키텍처 제안
2. **Chain of Thought**: Situation → Strategy → Plan → Verify
3. **Implement**: 최소한의 구현
4. **Refine**: 타입 안전성 및 규약 준수 확인

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
