import textwrap
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

        # 2. 헤더 생성 및 전송
        header = self._build_header(config)
        full_message = f"{header}\n\n{report.main_content}"
        self._notifier.send(full_message, report.thread_tickets)
        return True

    def _build_header(self, config: ReportConfig) -> str:
        formatted_date = datetime.now().strftime('%Y.%m.%d (%a)')
        team_prefix = f"{config.team_name} " if config.team_name else ""
        return textwrap.dedent(f"""
            {formatted_date}
            {team_prefix}업무 보고 드립니다.
        """).strip()
