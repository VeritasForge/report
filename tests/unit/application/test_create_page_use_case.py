"""CreateWeeklyPageUseCase 테스트"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.application.create_page_use_case import CreateWeeklyPageUseCase
from src.domain.models import WeeklyPageConfig


@pytest.fixture
def mock_confluence():
    return MagicMock()


@pytest.fixture
def mock_transformer():
    return MagicMock()


@pytest.fixture
def config():
    return WeeklyPageConfig(space_key="MAI", parent_page_id="1477279756")


@pytest.fixture
def use_case(mock_confluence, mock_transformer):
    return CreateWeeklyPageUseCase(
        confluence=mock_confluence, transformer=mock_transformer
    )


class TestCreateWeeklyPageUseCase:
    """주간 페이지 생성 유스케이스 테스트"""

    def test_should_create_page_with_transformed_content(
        self, use_case, mock_confluence, mock_transformer, config
    ):
        # Given: 이전 주 페이지가 존재하고 새 주 페이지는 없는 상황
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123", "title": "2026.04.06 ~ 04.10"},  # 이전 주 존재
            None,  # 새 주 미존재
        ]
        mock_confluence.get_page_content.return_value = "<table>old html</table>"
        mock_transformer.transform.return_value = "<table>new html</table>"
        mock_confluence.create_page.return_value = "https://test.atlassian.net/wiki/pages/456"

        # When: 유스케이스를 실행하면
        result = use_case.execute(config, target_date=date(2026, 4, 13))

        # Then: 페이지가 생성된다
        assert result is True
        mock_confluence.get_page_content.assert_called_once_with("123")
        mock_transformer.transform.assert_called_once()
        mock_confluence.create_page.assert_called_once()

    def test_should_skip_when_page_already_exists(
        self, use_case, mock_confluence, config
    ):
        # Given: 새 주 페이지가 이미 존재하는 상황
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123"},  # 이전 주 존재
            {"id": "456"},  # 새 주도 존재
        ]

        # When: 유스케이스를 실행하면
        result = use_case.execute(config, target_date=date(2026, 4, 13))

        # Then: True를 반환하고 페이지를 생성하지 않는다 (스킵)
        assert result is True
        mock_confluence.create_page.assert_not_called()

    def test_should_return_false_when_source_page_not_found(
        self, use_case, mock_confluence, config
    ):
        # Given: 이전 주 페이지가 없는 상황
        mock_confluence.get_page_by_title.return_value = None

        # When: 유스케이스를 실행하면
        result = use_case.execute(config, target_date=date(2026, 4, 13))

        # Then: False를 반환한다
        assert result is False
        mock_confluence.create_page.assert_not_called()

    def test_should_pass_correct_dates_to_transformer(
        self, use_case, mock_confluence, mock_transformer, config
    ):
        # Given: 2026-04-13 (월요일) 기준
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123"},  # 이전 주 존재
            None,  # 새 주 미존재
        ]
        mock_confluence.get_page_content.return_value = "<table>html</table>"
        mock_transformer.transform.return_value = "<table>new</table>"
        mock_confluence.create_page.return_value = "url"

        # When: 유스케이스를 실행하면
        use_case.execute(config, target_date=date(2026, 4, 13))

        # Then: 이전 주(04.06~04.10) → 새 주(04.13~04.17) 날짜가 전달된다
        call_args = mock_transformer.transform.call_args
        old_dates = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("old_dates")
        new_dates = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("new_dates")
        assert old_dates == ["04.06", "04.07", "04.08", "04.09", "04.10"]
        assert new_dates == ["04.13", "04.14", "04.15", "04.16", "04.17"]

    def test_should_create_page_with_correct_title_and_parent(
        self, use_case, mock_confluence, mock_transformer, config
    ):
        # Given: 정상 실행 상황
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123"},
            None,
        ]
        mock_confluence.get_page_content.return_value = "<table>html</table>"
        mock_transformer.transform.return_value = "<table>new</table>"
        mock_confluence.create_page.return_value = "url"

        # When: 유스케이스를 실행하면
        use_case.execute(config, target_date=date(2026, 4, 13))

        # Then: 올바른 제목과 parent_id로 생성한다
        call_args = mock_confluence.create_page.call_args
        assert call_args[1]["title"] == "2026.04.13 ~ 04.17"
        assert call_args[1]["parent_id"] == "1477279756"
        assert call_args[1]["space_key"] == "MAI"
