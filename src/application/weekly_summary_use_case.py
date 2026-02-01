from datetime import datetime

from ..domain.models import ReportConfig
from .ports import NotificationPort, ReportGeneratorPort


class GenerateWeeklySummaryUseCase:
    """주간 요약 보고서 생성 및 전송 유스케이스"""

    def __init__(
        self,
        report_generator: ReportGeneratorPort,
        notifier: NotificationPort,
    ):
        self._report_generator = report_generator
        self._notifier = notifier

    def execute(self, config: ReportConfig) -> bool:
        """보고서 생성 및 전송 실행"""
        print(f"\n--------------------\nGenerating weekly summary from: {config.space_key}\n--------------------")

        report = self._report_generator.generate(config)
        if report is None:
            print("ERROR: Failed to generate weekly summary. Skipping notification.")
            return False

        title = self._build_title(config)
        self._notifier.send(title, report.main_content)
        return True

    def _build_title(self, config: ReportConfig) -> str:
        """Slack 메인 메시지용 제목 생성 (예: [BE][26.01.27_Weekly])"""
        formatted_date = datetime.now().strftime('%y.%m.%d')
        prefix = f"[{config.team_prefix}]" if config.team_prefix else ""
        return f"{prefix}[{formatted_date}_Weekly]"
