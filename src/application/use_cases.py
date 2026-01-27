from datetime import datetime

from ..domain.models import ReportConfig
from .ports import NotificationPort, ReportGeneratorPort


class GenerateWeeklyReportUseCase:
    """주간 보고서 생성 및 전송 유스케이스"""

    def __init__(
        self,
        report_generator: ReportGeneratorPort,
        notifier: NotificationPort,
    ):
        self._report_generator = report_generator
        self._notifier = notifier

    def execute(self, config: ReportConfig) -> bool:
        """보고서 생성 및 전송 실행"""
        print(f"\n--------------------\nGenerating report from: {config.space_key}\n--------------------")

        # 1. 보고서 생성 (/daily_report 커맨드 실행 - 날짜는 자동 계산됨)
        report = self._report_generator.generate(config)
        if report is None:
            print("ERROR: Failed to generate report. Skipping notification.")
            return False

        # 2. 메인 메시지(제목)와 스레드 메시지(리포트 내용) 전송
        title = self._build_title(config)
        self._notifier.send(title, report.main_content)
        return True

    def _build_title(self, config: ReportConfig) -> str:
        """Slack 메인 메시지용 제목 생성 (예: [BE][26.01.27_Daily])"""
        formatted_date = datetime.now().strftime('%y.%m.%d')
        prefix = f"[{config.team_prefix}]" if config.team_prefix else ""
        return f"{prefix}[{formatted_date}_Daily]"
