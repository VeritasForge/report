"""CreatePageStatus Enum 테스트 — semantic 값 검증, presentation 문자열 부재 검증"""
from src.domain.models import CreatePageStatus


class TestCreatePageStatus:
    """create_page 유스케이스 결과 enum"""

    def test_created_value_is_semantic_identifier(self):
        # Given/When/Then: enum value는 semantic identifier (Korean/emoji 아님)
        assert CreatePageStatus.CREATED.value == "created"

    def test_already_exists_value_is_semantic_identifier(self):
        # Given/When/Then
        assert CreatePageStatus.ALREADY_EXISTS.value == "already_exists"

    def test_failed_value_is_semantic_identifier(self):
        # Given/When/Then
        assert CreatePageStatus.FAILED.value == "failed"

    def test_should_be_str_enum(self):
        # Given/When: str mixin enum이어야 dict key/log 사용 시 안정적
        # Then
        assert isinstance(CreatePageStatus.CREATED, str)
        assert CreatePageStatus.CREATED == "created"

    def test_value_format_is_lockable(self):
        # Given: f-string 포맷 시 .value 사용
        # When/Then: f"{status.value}"가 'created' 반환 (Python 3.11 StrEnum 거동 lock-in)
        status = CreatePageStatus.CREATED
        assert f"{status.value}" == "created"
