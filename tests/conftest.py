"""공유 픽스처 정의"""

from datetime import date

import pytest

from src.domain.models import DateRange, Report, ReportConfig


@pytest.fixture
def sample_date_range() -> DateRange:
    """테스트용 날짜 범위 (2026년 1월 27일 ~ 31일)"""
    return DateRange(start=date(2026, 1, 27), end=date(2026, 1, 31))


@pytest.fixture
def sample_report_config() -> ReportConfig:
    """테스트용 보고서 설정"""
    return ReportConfig(
        space_key="MAI",
        team_name="Backend Team",
        team_prefix="BE",
        mention_users="@홍길동 @김철수",
    )


@pytest.fixture
def sample_report_config_minimal() -> ReportConfig:
    """최소 설정만 있는 보고서 설정"""
    return ReportConfig(
        space_key="MAI",
        team_name="",
        team_prefix="",
        mention_users="",
    )


@pytest.fixture
def sample_report() -> Report:
    """테스트용 보고서"""
    return Report(
        main_content="# Daily Report\n\n- Task 1 완료\n- Task 2 진행 중",
        thread_tickets=None,
    )


@pytest.fixture
def sample_report_with_tickets() -> Report:
    """티켓 정보가 포함된 테스트용 보고서"""
    return Report(
        main_content="# Daily Report\n\n- Task 1 완료\n- Task 2 진행 중",
        thread_tickets="[TICKET-123](https://jira.example.com/TICKET-123) Fix bug",
    )
