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


class TestPageTransformerEdgeCases:
    """에지 케이스 및 오류 처리 테스트"""

    def test_should_raise_value_error_when_no_tbody(self):
        # Given: <tbody>가 없는 HTML
        html_no_tbody = '<p>No table here</p>'
        transformer = PageTransformer()

        # When/Then: transform을 호출하면 ValueError가 발생한다
        with pytest.raises(ValueError, match="테이블을 찾을 수 없습니다"):
            transformer.transform(html_no_tbody, old_dates=[], new_dates=[])

    def test_should_raise_value_error_when_only_header_row(self):
        # Given: 헤더 행만 있고 데이터 행이 없는 HTML
        html_header_only = (
            '<table><tbody>'
            '<tr><th><p>Name</p></th><th><p>Date</p></th>'
            '<th><p>Progress</p></th><th><p>Notifications</p></th></tr>'
            '</tbody></table>'
        )
        transformer = PageTransformer()

        # When/Then: transform을 호출하면 ValueError가 발생한다
        with pytest.raises(ValueError, match="테이블에 데이터 행이 없습니다"):
            transformer.transform(html_header_only, old_dates=[], new_dates=[])

    def test_should_handle_row_without_rowspan_in_identify_member_blocks(self):
        # Given: rowspan 없는 행들이 포함된 HTML (각 행이 독립 블록으로 처리)
        # rowspan이 없으면 _identify_member_blocks에서 i += 1 경로(line 58)가 실행됨
        from lxml import etree as _etree

        transformer = PageTransformer()

        # 직접 _identify_member_blocks 호출로 커버리지 확보
        row1 = _etree.fromstring(
            '<tr><td><p>04.06</p></td><td><p>Progress</p></td><td><p>Notes</p></td></tr>'
        )
        row2 = _etree.fromstring(
            '<tr><td><p>04.07</p></td><td><p>Progress</p></td><td><p>Notes</p></td></tr>'
        )

        # When: rowspan 없는 행 리스트로 _identify_member_blocks를 호출하면
        blocks = transformer._identify_member_blocks([row1, row2])

        # Then: rowspan 없는 행은 블록으로 추가되지 않고 건너뛴다 (i += 1 경로)
        assert blocks == []

    def test_should_return_empty_list_when_progress_cell_has_no_ul(self):
        # Given: Progress 셀에 <ul>이 없는 HTML
        html_no_ul = (
            '<table><tbody>'
            '<tr><th><p>Name</p></th><th><p>Date</p></th>'
            '<th><p>Progress</p></th><th><p>Notifications</p></th></tr>'
            '<tr><td rowspan="1"><p>@User</p></td>'
            '<td><p>04.06</p></td>'
            '<td><p>No list here</p></td>'
            '<td><p></p></td></tr>'
            '</tbody></table>'
        )
        transformer = PageTransformer()

        # When: transform을 호출하면 (ul 없는 경우 빈 리스트로 처리)
        result = transformer.transform(
            html_no_ul,
            old_dates=["04.06"],
            new_dates=["04.13"],
        )

        # Then: 예외 없이 변환되고 날짜가 바뀐다
        assert "04.13" in result

    def test_should_skip_carryover_when_no_items(self):
        # Given: 금요일 행의 Doing/ToDo에 항목이 없는 HTML (이월할 게 없음)
        html_empty_doing_todo = (
            '<table><tbody>'
            '<tr><th><p>Name</p></th><th><p>Date</p></th>'
            '<th><p>Progress</p></th><th><p>Notifications</p></th></tr>'
            '<tr><td rowspan="1"><p>@User</p></td>'
            '<td><p>04.06</p></td>'
            '<td><ul>'
            '<li><p>Done</p><ul><li><p>Completed Task</p></li></ul></li>'
            '<li><p>Doing</p></li>'
            '<li><p>ToDo</p></li>'
            '</ul></td>'
            '<td><p></p></td></tr>'
            '</tbody></table>'
        )
        transformer = PageTransformer()

        # When: transform을 호출하면 (이월 항목 없음)
        result = transformer.transform(
            html_empty_doing_todo,
            old_dates=["04.06"],
            new_dates=["04.13"],
        )

        # Then: 예외 없이 변환되고 이월 항목이 없다
        assert "Completed Task" not in result
        assert "04.13" in result

    def test_should_skip_insert_when_todo_ul_is_missing_after_reset(self):
        # Given: _insert_carryover_to_todo에서 ul이 None인 경우를 간접 테스트
        # PageTransformer._insert_carryover_to_todo를 직접 호출하여 ul=None 경계 커버
        from lxml import etree as _etree

        transformer = PageTransformer()
        # ul이 없는 progress_cell 생성
        progress_cell = _etree.fromstring('<td><p>Empty</p></td>')
        items = [_etree.fromstring('<li><p>CarryItem</p></li>')]

        # When: _insert_carryover_to_todo를 호출하면 (ul=None이므로 바로 return)
        transformer._insert_carryover_to_todo(progress_cell, items)

        # Then: 예외 없이 종료되고 셀은 변경되지 않는다
        assert progress_cell.find("ul") is None

    def test_should_skip_date_replace_when_p_text_not_in_date_map(self):
        # Given: Date 셀의 <p> 텍스트가 date_map에 없는 경우 (line 66 False 브랜치)
        html = (
            '<table><tbody>'
            '<tr><th><p>Name</p></th><th><p>Date</p></th>'
            '<th><p>Progress</p></th><th><p>Notifications</p></th></tr>'
            '<tr><td rowspan="1"><p>@User</p></td>'
            '<td><p>99.99</p></td>'
            '<td><ul><li><p>Done</p></li><li><p>Doing</p></li><li><p>ToDo</p></li></ul></td>'
            '<td><p></p></td></tr>'
            '</tbody></table>'
        )
        transformer = PageTransformer()

        # When: date_map에 없는 날짜가 포함된 HTML을 변환하면
        result = transformer.transform(html, old_dates=["04.06"], new_dates=["04.13"])

        # Then: 기존 날짜 텍스트가 그대로 유지된다
        assert "99.99" in result

    def test_should_skip_extract_when_li_p_has_no_text(self):
        # Given: Doing/ToDo li의 <p>에 텍스트가 없는 경우 (line 123 False 브랜치)
        from lxml import etree as _etree

        transformer = PageTransformer()
        # <p> 텍스트가 None인 li 포함
        progress_cell = _etree.fromstring(
            '<td><ul>'
            '<li><p></p></li>'
            '<li><p>Doing</p><ul><li><p>Task X</p></li></ul></li>'
            '</ul></td>'
        )

        # When: _extract_doing_todo_items를 호출하면
        items = transformer._extract_doing_todo_items(progress_cell)

        # Then: 텍스트 없는 li는 건너뛰고 Doing 항목만 추출된다
        assert len(items) == 1

    def test_should_skip_insert_when_no_todo_label_in_ul(self):
        # Given: ul에 "ToDo" 라벨이 없는 progress_cell (line 153 False 브랜치)
        from lxml import etree as _etree

        transformer = PageTransformer()
        progress_cell = _etree.fromstring(
            '<td><ul>'
            '<li><p>Done</p></li>'
            '<li><p>Doing</p></li>'
            '</ul></td>'
        )
        items = [_etree.fromstring('<li><p>CarryItem</p></li>')]

        # When: _insert_carryover_to_todo를 호출하면 (ToDo 라벨 없음)
        transformer._insert_carryover_to_todo(progress_cell, items)

        # Then: 예외 없이 종료되고 새 sub_ul이 생성되지 않는다
        # (Done, Doing li에는 ul이 없음)
        ul = progress_cell.find("ul")
        for li in ul.findall("li"):
            assert li.find("ul") is None


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
