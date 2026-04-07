import subprocess
from datetime import date


class ClaudeCLIExecutor:
    """Claude CLI 실행기 - 지정된 커맨드 실행"""

    def __init__(self, command: str = "daily_report"):
        self._command = command

    def execute(self, space_key: str, mention_users: str = "", report_date: date | None = None) -> str | None:
        """
        커맨드를 실행합니다.

        Args:
            space_key: Confluence 스페이스 키 (예: 'MAI')
            mention_users: 지연/보류 시 멘션할 사용자 (예: '@홍길동 @김철수')
            report_date: 리포트 대상 날짜 (None이면 오늘 기준)
        """
        prompt = self._build_prompt(space_key, mention_users, report_date)
        command = ['claude', '-p', prompt, '--dangerously-skip-permissions']
        return self._run_command(command, cli_name='claude')

    def _build_prompt(self, space_key: str, mention_users: str, report_date: date | None) -> str:
        parts = [f"/{self._command}", space_key]
        if mention_users:
            parts.append(f'"{mention_users}"')
        if report_date:
            parts.append(f"--date {report_date.isoformat()}")
        return " ".join(parts)

    def _run_command(self, command: list[str], cli_name: str) -> str | None:
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                print(f"ERROR: {cli_name} CLI failed with exit code {process.returncode}.")
                print(f"ERROR: Stderr: {stderr.strip()}")
                return None

            return stdout.strip()

        except FileNotFoundError:
            print(f"ERROR: '{cli_name}' CLI not found. Please ensure it is installed and in your system's PATH.")
            return None
        except Exception as e:
            print(f"ERROR: An unexpected error occurred: {e}")
            return None


class GeminiCLIExecutor:
    """Gemini CLI 실행기 - 지정된 커맨드 실행"""

    def __init__(self, command: str = "daily_report"):
        self._command = command

    def execute(self, space_key: str, mention_users: str = "", report_date: date | None = None) -> str | None:
        """
        커맨드를 실행합니다.

        Args:
            space_key: Confluence 스페이스 키 (예: 'MAI')
            mention_users: 지연/보류 시 멘션할 사용자 (예: '@홍길동 @김철수')
            report_date: 리포트 대상 날짜 (None이면 오늘 기준)
        """
        prompt = self._build_prompt(space_key, mention_users, report_date)
        command = ['gemini', '-p', prompt]
        return self._run_command(command, cli_name='gemini')

    def _build_prompt(self, space_key: str, mention_users: str, report_date: date | None) -> str:
        parts = [f"/{self._command}", space_key]
        if mention_users:
            parts.append(f'"{mention_users}"')
        if report_date:
            parts.append(f"--date {report_date.isoformat()}")
        return " ".join(parts)

    def _run_command(self, command: list[str], cli_name: str) -> str | None:
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                print(f"ERROR: {cli_name} CLI failed with exit code {process.returncode}.")
                print(f"ERROR: Stderr: {stderr.strip()}")
                return None

            return stdout.strip()

        except FileNotFoundError:
            print(f"ERROR: '{cli_name}' CLI not found. Please ensure it is installed and in your system's PATH.")
            return None
        except Exception as e:
            print(f"ERROR: An unexpected error occurred: {e}")
            return None
