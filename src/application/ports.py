from typing import Protocol

from ..domain.models import Report, ReportConfig


class CLIExecutorPort(Protocol):
    """CLI 실행기 추상 인터페이스"""

    def execute(self, space_key: str, mention_users: str = "") -> str | None:
        """/daily_report 커맨드를 실행하고 결과 반환"""
        ...


class ReportGeneratorPort(Protocol):
    """보고서 생성기 추상 인터페이스"""

    def generate(self, config: ReportConfig) -> Report | None:
        """Confluence 페이지에서 보고서 생성 (날짜는 실행 시점 기준 자동 계산)"""
        ...


class NotificationPort(Protocol):
    """알림 전송 추상 인터페이스"""

    def send(self, message: str, thread_message: str | None = None) -> None:
        """메시지 전송"""
        ...
