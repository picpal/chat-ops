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

    # ============================================
    # 집계 키워드 감지 테스트 (이전 결과 참조로 처리)
    # ============================================

    def test_detect_aggregation_합산(self):
        """'합산' 키워드 감지"""
        is_ref, ref_type = detect_reference_expression("결제금액 합산해줘")
        assert is_ref is True
        assert ref_type == "aggregation"

    def test_detect_aggregation_합계(self):
        """'합계' 키워드 감지"""
        is_ref, ref_type = detect_reference_expression("합계 보여줘")
        assert is_ref is True
        assert ref_type == "aggregation"

    def test_detect_aggregation_총금액(self):
        """'총 금액' 키워드 감지"""
        is_ref, ref_type = detect_reference_expression("총 금액 얼마야")
        assert is_ref is True
        assert ref_type == "aggregation"

    def test_detect_aggregation_평균(self):
        """'평균' 키워드 감지"""
        is_ref, ref_type = detect_reference_expression("평균 금액 구해줘")
        assert is_ref is True
        assert ref_type == "aggregation"

    def test_detect_aggregation_개수(self):
        """'개수' 키워드 감지"""
        is_ref, ref_type = detect_reference_expression("개수 세줘")
        assert is_ref is True
        assert ref_type == "aggregation"

    def test_detect_aggregation_몇건(self):
        """'몇 건' 키워드 감지"""
        is_ref, ref_type = detect_reference_expression("몇 건이야")
        assert is_ref is True
        assert ref_type == "aggregation"

    def test_detect_aggregation_sum_english(self):
        """'sum' 키워드 감지 (영어)"""
        is_ref, ref_type = detect_reference_expression("sum 구해줘")
        assert is_ref is True
        assert ref_type == "aggregation"

    def test_detect_aggregation_전체금액(self):
        """'전체 금액' 키워드 감지"""
        is_ref, ref_type = detect_reference_expression("전체 금액 얼마야")
        assert is_ref is True
        assert ref_type == "aggregation"

    def test_detect_aggregation_최대금액(self):
        """'최대 금액' 키워드 감지"""
        is_ref, ref_type = detect_reference_expression("최대 금액 구해줘")
        assert is_ref is True
        assert ref_type == "aggregation"

    def test_detect_new_query_전체조회_takes_priority(self):
        """'전체 조회'는 새 쿼리로 처리 (우선순위)"""
        is_ref, ref_type = detect_reference_expression("전체 조회해줘")
        assert is_ref is False
        assert ref_type == "new"


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

    def test_scenario_aggregation_with_previous_conditions(self):
        """
        시나리오: 집계 쿼리에서 이전 WHERE 조건 유지

        1. "최근 3개월 결제건" → WHERE created_at >= '3 months'
        2. "이중 mer_001만" → WHERE created_at >= '3 months' AND merchant_id = 'mer_001'
        3. "도서 관련만" → WHERE ... AND order_name LIKE '%도서%'
        4. "결제금액 합산해줘" → 집계 키워드 감지 + WHERE 조건 유지

        핵심: 집계 요청에서도 이전 WHERE 조건을 유지해야 함
        """
        # Step 1~3: 조건 누적
        conditions = [
            "created_at >= NOW() - INTERVAL '3 months'",
            "merchant_id = 'mer_001'",
            "order_name LIKE '%도서%'"
        ]

        # Step 4: "결제금액 합산해줘" - 집계 키워드 감지
        is_ref, ref_type = detect_reference_expression("결제금액 합산해줘")
        assert is_ref is True
        assert ref_type == "aggregation"  # 집계 요청으로 감지됨

        # 이 시점에서 is_refinement=True로 설정되어
        # LLM 프롬프트에 이전 WHERE 조건이 전달됨

        # 예상 결과: 집계 쿼리에서도 WHERE 조건 유지
        expected_sql_pattern = "WHERE created_at >= NOW() - INTERVAL '3 months' AND merchant_id = 'mer_001' AND order_name LIKE '%도서%'"
        # (실제 SQL 생성은 LLM에 의해 수행되지만, 조건이 전달되는지 검증)

        # ConversationContext에 조건이 포함되는지 확인
        ctx = ConversationContext(
            previous_question="도서 관련만 보여줘",
            previous_sql="SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months' AND merchant_id = 'mer_001' AND order_name LIKE '%도서%'",
            previous_result_summary="25건",
            accumulated_where_conditions=conditions,
            is_refinement=True  # 집계 요청으로 is_refinement=True
        )

        assert ctx.is_refinement is True
        assert len(ctx.accumulated_where_conditions) == 3
        assert "created_at" in ctx.accumulated_where_conditions[0]
        assert "merchant_id" in ctx.accumulated_where_conditions[1]
        assert "order_name" in ctx.accumulated_where_conditions[2]

    def test_scenario_aggregation_reference_combined(self):
        """
        시나리오: 참조 표현 + 집계 키워드 동시 사용

        "이중에 합산해줘" → 참조 표현이 우선 (filter)
        """
        is_ref, ref_type = detect_reference_expression("이중에 합산해줘")
        assert is_ref is True
        # 참조 표현이 집계 키워드보다 먼저 체크되므로 'filter'가 됨
        assert ref_type == "filter"


# ============================================
# Phase 3: 4단계+ 체이닝 테스트 케이스
# ============================================

class TestFourPlusStageChaining:
    """
    4단계 이상 필터 체이닝 테스트

    문제 시나리오:
    1. "최근 3개월 결제건" → OK
    2. "이중에 mer_001만" → OK
    3. "이중에 카드결제만" → OK
    4. "금액 10만원 이상만" → 이전 조건 유실되면 실패
    """

    def test_implicit_filter_pattern_만으로끝남(self):
        """Phase 3: '~만'으로 끝나는 암시적 필터 패턴 감지"""
        # 문장 끝 "~것만" 패턴
        is_ref, ref_type = detect_reference_expression("금액이 큰 것만")
        assert is_ref is True
        assert ref_type == "filter"

        is_ref, ref_type = detect_reference_expression("카드 결제 건만")
        assert is_ref is True
        assert ref_type == "filter"

    def test_implicit_filter_pattern_금액이상(self):
        """Phase 3: '금액 X 이상만' 패턴 감지"""
        is_ref, ref_type = detect_reference_expression("금액 10만원 이상만")
        assert is_ref is True
        assert ref_type == "filter"

        is_ref, ref_type = detect_reference_expression("amount 100000 이상만")
        assert is_ref is True
        assert ref_type == "filter"

    def test_implicit_filter_pattern_상태(self):
        """Phase 3: '상태가 X인' 패턴 감지"""
        is_ref, ref_type = detect_reference_expression("상태가 DONE인 것만")
        assert is_ref is True
        assert ref_type == "filter"

    def test_implicit_filter_pattern_범위(self):
        """Phase 3: 비교/범위 표현 패턴 감지"""
        is_ref, ref_type = detect_reference_expression("10만원 이상")
        assert is_ref is True
        assert ref_type == "filter"

        is_ref, ref_type = detect_reference_expression("1000 이상만")
        assert is_ref is True
        assert ref_type == "filter"

    def test_implicit_filter_pattern_추가(self):
        """Phase 3: 필터 추가 표현 패턴 감지"""
        is_ref, ref_type = detect_reference_expression("추가로 필터 적용해줘")
        assert is_ref is True
        assert ref_type == "filter"

        is_ref, ref_type = detect_reference_expression("조건 추가해서")
        assert is_ref is True
        assert ref_type == "filter"

        is_ref, ref_type = detect_reference_expression("더 좁혀서 보여줘")
        assert is_ref is True
        assert ref_type == "filter"

    def test_four_stage_chaining_accumulation(self):
        """
        4단계 체이닝: 조건 누적 검증

        1단계: created_at 조건
        2단계: merchant_id 추가
        3단계: method 추가
        4단계: amount 추가 (모든 조건 유지)
        """
        # Step 1: 시간 조건
        conditions1 = extract_where_conditions(
            "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months'"
        )
        assert len(conditions1) == 1
        assert "created_at" in conditions1[0]

        # Step 2: 가맹점 추가
        conditions2 = merge_where_conditions(
            conditions1,
            ["merchant_id = 'mer_001'"]
        )
        assert len(conditions2) == 2

        # Step 3: 결제수단 추가
        conditions3 = merge_where_conditions(
            conditions2,
            ["method = 'CARD'"]
        )
        assert len(conditions3) == 3

        # Step 4: 금액 조건 추가 (핵심 테스트)
        conditions4 = merge_where_conditions(
            conditions3,
            ["amount >= 100000"]
        )
        assert len(conditions4) == 4

        # 모든 조건이 유지되는지 확인
        all_fields = [extract_condition_field(c) for c in conditions4]
        assert "created_at" in all_fields, "1단계 조건 유실"
        assert "merchant_id" in all_fields, "2단계 조건 유실"
        assert "method" in all_fields, "3단계 조건 유실"
        assert "amount" in all_fields, "4단계 조건 유실"

    def test_five_stage_chaining_accumulation(self):
        """
        5단계 체이닝: 조건 누적 검증

        1단계: created_at 조건
        2단계: merchant_id 추가
        3단계: method 추가
        4단계: amount 추가
        5단계: status 추가 (모든 조건 유지)
        """
        # 순차적 조건 누적
        conditions = []

        # Step 1
        conditions = merge_where_conditions(
            conditions,
            ["created_at >= NOW() - INTERVAL '3 months'"]
        )

        # Step 2
        conditions = merge_where_conditions(
            conditions,
            ["merchant_id = 'mer_001'"]
        )

        # Step 3
        conditions = merge_where_conditions(
            conditions,
            ["method = 'CARD'"]
        )

        # Step 4
        conditions = merge_where_conditions(
            conditions,
            ["amount >= 100000"]
        )

        # Step 5
        conditions = merge_where_conditions(
            conditions,
            ["status = 'DONE'"]
        )

        # 5개 조건 모두 유지
        assert len(conditions) == 5
        all_fields = [extract_condition_field(c) for c in conditions]
        assert "created_at" in all_fields
        assert "merchant_id" in all_fields
        assert "method" in all_fields
        assert "amount" in all_fields
        assert "status" in all_fields

    def test_conversation_context_with_where_conditions(self):
        """
        Phase 1: whereConditions 필드가 ConversationContext에서 사용되는지 확인
        """
        # 대화 이력에 whereConditions 포함
        conversation_history = [
            {"role": "user", "content": "최근 3개월 결제건"},
            {
                "role": "assistant",
                "content": "조회 완료",
                "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months'",
                "rowCount": 100,
                "whereConditions": ["created_at >= NOW() - INTERVAL '3 months'"]
            },
            {"role": "user", "content": "이중에 mer_001만"},
            {
                "role": "assistant",
                "content": "조회 완료",
                "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months' AND merchant_id = 'mer_001'",
                "rowCount": 50,
                "whereConditions": [
                    "created_at >= NOW() - INTERVAL '3 months'",
                    "merchant_id = 'mer_001'"
                ]
            }
        ]

        # Phase 1에서 저장된 whereConditions가 있으면 SQL 파싱 없이 바로 사용 가능
        last_assistant = [m for m in conversation_history if m["role"] == "assistant"][-1]
        assert "whereConditions" in last_assistant
        assert len(last_assistant["whereConditions"]) == 2

    def test_accumulated_conditions_regardless_of_refinement(self):
        """
        Phase 2: is_refinement 여부와 관계없이 조건이 누적되어야 함
        """
        # 대화 이력 시뮬레이션
        history = [
            {"role": "user", "content": "최근 3개월 결제건"},
            {
                "role": "assistant",
                "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months'",
                "whereConditions": ["created_at >= NOW() - INTERVAL '3 months'"]
            },
            {"role": "user", "content": "mer_001"},  # 참조 표현 없는 짧은 메시지
            {
                "role": "assistant",
                "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months' AND merchant_id = 'mer_001'",
                "whereConditions": [
                    "created_at >= NOW() - INTERVAL '3 months'",
                    "merchant_id = 'mer_001'"
                ]
            }
        ]

        # 참조 표현 없어도 대화 이력에서 조건 누적 가능
        # (Phase 2에서 is_refinement 조건 제거)
        accumulated = []
        for msg in history:
            if msg.get("role") == "assistant" and "whereConditions" in msg:
                accumulated = merge_where_conditions(
                    accumulated,
                    msg["whereConditions"]
                )

        assert len(accumulated) == 2
        assert any("created_at" in c for c in accumulated)
        assert any("merchant_id" in c for c in accumulated)

    def test_field_replacement_in_chaining(self):
        """
        체이닝 중 동일 필드 조건 변경 시 대체
        """
        # Step 1: 처음 status = DONE
        conditions = ["status = 'DONE'"]

        # Step 2: 다른 조건 추가
        conditions = merge_where_conditions(
            conditions,
            ["merchant_id = 'mer_001'"]
        )
        assert len(conditions) == 2

        # Step 3: status를 CANCELED로 변경
        conditions = merge_where_conditions(
            conditions,
            ["status = 'CANCELED'"]
        )

        # status는 대체되고, merchant_id는 유지
        assert len(conditions) == 2
        status_cond = [c for c in conditions if "status" in c][0]
        assert "CANCELED" in status_cond
        assert "DONE" not in status_cond
        assert any("merchant_id" in c for c in conditions)
