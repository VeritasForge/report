"""Slack 어댑터 테스트"""

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.adapters.slack_adapter import SlackAdapter


class TestSlackAdapter:
    """SlackAdapter 테스트"""

    @pytest.fixture
    def adapter(self):
        """테스트용 어댑터 인스턴스"""
        return SlackAdapter(token="xoxb-test-token", channel="C12345678")

    @pytest.fixture
    def adapter_no_credentials(self):
        """인증 정보 없는 어댑터 인스턴스"""
        return SlackAdapter(token="", channel="")

    @patch("src.infrastructure.adapters.slack_adapter.WebClient")
    def test_should_send_message_successfully(self, mock_web_client_class, adapter):
        # Given: Slack 클라이언트가 정상 동작하는 상황
        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {"ts": "1234567890.123456"}
        mock_web_client_class.return_value = mock_client

        # When: send를 호출하면
        adapter.send("Test message")

        # Then: chat_postMessage가 호출된다
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C12345678", text="Test message"
        )

    @patch("src.infrastructure.adapters.slack_adapter.WebClient")
    def test_should_send_thread_message_when_provided(
        self, mock_web_client_class, adapter
    ):
        # Given: Slack 클라이언트가 정상 동작하는 상황
        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {"ts": "1234567890.123456"}
        mock_web_client_class.return_value = mock_client

        # When: thread_message와 함께 send를 호출하면
        adapter.send("Main message", "Thread message")

        # Then: 두 번의 chat_postMessage가 호출된다
        assert mock_client.chat_postMessage.call_count == 2

        # 첫 번째 호출: 메인 메시지
        first_call = mock_client.chat_postMessage.call_args_list[0]
        assert first_call.kwargs["channel"] == "C12345678"
        assert first_call.kwargs["text"] == "Main message"

        # 두 번째 호출: 스레드 메시지
        second_call = mock_client.chat_postMessage.call_args_list[1]
        assert second_call.kwargs["channel"] == "C12345678"
        assert second_call.kwargs["text"] == "Thread message"
        assert second_call.kwargs["thread_ts"] == "1234567890.123456"

    def test_should_skip_when_no_token(self, adapter_no_credentials):
        # Given: 토큰이 없는 상황

        # When: send를 호출하면
        adapter_no_credentials.send("Test message")

        # Then: 예외 없이 조용히 종료 (WebClient 생성 없음)
        # 클라이언트가 생성되지 않았으므로 _client는 None
        assert adapter_no_credentials._client is None

    def test_should_skip_when_no_channel(self):
        # Given: 채널이 없는 상황
        adapter = SlackAdapter(token="xoxb-test-token", channel="")

        # When: send를 호출하면
        adapter.send("Test message")

        # Then: 예외 없이 조용히 종료
        assert adapter._client is None

    @patch("src.infrastructure.adapters.slack_adapter.WebClient")
    def test_should_raise_exception_on_api_error(
        self, mock_web_client_class, adapter
    ):
        # Given: Slack API가 에러를 반환하는 상황
        mock_client = MagicMock()
        mock_client.chat_postMessage.side_effect = Exception("API Error")
        mock_web_client_class.return_value = mock_client

        # When/Then: send를 호출하면 예외가 발생한다
        with pytest.raises(Exception, match="API Error"):
            adapter.send("Test message")

    @patch("src.infrastructure.adapters.slack_adapter.WebClient")
    def test_should_reuse_client_instance(self, mock_web_client_class, adapter):
        # Given: Slack 클라이언트가 정상 동작하는 상황
        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {"ts": "1234567890.123456"}
        mock_web_client_class.return_value = mock_client

        # When: send를 두 번 호출하면
        adapter.send("First message")
        adapter.send("Second message")

        # Then: WebClient는 한 번만 생성된다
        mock_web_client_class.assert_called_once_with(token="xoxb-test-token")

    @patch("src.infrastructure.adapters.slack_adapter.WebClient")
    def test_should_not_send_thread_when_none(self, mock_web_client_class, adapter):
        # Given: Slack 클라이언트가 정상 동작하는 상황
        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {"ts": "1234567890.123456"}
        mock_web_client_class.return_value = mock_client

        # When: thread_message가 None인 상태로 send를 호출하면
        adapter.send("Main message", None)

        # Then: 메인 메시지만 전송된다
        mock_client.chat_postMessage.assert_called_once()


class TestSlackAdapterInitialization:
    """SlackAdapter 초기화 테스트"""

    def test_should_store_token_and_channel(self):
        # Given/When: SlackAdapter를 생성하면
        adapter = SlackAdapter(token="test-token", channel="test-channel")

        # Then: 토큰과 채널이 저장된다
        assert adapter._token == "test-token"
        assert adapter._channel == "test-channel"

    def test_should_initialize_client_as_none(self):
        # Given/When: SlackAdapter를 생성하면
        adapter = SlackAdapter(token="test-token", channel="test-channel")

        # Then: 클라이언트는 None으로 초기화된다 (lazy initialization)
        assert adapter._client is None
