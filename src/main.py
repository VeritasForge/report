import argparse
from datetime import date, datetime

from .application.ports import CLIExecutorPort, NotificationPort
from .application.use_cases import GenerateWeeklyReportUseCase
from .application.weekly_summary_use_case import GenerateWeeklySummaryUseCase
from .infrastructure.adapters.cli_executors import ClaudeCLIExecutor
from .infrastructure.adapters.report_generator import ReportGenerator
from .infrastructure.adapters.slack_adapter import SlackAdapter
from .infrastructure.adapters.stdout_adapter import StdoutAdapter
from .infrastructure.config import load_config_from_env


def create_cli_executor(
    cli_type: str,
    command: str = "daily_report",
    model: str | None = None,
) -> CLIExecutorPort:
    """CLI 타입에 따라 적절한 실행기 생성."""
    if cli_type == "claude":
        return ClaudeCLIExecutor(command=command, model=model)
    raise ValueError(f"Unknown CLI type: {cli_type}. Supported: ['claude']")


def parse_args() -> argparse.Namespace:
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(description="Weekly Report Generator")
    parser.add_argument(
        "--date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=None,
        help="리포트 대상 날짜 (YYYY-MM-DD). 미지정 시 오늘 날짜 사용.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Claude 모델 (예: sonnet, haiku). CLI_MODEL env보다 우선. 둘 다 미설정 시 sonnet.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Slack 전송 없이 stdout으로 리포트 출력. DRY_RUN env와 동등.",
    )
    return parser.parse_args()


def resolve_effective_settings(args, config) -> tuple[str, bool]:
    """CLI 인자와 config(ENV)에서 effective model/dry_run 결정.

    우선순위: CLI 인자 > config(ENV) > 코드 default("sonnet" / False).
    """
    effective_model = args.model or config.cli_model or "sonnet"
    effective_dry_run = bool(args.dry_run) or bool(config.dry_run)
    return effective_model, effective_dry_run


def create_notifier(dry_run: bool, slack_token: str, slack_channel: str) -> NotificationPort:
    """dry_run 여부에 따라 적절한 Notifier 인스턴스 반환.

    - dry_run=True → `StdoutAdapter` (Slack 미호출, SLACK_TOKEN 무관)
    - dry_run=False → `SlackAdapter` (token 누락은 send 시점 warning으로 처리)
    """
    if dry_run:
        return StdoutAdapter()
    return SlackAdapter(token=slack_token, channel=slack_channel)


def main():  # pragma: no cover
    """Composition Root: 의존성 조립 + 애플리케이션 실행.

    내부 분기 헬퍼(`parse_args`, `resolve_effective_settings`, `create_notifier`,
    `create_cli_executor`)는 단위 테스트로 검증된다.
    이 함수 자체는 글루 코드이므로 통합 테스트 영역으로 위임 (coverage 제외).
    """
    args = parse_args()

    # 1. 설정 로드
    config = load_config_from_env(report_date=args.date)
    if config is None:
        print("Exiting due to configuration error.")
        return

    effective_model, effective_dry_run = resolve_effective_settings(args, config)

    report_date = config.report.report_date or date.today()
    print(f"Using CLI: {config.cli_type}")
    print(f"Model: {effective_model} | dry_run: {effective_dry_run}")
    print(f"Report date: {report_date.isoformat()}")

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

    elif config.report_mode == "weekly":
        # weekly 전용 경로
        cli_executor = create_cli_executor(
            config.cli_type, command="weekly_report", model=effective_model
        )
        report_generator = ReportGenerator(cli_executor)
        notifier = create_notifier(
            dry_run=effective_dry_run,
            slack_token=config.slack_token,
            slack_channel=config.slack_channel_weekly,
        )
        use_case = GenerateWeeklySummaryUseCase(
            report_generator=report_generator,
            notifier=notifier,
        )
    else:
        # daily 경로
        cli_executor = create_cli_executor(config.cli_type, model=effective_model)
        report_generator = ReportGenerator(cli_executor)
        notifier = create_notifier(
            dry_run=effective_dry_run,
            slack_token=config.slack_token,
            slack_channel=config.slack_channel,
        )
        use_case = GenerateWeeklyReportUseCase(
            report_generator=report_generator,
            notifier=notifier,
        )

    success = use_case.execute(config.report)
    if not success:
        print("ERROR: Failed to generate and send report.")


if __name__ == "__main__":
    main()
