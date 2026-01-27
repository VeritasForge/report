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

        output = self._cli_executor.execute(config.space_key, config.mention_users)
        if output is None:
            return None

        print("Report generated successfully.")
        return self._parse_output(output)

    def _parse_output(self, output: str) -> Report:
        """CLI 출력을 Report 객체로 파싱"""
        # daily_report.md의 출력 형식에 맞게 파싱
        # 출력은 슬랙 호환 형식으로 제공됨
        return Report(main_content=output.strip())
