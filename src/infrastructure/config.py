import os
from dataclasses import dataclass, field
from datetime import date

from dotenv import load_dotenv

from ..domain.models import ReportConfig


@dataclass
class AppConfig:
    """애플리케이션 전체 설정"""
    report: ReportConfig
    slack_token: str
    slack_channel: str
    cli_type: str
    report_mode: str = "daily"
    slack_channel_weekly: str = ""
    parent_page_id: str = ""
    team_members: list[str] = field(default_factory=list)


def load_config_from_env(report_date: date | None = None) -> AppConfig | None:
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
    report_mode = os.environ.get("REPORT_MODE", "daily")

    parent_page_id = os.environ.get("CONFLUENCE_PARENT_PAGE_ID", "")
    team_members_str = os.environ.get("PAGE_TEAM_MEMBERS", "")
    team_members = [m.strip() for m in team_members_str.split(",") if m.strip()]

    report_config = ReportConfig(
        space_key=space_key,
        team_name=team_name,
        team_prefix=team_prefix,
        mention_users=mention_users,
        report_date=report_date,
    )

    return AppConfig(
        report=report_config,
        slack_token=os.environ.get("SLACK_TOKEN", ""),
        slack_channel=os.environ.get("SLACK_CHANNEL", ""),
        slack_channel_weekly=os.environ.get("SLACK_CHANNEL_WEEKLY", ""),
        cli_type=cli_type,
        report_mode=report_mode,
        parent_page_id=parent_page_id,
        team_members=team_members,
    )
