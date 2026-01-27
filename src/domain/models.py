from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DateRange:
    """날짜 범위 값 객체"""
    start: date
    end: date

    def format(self) -> str:
        return f"{self.start.strftime('%Y-%m-%d')} ~ {self.end.strftime('%Y-%m-%d')}"


@dataclass(frozen=True)
class ReportConfig:
    """보고서 생성 설정"""
    space_key: str
    page_title_prefix: str
    products: str
    page_products: str
    authors: str
    team_name: str


@dataclass
class Report:
    """생성된 보고서"""
    main_content: str
    thread_tickets: str | None = None
