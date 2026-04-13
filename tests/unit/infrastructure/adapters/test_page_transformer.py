"""PageTransformer 테스트"""

import pytest
from lxml import etree

from src.infrastructure.adapters.page_transformer import (
    NS_WRAPPER_CLOSE,
    NS_WRAPPER_OPEN,
    PageTransformer,
)

# 최소 테이블 HTML 픽스처 (1명, 2일 — 월/금 구조)
MINIMAL_TABLE_HTML = (
    '<p></p>'
    '<table data-layout="center">'
    '<colgroup><col/><col/><col/><col/></colgroup>'
    '<tbody>'
    '<tr><th><p><strong>Name</strong></p></th>'
    '<th><p><strong>Date</strong></p></th>'
    '<th><p><strong>Progress</strong></p></th>'
    '<th><p><strong>Notifications</strong></p></th></tr>'
    '<tr><td rowspan="2"><p>@TestUser</p></td>'
    '<td><p>04.06</p></td>'
    '<td><ul>'
    '<li><p>Done</p></li>'
    '<li><p>Doing</p><ul><li><p>Task A</p></li></ul></li>'
    '<li><p>ToDo</p><ul><li><p>Task B</p></li></ul></li>'
    '</ul></td>'
    '<td><p>Some notification</p></td></tr>'
    '<tr>'
    '<td><p>04.10</p></td>'
    '<td><ul>'
    '<li><p>Done</p><ul><li><p>Task C</p></li></ul></li>'
    '<li><p>Doing</p><ul><li><p>Task D</p></li></ul></li>'
    '<li><p>ToDo</p><ul><li><p>Task E</p></li></ul></li>'
    '</ul></td>'
    '<td><p>Alert!</p></td></tr>'
    '</tbody></table>'
)

# 3일짜리 rowspan 테이블 (rowspan=3)
ROWSPAN_3_TABLE_HTML = (
    '<p></p>'
    '<table data-layout="center">'
    '<colgroup><col/><col/><col/><col/></colgroup>'
    '<tbody>'
    '<tr><th><p><strong>Name</strong></p></th>'
    '<th><p><strong>Date</strong></p></th>'
    '<th><p><strong>Progress</strong></p></th>'
    '<th><p><strong>Notifications</strong></p></th></tr>'
    '<tr><td rowspan="3"><p>@User1</p></td>'
    '<td><p>04.06</p></td>'
    '<td><ul><li><p>Done</p></li><li><p>Doing</p></li><li><p>ToDo</p></li></ul></td>'
    '<td><p></p></td></tr>'
    '<tr><td><p>04.07</p></td>'
    '<td><ul><li><p>Done</p></li><li><p>Doing</p></li><li><p>ToDo</p></li></ul></td>'
    '<td><p></p></td></tr>'
    '<tr><td><p>04.08</p></td>'
    '<td><ul><li><p>Done</p></li><li><p>Doing</p><ul><li><p>Ongoing work</p></li></ul></li><li><p>ToDo</p></li></ul></td>'
    '<td><p></p></td></tr>'
    '</tbody></table>'
)


class TestPageTransformerDates:
    """날짜 치환 테스트"""

    def test_should_replace_dates_when_transforming_page(self):
        # Given: 이전 주 날짜가 포함된 HTML
        transformer = PageTransformer()

        # When: 새 주 날짜로 변환하면
        result = transformer.transform(
            MINIMAL_TABLE_HTML,
            old_dates=["04.06", "04.10"],
            new_dates=["04.13", "04.17"],
        )

        # Then: 날짜가 새 주로 치환된다
        assert "04.13" in result
        assert "04.17" in result
        assert "04.06" not in result
        assert "04.10" not in result


class TestPageTransformerNotifications:
    """Notifications 컬럼 초기화 테스트"""

    def test_should_clear_all_notifications(self):
        # Given: Notifications에 내용이 있는 HTML
        transformer = PageTransformer()

        # When: 변환하면
        result = transformer.transform(
            MINIMAL_TABLE_HTML,
            old_dates=["04.06", "04.10"],
            new_dates=["04.13", "04.17"],
        )

        # Then: Notifications 내용이 모두 비워진다
        assert "Some notification" not in result
        assert "Alert!" not in result


class TestPageTransformerProgress:
    """Progress 컬럼 초기화 및 이월 테스트"""

    def test_should_keep_empty_done_doing_todo_structure(self):
        # Given: Progress에 작업 내용이 있는 HTML
        transformer = PageTransformer()

        # When: 변환하면
        result = transformer.transform(
            MINIMAL_TABLE_HTML,
            old_dates=["04.06", "04.10"],
            new_dates=["04.13", "04.17"],
        )

        # Then: Done/Doing/ToDo 헤더는 유지된다
        assert "Done" in result
        assert "Doing" in result
        assert "ToDo" in result

    def test_should_carry_over_friday_doing_todo_to_monday_todo(self):
        # Given: 금요일(마지막 행)에 Doing/ToDo 항목이 있는 HTML
        transformer = PageTransformer()

        # When: 변환하면
        result = transformer.transform(
            MINIMAL_TABLE_HTML,
            old_dates=["04.06", "04.10"],
            new_dates=["04.13", "04.17"],
        )

        # Then: 금요일의 Doing(Task D)과 ToDo(Task E)가 월요일의 ToDo로 이월된다
        wrapped = f'{NS_WRAPPER_OPEN}{result}{NS_WRAPPER_CLOSE}'
        root = etree.fromstring(wrapped.encode("utf-8"))
        data_rows = root.findall(".//tbody/tr")[1:]

        # 첫 번째 행(월요일) Progress 셀
        monday_row = data_rows[0]
        progress_cell = monday_row.findall("td")[2]  # rowspan 행이므로 index 2
        progress_text = etree.tostring(progress_cell, encoding="unicode")

        assert "Task D" in progress_text
        assert "Task E" in progress_text

    def test_should_clear_friday_progress_after_carryover(self):
        # Given: 금요일(마지막 행)에 작업 내용이 있는 HTML
        transformer = PageTransformer()

        # When: 변환하면
        result = transformer.transform(
            MINIMAL_TABLE_HTML,
            old_dates=["04.06", "04.10"],
            new_dates=["04.13", "04.17"],
        )

        # Then: 금요일 행의 작업 내용이 초기화된다
        wrapped = f'{NS_WRAPPER_OPEN}{result}{NS_WRAPPER_CLOSE}'
        root = etree.fromstring(wrapped.encode("utf-8"))
        data_rows = root.findall(".//tbody/tr")[1:]

        friday_row = data_rows[-1]
        progress_cell = friday_row.findall("td")[1]  # rowspan 없는 행이므로 index 1
        progress_text = etree.tostring(progress_cell, encoding="unicode")

        assert "Task C" not in progress_text
        assert "Task D" not in progress_text
        assert "Task E" not in progress_text


class TestPageTransformerDynamicRowspan:
    """동적 rowspan 처리 테스트"""

    def test_should_handle_dynamic_rowspan(self):
        # Given: rowspan=3인 테이블
        transformer = PageTransformer()

        # When: 변환하면
        result = transformer.transform(
            ROWSPAN_3_TABLE_HTML,
            old_dates=["04.06", "04.07", "04.08"],
            new_dates=["04.13", "04.14", "04.15"],
        )

        # Then: 3번째 행(마지막)의 Doing 항목이 1번째 행 ToDo로 이월된다
        wrapped = f'{NS_WRAPPER_OPEN}{result}{NS_WRAPPER_CLOSE}'
        root = etree.fromstring(wrapped.encode("utf-8"))
        data_rows = root.findall(".//tbody/tr")[1:]
        monday_progress = data_rows[0].findall("td")[2]
        progress_text = etree.tostring(monday_progress, encoding="unicode")
        assert "Ongoing work" in progress_text


class TestPageTransformerNamespace:
    """네임스페이스 전처리 테스트"""

    def test_should_handle_namespace_preprocessing(self):
        # Given: ac: 네임스페이스가 포함된 HTML
        html_with_ns = (
            '<p></p>'
            '<table data-layout="center">'
            '<colgroup><col/><col/><col/><col/></colgroup>'
            '<tbody>'
            '<tr><th><p><strong>Name</strong></p></th>'
            '<th><p><strong>Date</strong></p></th>'
            '<th><p><strong>Progress</strong></p></th>'
            '<th><p><strong>Notifications</strong></p></th></tr>'
            '<tr><td rowspan="1"><p>@User</p></td>'
            '<td><p>04.06</p></td>'
            '<td><ul><li><p>Done</p></li>'
            '<li><p>Doing</p><ul><li><p>'
            '<ac:structured-macro ac:name="jira"><ac:parameter ac:name="key">TICKET-123</ac:parameter></ac:structured-macro>'
            '</p></li></ul></li>'
            '<li><p>ToDo</p></li></ul></td>'
            '<td><p></p></td></tr>'
            '</tbody></table>'
        )

        transformer = PageTransformer()

        # When: 변환하면
        result = transformer.transform(
            html_with_ns,
            old_dates=["04.06"],
            new_dates=["04.13"],
        )

        # Then: 매크로가 보존되고 날짜가 변경된다
        assert "04.13" in result
        assert "TICKET-123" in result

    def test_should_preserve_jira_macros_in_carryover(self):
        # Given: 금요일 Doing에 JIRA 매크로가 포함된 HTML (rowspan=1이므로 동일 행이 금요일)
        html_with_jira = (
            '<p></p>'
            '<table data-layout="center">'
            '<colgroup><col/><col/><col/><col/></colgroup>'
            '<tbody>'
            '<tr><th><p><strong>Name</strong></p></th>'
            '<th><p><strong>Date</strong></p></th>'
            '<th><p><strong>Progress</strong></p></th>'
            '<th><p><strong>Notifications</strong></p></th></tr>'
            '<tr><td rowspan="1"><p>@User</p></td>'
            '<td><p>04.10</p></td>'
            '<td><ul><li><p>Done</p></li>'
            '<li><p>Doing</p><ul><li><p>'
            '<ac:structured-macro ac:name="jira"><ac:parameter ac:name="key">TICKET-999</ac:parameter></ac:structured-macro>'
            ' review</p></li></ul></li>'
            '<li><p>ToDo</p></li></ul></td>'
            '<td><p></p></td></tr>'
            '</tbody></table>'
        )

        transformer = PageTransformer()

        # When: 변환하면
        result = transformer.transform(
            html_with_jira,
            old_dates=["04.10"],
            new_dates=["04.17"],
        )

        # Then: JIRA 매크로가 월요일 ToDo에 이월된다
        assert "TICKET-999" in result
