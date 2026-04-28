"""CreateWeeklyPageUseCase 테스트"""

from datetime import date
from datetime import date as _date
from unittest.mock import MagicMock
from unittest.mock import MagicMock as _MagicMock

import pytest

from src.application.create_page_use_case import STATUS_LABELS, CreateWeeklyPageUseCase
from src.application.create_page_use_case import CreateWeeklyPageUseCase as _UseCase
from src.domain.models import CreatePageStatus, WeeklyPageConfig
from src.domain.models import CreatePageStatus as _Status, DateRange as _DateRange


@pytest.fixture
def mock_confluence():
    return MagicMock()


@pytest.fixture
def mock_transformer():
    return MagicMock()


@pytest.fixture
def config():
    return WeeklyPageConfig(space_key="MAI", parent_page_id="1477279756")


@pytest.fixture
def use_case(mock_confluence, mock_transformer):
    return CreateWeeklyPageUseCase(
        confluence=mock_confluence, transformer=mock_transformer
    )


class TestCreateWeeklyPageUseCase:
    """주간 페이지 생성 유스케이스 테스트"""

    def test_should_create_page_with_transformed_content(
        self, use_case, mock_confluence, mock_transformer, config
    ):
        # Given: 이전 주 페이지가 존재하고 새 주 페이지는 없는 상황
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123", "title": "2026.04.06 ~ 04.10"},  # 이전 주 존재
            None,  # 새 주 미존재
        ]
        mock_confluence.get_page_content.return_value = "<table>old html</table>"
        mock_transformer.transform.return_value = "<table>new html</table>"
        mock_confluence.create_page.return_value = "https://test.atlassian.net/wiki/pages/456"

        # When: 유스케이스를 실행하면
        result = use_case.execute(config, target_date=date(2026, 4, 13))

        # Then: 페이지가 생성된다
        assert result is True
        mock_confluence.get_page_content.assert_called_once_with("123")
        mock_transformer.transform.assert_called_once()
        mock_confluence.create_page.assert_called_once()

    def test_should_skip_when_page_already_exists(
        self, use_case, mock_confluence, config
    ):
        # Given: 새 주 페이지가 이미 존재하는 상황
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123"},  # 이전 주 존재
            {"id": "456", "url": "https://fake.url/456"},  # 새 주도 존재 (url 키 필요)
        ]

        # When: 유스케이스를 실행하면
        result = use_case.execute(config, target_date=date(2026, 4, 13))

        # Then: True를 반환하고 페이지를 생성하지 않는다 (스킵)
        assert result is True
        mock_confluence.create_page.assert_not_called()

    def test_should_return_false_when_source_page_not_found(
        self, use_case, mock_confluence, config
    ):
        # Given: 이전 주 페이지가 없는 상황
        mock_confluence.get_page_by_title.return_value = None

        # When: 유스케이스를 실행하면
        result = use_case.execute(config, target_date=date(2026, 4, 13))

        # Then: False를 반환한다
        assert result is False
        mock_confluence.create_page.assert_not_called()

    def test_should_pass_correct_dates_to_transformer(
        self, use_case, mock_confluence, mock_transformer, config
    ):
        # Given: 2026-04-13 (월요일) 기준
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123"},  # 이전 주 존재
            None,  # 새 주 미존재
        ]
        mock_confluence.get_page_content.return_value = "<table>html</table>"
        mock_transformer.transform.return_value = "<table>new</table>"
        mock_confluence.create_page.return_value = "url"

        # When: 유스케이스를 실행하면
        use_case.execute(config, target_date=date(2026, 4, 13))

        # Then: 이전 주(04.06~04.10) → 새 주(04.13~04.17) 날짜가 전달된다
        call_args = mock_transformer.transform.call_args
        old_dates = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("old_dates")
        new_dates = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("new_dates")
        assert old_dates == ["04.06", "04.07", "04.08", "04.09", "04.10"]
        assert new_dates == ["04.13", "04.14", "04.15", "04.16", "04.17"]

    def test_should_create_page_with_correct_title_and_parent(
        self, use_case, mock_confluence, mock_transformer, config
    ):
        # Given: 정상 실행 상황
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123"},
            None,
        ]
        mock_confluence.get_page_content.return_value = "<table>html</table>"
        mock_transformer.transform.return_value = "<table>new</table>"
        mock_confluence.create_page.return_value = "url"

        # When: 유스케이스를 실행하면
        use_case.execute(config, target_date=date(2026, 4, 13))

        # Then: 올바른 제목과 parent_id로 생성한다
        call_args = mock_confluence.create_page.call_args
        assert call_args[1]["title"] == "2026.04.13 ~ 04.17"
        assert call_args[1]["parent_id"] == "1477279756"
        assert call_args[1]["space_key"] == "MAI"


class TestStatusLabels:
    """STATUS_LABELS — application 레이어 presentation mapping"""

    def test_created_label_is_korean_with_emoji(self):
        # Given/When/Then
        assert STATUS_LABELS[CreatePageStatus.CREATED] == "✅ 생성 완료"

    def test_already_exists_label_is_korean_with_emoji(self):
        # Given/When/Then
        assert STATUS_LABELS[CreatePageStatus.ALREADY_EXISTS] == "ℹ️ 이미 존재"

    def test_failed_label_is_korean_with_emoji(self):
        # Given/When/Then
        assert STATUS_LABELS[CreatePageStatus.FAILED] == "❌ 생성 실패"

    def test_all_enum_values_have_labels(self):
        # Given: 모든 enum 값
        # When/Then: STATUS_LABELS에 키 누락 없음 (KeyError 방지)
        for status in CreatePageStatus:
            assert status in STATUS_LABELS
            assert isinstance(STATUS_LABELS[status], str)
            assert len(STATUS_LABELS[status]) > 0


@pytest.fixture
def mock_notifier():
    return MagicMock()


@pytest.fixture
def use_case_with_notifier(mock_confluence, mock_transformer, mock_notifier):
    return CreateWeeklyPageUseCase(
        confluence=mock_confluence,
        transformer=mock_transformer,
        notifier=mock_notifier,
    )


class TestBuildTitle:
    """_build_title 헬퍼 — Slack 알림 제목 생성"""

    def test_should_build_title_with_prefix(self, use_case_with_notifier):
        # Given: 2026-04-27(월) ~ 2026-05-01(금) 주간
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When: prefix='BE', status=CREATED로 제목 생성
        title = use_case_with_notifier._build_title(
            "BE", this_week, _Status.CREATED
        )

        # Then: spec §5 형식
        assert title == "[BE][26.04.27 ~ 05.01_WeeklyPage] ✅ 생성 완료"

    def test_should_build_title_without_prefix_when_empty(self, use_case_with_notifier):
        # Given: prefix 빈 문자열
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When
        title = use_case_with_notifier._build_title(
            "", this_week, _Status.ALREADY_EXISTS
        )

        # Then: [BE] 부분 생략
        assert title == "[26.04.27 ~ 05.01_WeeklyPage] ℹ️ 이미 존재"

    def test_should_use_failed_label(self, use_case_with_notifier):
        # Given
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When
        title = use_case_with_notifier._build_title("BE", this_week, _Status.FAILED)

        # Then
        assert title == "[BE][26.04.27 ~ 05.01_WeeklyPage] ❌ 생성 실패"


class TestNotify:
    """_notify — 알림 전송 + 격리"""

    def test_should_skip_when_notifier_is_none(self, mock_confluence, mock_transformer):
        # Given: notifier 없는 use case (default)
        use_case = _UseCase(confluence=mock_confluence, transformer=mock_transformer)
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When: _notify 호출
        # Then: 예외 발생 없이 조용히 return
        use_case._notify(_Status.CREATED, "BE", this_week, "url")
        # 추가 검증: _already_notified가 False 유지
        assert use_case._already_notified is False

    def test_should_send_notification_when_notifier_set(
        self, use_case_with_notifier, mock_notifier
    ):
        # Given: notifier 주입된 use case
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When: _notify 호출
        use_case_with_notifier._notify(_Status.CREATED, "BE", this_week, "https://...")

        # Then: notifier.send 호출됨, _already_notified=True 설정
        mock_notifier.send.assert_called_once()
        call_args = mock_notifier.send.call_args
        assert call_args[0][0] == "[BE][26.04.27 ~ 05.01_WeeklyPage] ✅ 생성 완료"
        assert call_args[0][1] == "https://..."
        assert use_case_with_notifier._already_notified is True

    def test_should_swallow_notifier_exception(
        self, use_case_with_notifier, mock_notifier
    ):
        # Given: notifier.send가 예외 발생
        mock_notifier.send.side_effect = RuntimeError("Slack down")
        this_week = _DateRange(start=_date(2026, 4, 27), end=_date(2026, 5, 1))

        # When: _notify 호출 — 예외 전파 안 됨
        use_case_with_notifier._notify(
            _Status.FAILED, "BE", this_week, "error body"
        )

        # Then: _already_notified는 False 유지 (실패한 알림은 latch 트리거 안 함)
        assert use_case_with_notifier._already_notified is False


class TestExecuteNotificationIntegration:
    """execute()에 알림 호출 통합 — 케이스별 알림, 래치, 예외 격리"""

    def test_should_send_created_notification_on_success(
        self, use_case_with_notifier, mock_confluence, mock_transformer, mock_notifier, config
    ):
        # Given: 정상 생성 경로
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123", "title": "2026.04.20 ~ 04.24"},
            None,
        ]
        mock_confluence.get_page_content.return_value = "<table>old</table>"
        mock_transformer.transform.return_value = "<table>new</table>"
        mock_confluence.create_page.return_value = "https://wiki/spaces/MAI/pages/456/title"

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: True + CREATED 알림 1회
        assert result is True
        assert mock_notifier.send.call_count == 1
        call_args = mock_notifier.send.call_args
        assert "✅ 생성 완료" in call_args[0][0]
        assert call_args[0][1] == "https://wiki/spaces/MAI/pages/456/title"

    def test_should_send_already_exists_notification_with_url_from_dict(
        self, use_case_with_notifier, mock_confluence, mock_notifier, config
    ):
        # Given: 새 주 페이지가 이미 존재 — get_page_by_title이 'url' 키 포함
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123", "url": "https://wiki/spaces/MAI/pages/123/old"},
            {"id": "456", "url": "https://wiki/spaces/MAI/pages/456/new"},
        ]

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: True (스킵) + ALREADY_EXISTS 알림 with existing_page['url']
        assert result is True
        assert mock_notifier.send.call_count == 1
        call_args = mock_notifier.send.call_args
        assert "ℹ️ 이미 존재" in call_args[0][0]
        assert call_args[0][1] == "https://wiki/spaces/MAI/pages/456/new"

    def test_should_send_failed_notification_when_source_not_found(
        self, use_case_with_notifier, mock_confluence, mock_notifier, config
    ):
        # Given: 이전 주 페이지 없음
        mock_confluence.get_page_by_title.return_value = None

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: False + FAILED 알림 (사유 포함)
        assert result is False
        assert mock_notifier.send.call_count == 1
        call_args = mock_notifier.send.call_args
        assert "❌ 생성 실패" in call_args[0][0]
        assert "이전 주 페이지를 찾을 수 없습니다" in call_args[0][1]

    def test_should_send_failed_notification_on_unexpected_exception(
        self, use_case_with_notifier, mock_confluence, mock_notifier, config
    ):
        # Given: confluence 호출이 예외 발생
        mock_confluence.get_page_by_title.side_effect = RuntimeError("Network timeout")

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: False + FAILED 알림 (예외 메시지 포함)
        assert result is False
        assert mock_notifier.send.call_count == 1
        call_args = mock_notifier.send.call_args
        assert "❌ 생성 실패" in call_args[0][0]
        assert "Unexpected error" in call_args[0][1]
        assert "Network timeout" in call_args[0][1]

    def test_should_not_double_notify_when_post_success_code_raises(
        self, use_case_with_notifier, mock_confluence, mock_transformer, mock_notifier, config, monkeypatch
    ):
        # Given: 정상 생성 후 추가 코드가 raise하는 시나리오
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123"},
            None,
        ]
        mock_confluence.get_page_content.return_value = "<table>old</table>"
        mock_transformer.transform.return_value = "<table>new</table>"
        mock_confluence.create_page.return_value = "https://wiki/url"

        # _notify를 monkeypatch하여 CREATED 후에 raise
        original_notify = use_case_with_notifier._notify

        def notify_then_raise(status, prefix, week, body):
            original_notify(status, prefix, week, body)
            if status == _Status.CREATED:
                raise RuntimeError("Simulated post-success failure")

        monkeypatch.setattr(use_case_with_notifier, "_notify", notify_then_raise)

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: outer except는 _already_notified=True를 보고 추가 알림 발송 안 함
        # → notifier.send 호출은 정확히 1회 (성공 알림만)
        assert result is False  # outer except가 False 반환
        assert mock_notifier.send.call_count == 1  # CREATED만, FAILED 추가 발송 안 됨

    def test_should_skip_notification_when_pre_try_fails(
        self, use_case_with_notifier, mock_notifier, config, monkeypatch
    ):
        # Given: calculate_this_week_range 자체가 raise (this_week=None 가드 검증)
        from src.application import create_page_use_case as cpuc_mod

        def boom(today):
            raise RuntimeError("date calc failed")

        monkeypatch.setattr(cpuc_mod, "calculate_this_week_range", boom)

        # When
        result = use_case_with_notifier.execute(
            config, target_date=date(2026, 4, 27), notification_prefix="BE"
        )

        # Then: False, 알림 호출 안 됨 (this_week is None 가드)
        assert result is False
        assert mock_notifier.send.call_count == 0


class TestExecuteWithoutNotifier:
    """notifier=None 일 때 실행 — 알림 스킵, 페이지 동작 정상"""

    def test_should_run_normally_when_notifier_is_none(
        self, use_case, mock_confluence, mock_transformer, config
    ):
        # Given: notifier 없음 (use_case 픽스처 사용)
        mock_confluence.get_page_by_title.side_effect = [
            {"id": "123"},
            None,
        ]
        mock_confluence.get_page_content.return_value = "<table>old</table>"
        mock_transformer.transform.return_value = "<table>new</table>"
        mock_confluence.create_page.return_value = "url"

        # When
        result = use_case.execute(config, target_date=date(2026, 4, 27))

        # Then: 페이지 생성 정상, 어떤 알림도 시도되지 않음
        assert result is True
        mock_confluence.create_page.assert_called_once()
