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

    page_title_prefix = os.environ.get("CONFLUENCE_PAGE_TITLE_PREFIX")
    if not page_title_prefix:
        print("ERROR: CONFLUENCE_PAGE_TITLE_PREFIX environment variable is not set.")
        return None

    products = os.environ.get("CONFLUENCE_PRODUCTS")
    if not products:
        print("ERROR: CONFLUENCE_PRODUCTS environment variable is not set.")
        return None

    authors = os.environ.get("CONFLUENCE_AUTHORS")
    if not authors:
        print("ERROR: CONFLUENCE_AUTHORS environment variable is not set.")
        return None

    page_products = os.environ.get("CONFLUENCE_PAGE_PRODUCTS", products)
    team_name = os.environ.get("REPORT_TEAM_NAME", "")
    cli_type = os.environ.get("CLI_TYPE", "claude")

    report_config = ReportConfig(
        space_key=space_key,
        page_title_prefix=page_title_prefix,
        products=products,
        page_products=page_products,
        authors=authors,
        team_name=team_name,
    )

    return AppConfig(
        report=report_config,
        slack_token=os.environ.get("SLACK_TOKEN", ""),
        slack_channel=os.environ.get("SLACK_CHANNEL", ""),
        cli_type=cli_type,
    )
