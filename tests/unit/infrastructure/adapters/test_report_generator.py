"""보고서 생성기 테스트"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.domain.models import Report, ReportConfig
from src.infrastructure.adapters.report_generator import ReportGenerator


class TestReportGenerator:
    """ReportGenerator 오케스트레이터 테스트"""

    @pytest.fixture
    def mock_cli_executor(self):
        """Mock CLI 실행기"""
        return MagicMock()

    @pytest.fixture
    def generator(self, mock_cli_executor):
        """테스트용 ReportGenerator 인스턴스"""
        return ReportGenerator(cli_executor=mock_cli_executor)

    def test_should_generate_report_successfully(
        self, generator, mock_cli_executor, sample_report_config
    ):
        # Given: CLI가 성공적으로 실행되는 상황
        mock_cli_executor.execute.return_value = "# Report\n- Task 1"

        # When: generate를 호출하면
        result = generator.generate(sample_report_config)

        # Then: Report 객체를 반환한다
        assert result is not None
        assert isinstance(result, Report)
        assert result.main_content == "# Report\n- Task 1"

    def test_should_return_none_when_cli_fails(
        self, generator, mock_cli_executor, sample_report_config
    ):
        # Given: CLI가 실패하는 상황
        mock_cli_executor.execute.return_value = None

        # When: generate를 호출하면
        result = generator.generate(sample_report_config)

        # Then: None을 반환한다
        assert result is None

    def test_should_call_cli_with_correct_arguments(
        self, generator, mock_cli_executor, sample_report_config
    ):
        # Given: 설정이 주어진 상황
        mock_cli_executor.execute.return_value = "Report"

        # When: generate를 호출하면
        generator.generate(sample_report_config)

        # Then: 올바른 인자로 CLI가 호출된다
        mock_cli_executor.execute.assert_called_once_with(
            sample_report_config.space_key, sample_report_config.mention_users, sample_report_config.report_date
        )

    def test_should_call_cli_without_mention_users(
        self, generator, mock_cli_executor, sample_report_config_minimal
    ):
        # Given: mention_users가 없는 설정
        mock_cli_executor.execute.return_value = "Report"

        # When: generate를 호출하면
        generator.generate(sample_report_config_minimal)

        # Then: 빈 mention_users로 CLI가 호출된다
        mock_cli_executor.execute.assert_called_once_with(
            sample_report_config_minimal.space_key, "", None
        )

    def test_should_pass_report_date_to_cli(self, generator, mock_cli_executor):
        # Given: report_date가 지정된 설정
        mock_cli_executor.execute.return_value = "Report"
        config = ReportConfig(
            space_key="MAI", team_name="", team_prefix="BE",
            mention_users="@홍길동", report_date=date(2026, 4, 6),
        )

        # When: generate를 호출하면
        generator.generate(config)

        # Then: report_date가 CLI에 전달된다
        mock_cli_executor.execute.assert_called_once_with(
            "MAI", "@홍길동", date(2026, 4, 6)
        )

    def test_should_strip_cli_output(self, generator, mock_cli_executor):
        # Given: CLI 출력에 공백이 있는 상황
        mock_cli_executor.execute.return_value = "  Report content  \n"
        config = ReportConfig(
            space_key="MAI", team_name="", team_prefix="", mention_users=""
        )

        # When: generate를 호출하면
        result = generator.generate(config)

        # Then: 공백이 제거된 내용이 반환된다
        assert result is not None
        assert result.main_content == "Report content"


class TestParseOutput:
    """_parse_output 메서드 테스트"""

    @pytest.fixture
    def generator(self):
        """테스트용 ReportGenerator 인스턴스"""
        return ReportGenerator(cli_executor=MagicMock())

    def test_should_parse_simple_output(self, generator):
        # Given: 간단한 출력이 주어졌을 때
        output = "# Report\n- Task 1\n- Task 2"

        # When: _parse_output을 호출하면
        result = generator._parse_output(output)

        # Then: Report 객체를 반환한다
        assert result.main_content == output

    def test_should_strip_whitespace(self, generator):
        # Given: 공백이 포함된 출력이 주어졌을 때
        output = "  Report content  \n\n"

        # When: _parse_output을 호출하면
        result = generator._parse_output(output)

        # Then: 공백이 제거된 내용이 반환된다
        assert result.main_content == "Report content"

    def test_should_return_report_with_none_thread_tickets(self, generator):
        # Given: 출력이 주어졌을 때
        output = "Report content"

        # When: _parse_output을 호출하면
        result = generator._parse_output(output)

        # Then: thread_tickets는 None이다
        assert result.thread_tickets is None

    def test_should_extract_report_from_output_with_intermediate_text(self, generator):
        # Given: 중간 분석 텍스트가 포함된 출력
        output = (
            "JIRA 티켓 정보를 확인했습니다.\n\n"
            "**04.09 데이터 정리:**\n| 팀원 | Done |\n\n"
            "📊 일정 요약\n\n• ✅ 작업 완료 - 김철수"
        )

        # When: _parse_output을 호출하면
        result = generator._parse_output(output)

        # Then: 리포트 시작점부터만 추출된다
        assert result.main_content == "📊 일정 요약\n\n• ✅ 작업 완료 - 김철수"

    def test_should_extract_report_with_bold_marker(self, generator):
        # Given: Bold 마커(*📊 일정 요약*)가 포함된 출력
        output = (
            "분석하겠습니다.\n\n"
            "*📊 일정 요약*\n\n• ✅ 작업 완료"
        )

        # When: _parse_output을 호출하면
        result = generator._parse_output(output)

        # Then: Bold 마커부터 추출된다
        assert result.main_content == "*📊 일정 요약*\n\n• ✅ 작업 완료"

    def test_should_extract_report_with_slack_emoji_marker(self, generator):
        # Given: 슬랙 이모지 형식(:bar_chart:)이 포함된 출력
        output = (
            "중간 분석 내용\n\n"
            ":bar_chart: 일정 요약\n\n• ✅ 작업 완료"
        )

        # When: _parse_output을 호출하면
        result = generator._parse_output(output)

        # Then: 슬랙 이모지 마커부터 추출된다
        assert result.main_content == ":bar_chart: 일정 요약\n\n• ✅ 작업 완료"

    def test_should_return_full_output_when_no_marker_found(self, generator):
        # Given: 마커가 없는 출력 (이미 깔끔한 리포트)
        output = "깔끔한 리포트 내용"

        # When: _parse_output을 호출하면
        result = generator._parse_output(output)

        # Then: 전체 출력이 그대로 반환된다
        assert result.main_content == "깔끔한 리포트 내용"
