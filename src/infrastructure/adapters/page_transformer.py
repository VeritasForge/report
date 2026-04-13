"""Confluence 페이지 HTML 변환 어댑터"""

import re
from copy import deepcopy
from html import unescape as _html_unescape

from lxml import etree

# Confluence storage format에서 사용하는 네임스페이스
AC_NS = "http://atlassian.com/content"
RI_NS = "http://atlassian.com/resource/identifier"
NSMAP = {"ac": AC_NS, "ri": RI_NS}
NS_WRAPPER_OPEN = f'<root xmlns:ac="{AC_NS}" xmlns:ri="{RI_NS}">'
NS_WRAPPER_CLOSE = "</root>"

# XML 표준 엔티티 (unescape하면 XML이 깨지므로 보존)
_XML_ENTITY_NAMES = frozenset({"amp", "lt", "gt", "quot", "apos"})


def _unescape_html_entities(text: str) -> str:
    """HTML named entities를 유니코드로 변환 (XML 표준 엔티티 &amp; 등은 보존)"""
    def _replace(match: re.Match) -> str:
        name = match.group(1)
        if name in _XML_ENTITY_NAMES:
            return match.group(0)
        return _html_unescape(match.group(0))
    return re.sub(r"&([a-zA-Z]+);", _replace, text)


class PageTransformer:
    """Confluence storage format HTML을 새 주간 페이지로 변환"""

    def transform(self, html: str, old_dates: list[str], new_dates: list[str]) -> str:
        """이전 주 HTML을 새 주 형식으로 변환"""
        # HTML 엔티티(&rarr;, &nbsp; 등)를 유니코드로 변환 (XML 표준 엔티티 보존)
        html = _unescape_html_entities(html)
        wrapped = f"{NS_WRAPPER_OPEN}{html}{NS_WRAPPER_CLOSE}"
        root = etree.fromstring(wrapped.encode("utf-8"))

        table = root.find(".//tbody")
        if table is None:
            raise ValueError("테이블을 찾을 수 없습니다.")

        rows = table.findall("tr")
        if len(rows) < 2:
            raise ValueError("테이블에 데이터 행이 없습니다.")

        data_rows = rows[1:]  # 헤더 행 스킵
        date_map = dict(zip(old_dates, new_dates))

        # 팀원 블록별 처리
        blocks = self._identify_member_blocks(data_rows)
        for block in blocks:
            self._replace_dates(block, date_map)
            self._transform_progress(block)
            self._clear_notifications(block)

        result = etree.tostring(root, encoding="unicode")
        # wrapper 제거
        result = result[len(NS_WRAPPER_OPEN) : -len(NS_WRAPPER_CLOSE)]
        return result

    def _identify_member_blocks(self, rows: list) -> list[list]:
        """rowspan 값을 기반으로 팀원별 행 블록 식별"""
        blocks = []
        i = 0
        while i < len(rows):
            cells = rows[i].findall("td")
            rowspan = cells[0].get("rowspan")
            if rowspan:
                span = int(rowspan)
                blocks.append(rows[i : i + span])
                i += span
            else:
                i += 1
        return blocks

    def _replace_dates(self, block: list, date_map: dict[str, str]) -> None:
        """Date 컬럼의 날짜 텍스트를 치환"""
        for row in block:
            date_cell = self._get_date_cell(row)
            for p in date_cell.findall("p"):
                if p.text and p.text.strip() in date_map:
                    p.text = date_map[p.text.strip()]

    def _transform_progress(self, block: list) -> None:
        """Progress 컬럼 변환: 금요일 이월 + 전체 초기화"""
        # 마지막 행(금요일)에서 Doing/ToDo 항목 추출
        friday_row = block[-1]
        friday_progress = self._get_progress_cell(friday_row)
        carryover_items = self._extract_doing_todo_items(friday_progress)

        # 모든 행의 Progress 초기화
        for row in block:
            progress_cell = self._get_progress_cell(row)
            self._reset_progress(progress_cell)

        # 첫 번째 행(월요일)의 ToDo에 이월 항목 삽입
        monday_progress = self._get_progress_cell(block[0])
        self._insert_carryover_to_todo(monday_progress, carryover_items)

    def _clear_notifications(self, block: list) -> None:
        """Notifications 컬럼의 내용을 빈 <p>로 교체"""
        for row in block:
            notif_cell = self._get_notification_cell(row)
            for child in list(notif_cell):
                notif_cell.remove(child)
            notif_cell.text = None
            empty_p = etree.SubElement(notif_cell, "p")
            empty_p.text = None

    def _get_date_cell(self, row) -> etree._Element:
        """행에서 Date 셀 반환"""
        cells = row.findall("td")
        return cells[1] if self._has_rowspan(cells) else cells[0]

    def _get_progress_cell(self, row) -> etree._Element:
        """행에서 Progress 셀 반환"""
        cells = row.findall("td")
        return cells[2] if self._has_rowspan(cells) else cells[1]

    def _get_notification_cell(self, row) -> etree._Element:
        """행에서 Notifications 셀 반환"""
        cells = row.findall("td")
        return cells[3] if self._has_rowspan(cells) else cells[2]

    def _has_rowspan(self, cells: list) -> bool:
        """첫 번째 셀에 rowspan 속성이 있는지 확인"""
        return cells[0].get("rowspan") is not None

    def _extract_doing_todo_items(self, progress_cell) -> list:
        """Progress 셀에서 Doing/ToDo 하위 <li> 항목 추출 (deep copy)"""
        items = []
        ul = progress_cell.find("ul")
        if ul is None:
            return items

        for li in ul.findall("li"):
            p = li.find("p")
            if p is not None and p.text:
                label = p.text.strip()
                if label in ("Doing", "ToDo"):
                    sub_ul = li.find("ul")
                    if sub_ul is not None:
                        for sub_li in sub_ul.findall("li"):
                            items.append(deepcopy(sub_li))
        return items

    def _reset_progress(self, progress_cell) -> None:
        """Progress 셀을 빈 Done/Doing/ToDo 리스트로 초기화"""
        for child in list(progress_cell):
            progress_cell.remove(child)
        progress_cell.text = None

        ul = etree.SubElement(progress_cell, "ul")
        for label in ("Done", "Doing", "ToDo"):
            li = etree.SubElement(ul, "li")
            p = etree.SubElement(li, "p")
            p.text = label

    def _insert_carryover_to_todo(self, progress_cell, items: list) -> None:
        """월요일 Progress의 ToDo 하위에 이월 항목 삽입"""
        if not items:
            return

        ul = progress_cell.find("ul")
        if ul is None:
            return

        for li in ul.findall("li"):
            p = li.find("p")
            if p is not None and p.text and p.text.strip() == "ToDo":
                sub_ul = etree.SubElement(li, "ul")
                for item in items:
                    sub_ul.append(item)
                break
