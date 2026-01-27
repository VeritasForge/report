from typing import Protocol

from ..domain.models import DateRange, Report, ReportConfig


class CLIExecutorPort(Protocol):
    """CLI 실행기 추상 인터페이스"""

    def execute(self, prompt: str) -> str | None:
        """프롬프트를 CLI에 전달하고 결과 반환"""
        ...


class ReportGeneratorPort(Protocol):
    """보고서 생성기 추상 인터페이스"""

    def generate(self, config: ReportConfig, date_range: DateRange) -> Report | None:
        """Confluence 페이지에서 보고서 생성"""
        ...


class NotificationPort(Protocol):
    """알림 전송 추상 인터페이스"""

    def send(self, message: str, thread_message: str | None = None) -> None:
        """메시지 전송"""
        ...
