"""
집계 쿼리 감지 및 컨텍스트 생성 테스트
"""

import pytest
from app.services.text_to_sql import (
    detect_aggregation_functions,
    detect_group_by,
    build_aggregation_context,
    aggregation_context_to_dict,
    AggregationInfo,
    AggregationContext
)


class TestDetectAggregationFunctions:
    """집계 함수 감지 테스트"""

    def test_sum_detection(self):
        """SUM 함수 감지"""
        sql = "SELECT SUM(amount) AS total_amount FROM payments"
        aggs = detect_aggregation_functions(sql)

        assert len(aggs) == 1
        assert aggs[0].function == "SUM"
        assert aggs[0].target_column == "amount"
        assert aggs[0].alias == "total_amount"

    def test_count_star_detection(self):
        """COUNT(*) 감지"""
        sql = "SELECT COUNT(*) AS cnt FROM payments"
        aggs = detect_aggregation_functions(sql)

        assert len(aggs) == 1
        assert aggs[0].function == "COUNT"
        assert aggs[0].target_column == "*"
        assert aggs[0].alias == "cnt"

    def test_avg_detection(self):
        """AVG 함수 감지"""
        sql = "SELECT AVG(amount) AS avg_amount FROM payments"
        aggs = detect_aggregation_functions(sql)

        assert len(aggs) == 1
        assert aggs[0].function == "AVG"
        assert aggs[0].target_column == "amount"

    def test_max_min_detection(self):
        """MAX, MIN 함수 감지"""
        sql = "SELECT MAX(amount) AS max_amt, MIN(amount) AS min_amt FROM payments"
        aggs = detect_aggregation_functions(sql)

        assert len(aggs) == 2
        funcs = {agg.function for agg in aggs}
        assert "MAX" in funcs
        assert "MIN" in funcs

    def test_multiple_aggregations(self):
        """복수 집계 함수 감지"""
        sql = "SELECT COUNT(*) AS cnt, SUM(amount) AS total, AVG(amount) AS avg FROM payments"
        aggs = detect_aggregation_functions(sql)

        assert len(aggs) == 3
        funcs = {agg.function for agg in aggs}
        assert funcs == {"COUNT", "SUM", "AVG"}

    def test_no_aggregation(self):
        """일반 SELECT 쿼리 (집계 없음)"""
        sql = "SELECT * FROM payments WHERE merchant_id = 'mer_001'"
        aggs = detect_aggregation_functions(sql)

        assert len(aggs) == 0

    def test_aggregation_without_alias(self):
        """별칭 없는 집계 함수"""
        sql = "SELECT SUM(amount) FROM payments"
        aggs = detect_aggregation_functions(sql)

        assert len(aggs) == 1
        assert aggs[0].function == "SUM"
        assert aggs[0].target_column == "amount"
        # 별칭은 None 또는 없음

    def test_case_insensitivity(self):
        """대소문자 구분 없이 감지"""
        sql = "SELECT sum(amount) AS total, Count(*) AS cnt FROM payments"
        aggs = detect_aggregation_functions(sql)

        assert len(aggs) == 2


class TestDetectGroupBy:
    """GROUP BY 감지 테스트"""

    def test_single_group_by(self):
        """단일 컬럼 GROUP BY"""
        sql = "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id"
        has_group, columns = detect_group_by(sql)

        assert has_group is True
        assert columns == ["merchant_id"]

    def test_multiple_group_by(self):
        """복수 컬럼 GROUP BY"""
        sql = "SELECT merchant_id, status, COUNT(*) FROM payments GROUP BY merchant_id, status"
        has_group, columns = detect_group_by(sql)

        assert has_group is True
        assert len(columns) == 2
        assert "merchant_id" in columns
        assert "status" in columns

    def test_no_group_by(self):
        """GROUP BY 없는 쿼리"""
        sql = "SELECT SUM(amount) FROM payments WHERE merchant_id = 'mer_001'"
        has_group, columns = detect_group_by(sql)

        assert has_group is False
        assert columns == []

    def test_group_by_with_having(self):
        """GROUP BY + HAVING 절"""
        sql = "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id HAVING SUM(amount) > 1000"
        has_group, columns = detect_group_by(sql)

        assert has_group is True
        assert columns == ["merchant_id"]

    def test_group_by_with_order_by(self):
        """GROUP BY + ORDER BY 절"""
        sql = "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id ORDER BY merchant_id"
        has_group, columns = detect_group_by(sql)

        assert has_group is True
        assert columns == ["merchant_id"]


class TestBuildAggregationContext:
    """집계 컨텍스트 생성 테스트"""

    def test_new_query_context(self):
        """새 쿼리 컨텍스트 생성"""
        sql = "SELECT SUM(amount) AS total FROM payments WHERE merchant_id = 'mer_001'"
        ctx = build_aggregation_context(sql, is_refinement=False)

        assert ctx is not None
        assert ctx.query_type == "NEW_QUERY"
        assert len(ctx.aggregations) == 1
        assert ctx.aggregations[0].function == "SUM"
        assert "merchant_id = 'mer_001'" in ctx.based_on_filters

    def test_refinement_context(self):
        """세분화 쿼리 컨텍스트 생성"""
        sql = "SELECT SUM(amount) FROM payments WHERE merchant_id = 'mer_001' AND status = 'DONE'"
        ctx = build_aggregation_context(sql, is_refinement=True, previous_row_count=25)

        assert ctx is not None
        assert ctx.query_type == "REFINEMENT"
        assert ctx.source_row_count == 25
        assert len(ctx.based_on_filters) == 2

    def test_no_context_for_non_aggregation(self):
        """일반 쿼리는 None 반환"""
        sql = "SELECT * FROM payments LIMIT 10"
        ctx = build_aggregation_context(sql)

        assert ctx is None

    def test_context_with_group_by(self):
        """GROUP BY 포함 컨텍스트"""
        sql = "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id"
        ctx = build_aggregation_context(sql)

        assert ctx is not None
        assert ctx.has_group_by is True
        assert ctx.group_by_columns == ["merchant_id"]

    def test_context_with_multiple_conditions(self):
        """복수 WHERE 조건 추출"""
        sql = """SELECT COUNT(*) FROM payments
                 WHERE created_at >= '2024-01-01'
                 AND merchant_id = 'mer_001'
                 AND status = 'DONE'"""
        ctx = build_aggregation_context(sql)

        assert ctx is not None
        assert len(ctx.based_on_filters) == 3


class TestAggregationContextToDict:
    """딕셔너리 변환 테스트"""

    def test_full_conversion(self):
        """전체 컨텍스트 변환"""
        ctx = AggregationContext(
            query_type="NEW_QUERY",
            based_on_filters=["status = 'DONE'", "merchant_id = 'mer_001'"],
            source_row_count=100,
            aggregations=[
                AggregationInfo(function="SUM", target_column="amount", alias="total"),
                AggregationInfo(function="COUNT", target_column="*", alias="cnt")
            ],
            has_group_by=True,
            group_by_columns=["merchant_id"]
        )

        result = aggregation_context_to_dict(ctx)

        assert result["queryType"] == "NEW_QUERY"
        assert len(result["basedOnFilters"]) == 2
        assert result["sourceRowCount"] == 100
        assert len(result["aggregations"]) == 2
        assert result["hasGroupBy"] is True
        assert result["groupByColumns"] == ["merchant_id"]

    def test_aggregation_structure(self):
        """집계 정보 구조 확인"""
        ctx = AggregationContext(
            query_type="NEW_QUERY",
            based_on_filters=[],
            source_row_count=None,
            aggregations=[
                AggregationInfo(function="AVG", target_column="amount", alias="avg_amount")
            ],
            has_group_by=False,
            group_by_columns=[]
        )

        result = aggregation_context_to_dict(ctx)

        agg = result["aggregations"][0]
        assert agg["function"] == "AVG"
        assert agg["targetColumn"] == "amount"
        assert agg["alias"] == "avg_amount"


class TestIntegration:
    """통합 테스트"""

    def test_realistic_payment_sum_query(self):
        """실제 결제 합계 쿼리 시나리오"""
        sql = """SELECT SUM(amount) AS total_payment_amount
                 FROM payments
                 WHERE created_at >= NOW() - INTERVAL '3 months'
                 AND merchant_id = 'mer_001'
                 AND status = 'DONE'"""

        ctx = build_aggregation_context(sql, is_refinement=False)

        assert ctx is not None
        ctx_dict = aggregation_context_to_dict(ctx)

        assert ctx_dict["queryType"] == "NEW_QUERY"
        assert len(ctx_dict["aggregations"]) == 1
        assert ctx_dict["aggregations"][0]["function"] == "SUM"
        assert ctx_dict["aggregations"][0]["targetColumn"] == "amount"
        assert len(ctx_dict["basedOnFilters"]) == 3

    def test_merchant_breakdown_query(self):
        """가맹점별 매출 집계 쿼리"""
        sql = """SELECT merchant_id,
                        SUM(amount) AS total_amount,
                        COUNT(*) AS transaction_count,
                        AVG(amount) AS avg_amount
                 FROM payments
                 WHERE status = 'DONE'
                 GROUP BY merchant_id
                 ORDER BY total_amount DESC"""

        ctx = build_aggregation_context(sql, is_refinement=False)

        assert ctx is not None
        ctx_dict = aggregation_context_to_dict(ctx)

        assert ctx_dict["hasGroupBy"] is True
        assert ctx_dict["groupByColumns"] == ["merchant_id"]
        assert len(ctx_dict["aggregations"]) == 3

        funcs = {agg["function"] for agg in ctx_dict["aggregations"]}
        assert funcs == {"SUM", "COUNT", "AVG"}

    def test_refinement_from_previous_result(self):
        """이전 결과에서 세분화 쿼리"""
        # 시나리오: "이중에 결제금액 합산해서 보여줘"
        sql = """SELECT SUM(amount) AS total
                 FROM payments
                 WHERE merchant_id = 'mer_001'
                 AND order_name LIKE '%도서%'"""

        ctx = build_aggregation_context(
            sql,
            is_refinement=True,
            previous_row_count=25
        )

        assert ctx is not None
        ctx_dict = aggregation_context_to_dict(ctx)

        assert ctx_dict["queryType"] == "REFINEMENT"
        assert ctx_dict["sourceRowCount"] == 25
        assert len(ctx_dict["basedOnFilters"]) == 2
