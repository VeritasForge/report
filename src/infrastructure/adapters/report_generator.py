from ...application.ports import CLIExecutorPort
from ...domain.models import Report, ReportConfig


class ReportGenerator:
    """CLI 실행기를 사용하여 보고서를 생성하는 오케스트레이터"""

    def __init__(self, cli_executor: CLIExecutorPort):
        self._cli_executor = cli_executor

    def generate(self, config: ReportConfig) -> Report | None:
        """
        보고서를 생성합니다.
        날짜 범위는 daily_report.md에서 실행 시점 기준으로 자동 계산됩니다.
        """
        print(f"Starting report generation for Space: {config.space_key}")
        if config.mention_users:
            print(f"Executing: /daily_report {config.space_key} \"{config.mention_users}\"")
        else:
            print(f"Executing: /daily_report {config.space_key}")

        output = self._cli_executor.execute(config.space_key, config.mention_users, config.report_date)
        if output is None:
            return None

        print("Report generated successfully.")
        return self._parse_output(output)

    def _parse_output(self, output: str) -> Report:
        """CLI 출력을 Report 객체로 파싱

        CLI 출력에서 최종 리포트만 추출합니다.
        리포트는 '📊 일정 요약' 또는 ':bar_chart: 일정 요약'으로 시작합니다.
        중간 분석 과정이 포함된 경우 리포트 시작점부터만 추출합니다.
        """
        content = output.strip()
        report_markers = ["*\U0001f4ca 일정 요약*", "*:bar_chart: 일정 요약*",
                          "\U0001f4ca 일정 요약", ":bar_chart: 일정 요약",
                          "*\U0001f4ca 주간 요약", "*:bar_chart: 주간 요약"]

        for marker in report_markers:
            idx = content.find(marker)
            if idx != -1:
                return Report(main_content=content[idx:].strip())

        return Report(main_content=content)
