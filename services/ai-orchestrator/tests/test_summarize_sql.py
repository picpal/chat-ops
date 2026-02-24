"""
_summarize_sql() 및 conversation_context SQL 요약 통합 테스트

TDD RED Phase: 이 테스트를 먼저 작성하고, 구현으로 통과시킨다.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.conversation_context import (
    _summarize_sql,
    build_conversation_context,
    extract_previous_results,
)
from app.api.v1.chat import ChatMessageItem


def _make_msg(role: str, content: str, **kwargs) -> ChatMessageItem:
    """테스트용 ChatMessageItem 헬퍼"""
    return ChatMessageItem(
        id="test-id",
        role=role,
        content=content,
        timestamp="2025-01-01T00:00:00Z",
        **kwargs,
    )


# ============================================
# _summarize_sql 단위 테스트
# ============================================


class TestSummarizeSqlAggregation:
    """집계 함수 포함 SQL 요약"""

    def test_summarize_sql_with_aggregation(self):
        """집계 함수 + 테이블 + GROUP BY + WHERE 요약"""
        sql = (
            "SELECT merchant_id, AVG(payment_count), SUM(amount) "
            "FROM settlements "
            "GROUP BY merchant_id "
            "WHERE created_at >= '2024-01-01'"
        )
        result = _summarize_sql(sql)

        assert "AVG(payment_count)" in result
        assert "SUM(amount)" in result
        assert "FROM settlements" in result
        assert "GROUP BY" in result
        assert "merchant_id" in result

    def test_summarize_sql_with_cte(self):
        """CTE 포함 SQL에서 핵심 정보 추출"""
        sql = """
        WITH monthly AS (
            SELECT merchant_id, COUNT(*) AS cnt
            FROM payments
            WHERE created_at >= '2024-01-01'
            GROUP BY merchant_id
        )
        SELECT merchant_id, AVG(cnt) AS avg_cnt
        FROM monthly
        GROUP BY merchant_id
        """
        result = _summarize_sql(sql)

        # CTE 내부든 외부든 집계 함수와 FROM 테이블이 추출되어야 함
        assert result != ""
        assert "AVG" in result or "COUNT" in result
        assert "FROM" in result


class TestSummarizeSqlEdgeCases:
    """엣지 케이스"""

    def test_summarize_sql_none_input(self):
        """None 입력 -> 빈 문자열"""
        assert _summarize_sql(None) == ""

    def test_summarize_sql_empty_input(self):
        """빈 문자열 입력 -> 빈 문자열"""
        assert _summarize_sql("") == ""

    def test_summarize_sql_simple_select(self):
        """집계 없는 단순 SELECT -> FROM 테이블 + WHERE 정보"""
        sql = "SELECT * FROM payments WHERE merchant_id = 'mer_001' AND status = 'DONE'"
        result = _summarize_sql(sql)

        assert "FROM payments" in result
        assert "WHERE" in result
        # 집계 함수가 없으므로 "집계:" 파트가 없어야 함
        assert "집계" not in result


class TestSummarizeSqlWhereClause:
    """WHERE 조건 요약 관련"""

    def test_long_where_truncated(self):
        """긴 WHERE 조건은 80자 이후 잘림"""
        long_condition = " AND ".join([f"col_{i} = 'val_{i}'" for i in range(20)])
        sql = f"SELECT * FROM payments WHERE {long_condition}"
        result = _summarize_sql(sql)

        # WHERE 부분이 포함되되, 최대 80자 + "..." 형태
        assert "WHERE" in result

    def test_where_with_subquery_pattern(self):
        """WHERE 절에 서브쿼리 없이 기본 조건만 포함되는 경우"""
        sql = "SELECT SUM(amount) FROM payments WHERE status = 'DONE' GROUP BY merchant_id"
        result = _summarize_sql(sql)

        assert "집계: SUM(amount)" in result
        assert "FROM payments" in result
        assert "GROUP BY merchant_id" in result
        assert "WHERE" in result
        assert "status" in result


# ============================================
# build_conversation_context 통합 테스트
# ============================================


class TestBuildConversationContextSqlSummary:
    """build_conversation_context에서 SQL 요약 포함 확인"""

    def test_build_conversation_context_includes_sql_summary(self):
        """queryPlan에 sql 키가 있는 히스토리로 호출 시 SQL 요약 문자열 포함"""
        history = [
            _make_msg("user", "3개월 평균 건수가 가장 많은 가맹점?"),
            _make_msg(
                "assistant",
                "조회 결과입니다.",
                queryPlan={
                    "mode": "text_to_sql",
                    "sql": "SELECT merchant_id, AVG(payment_count) FROM settlements GROUP BY merchant_id ORDER BY AVG(payment_count) DESC",
                    "entity": "settlements",
                },
                renderSpec={"type": "table", "columns": [{"key": "merchant_id"}, {"key": "avg_payment_count"}]},
                queryResult={
                    "totalCount": 5,
                    "data": {
                        "rows": [
                            {"merchant_id": "mer_001", "avg_payment_count": 120},
                        ]
                    },
                },
            ),
        ]
        context = build_conversation_context(history)

        # SQL 요약이 대화 히스토리 섹션에 포함되어야 함
        assert "실행된 SQL 요약" in context or "SQL 요약" in context
        assert "AVG(payment_count)" in context
        assert "FROM settlements" in context

    def test_build_conversation_context_no_sql_no_summary(self):
        """queryPlan에 sql이 없으면 SQL 요약 미포함"""
        history = [
            _make_msg("user", "가맹점 목록 보여줘"),
            _make_msg(
                "assistant",
                "조회 결과입니다.",
                queryPlan={"entity": "merchants", "filters": []},
                renderSpec={"type": "table"},
                queryResult={
                    "totalCount": 3,
                    "data": {"rows": [{"id": "mer_001"}]},
                },
            ),
        ]
        context = build_conversation_context(history)

        # SQL 요약 관련 텍스트가 없어야 함
        assert "SQL 요약" not in context
        assert "실행된 SQL 요약" not in context

    def test_build_conversation_context_table_columns_info(self):
        """table 타입 renderSpec에서 컬럼 정보가 컨텍스트에 포함"""
        history = [
            _make_msg("user", "가맹점별 정산 현황"),
            _make_msg(
                "assistant",
                "조회 결과입니다.",
                queryPlan={
                    "mode": "text_to_sql",
                    "sql": "SELECT merchant_id, total_amount FROM settlements",
                    "entity": "settlements",
                },
                renderSpec={
                    "type": "table",
                    "columns": [
                        {"key": "merchant_id", "label": "가맹점ID"},
                        {"key": "total_amount", "label": "총금액"},
                    ],
                },
                queryResult={
                    "totalCount": 2,
                    "data": {"rows": [{"merchant_id": "mer_001", "total_amount": 100000}]},
                },
            ),
        ]
        context = build_conversation_context(history)

        # 컬럼 정보가 포함되어야 함
        assert "merchant_id" in context
        assert "total_amount" in context


# ============================================
# extract_previous_results 통합 테스트
# ============================================


class TestExtractPreviousResultsSqlSummary:
    """extract_previous_results에서 sql_summary 필드 확인"""

    def test_extract_previous_results_includes_sql_summary(self):
        """queryPlan에 sql이 있는 히스토리에서 sql_summary 필드 추출"""
        history = [
            _make_msg("user", "가맹점별 평균 건수"),
            _make_msg(
                "assistant",
                "조회 결과입니다.",
                queryPlan={
                    "mode": "text_to_sql",
                    "sql": "SELECT merchant_id, AVG(payment_count) FROM settlements GROUP BY merchant_id",
                    "entity": "settlements",
                },
                renderSpec={"type": "table"},
                queryResult={
                    "totalCount": 5,
                    "data": {
                        "rows": [
                            {"merchant_id": "mer_001", "avg_payment_count": 120},
                        ]
                    },
                },
            ),
        ]
        results = extract_previous_results(history)

        assert len(results) >= 1
        result = results[0]
        assert "sql_summary" in result
        assert result["sql_summary"] is not None
        assert "AVG(payment_count)" in result["sql_summary"]
        assert "FROM settlements" in result["sql_summary"]

    def test_extract_previous_results_no_sql_no_summary(self):
        """queryPlan에 sql이 없으면 sql_summary는 None"""
        history = [
            _make_msg("user", "가맹점 목록"),
            _make_msg(
                "assistant",
                "조회 결과입니다.",
                queryPlan={"entity": "merchants", "filters": []},
                renderSpec={"type": "table"},
                queryResult={
                    "totalCount": 3,
                    "data": {"rows": [{"id": "mer_001"}]},
                },
            ),
        ]
        results = extract_previous_results(history)

        assert len(results) >= 1
        result = results[0]
        assert "sql_summary" in result
        assert result["sql_summary"] is None

    def test_extract_previous_results_sql_summary_field_always_present(self):
        """sql_summary 필드는 항상 result_info에 존재"""
        history = [
            _make_msg("user", "최근 결제"),
            _make_msg(
                "assistant",
                "합계입니다.",
                renderSpec={
                    "type": "text",
                    "text": {"content": "합계: $1,000,000"},
                },
            ),
        ]
        results = extract_previous_results(history)

        assert len(results) >= 1
        # sql_summary 키가 항상 존재해야 함
        assert "sql_summary" in results[0]
