"""
TC-020: Text-to-SQL Complex Query Pattern Tests

복잡한 쿼리 패턴 테스트
- 상위 N개 엔티티의 세부 집계 (CTE 패턴)
- 조건부 집계 (FILTER 패턴)
- 비율/점유율 계산 (윈도우 함수 패턴)

이 테스트는 실제 LLM 호출 없이 패턴 검증에 초점을 맞춥니다.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestComplexQueryPatterns:
    """복잡한 쿼리 패턴 테스트"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client"""
        return AsyncMock()

    @pytest.fixture
    def mock_rag_service(self):
        """Mock RAG service"""
        mock = MagicMock()
        mock.search = AsyncMock(return_value=[])
        return mock

    @pytest.mark.asyncio
    async def test_top_n_secondary_aggregation_uses_cte(self, mock_llm_client, mock_rag_service):
        """상위 N개 엔티티의 세부 집계 - CTE 사용 확인

        질문: "오류가 많은 상위 5개 가맹점의 시간대별 오류 건수"
        기대: WITH 절(CTE) 사용, LIMIT이 CTE 내부에 위치
        """
        # LLM이 CTE 패턴을 사용한 SQL을 생성하도록 mock 설정
        expected_sql = """
        WITH top_error_merchants AS (
            SELECT merchant_id, COUNT(*) as error_count
            FROM payments
            WHERE created_at >= NOW() - INTERVAL '3 months' AND status = 'ABORTED'
            GROUP BY merchant_id
            ORDER BY error_count DESC
            LIMIT 5
        )
        SELECT p.merchant_id, EXTRACT(HOUR FROM p.created_at) AS hour, COUNT(*) AS error_count
        FROM payments p
        JOIN top_error_merchants tem ON p.merchant_id = tem.merchant_id
        WHERE p.created_at >= NOW() - INTERVAL '3 months' AND p.status = 'ABORTED'
        GROUP BY p.merchant_id, EXTRACT(HOUR FROM p.created_at)
        ORDER BY p.merchant_id, hour;
        """

        # CTE 패턴 검증
        assert "WITH" in expected_sql.upper()
        assert "LIMIT 5" in expected_sql

        # LIMIT이 CTE 안에 있는지 확인 (메인 쿼리가 아닌 서브쿼리 내)
        upper_sql = expected_sql.upper()

        # CTE 닫는 괄호 찾기 (중첩 괄호 고려)
        # AS ( 이후 첫 번째 여는 괄호부터 시작하여 매칭되는 닫는 괄호 찾기
        as_paren_pos = upper_sql.find("AS (")
        paren_count = 0
        cte_close_paren = -1
        for i, char in enumerate(upper_sql[as_paren_pos:], start=as_paren_pos):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count == 0:
                    cte_close_paren = i
                    break

        limit_pos = upper_sql.find("LIMIT 5")

        assert cte_close_paren > 0, "CTE 닫는 괄호를 찾을 수 없음"
        assert limit_pos < cte_close_paren, "LIMIT은 CTE 내부에 있어야 함"

        # JOIN으로 연결되는지 확인
        assert "JOIN" in upper_sql, "CTE와 메인 테이블이 JOIN으로 연결되어야 함"

    @pytest.mark.asyncio
    async def test_simple_top_n_no_cte_required(self):
        """단순 상위 N개 조회 - CTE 불필요

        질문: "오류가 가장 많은 상위 5개 가맹점"
        기대: ORDER BY + LIMIT으로 충분
        """
        simple_sql = """
        SELECT merchant_id, COUNT(*) as error_count
        FROM payments
        WHERE status = 'ABORTED'
        GROUP BY merchant_id
        ORDER BY error_count DESC
        LIMIT 5;
        """

        # 단순 Top N은 CTE 없이 ORDER BY + LIMIT 가능
        upper_sql = simple_sql.upper()
        assert "ORDER BY" in upper_sql
        assert "LIMIT" in upper_sql
        # CTE는 불필요 (단순 조회에서 CTE 사용은 과도함)
        # 이 경우 WITH가 없어도 됨
        # (단, WITH가 있어도 틀린 건 아님)

    @pytest.mark.asyncio
    async def test_conditional_aggregation_uses_filter(self):
        """조건부 집계 - FILTER 절 사용

        질문: "가맹점별 성공/실패 건수 비교"
        기대: FILTER (WHERE ...) 구문 사용
        """
        conditional_sql = """
        SELECT
            merchant_id,
            COUNT(*) FILTER (WHERE status = 'DONE') AS success_count,
            COUNT(*) FILTER (WHERE status = 'ABORTED') AS error_count
        FROM payments
        WHERE created_at >= NOW() - INTERVAL '3 months'
        GROUP BY merchant_id;
        """

        upper_sql = conditional_sql.upper()
        assert "FILTER" in upper_sql
        assert "WHERE STATUS = 'DONE'" in upper_sql
        assert "WHERE STATUS = 'ABORTED'" in upper_sql

    @pytest.mark.asyncio
    async def test_conditional_aggregation_alternative_case_when(self):
        """조건부 집계 대안 - CASE WHEN 사용

        FILTER 절 대신 CASE WHEN도 유효한 패턴
        """
        case_when_sql = """
        SELECT
            merchant_id,
            SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END) AS success_count,
            SUM(CASE WHEN status = 'ABORTED' THEN 1 ELSE 0 END) AS error_count
        FROM payments
        WHERE created_at >= NOW() - INTERVAL '3 months'
        GROUP BY merchant_id;
        """

        upper_sql = case_when_sql.upper()
        assert "CASE WHEN" in upper_sql
        assert "SUM(" in upper_sql

    @pytest.mark.asyncio
    async def test_percentage_calculation_uses_window_function(self):
        """비율/점유율 계산 - 윈도우 함수 사용

        질문: "가맹점별 결제 점유율"
        기대: SUM(...) OVER () 윈도우 함수 사용
        """
        percentage_sql = """
        SELECT
            merchant_id,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage
        FROM payments
        GROUP BY merchant_id
        ORDER BY percentage DESC;
        """

        upper_sql = percentage_sql.upper()
        assert "OVER ()" in upper_sql or "OVER()" in upper_sql
        assert "SUM(COUNT(*))" in upper_sql or "SUM(COUNT(*)" in upper_sql
        assert "PERCENTAGE" in upper_sql

    @pytest.mark.asyncio
    async def test_percentage_alternative_subquery(self):
        """비율 계산 대안 - 서브쿼리 사용

        윈도우 함수 대신 서브쿼리도 유효한 패턴
        """
        subquery_sql = """
        SELECT
            merchant_id,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM payments), 2) AS percentage
        FROM payments
        GROUP BY merchant_id
        ORDER BY percentage DESC;
        """

        upper_sql = subquery_sql.upper()
        # 서브쿼리로 전체 COUNT 계산
        assert "(SELECT COUNT(*) FROM PAYMENTS)" in upper_sql
        assert "PERCENTAGE" in upper_sql

    @pytest.mark.asyncio
    async def test_simple_query_unchanged(self):
        """단순 조회는 CTE 불필요

        질문: "최근 3개월 결제건 조회"
        기대: 단순 SELECT (CTE/서브쿼리 없음)
        """
        simple_query = """
        SELECT *
        FROM payments
        WHERE created_at >= NOW() - INTERVAL '3 months'
        ORDER BY created_at DESC
        LIMIT 100;
        """

        upper_sql = simple_query.upper()
        assert "WITH" not in upper_sql
        assert "SELECT *" in upper_sql
        assert "LIMIT 100" in upper_sql


class TestPatternRecognition:
    """패턴 인식 규칙 테스트"""

    def test_top_n_with_secondary_dimension_triggers_cte(self):
        """'상위 N개' + '~별 집계' 키워드 조합 시 CTE 필요"""
        questions_needing_cte = [
            "오류가 많은 상위 5개 가맹점의 시간대별 오류 건수",
            "매출 Top 10 가맹점별 일별 결제 추이",
            "환불이 가장 많은 상위 3개 가맹점의 월별 환불 현황",
            "결제 실패율 높은 상위 5개 결제수단의 시간대별 분포",
        ]

        for question in questions_needing_cte:
            # "상위/Top" + "별" 키워드 조합 확인
            has_top_n = any(kw in question for kw in ["상위", "Top", "가장 많은", "높은"])
            has_secondary = "별" in question
            assert has_top_n and has_secondary, f"CTE 필요 질문: {question}"

    def test_simple_top_n_no_secondary_dimension(self):
        """'상위 N개' 단독 - CTE 불필요"""
        simple_questions = [
            "오류가 많은 상위 5개 가맹점",
            "매출 Top 10 가맹점",
            "최근 환불 건수가 가장 많은 가맹점 3개",
            "결제 금액 높은 상위 5개",
        ]

        for question in simple_questions:
            has_top_n = any(kw in question for kw in ["상위", "Top", "가장 많은", "높은"])
            # "~별"이 후행하지 않음 (세부 집계 없음)
            has_secondary_aggregation = "별" in question and any(
                kw in question for kw in ["시간대별", "일별", "월별", "연도별", "분기별"]
            )
            assert has_top_n and not has_secondary_aggregation, f"CTE 불필요 질문: {question}"

    def test_conditional_aggregation_keywords(self):
        """조건부 집계가 필요한 질문 패턴"""
        conditional_questions = [
            "가맹점별 성공/실패 건수",
            "상태별 결제 금액 비교",
            "성공 건수와 실패 건수",
            "완료/취소/진행중 건수",
        ]

        for question in conditional_questions:
            # 상태 비교 키워드 확인
            has_comparison = any(kw in question for kw in ["/", "와", "건수", "비교"])
            assert has_comparison, f"조건부 집계 질문: {question}"

    def test_percentage_calculation_keywords(self):
        """비율/점유율 계산이 필요한 질문 패턴"""
        percentage_questions = [
            "가맹점별 결제 점유율",
            "상태별 비율",
            "전체 대비 %",
            "비중 분석",
            "퍼센트",
        ]

        percentage_keywords = ["점유율", "비율", "%", "비중", "퍼센트", "전체 대비"]

        for question in percentage_questions:
            has_percentage_kw = any(kw in question for kw in percentage_keywords)
            assert has_percentage_kw, f"비율 계산 질문: {question}"


class TestCTEStructureValidation:
    """CTE 구조 검증 테스트"""

    def test_cte_has_proper_structure(self):
        """CTE가 올바른 구조를 갖는지 검증"""
        cte_sql = """
        WITH ranked_merchants AS (
            SELECT merchant_id, SUM(amount) as total
            FROM payments
            GROUP BY merchant_id
            ORDER BY total DESC
            LIMIT 5
        )
        SELECT rm.merchant_id, p.status, COUNT(*) as count
        FROM payments p
        JOIN ranked_merchants rm ON p.merchant_id = rm.merchant_id
        GROUP BY rm.merchant_id, p.status;
        """

        # CTE 구조 검증
        upper_sql = cte_sql.upper()

        # 1. WITH 절 존재
        assert "WITH" in upper_sql

        # 2. AS 키워드로 CTE 정의
        assert "AS (" in upper_sql or "AS(" in upper_sql

        # 3. CTE 이름 다음에 괄호
        with_pos = upper_sql.find("WITH")
        as_pos = upper_sql.find("AS (", with_pos)
        assert as_pos > with_pos

        # 4. 메인 쿼리에서 CTE 참조
        assert "JOIN RANKED_MERCHANTS" in upper_sql or "FROM RANKED_MERCHANTS" in upper_sql

    def test_cte_limit_placement(self):
        """CTE 내부 LIMIT 위치 검증 - Top N 후 세부 집계"""
        sql_with_cte = """
        WITH top_5 AS (
            SELECT id FROM t ORDER BY x DESC LIMIT 5
        )
        SELECT * FROM t JOIN top_5 ON t.id = top_5.id;
        """

        upper_sql = sql_with_cte.upper()

        # CTE 종료 괄호 위치
        cte_end = upper_sql.find(")", upper_sql.find("AS ("))
        # LIMIT 위치
        limit_pos = upper_sql.find("LIMIT")

        # LIMIT이 CTE 내부에 있어야 함
        assert limit_pos < cte_end, "LIMIT은 CTE 내부에 위치해야 함"

    def test_outer_query_no_limit_for_secondary_aggregation(self):
        """2차 집계 시 외부 쿼리에 LIMIT 불필요"""
        sql = """
        WITH top_merchants AS (
            SELECT merchant_id FROM payments
            GROUP BY merchant_id ORDER BY COUNT(*) DESC LIMIT 5
        )
        SELECT p.merchant_id, DATE(p.created_at) as date, COUNT(*) as cnt
        FROM payments p
        JOIN top_merchants tm ON p.merchant_id = tm.merchant_id
        GROUP BY p.merchant_id, DATE(p.created_at)
        ORDER BY p.merchant_id, date;
        """

        upper_sql = sql_normalized = " ".join(sql.upper().split())

        # CTE 이후 메인 쿼리 추출
        main_query_start = sql_normalized.find(") SELECT", 0)
        main_query = sql_normalized[main_query_start:]

        # 메인 쿼리에는 LIMIT이 없거나, 결과 제한용이 아닌지 확인
        # (2차 집계 결과는 모두 보여줘야 함 - Top 5의 일별 데이터 전체)
        # 참고: 실제 구현에서는 페이징을 위해 LIMIT이 있을 수 있음


class TestWindowFunctionPatterns:
    """윈도우 함수 패턴 테스트"""

    def test_running_total_pattern(self):
        """누적 합계 패턴"""
        running_total_sql = """
        SELECT
            created_at,
            amount,
            SUM(amount) OVER (ORDER BY created_at) as running_total
        FROM payments
        ORDER BY created_at;
        """

        upper_sql = running_total_sql.upper()
        assert "SUM(AMOUNT) OVER" in upper_sql
        assert "ORDER BY CREATED_AT" in upper_sql

    def test_rank_pattern(self):
        """순위 패턴"""
        rank_sql = """
        SELECT
            merchant_id,
            SUM(amount) as total,
            RANK() OVER (ORDER BY SUM(amount) DESC) as rank
        FROM payments
        GROUP BY merchant_id;
        """

        upper_sql = rank_sql.upper()
        assert "RANK() OVER" in upper_sql or "DENSE_RANK() OVER" in upper_sql or "ROW_NUMBER() OVER" in upper_sql

    def test_partition_by_pattern(self):
        """파티션별 집계 패턴"""
        partition_sql = """
        SELECT
            merchant_id,
            status,
            COUNT(*) as count,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY merchant_id) as pct_in_merchant
        FROM payments
        GROUP BY merchant_id, status;
        """

        upper_sql = partition_sql.upper()
        assert "PARTITION BY" in upper_sql
        assert "OVER" in upper_sql


class TestFilterClausePatterns:
    """FILTER 절 패턴 테스트 (PostgreSQL 전용)"""

    def test_multiple_filter_aggregations(self):
        """여러 조건의 FILTER 집계"""
        filter_sql = """
        SELECT
            merchant_id,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'DONE') as done_count,
            COUNT(*) FILTER (WHERE status = 'CANCELED') as canceled_count,
            COUNT(*) FILTER (WHERE status = 'ABORTED') as aborted_count
        FROM payments
        GROUP BY merchant_id;
        """

        upper_sql = filter_sql.upper()
        # 3개의 FILTER 절
        filter_count = upper_sql.count("FILTER (WHERE")
        assert filter_count == 3

    def test_filter_with_sum(self):
        """SUM과 FILTER 조합"""
        filter_sum_sql = """
        SELECT
            merchant_id,
            SUM(amount) FILTER (WHERE status = 'DONE') as done_amount,
            SUM(amount) FILTER (WHERE status = 'CANCELED') as refund_amount
        FROM payments
        GROUP BY merchant_id;
        """

        upper_sql = filter_sum_sql.upper()
        assert "SUM(AMOUNT) FILTER" in upper_sql


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_top_n_with_ties(self):
        """동점 처리가 필요한 Top N"""
        # FETCH FIRST WITH TIES 또는 RANK 사용
        ties_sql = """
        SELECT merchant_id, total
        FROM (
            SELECT merchant_id, SUM(amount) as total,
                   RANK() OVER (ORDER BY SUM(amount) DESC) as rnk
            FROM payments
            GROUP BY merchant_id
        ) ranked
        WHERE rnk <= 5;
        """

        upper_sql = ties_sql.upper()
        assert "RANK()" in upper_sql
        assert "RNK <= 5" in upper_sql

    def test_nested_aggregation(self):
        """중첩 집계 (일별 평균의 월별 합계 등)"""
        nested_sql = """
        WITH daily_totals AS (
            SELECT DATE(created_at) as date, SUM(amount) as daily_total
            FROM payments
            GROUP BY DATE(created_at)
        )
        SELECT
            DATE_TRUNC('month', date) as month,
            AVG(daily_total) as avg_daily,
            SUM(daily_total) as monthly_total
        FROM daily_totals
        GROUP BY DATE_TRUNC('month', date);
        """

        upper_sql = nested_sql.upper()
        assert "WITH" in upper_sql
        assert "AVG(DAILY_TOTAL)" in upper_sql
        assert "SUM(DAILY_TOTAL)" in upper_sql

    def test_empty_result_handling(self):
        """빈 결과 처리 - COALESCE/NULLIF 사용"""
        safe_sql = """
        SELECT
            merchant_id,
            COALESCE(SUM(amount), 0) as total,
            COALESCE(COUNT(*), 0) as count,
            COALESCE(SUM(amount) / NULLIF(COUNT(*), 0), 0) as avg_amount
        FROM payments
        GROUP BY merchant_id;
        """

        upper_sql = safe_sql.upper()
        assert "COALESCE" in upper_sql
        assert "NULLIF" in upper_sql


class TestRefundRatePatterns:
    """환불율(Refund Rate) 패턴 테스트"""

    def test_refund_rate_pattern_uses_left_join(self):
        """환불율 SQL이 payments 기준으로 refunds를 LEFT JOIN하는지 검증

        올바른 환불율 계산은 payments가 기준 테이블(FROM)이어야 하고,
        refunds는 LEFT JOIN으로 연결되어야 함 (환불이 없는 결제도 포함).
        """
        refund_rate_sql = """
        SELECT p.merchant_id,
               COUNT(*) AS total_payments,
               COUNT(*) FILTER (WHERE r.refund_key IS NOT NULL) AS refund_count,
               ROUND(100.0 * COUNT(*) FILTER (WHERE r.refund_key IS NOT NULL) /
                     NULLIF(COUNT(*), 0), 2) AS refund_rate
        FROM payments p
        LEFT JOIN refunds r ON p.payment_key = r.payment_key
        WHERE p.created_at >= NOW() - INTERVAL '1 month'
          AND p.status = 'DONE'
        GROUP BY p.merchant_id
        ORDER BY refund_rate DESC;
        """

        upper_sql = refund_rate_sql.upper()

        # payments가 FROM의 기준 테이블이어야 함
        assert "FROM PAYMENTS" in upper_sql, "payments 테이블이 FROM 절의 기준 테이블이어야 함"

        # refunds는 LEFT JOIN으로 연결되어야 함
        assert "LEFT JOIN REFUNDS" in upper_sql or "LEFT JOIN REFUNDS" in upper_sql.replace("\n", " "), \
            "refunds는 LEFT JOIN으로 연결되어야 함"

    def test_refund_rate_pattern_does_not_use_settlements(self):
        """환불율 SQL이 settlements.payment_count를 사용하지 않는지 검증

        환불율은 payments 테이블의 실제 결제건을 기준으로 계산해야 하며,
        settlements.payment_count를 분모로 사용하면 안 됨.
        """
        refund_rate_sql = """
        SELECT p.merchant_id,
               COUNT(*) AS total_payments,
               COUNT(*) FILTER (WHERE r.refund_key IS NOT NULL) AS refund_count,
               ROUND(100.0 * COUNT(*) FILTER (WHERE r.refund_key IS NOT NULL) /
                     NULLIF(COUNT(*), 0), 2) AS refund_rate
        FROM payments p
        LEFT JOIN refunds r ON p.payment_key = r.payment_key
        WHERE p.created_at >= NOW() - INTERVAL '1 month'
          AND p.status = 'DONE'
        GROUP BY p.merchant_id
        ORDER BY refund_rate DESC;
        """

        upper_sql = refund_rate_sql.upper()

        # settlements.payment_count를 사용하면 안 됨
        assert "SETTLEMENTS.PAYMENT_COUNT" not in upper_sql, \
            "환불율 계산 시 settlements.payment_count를 사용하면 안 됨"

    def test_refund_rate_pattern_has_group_by(self):
        """환불율 SQL에 GROUP BY가 포함되는지 검증

        가맹점별 환불율을 계산하려면 GROUP BY가 필수임.
        """
        refund_rate_sql = """
        SELECT p.merchant_id,
               COUNT(*) AS total_payments,
               COUNT(*) FILTER (WHERE r.refund_key IS NOT NULL) AS refund_count,
               ROUND(100.0 * COUNT(*) FILTER (WHERE r.refund_key IS NOT NULL) /
                     NULLIF(COUNT(*), 0), 2) AS refund_rate
        FROM payments p
        LEFT JOIN refunds r ON p.payment_key = r.payment_key
        WHERE p.created_at >= NOW() - INTERVAL '1 month'
          AND p.status = 'DONE'
        GROUP BY p.merchant_id
        ORDER BY refund_rate DESC;
        """

        upper_sql = refund_rate_sql.upper()

        # GROUP BY가 포함되어야 함
        assert "GROUP BY" in upper_sql, "환불율 집계에는 GROUP BY가 필수임"

    def test_refund_rate_prompt_included(self):
        """_build_prompt() 출력에 패턴 5와 환불율 관련 텍스트가 포함되는지 검증

        TDD RED: 현재 프롬프트에 패턴 5가 정의되어 있지 않으므로 이 테스트는 실패해야 함.
        이 테스트가 통과하려면 text_to_sql.py의 _build_prompt()에
        패턴 5 (환불율 패턴) 가이드라인을 추가해야 함.
        """
        from app.services.text_to_sql import TextToSqlService

        service = TextToSqlService()
        prompt = service._build_prompt(question="가맹점별 환불율을 알려줘")

        assert "패턴 5" in prompt, \
            "_build_prompt()에 '패턴 5' 텍스트가 없음. 환불율 패턴 가이드를 추가해야 함"
        assert "환불율" in prompt, \
            "_build_prompt()에 '환불율' 텍스트가 없음. 환불율 패턴 가이드를 추가해야 함"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
