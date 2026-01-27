from slack_sdk import WebClient


class SlackAdapter:
    """Slack API를 통한 알림 전송 구현체"""

    def __init__(self, token: str, channel: str):
        self._token = token
        self._channel = channel
        self._client: WebClient | None = None

    def send(self, message: str, thread_message: str | None = None) -> None:
        if not self._token or not self._channel:
            print("WARNING: SLACK_TOKEN or SLACK_CHANNEL environment variables not set. Skipping Slack notification.")
            return

        try:
            if self._client is None:
                self._client = WebClient(token=self._token)

            response = self._client.chat_postMessage(channel=self._channel, text=message)
            print(f"Successfully sent report to Slack channel '{self._channel}'.")

            if thread_message:
                self._client.chat_postMessage(
                    channel=self._channel,
                    text=thread_message,
                    thread_ts=response["ts"]
                )
                print("Successfully sent ticket links as thread reply.")

        except Exception as e:
            print(f"ERROR: An error occurred while sending report to Slack: {e}")
            raise e
