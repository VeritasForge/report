import textwrap
from datetime import date, datetime

from ..domain.models import ReportConfig
from ..domain.services import calculate_last_week_range
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
        # 1. 날짜 범위 계산
        date_range = calculate_last_week_range(date.today())
        page_title = f"{config.page_title_prefix} {date_range.format()} ({config.page_products}, etc.)"
        print(f"\n--------------------\nGenerating report from: {page_title}\n--------------------")

        # 2. 보고서 생성
        report = self._report_generator.generate(config, date_range)
        if report is None:
            print("ERROR: Failed to generate report. Skipping notification.")
            return False

        # 3. 헤더 생성 및 전송
        header = self._build_header(config)
        full_message = f"{header}\n\n{report.main_content}"
        self._notifier.send(full_message, report.thread_tickets)
        return True

    def _build_header(self, config: ReportConfig) -> str:
        formatted_date = datetime.now().strftime('%Y.%m.%d (%a)')
        team_prefix = f"{config.team_name} " if config.team_name else ""
        return textwrap.dedent(f"""
            {formatted_date}
            {team_prefix}주간 업무 보고 드립니다.
        """).strip()
