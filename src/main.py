import argparse
from datetime import date, datetime

from .application.ports import CLIExecutorPort
from .application.use_cases import GenerateWeeklyReportUseCase
from .application.weekly_summary_use_case import GenerateWeeklySummaryUseCase
from .infrastructure.adapters.cli_executors import ClaudeCLIExecutor, GeminiCLIExecutor
from .infrastructure.adapters.report_generator import ReportGenerator
from .infrastructure.adapters.slack_adapter import SlackAdapter
from .infrastructure.config import load_config_from_env


def create_cli_executor(cli_type: str) -> CLIExecutorPort:
    """CLI 타입에 따라 적절한 실행기 생성"""
    executors = {
        "claude": ClaudeCLIExecutor,
        "gemini": GeminiCLIExecutor,
    }
    executor_class = executors.get(cli_type)
    if executor_class is None:
        raise ValueError(f"Unknown CLI type: {cli_type}. Supported: {list(executors.keys())}")
    return executor_class()


def parse_args() -> argparse.Namespace:
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(description="Weekly Report Generator")
    parser.add_argument(
        "--date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=None,
        help="리포트 대상 날짜 (YYYY-MM-DD). 미지정 시 오늘 날짜 사용.",
    )
    return parser.parse_args()


def main():
    """
    Composition Root: 모든 의존성을 조립하고 애플리케이션을 실행
    """
    args = parse_args()

    # 1. 설정 로드
    config = load_config_from_env(report_date=args.date)
    if config is None:
        print("Exiting due to configuration error.")
        return

    report_date = config.report.report_date or date.today()
    print(f"Using CLI: {config.cli_type}")
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
        use_case = CreateWeeklyPageUseCase(confluence, transformer)

        weekly_page_config = WeeklyPageConfig(
            space_key=config.report.space_key,
            parent_page_id=config.parent_page_id,
        )
        success = use_case.execute(weekly_page_config, target_date=report_date)
        if not success:
            print("ERROR: Failed to create weekly page.")
        return

    elif config.report_mode == "weekly":
        # weekly 전용 경로
        executors: dict[str, type] = {"claude": ClaudeCLIExecutor, "gemini": GeminiCLIExecutor}
        executor_class = executors.get(config.cli_type)
        if executor_class is None:
            raise ValueError(f"Unknown CLI type: {config.cli_type}. Supported: {list(executors.keys())}")
        cli_executor = executor_class(command="weekly_report")
        report_generator = ReportGenerator(cli_executor)
        notifier = SlackAdapter(token=config.slack_token, channel=config.slack_channel_weekly)
        use_case = GenerateWeeklySummaryUseCase(
            report_generator=report_generator,
            notifier=notifier,
        )
    else:
        # daily 경로
        cli_executor = create_cli_executor(config.cli_type)
        report_generator = ReportGenerator(cli_executor)
        notifier = SlackAdapter(token=config.slack_token, channel=config.slack_channel)
        use_case = GenerateWeeklyReportUseCase(
            report_generator=report_generator,
            notifier=notifier,
        )

    success = use_case.execute(config.report)
    if not success:
        print("ERROR: Failed to generate and send report.")


if __name__ == "__main__":
    main()
