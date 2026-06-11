from dataclasses import dataclass
from datetime import date
from enum import Enum


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
    team_name: str
    team_prefix: str  # 리포트 제목에 사용할 팀 접두사 (예: "BE", "FE")
    mention_users: str  # 지연/보류 시 멘션할 사용자 (예: "@홍길동 @김철수")
    report_date: date | None = None  # 리포트 대상 날짜 (None이면 오늘)


@dataclass(frozen=True)
class WeeklyPageConfig:
    """주간 페이지 자동 생성 설정"""
    space_key: str
    parent_page_id: str


class CreatePageStatus(str, Enum):
    """create_page 유스케이스 실행 결과 (semantic identifier)

    값은 Korean/emoji가 아닌 semantic identifier. 사용자에게 보이는 라벨은
    application 레이어의 STATUS_LABELS dict에 mapping된다 (Clean Architecture
    의 도메인-프레젠테이션 분리 준수).
    """
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"
    FAILED = "failed"
