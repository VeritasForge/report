from ...application.ports import CLIExecutorPort
from ...domain.models import DateRange, Report, ReportConfig
from ...domain.services import build_report_prompt


class ReportGenerator:
    """CLI 실행기를 사용하여 보고서를 생성하는 오케스트레이터"""

    def __init__(self, cli_executor: CLIExecutorPort):
        self._cli_executor = cli_executor

    def generate(self, config: ReportConfig, date_range: DateRange) -> Report | None:
        prompt = build_report_prompt(config, date_range)
        page_title = f"{config.page_title_prefix} {date_range.format()} ({config.page_products}, etc.)"
        print(f"Starting report generation for Space: {config.space_key}, Title: {page_title}")
        print(prompt)

        output = self._cli_executor.execute(prompt)
        if output is None:
            return None

        print("Report generated successfully.")
        return self._parse_output(output)

    def _parse_output(self, output: str) -> Report:
        if "---THREAD_TICKETS---" in output:
            parts = output.split("---THREAD_TICKETS---")
            main = parts[0].replace("[메인 보고서]", "").strip()
            thread = parts[1].replace("[스레드용 티켓 목록]", "").strip() if len(parts) > 1 else None
            return Report(main_content=main, thread_tickets=thread if thread else None)
        return Report(main_content=output)
