"""
Tests for composite daily-check followup handling (TODO-1~6)

Covers:
- extract_previous_results with composite (context_for_followup) data
- build_conversation_context with composite results
- build_sql_history with daily_check_template mode
- _find_daily_check_context utility
- _format_daily_check_metrics utility
- Phase 0 non-error followup date injection (_is_error_related_query, _has_date_in_message)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.chat import (
    ChatMessageItem,
    build_sql_history,
    _find_daily_check_context,
    _format_daily_check_metrics,
    _is_error_related_query,
    _has_date_in_message,
)
from app.services.conversation_context import (
    extract_previous_results,
    build_conversation_context,
)


# ============================================
# Fixtures
# ============================================

def _daily_check_query_result() -> dict:
    """Fixture: daily check queryResult with context_for_followup."""
    return {
        "requestId": "test-123",
        "status": "success",
        "data": {"rows": [], "aggregations": {}},
        "metadata": {
            "dataSource": "daily_check_template",
            "targetDate": "2026-02-25",
            "queryCount": 4,
        },
        "context_for_followup": {
            "type": "daily_check_result",
            "targetDate": "2026-02-25",
            "metrics": {
                "todayCount": 10,
                "todayAmount": 389700,
                "statusDistribution": [
                    {"status": "DONE", "count": 7},
                    {"status": "IN_PROGRESS", "count": 1},
                    {"status": "CANCELED", "count": 1},
                    {"status": "PARTIAL_CANCELED", "count": 1},
                ],
                "refundCount": 2,
                "errorCount": 0,
            },
            "availableFilters": [
                {
                    "field": "status",
                    "options": [
                        "DONE",
                        "CANCELED",
                        "IN_PROGRESS",
                        "PARTIAL_CANCELED",
                    ],
                },
                {"field": "created_at", "value": "2026-02-25"},
            ],
        },
    }


def _daily_check_query_plan() -> dict:
    """Fixture: daily check queryPlan."""
    return {
        "mode": "daily_check_template",
        "targetDate": "2026-02-25",
        "requestId": "test-123",
    }


def _make_assistant_msg(
    content: str = "일일점검 결과입니다.",
    query_result: dict = None,
    query_plan: dict = None,
    render_spec: dict = None,
) -> ChatMessageItem:
    """Helper to create an assistant ChatMessageItem."""
    return ChatMessageItem(
        id="msg-assistant-1",
        role="assistant",
        content=content,
        timestamp="2026-02-25T12:00:00Z",
        queryResult=query_result,
        queryPlan=query_plan,
        renderSpec=render_spec,
    )


def _make_user_msg(content: str = "오늘 결제 현황 알려줘") -> ChatMessageItem:
    """Helper to create a user ChatMessageItem."""
    return ChatMessageItem(
        id="msg-user-1",
        role="user",
        content=content,
        timestamp="2026-02-25T11:59:00Z",
    )


# ============================================
# Test 1: extract_previous_results with daily check composite
# ============================================

class TestExtractPreviousResultsComposite:
    """extract_previous_results should parse context_for_followup from composite result."""

    def test_extract_previous_results_with_daily_check_composite(self):
        """composite 결과(rows 비어있고 context_for_followup 있는 경우)에서
        entity가 DailyCheck으로 변환되고 metrics에서 count/amount가 추출되어야 한다."""
        # Arrange
        history = [
            _make_user_msg("오늘 결제 현황 알려줘"),
            _make_assistant_msg(
                content="일일점검 결과입니다.",
                query_result=_daily_check_query_result(),
                query_plan=_daily_check_query_plan(),
            ),
        ]

        # Act
        results = extract_previous_results(history)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result["entity"] == "DailyCheck"
        assert result["count"] == 10
        assert result["total_amount"] == 389700.0
        assert "context_for_followup" in result
        assert result["context_for_followup"]["type"] == "daily_check_result"
        assert result["context_for_followup"]["targetDate"] == "2026-02-25"


# ============================================
# Test 2: extract_previous_results with empty rows and context_for_followup
# ============================================

class TestExtractPreviousResultsEmptyRowsWithContext:
    """extract_previous_results should include result even when count is 0
    if context_for_followup exists."""

    def test_extract_previous_results_with_empty_rows_and_context(self):
        """rows가 비어있고 todayCount가 0이어도 context_for_followup이 있으면
        결과에 포함되어야 한다."""
        # Arrange
        qr = _daily_check_query_result()
        # todayCount를 0으로 설정
        qr["context_for_followup"]["metrics"]["todayCount"] = 0
        qr["context_for_followup"]["metrics"]["todayAmount"] = 0

        history = [
            _make_user_msg("오늘 결제 현황 알려줘"),
            _make_assistant_msg(
                content="일일점검 결과입니다.",
                query_result=qr,
                query_plan=_daily_check_query_plan(),
            ),
        ]

        # Act
        results = extract_previous_results(history)

        # Assert - context_for_followup이 있으므로 count 0이어도 추가됨
        assert len(results) == 1
        result = results[0]
        assert result["entity"] == "DailyCheck"
        assert result["count"] == 0
        assert result["total_amount"] == 0.0
        assert "context_for_followup" in result


# ============================================
# Test 3: build_conversation_context with composite
# ============================================

class TestBuildConversationContextComposite:
    """build_conversation_context should handle composite daily-check results."""

    def test_build_conversation_context_with_composite(self):
        """composite daily-check 결과가 있는 대화 이력에서 컨텍스트를 빌드하면
        DailyCheck 엔티티로 표시되어야 한다."""
        # Arrange
        history = [
            _make_user_msg("오늘 결제 현황 알려줘"),
            _make_assistant_msg(
                content="일일점검 결과입니다.",
                query_result=_daily_check_query_result(),
                query_plan=_daily_check_query_plan(),
            ),
        ]

        # Act
        context = build_conversation_context(history)

        # Assert
        assert "이전 대화 컨텍스트" in context
        assert "DailyCheck" in context
        assert "10" in context  # todayCount
        assert "조회 결과 현황" in context


# ============================================
# Test 4: build_sql_history with daily check
# ============================================

class TestBuildSqlHistoryDailyCheck:
    """build_sql_history should convert daily_check_template results into
    structured SQL history with dailyCheckContext."""

    def test_build_sql_history_with_daily_check(self):
        """daily_check_template 모드의 assistant 메시지가 SQL 히스토리로 변환될 때
        dailyCheckContext에 targetDate, metrics, availableFilters가 포함되어야 한다."""
        # Arrange
        history = [
            _make_user_msg("오늘 결제 현황 알려줘"),
            _make_assistant_msg(
                content="일일점검 결과입니다.",
                query_result=_daily_check_query_result(),
                query_plan=_daily_check_query_plan(),
            ),
        ]

        # Act
        sql_history = build_sql_history(history)

        # Assert
        assert len(sql_history) == 2

        # user 메시지
        assert sql_history[0]["role"] == "user"
        assert sql_history[0]["content"] == "오늘 결제 현황 알려줘"

        # assistant 메시지 - dailyCheckContext 포함
        assistant_entry = sql_history[1]
        assert assistant_entry["role"] == "assistant"
        assert "dailyCheckContext" in assistant_entry

        ctx = assistant_entry["dailyCheckContext"]
        assert ctx["targetDate"] == "2026-02-25"
        assert "metrics" in ctx
        assert ctx["metrics"]["todayCount"] == 10
        assert ctx["metrics"]["todayAmount"] == 389700
        assert "availableFilters" in ctx
        assert len(ctx["availableFilters"]) == 2

        # content에 일일점검 요약이 포함되어야 함
        assert "일일점검" in assistant_entry["content"]

        # rowCount는 queryCount 값
        assert assistant_entry["rowCount"] == 4


# ============================================
# Test 5: _find_daily_check_context returns full metrics
# ============================================

class TestFindDailyCheckContext:
    """_find_daily_check_context should return complete metrics and availableFilters."""

    def test_find_daily_check_context_returns_full_metrics(self):
        """대화 이력에서 일일점검 컨텍스트를 찾으면 targetDate, metrics,
        availableFilters가 모두 반환되어야 한다."""
        # Arrange
        history = [
            _make_user_msg("오늘 결제 현황 알려줘"),
            _make_assistant_msg(
                content="일일점검 결과입니다.",
                query_result=_daily_check_query_result(),
                query_plan=_daily_check_query_plan(),
            ),
        ]

        # Act
        result = _find_daily_check_context(history)

        # Assert
        assert result is not None
        assert result["targetDate"] == "2026-02-25"

        metrics = result["metrics"]
        assert metrics["todayCount"] == 10
        assert metrics["todayAmount"] == 389700
        assert metrics["refundCount"] == 2
        assert metrics["errorCount"] == 0
        assert len(metrics["statusDistribution"]) == 4

        available_filters = result["availableFilters"]
        assert len(available_filters) == 2
        status_filter = next(f for f in available_filters if f["field"] == "status")
        assert "DONE" in status_filter["options"]
        assert "CANCELED" in status_filter["options"]

    def test_find_daily_check_context_returns_none_without_daily_check(self):
        """일일점검 결과가 없으면 None을 반환해야 한다."""
        # Arrange
        history = [
            _make_user_msg("결제 목록 보여줘"),
            _make_assistant_msg(
                content="결제 목록입니다.",
                query_result={
                    "requestId": "test-456",
                    "status": "success",
                    "data": {"rows": [{"id": 1}]},
                    "metadata": {},
                },
                query_plan={"entity": "payments", "filters": []},
            ),
        ]

        # Act
        result = _find_daily_check_context(history)

        # Assert
        assert result is None

    def test_find_daily_check_context_via_queryplan_mode(self):
        """queryPlan.mode가 daily_check_template이면 컨텍스트를 찾아야 한다."""
        # Arrange
        history = [
            _make_user_msg("오늘 결제 현황 알려줘"),
            _make_assistant_msg(
                content="일일점검 결과입니다.",
                query_result={
                    "requestId": "test-789",
                    "status": "success",
                    "data": {"rows": []},
                    "metadata": {"dataSource": "daily_check_template"},
                    "context_for_followup": {
                        "type": "daily_check_result",
                        "targetDate": "2026-02-20",
                        "metrics": {"todayCount": 5},
                        "availableFilters": [],
                    },
                },
                query_plan={
                    "mode": "daily_check_template",
                    "targetDate": "2026-02-20",
                },
            ),
        ]

        # Act
        result = _find_daily_check_context(history)

        # Assert
        assert result is not None
        assert result["targetDate"] == "2026-02-20"


# ============================================
# Test 6: _format_daily_check_metrics
# ============================================

class TestFormatDailyCheckMetrics:
    """_format_daily_check_metrics should format metrics dict to readable text."""

    def test_format_daily_check_metrics(self):
        """정상적인 metrics dict가 포맷팅되면 각 항목이 포함되어야 한다."""
        # Arrange
        metrics = {
            "todayCount": 10,
            "todayAmount": 389700,
            "statusDistribution": [
                {"status": "DONE", "count": 7},
                {"status": "IN_PROGRESS", "count": 1},
                {"status": "CANCELED", "count": 1},
                {"status": "PARTIAL_CANCELED", "count": 1},
            ],
            "refundCount": 2,
            "errorCount": 0,
        }

        # Act
        result = _format_daily_check_metrics(metrics)

        # Assert
        assert "[일일점검 컨텍스트]" in result
        assert "10건" in result
        assert "389,700원" in result
        assert "환불: 2건" in result
        assert "오류/실패: 0건" in result
        assert "DONE 7건" in result
        assert "IN_PROGRESS 1건" in result

    def test_format_daily_check_metrics_empty_dict(self):
        """빈 dict이면 빈 문자열을 반환해야 한다."""
        # Arrange / Act
        result = _format_daily_check_metrics({})

        # Assert
        assert result == ""

    def test_format_daily_check_metrics_partial(self):
        """todayCount만 있어도 포맷팅되어야 한다."""
        # Arrange
        metrics = {"todayCount": 42}

        # Act
        result = _format_daily_check_metrics(metrics)

        # Assert
        assert "42건" in result
        assert "[일일점검 컨텍스트]" in result


# ============================================
# Test 7: Phase 0 non-error followup date injection
# ============================================

class TestPhase0NonErrorFollowupDateInjection:
    """Non-error followup questions should also get date injection in Phase 0.
    This tests the helper functions _is_error_related_query and _has_date_in_message."""

    def test_phase0_non_error_followup_date_injection(self):
        """비오류 꼬리 질문(예: 'DONE 상태인 거래 보여줘')에 날짜가 없을 때
        _is_error_related_query는 False를 반환하고,
        _has_date_in_message는 False를 반환하여
        Phase 0에서 날짜 자동 주입 대상이 되어야 한다."""
        # Arrange
        non_error_message = "DONE 상태인 거래 보여줘"

        # Act
        is_error = _is_error_related_query(non_error_message)
        has_date = _has_date_in_message(non_error_message)

        # Assert
        # 비오류 질문이므로 is_error는 False
        assert is_error is False
        # 날짜가 없으므로 has_date는 False
        assert has_date is False
        # 따라서 Phase 0에서 date injection 대상임
        # (Phase 0 로직: daily_check_context 있고 + _has_date_in_message() False면 주입)

    def test_error_related_query_detected(self):
        """오류 관련 질문은 _is_error_related_query가 True를 반환해야 한다."""
        # Arrange / Act / Assert
        assert _is_error_related_query("오류 건수 보여줘") is True
        assert _is_error_related_query("실패한 결제 목록") is True
        assert _is_error_related_query("에러 코드별 집계") is True
        assert _is_error_related_query("failure_code 분석") is True

    def test_has_date_in_message_detected(self):
        """날짜가 포함된 메시지는 _has_date_in_message가 True를 반환해야 한다."""
        # Arrange / Act / Assert
        assert _has_date_in_message("2026-02-25 결제 현황") is True
        assert _has_date_in_message("오늘 결제 현황") is True
        assert _has_date_in_message("어제 결제 건수") is True
        assert _has_date_in_message("2026년 2월 25일 거래") is True
        assert _has_date_in_message("1월 24일 결제") is True

    def test_has_date_in_message_not_detected(self):
        """날짜가 없는 메시지는 _has_date_in_message가 False를 반환해야 한다."""
        # Arrange / Act / Assert
        assert _has_date_in_message("DONE 상태인 거래 보여줘") is False
        assert _has_date_in_message("환불 건수 알려줘") is False
        assert _has_date_in_message("결제 목록 보여줘") is False
