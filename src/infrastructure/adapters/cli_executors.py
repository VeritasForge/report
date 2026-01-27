import subprocess


class ClaudeCLIExecutor:
    """Claude CLI 실행기"""

    def execute(self, prompt: str) -> str | None:
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
    """Gemini CLI 실행기"""

    def execute(self, prompt: str) -> str | None:
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
