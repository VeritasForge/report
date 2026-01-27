import subprocess


class ClaudeCLIExecutor:
    """Claude CLI 실행기 - /daily_report 커맨드 실행"""

    def execute(self, space_key: str, mention_users: str = "") -> str | None:
        """
        /daily_report 커맨드를 실행합니다.
        날짜 범위는 daily_report.md에서 자동으로 계산됩니다.

        Args:
            space_key: Confluence 스페이스 키 (예: 'MAI')
            mention_users: 지연/보류 시 멘션할 사용자 (예: '@홍길동 @김철수')
        """
        prompt = f'/daily_report {space_key} "{mention_users}"' if mention_users else f"/daily_report {space_key}"
        command = ['claude', '-p', prompt, '--dangerously-skip-permissions']
        return self._run_command(command, cli_name='claude')

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
    """Gemini CLI 실행기 - /daily_report 커맨드 실행"""

    def execute(self, space_key: str, mention_users: str = "") -> str | None:
        """
        /daily_report 커맨드를 실행합니다.
        날짜 범위는 daily_report.md에서 자동으로 계산됩니다.

        Args:
            space_key: Confluence 스페이스 키 (예: 'MAI')
            mention_users: 지연/보류 시 멘션할 사용자 (예: '@홍길동 @김철수')
        """
        prompt = f'/daily_report {space_key} "{mention_users}"' if mention_users else f"/daily_report {space_key}"
        command = ['gemini', '-p', prompt]
        return self._run_command(command, cli_name='gemini')

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
