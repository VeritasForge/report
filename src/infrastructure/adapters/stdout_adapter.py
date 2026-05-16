"""Stdout 알림 어댑터 — dry-run 모드용 NotificationPort 구현."""


class StdoutAdapter:
    """Slack 대신 stdout으로 출력. NotificationPort 시그니처 준수.

    `--dry-run` / `DRY_RUN=1` 시 SlackAdapter 자리에 주입되어 로컬 디버깅용 출력 수행.
    """

    _SEPARATOR = "─" * 40

    def send(self, message: str, thread_message: str | None = None) -> None:
        """메시지를 stdout에 출력. thread_message가 truthy면 구분선 후 함께 출력."""
        print(message)
        if thread_message:
            print(self._SEPARATOR)
            print(thread_message)
