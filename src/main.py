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


def main():
    """
    Composition Root: 모든 의존성을 조립하고 애플리케이션을 실행
    """
    # 1. 설정 로드
    config = load_config_from_env()
    if config is None:
        print("Exiting due to configuration error.")
        return

    print(f"Using CLI: {config.cli_type}")

    if config.report_mode == "weekly":
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
        # daily 경로: 기존 코드 100% 동일
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
