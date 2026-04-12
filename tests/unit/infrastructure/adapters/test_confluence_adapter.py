"""ConfluenceAdapter 테스트"""

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.adapters.confluence_adapter import ConfluenceAdapter


class TestConfluenceAdapterGetPageByTitle:
    """제목으로 페이지 조회 테스트"""

    @pytest.fixture
    def mock_confluence(self):
        with patch("src.infrastructure.adapters.confluence_adapter.Confluence") as mock:
            yield mock.return_value

    @pytest.fixture
    def adapter(self, mock_confluence):
        return ConfluenceAdapter(
            url="https://test.atlassian.net",
            user="test@test.com",
            token="test-token",
        )

    def test_should_return_page_when_found(self, adapter, mock_confluence):
        # Given: 페이지가 존재하는 상황
        mock_confluence.get_page_by_title.return_value = {
            "id": "123",
            "title": "2026.04.06 ~ 04.10",
        }

        # When: 제목으로 페이지를 조회하면
        result = adapter.get_page_by_title("MAI", "2026.04.06 ~ 04.10")

        # Then: 페이지 정보를 반환한다
        assert result is not None
        assert result["id"] == "123"
        mock_confluence.get_page_by_title.assert_called_once_with(
            "MAI", "2026.04.06 ~ 04.10"
        )

    def test_should_return_none_when_not_found(self, adapter, mock_confluence):
        # Given: 페이지가 존재하지 않는 상황
        mock_confluence.get_page_by_title.return_value = None

        # When: 제목으로 페이지를 조회하면
        result = adapter.get_page_by_title("MAI", "2026.04.13 ~ 04.17")

        # Then: None을 반환한다
        assert result is None


class TestConfluenceAdapterGetPageContent:
    """페이지 content 조회 테스트"""

    @pytest.fixture
    def mock_confluence(self):
        with patch("src.infrastructure.adapters.confluence_adapter.Confluence") as mock:
            yield mock.return_value

    @pytest.fixture
    def adapter(self, mock_confluence):
        return ConfluenceAdapter(
            url="https://test.atlassian.net",
            user="test@test.com",
            token="test-token",
        )

    def test_should_return_storage_format_html(self, adapter, mock_confluence):
        # Given: 페이지의 body.storage가 존재하는 상황
        mock_confluence.get_page_by_id.return_value = {
            "body": {"storage": {"value": "<p>test content</p>"}}
        }

        # When: 페이지 내용을 조회하면
        result = adapter.get_page_content("123")

        # Then: storage format HTML을 반환한다
        assert result == "<p>test content</p>"
        mock_confluence.get_page_by_id.assert_called_once_with(
            "123", expand="body.storage"
        )


class TestConfluenceAdapterCreatePage:
    """페이지 생성 테스트"""

    @pytest.fixture
    def mock_confluence(self):
        with patch("src.infrastructure.adapters.confluence_adapter.Confluence") as mock:
            yield mock.return_value

    @pytest.fixture
    def adapter(self, mock_confluence):
        return ConfluenceAdapter(
            url="https://test.atlassian.net",
            user="test@test.com",
            token="test-token",
        )

    def test_should_create_page_and_return_url(self, adapter, mock_confluence):
        # Given: 페이지 생성이 성공하는 상황
        mock_confluence.create_page.return_value = {
            "id": "456",
            "_links": {"base": "https://test.atlassian.net/wiki", "webui": "/spaces/MAI/pages/456"},
        }

        # When: 페이지를 생성하면
        result = adapter.create_page(
            space_key="MAI",
            title="2026.04.13 ~ 04.17",
            content="<p>new content</p>",
            parent_id="1477279756",
        )

        # Then: 페이지 URL을 반환한다
        assert "456" in result
        mock_confluence.create_page.assert_called_once_with(
            space="MAI",
            title="2026.04.13 ~ 04.17",
            body="<p>new content</p>",
            parent_id="1477279756",
            representation="storage",
        )
