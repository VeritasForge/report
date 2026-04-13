"""주간 페이지 자동 생성 유스케이스"""

from datetime import date, timedelta

from ..domain.models import WeeklyPageConfig
from ..domain.services import (
    calculate_last_week_range,
    calculate_this_week_range,
    format_confluence_page_title,
)
from .ports import ConfluencePort, PageTransformerPort


class CreateWeeklyPageUseCase:
    """이전 주 Confluence 페이지를 복사하여 새 주간 페이지 생성"""

    def __init__(self, confluence: ConfluencePort, transformer: PageTransformerPort):
        self.confluence = confluence
        self.transformer = transformer

    def execute(self, config: WeeklyPageConfig, target_date: date | None = None) -> bool:
        """
        새 주간 페이지 생성.
        Returns: True (성공 또는 스킵), False (실패)
        """
        today = target_date or date.today()

        # 1. 날짜 계산
        last_week = calculate_last_week_range(today)
        this_week = calculate_this_week_range(today)
        old_title = format_confluence_page_title(last_week)
        new_title = format_confluence_page_title(this_week)

        print(f"Source page: {old_title}")
        print(f"Target page: {new_title}")

        # 2. 이전 주 페이지 조회
        source_page = self.confluence.get_page_by_title(config.space_key, old_title)
        if source_page is None:
            print(f"ERROR: Source page not found: {old_title}")
            return False

        # 3. 새 주 페이지 중복 확인
        existing_page = self.confluence.get_page_by_title(config.space_key, new_title)
        if existing_page is not None:
            print(f"Page already exists: {new_title} — skipping.")
            return True

        # 4. 이전 페이지 HTML 가져오기
        html = self.confluence.get_page_content(source_page["id"])

        # 5. HTML 변환
        old_dates = self._generate_date_strings(last_week.start, last_week.end)
        new_dates = self._generate_date_strings(this_week.start, this_week.end)
        new_html = self.transformer.transform(html, old_dates, new_dates)

        # 6. 새 페이지 생성
        url = self.confluence.create_page(
            space_key=config.space_key,
            title=new_title,
            content=new_html,
            parent_id=config.parent_page_id,
        )
        print(f"Created: {url}")
        return True

    def _generate_date_strings(self, monday: date, friday: date) -> list[str]:
        """월~금 날짜를 MM.DD 형식 리스트로 생성"""
        dates = []
        current = monday
        while current <= friday:
            dates.append(current.strftime("%m.%d"))
            current += timedelta(days=1)
        return dates
