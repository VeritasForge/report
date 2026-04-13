"""Confluence REST API 어댑터"""

import requests
from atlassian import Confluence


class ConfluenceAdapter:
    """atlassian-python-api + REST API v2를 사용한 Confluence 페이지 접근"""

    def __init__(self, url: str, user: str, token: str):
        self.client = Confluence(url=url, username=user, password=token)
        self._base_url = url.rstrip("/")
        self._auth = (user, token)

    def get_page_by_title(self, space_key: str, title: str) -> dict | None:
        """제목으로 페이지 조회. 없으면 None 반환."""
        return self.client.get_page_by_title(space_key, title)

    def get_page_content(self, page_id: str) -> str:
        """페이지의 storage format HTML 조회"""
        page = self.client.get_page_by_id(page_id, expand="body.storage")
        return page["body"]["storage"]["value"]

    def get_space_id(self, space_key: str) -> str:
        """space key로 space ID(숫자) 조회 (v2 API용)"""
        resp = requests.get(
            f"{self._base_url}/api/v2/spaces?keys={space_key}",
            auth=self._auth,
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            raise ValueError(f"Space not found: {space_key}")
        return results[0]["id"]

    def create_page(
        self, space_key: str, title: str, content: str, parent_id: str
    ) -> str:
        """Live Page로 새 페이지 생성 (v2 API). 생성된 페이지 URL 반환."""
        space_id = self.get_space_id(space_key)

        payload = {
            "spaceId": space_id,
            "title": title,
            "parentId": parent_id,
            "status": "current",
            "body": {
                "representation": "storage",
                "value": content,
            },
        }

        resp = requests.post(
            f"{self._base_url}/api/v2/pages",
            json=payload,
            auth=self._auth,
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        page_id = result["id"]
        return f"{self._base_url}/spaces/{space_key}/pages/{page_id}/{title}"
