from datetime import date
from typing import Protocol

from ..domain.models import Report, ReportConfig


class CLIExecutorPort(Protocol):
    """CLI 실행기 추상 인터페이스"""

    def execute(self, space_key: str, mention_users: str = "", report_date: date | None = None) -> str | None:
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


class ConfluencePort(Protocol):
    """Confluence 페이지 접근 추상 인터페이스"""

    def get_page_by_title(self, space_key: str, title: str) -> dict | None:
        """제목으로 페이지 조회. 없으면 None 반환."""
        ...

    def get_page_content(self, page_id: str) -> str:
        """페이지의 storage format HTML 조회"""
        ...

    def create_page(self, space_key: str, title: str, content: str, parent_id: str) -> str:
        """새 페이지 생성. 생성된 페이지 URL 반환."""
        ...


class PageTransformerPort(Protocol):
    """페이지 HTML 변환 추상 인터페이스"""

    def transform(self, html: str, old_dates: list[str], new_dates: list[str]) -> str:
        """이전 주 HTML을 새 주 형식으로 변환"""
        ...
