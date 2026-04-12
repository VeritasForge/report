"""Confluence REST API 어댑터"""

from atlassian import Confluence


class ConfluenceAdapter:
    """atlassian-python-api를 사용한 Confluence 페이지 접근"""

    def __init__(self, url: str, user: str, token: str):
        self.client = Confluence(url=url, username=user, password=token)

    def get_page_by_title(self, space_key: str, title: str) -> dict | None:
        """제목으로 페이지 조회. 없으면 None 반환."""
        return self.client.get_page_by_title(space_key, title)

    def get_page_content(self, page_id: str) -> str:
        """페이지의 storage format HTML 조회"""
        page = self.client.get_page_by_id(page_id, expand="body.storage")
        return page["body"]["storage"]["value"]

    def create_page(
        self, space_key: str, title: str, content: str, parent_id: str
    ) -> str:
        """새 페이지 생성. 생성된 페이지 URL 반환."""
        result = self.client.create_page(
            space=space_key,
            title=title,
            body=content,
            parent_id=parent_id,
            representation="storage",
        )
        base = result["_links"]["base"]
        webui = result["_links"]["webui"]
        return f"{base}{webui}"
