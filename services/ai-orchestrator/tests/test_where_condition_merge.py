"""
WHERE 조건 추출/병합 및 참조 표현 감지 테스트

연속 대화에서 WHERE 조건 누락 문제 해결을 검증합니다.
"""

import pytest
from app.api.v1.chat import detect_reference_expression
from app.services.text_to_sql import (
    extract_where_conditions,
    extract_condition_field,
    merge_where_conditions,
    ConversationContext,
)


class TestDetectReferenceExpression:
    """참조 표현 감지 테스트"""

    def test_detect_이중에(self):
        """'이중에' 패턴 감지"""
        is_ref, ref_type = detect_reference_expression("이중에 mer_001만 보여줘")
        assert is_ref is True
        assert ref_type == "filter"

    def test_detect_이중(self):
        """'이중' 패턴 감지 (공백 없음)"""
        is_ref, ref_type = detect_reference_expression("이중 도서관련만")
        assert is_ref is True
        assert ref_type == "filter"

    def test_detect_여기서(self):
        """'여기서' 패턴 감지"""
        is_ref, ref_type = detect_reference_expression("여기서 DONE 상태만")
        assert is_ref is True
        assert ref_type == "filter"

    def test_detect_그중(self):
        """'그중' 패턴 감지"""
        is_ref, ref_type = detect_reference_expression("그 중에서 금액 큰 것")
        assert is_ref is True
        assert ref_type == "filter"

    def test_detect_직전(self):
        """'직전' 패턴 감지"""
        is_ref, ref_type = detect_reference_expression("직전 결과에서 필터")
        assert is_ref is True
        assert ref_type == "filter"

    def test_detect_방금(self):
        """'방금' 패턴 감지"""
        is_ref, ref_type = detect_reference_expression("방금 결과 중 환불건")
        assert is_ref is True
        assert ref_type == "filter"

    def test_detect_위결과(self):
        """'위 결과' 패턴 감지"""
        is_ref, ref_type = detect_reference_expression("위 결과에서 카드만")
        assert is_ref is True
        assert ref_type == "filter"

    def test_detect_new_query_새로조회(self):
        """'새로 조회' 패턴 감지 (새 쿼리)"""
        is_ref, ref_type = detect_reference_expression("새로 환불 내역 조회해줘")
        assert is_ref is False
        assert ref_type == "new"

    def test_detect_new_query_다시조회(self):
        """'다시 조회' 패턴 감지 (새 쿼리)"""
        is_ref, ref_type = detect_reference_expression("다시 조회")
        assert is_ref is False
        assert ref_type == "new"

    def test_detect_new_query_처음부터(self):
        """'처음부터' 패턴 감지 (새 쿼리)"""
        is_ref, ref_type = detect_reference_expression("처음부터 다시")
        assert is_ref is False
        assert ref_type == "new"

    def test_no_reference_expression(self):
        """참조 표현 없음"""
        is_ref, ref_type = detect_reference_expression("최근 결제 내역 보여줘")
        assert is_ref is False
        assert ref_type == "none"

    def test_no_reference_simple_query(self):
        """단순 쿼리 (참조 없음)"""
        is_ref, ref_type = detect_reference_expression("오늘 결제 현황")
        assert is_ref is False
        assert ref_type == "none"


class TestExtractWhereConditions:
    """WHERE 조건 추출 테스트"""

    def test_single_condition(self):
        """단일 조건 추출"""
        sql = "SELECT * FROM payments WHERE status = 'DONE'"
        conditions = extract_where_conditions(sql)
        assert len(conditions) == 1
        assert "status = 'DONE'" in conditions[0]

    def test_multiple_conditions(self):
        """다중 조건 추출 (AND 연결)"""
        sql = """SELECT * FROM payments
                 WHERE created_at >= '2024-01-01'
                 AND merchant_id = 'mer_001'"""
        conditions = extract_where_conditions(sql)
        assert len(conditions) == 2
        assert any("created_at" in c for c in conditions)
        assert any("merchant_id" in c for c in conditions)

    def test_with_group_by(self):
        """GROUP BY 앞까지만 추출"""
        sql = """SELECT merchant_id, SUM(amount) FROM payments
                 WHERE created_at >= '2024-01-01'
                 GROUP BY merchant_id"""
        conditions = extract_where_conditions(sql)
        assert len(conditions) == 1
        assert "created_at" in conditions[0]

    def test_with_order_by(self):
        """ORDER BY 앞까지만 추출"""
        sql = """SELECT * FROM payments
                 WHERE status = 'DONE'
                 ORDER BY created_at DESC"""
        conditions = extract_where_conditions(sql)
        assert len(conditions) == 1
        assert "status = 'DONE'" in conditions[0]

    def test_with_limit(self):
        """LIMIT 앞까지만 추출"""
        sql = """SELECT * FROM payments
                 WHERE amount > 10000
                 LIMIT 100"""
        conditions = extract_where_conditions(sql)
        assert len(conditions) == 1
        assert "amount > 10000" in conditions[0]

    def test_no_where_clause(self):
        """WHERE 절 없음"""
        sql = "SELECT * FROM payments"
        conditions = extract_where_conditions(sql)
        assert conditions == []

    def test_empty_sql(self):
        """빈 SQL"""
        conditions = extract_where_conditions("")
        assert conditions == []

    def test_complex_conditions(self):
        """복잡한 조건 (IN, LIKE 등)"""
        sql = """SELECT * FROM payments
                 WHERE status IN ('DONE', 'CANCELED')
                 AND order_name LIKE '%도서%'"""
        conditions = extract_where_conditions(sql)
        assert len(conditions) == 2


class TestExtractConditionField:
    """조건에서 필드명 추출 테스트"""

    def test_equal_operator(self):
        """= 연산자"""
        field = extract_condition_field("status = 'DONE'")
        assert field == "status"

    def test_comparison_operators(self):
        """비교 연산자"""
        assert extract_condition_field("amount >= 10000") == "amount"
        assert extract_condition_field("created_at < '2024-01-01'") == "created_at"

    def test_like_operator(self):
        """LIKE 연산자"""
        field = extract_condition_field("order_name LIKE '%도서%'")
        assert field == "order_name"

    def test_in_operator(self):
        """IN 연산자"""
        field = extract_condition_field("status IN ('DONE', 'CANCELED')")
        assert field == "status"

    def test_is_null(self):
        """IS NULL"""
        field = extract_condition_field("failure_code IS NULL")
        assert field == "failure_code"

    def test_is_not_null(self):
        """IS NOT NULL"""
        field = extract_condition_field("approved_at IS NOT NULL")
        assert field == "approved_at"


class TestMergeWhereConditions:
    """WHERE 조건 병합 테스트"""

    def test_merge_different_fields(self):
        """다른 필드 조건 병합"""
        existing = ["created_at >= '2024-01-01'"]
        new = ["merchant_id = 'mer_001'"]
        merged = merge_where_conditions(existing, new)
        assert len(merged) == 2
        assert any("created_at" in c for c in merged)
        assert any("merchant_id" in c for c in merged)

    def test_merge_same_field_replaced(self):
        """동일 필드는 새 조건으로 대체"""
        existing = ["status = 'DONE'"]
        new = ["status = 'CANCELED'"]
        merged = merge_where_conditions(existing, new)
        assert len(merged) == 1
        assert "CANCELED" in merged[0]
        assert "DONE" not in merged[0]

    def test_merge_accumulative(self):
        """누적 병합 (시나리오: 3단계)"""
        # 1단계: 시간 조건
        step1 = ["created_at >= '2024-01-01'"]

        # 2단계: 가맹점 추가
        step2 = merge_where_conditions(step1, ["merchant_id = 'mer_001'"])
        assert len(step2) == 2

        # 3단계: 상품명 추가
        step3 = merge_where_conditions(step2, ["order_name LIKE '%도서%'"])
        assert len(step3) == 3
        assert any("created_at" in c for c in step3)
        assert any("merchant_id" in c for c in step3)
        assert any("order_name" in c for c in step3)

    def test_empty_existing(self):
        """기존 조건 없음"""
        merged = merge_where_conditions([], ["status = 'DONE'"])
        assert len(merged) == 1

    def test_empty_new(self):
        """새 조건 없음"""
        merged = merge_where_conditions(["status = 'DONE'"], [])
        assert len(merged) == 1


class TestConversationContext:
    """ConversationContext 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        ctx = ConversationContext(
            previous_question="이전 질문",
            previous_sql="SELECT * FROM payments",
            previous_result_summary="1000건"
        )
        assert ctx.accumulated_where_conditions == []
        assert ctx.is_refinement is False

    def test_with_refinement(self):
        """참조 모드 설정"""
        ctx = ConversationContext(
            previous_question="이전 질문",
            previous_sql="SELECT * FROM payments WHERE status = 'DONE'",
            previous_result_summary="1000건",
            accumulated_where_conditions=["status = 'DONE'"],
            is_refinement=True
        )
        assert len(ctx.accumulated_where_conditions) == 1
        assert ctx.is_refinement is True


class TestIntegrationScenario:
    """통합 시나리오 테스트"""

    def test_scenario_where_condition_accumulation(self):
        """
        시나리오: 연속 대화에서 WHERE 조건 누적

        1. "최근 3개월 결제건" → WHERE created_at >= '3 months'
        2. "이중 mer_001만" → WHERE created_at >= '3 months' AND merchant_id = 'mer_001'
        3. "이중 도서관련만" → WHERE created_at >= '3 months' AND merchant_id = 'mer_001' AND order_name LIKE '%도서%'
        """
        # Step 1: 첫 쿼리
        sql1 = "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months'"
        conditions1 = extract_where_conditions(sql1)
        assert len(conditions1) == 1

        # Step 2: "이중에 mer_001만" - 참조 표현 감지
        is_ref2, _ = detect_reference_expression("이중에 mer_001만")
        assert is_ref2 is True

        # 조건 병합
        new_conditions2 = ["merchant_id = 'mer_001'"]
        merged2 = merge_where_conditions(conditions1, new_conditions2)
        assert len(merged2) == 2

        # Step 3: "이중 도서관련만" - 참조 표현 감지
        is_ref3, _ = detect_reference_expression("이중 도서관련만")
        assert is_ref3 is True

        # 조건 병합
        new_conditions3 = ["order_name LIKE '%도서%'"]
        merged3 = merge_where_conditions(merged2, new_conditions3)
        assert len(merged3) == 3

        # 최종 조건 확인
        all_fields = [extract_condition_field(c) for c in merged3]
        assert "created_at" in all_fields
        assert "merchant_id" in all_fields
        assert "order_name" in all_fields

    def test_scenario_new_query_resets_conditions(self):
        """
        시나리오: "새로 조회"는 이전 조건 무시

        1. "결제 현황" → FROM payments ...
        2. "새로 환불 내역 조회" → FROM refunds ... (이전 조건 무시)
        """
        # Step 1: 첫 쿼리 (결제)
        is_ref1, ref_type1 = detect_reference_expression("결제 현황")
        assert is_ref1 is False
        assert ref_type1 == "none"

        # Step 2: 새 쿼리 요청
        is_ref2, ref_type2 = detect_reference_expression("새로 환불 내역 조회")
        assert is_ref2 is False
        assert ref_type2 == "new"  # 새 쿼리 타입

    def test_scenario_same_field_replacement(self):
        """
        시나리오: 동일 필드 변경

        1. "DONE 상태" → WHERE status = 'DONE'
        2. "이중 CANCELED만" → WHERE status = 'CANCELED' (status 조건 교체)
        """
        # Step 1: DONE 상태
        conditions1 = ["status = 'DONE'"]

        # Step 2: 참조 표현 + 상태 변경
        is_ref, _ = detect_reference_expression("이중 CANCELED만")
        assert is_ref is True

        new_conditions = ["status = 'CANCELED'"]
        merged = merge_where_conditions(conditions1, new_conditions)

        # 결과: status 조건은 1개만 있어야 함 (CANCELED로 대체)
        assert len(merged) == 1
        assert "CANCELED" in merged[0]
        assert "DONE" not in merged[0]
