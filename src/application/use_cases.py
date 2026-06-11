from datetime import date

from ..domain.models import ReportConfig
from ..domain.services import extract_report_content
from .ports import CLIExecutorPort, NotificationPort


class GenerateReportUseCase:
    """리포트 생성 및 전송 유스케이스 (daily/weekly 공용)

    title_suffix가 Slack 제목의 모드 구분자가 된다.
    예: "Daily" → [BE][26.01.27_Daily], "Weekly" → [BE][26.01.27_Weekly]
    """

    def __init__(
        self,
        cli_executor: CLIExecutorPort,
        notifier: NotificationPort,
        title_suffix: str,
    ):
        self._cli_executor = cli_executor
        self._notifier = notifier
        self._title_suffix = title_suffix

    def execute(self, config: ReportConfig) -> bool:
        print(f"\n--------------------\nGenerating {self._title_suffix} report from: {config.space_key}\n--------------------")

        output = self._cli_executor.execute(
            config.space_key, config.mention_users, config.report_date
        )
        if output is None:
            print("ERROR: Failed to generate report. Skipping notification.")
            return False

        self._notifier.send(self._build_title(config), extract_report_content(output))
        return True

    def _build_title(self, config: ReportConfig) -> str:
        report_date = config.report_date or date.today()
        formatted_date = report_date.strftime("%y.%m.%d")
        prefix = f"[{config.team_prefix}]" if config.team_prefix else ""
        return f"{prefix}[{formatted_date}_{self._title_suffix}]"
