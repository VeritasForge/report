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


class TestConfluenceAdapterGetSpaceId:
    """Space ID 조회 테스트"""

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

    @patch("src.infrastructure.adapters.confluence_adapter.requests")
    def test_should_return_space_id(self, mock_requests, adapter):
        # Given: v2 API가 space 정보를 반환하는 상황
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{"id": "11042820", "key": "MAI"}]}
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        # When: space ID를 조회하면
        result = adapter.get_space_id("MAI")

        # Then: 숫자 ID를 반환한다
        assert result == "11042820"

    @patch("src.infrastructure.adapters.confluence_adapter.requests")
    def test_should_raise_when_space_not_found(self, mock_requests, adapter):
        # Given: space가 존재하지 않는 상황
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        # When/Then: ValueError가 발생한다
        with pytest.raises(ValueError, match="Space not found"):
            adapter.get_space_id("NONEXIST")


class TestConfluenceAdapterCreatePage:
    """페이지 생성 테스트 (v2 API — Live Page)"""

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

    @patch("src.infrastructure.adapters.confluence_adapter.requests")
    def test_should_create_page_via_v2_api(self, mock_requests, adapter):
        # Given: v2 API로 페이지 생성이 성공하는 상황
        mock_space_resp = MagicMock()
        mock_space_resp.json.return_value = {"results": [{"id": "11042820", "key": "MAI"}]}
        mock_space_resp.raise_for_status.return_value = None

        mock_create_resp = MagicMock()
        mock_create_resp.json.return_value = {"id": "456", "title": "2026.04.13 ~ 04.17"}
        mock_create_resp.raise_for_status.return_value = None

        mock_requests.get.return_value = mock_space_resp
        mock_requests.post.return_value = mock_create_resp

        # When: 페이지를 생성하면
        result = adapter.create_page(
            space_key="MAI",
            title="2026.04.13 ~ 04.17",
            content="<p>new content</p>",
            parent_id="1477279756",
        )

        # Then: v2 API가 호출되고 URL이 반환된다
        assert "456" in result
        call_args = mock_requests.post.call_args
        payload = call_args[1]["json"]
        assert payload["spaceId"] == "11042820"
        assert payload["title"] == "2026.04.13 ~ 04.17"
        assert payload["parentId"] == "1477279756"
        assert payload["body"]["representation"] == "storage"
        assert payload["body"]["value"] == "<p>new content</p>"
