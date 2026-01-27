import os
from dataclasses import dataclass

from dotenv import load_dotenv

from ..domain.models import ReportConfig


@dataclass
class AppConfig:
    """애플리케이션 전체 설정"""
    report: ReportConfig
    slack_token: str
    slack_channel: str
    cli_type: str


def load_config_from_env() -> AppConfig | None:
    """환경변수에서 설정 로드. 필수 값이 없으면 None 반환."""
    load_dotenv()

    space_key = os.environ.get("CONFLUENCE_SPACE_KEY")
    if not space_key:
        print("ERROR: CONFLUENCE_SPACE_KEY environment variable is not set.")
        return None

    team_name = os.environ.get("REPORT_TEAM_NAME", "")
    team_prefix = os.environ.get("REPORT_TEAM_PREFIX", "")
    mention_users = os.environ.get("REPORT_MENTION_USERS", "")
    cli_type = os.environ.get("CLI_TYPE", "claude")

    report_config = ReportConfig(
        space_key=space_key,
        team_name=team_name,
        team_prefix=team_prefix,
        mention_users=mention_users,
    )

    return AppConfig(
        report=report_config,
        slack_token=os.environ.get("SLACK_TOKEN", ""),
        slack_channel=os.environ.get("SLACK_CHANNEL", ""),
        cli_type=cli_type,
    )
