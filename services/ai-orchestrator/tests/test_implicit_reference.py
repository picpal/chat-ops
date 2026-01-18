"""
TC-005: 암시적 참조 표현 인식 테스트

"mer_008 가맹점만"처럼 명시적 키워드("이중", "여기서") 없이 필터 추가 요청 시에도
LLM이 올바르게 인식하도록 개선된 프롬프트 및 컨텍스트 빌더 테스트
"""

import pytest
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.text_to_sql import (
    TextToSqlService,
    ConversationContext,
    extract_where_conditions,
    humanize_where_condition,
)


class TestImplicitReferencePrompt:
    """TC-005-1: 암시적 참조 표현 가이드라인이 프롬프트에 포함되는지 테스트"""

    @pytest.fixture
    def service(self):
        """TextToSqlService 인스턴스 (LLM 호출 없이 프롬프트 테스트용)"""
        return TextToSqlService()

    def test_prompt_contains_implicit_reference_guidelines(self, service):
        """프롬프트에 암시적 참조 가이드라인이 포함되는지 확인"""
        prompt = service._build_prompt(
            question="mer_008 가맹점만",
            conversation_context=None,
            rag_context=""
        )

        # 암시적 참조 표현 가이드라인 키워드 확인
        assert "암시적 참조 표현" in prompt, "암시적 참조 표현 가이드라인이 프롬프트에 없음"
        assert "[값] ~만" in prompt, "'[값] ~만' 패턴 가이드라인이 프롬프트에 없음"
        assert "refinement 판단 기준" in prompt, "refinement 판단 기준이 프롬프트에 없음"

    def test_prompt_contains_implicit_reference_examples(self, service):
        """프롬프트에 암시적 참조 예시가 포함되는지 확인"""
        prompt = service._build_prompt(
            question="DONE 상태만",
            conversation_context=None,
            rag_context=""
        )

        # 예시 패턴 확인
        expected_patterns = [
            "mer_008 가맹점만",
            "DONE 상태만",
            "10만원 이상만"
        ]
        for pattern in expected_patterns:
            assert pattern in prompt, f"'{pattern}' 예시가 프롬프트에 없음"


class TestConversationFlowBuilder:
    """TC-005-2: 대화 컨텍스트 빌더가 직전 쿼리 정보를 올바르게 표시하는지 테스트"""

    @pytest.fixture
    def service(self):
        return TextToSqlService()

    def test_conversation_flow_shows_last_query_summary(self, service):
        """직전 쿼리 요약 섹션이 표시되는지 확인"""
        context = ConversationContext(
            previous_question="최근 3개월 결제건 조회",
            previous_sql="SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months' LIMIT 1000;",
            previous_result_summary="1000건 조회됨",
            accumulated_where_conditions=["created_at >= NOW() - INTERVAL '3 months'"],
            is_refinement=False,
            conversation_history=[
                {"role": "user", "content": "최근 3개월 결제건 조회"},
                {
                    "role": "assistant",
                    "content": "결과입니다",
                    "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months' LIMIT 1000;",
                    "rowCount": 1000,
                    "whereConditions": ["created_at >= NOW() - INTERVAL '3 months'"]
                }
            ]
        )

        flow = service._build_conversation_flow(context)

        # 직전 쿼리 요약 섹션 확인
        assert "직전 쿼리 요약" in flow, "직전 쿼리 요약 섹션이 없음"
        assert "refinement 판단용" in flow, "refinement 판단용 안내가 없음"
        assert "payments" in flow, "테이블명이 표시되지 않음"

    def test_conversation_flow_shows_where_conditions_humanized(self, service):
        """WHERE 조건이 사람이 읽기 쉬운 형태로 표시되는지 확인"""
        context = ConversationContext(
            previous_question="최근 1개월 결제건",
            previous_sql="SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '1 months' LIMIT 1000;",
            previous_result_summary="500건 조회됨",
            accumulated_where_conditions=["created_at >= NOW() - INTERVAL '1 months'"],
            is_refinement=False,
            conversation_history=[
                {"role": "user", "content": "최근 1개월 결제건"},
                {
                    "role": "assistant",
                    "content": "결과입니다",
                    "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '1 months' LIMIT 1000;",
                    "rowCount": 500,
                    "whereConditions": ["created_at >= NOW() - INTERVAL '1 months'"]
                }
            ]
        )

        flow = service._build_conversation_flow(context)

        # 사람이 읽기 쉬운 형태 확인 (humanize 함수 결과)
        assert "기간: 최근 1개월" in flow, "humanized 조건이 표시되지 않음"

    def test_conversation_flow_guidance_message(self, service):
        """암시적 참조 판단 안내 메시지가 포함되는지 확인"""
        context = ConversationContext(
            previous_question="오늘 결제 내역",
            previous_sql="SELECT * FROM payments WHERE created_at >= '2024-01-15' LIMIT 1000;",
            previous_result_summary="200건 조회됨",
            accumulated_where_conditions=["created_at >= '2024-01-15'"],
            is_refinement=False,
            conversation_history=[
                {"role": "user", "content": "오늘 결제 내역"},
                {
                    "role": "assistant",
                    "content": "결과입니다",
                    "sql": "SELECT * FROM payments WHERE created_at >= '2024-01-15' LIMIT 1000;",
                    "rowCount": 200,
                    "whereConditions": ["created_at >= '2024-01-15'"]
                }
            ]
        )

        flow = service._build_conversation_flow(context)

        # 안내 메시지 확인
        assert "현재 질문이 위 결과를 필터링하는 것인지 판단" in flow
        assert "짧은 필터 표현" in flow
        assert "refinement일 가능성이 높습니다" in flow


class TestHumanizeWhereCondition:
    """TC-005-3: WHERE 조건 humanize 함수 테스트"""

    def test_humanize_interval_condition(self):
        """INTERVAL 조건 humanize 테스트"""
        # 3개월
        cond = "created_at >= NOW() - INTERVAL '3 months'"
        result = humanize_where_condition(cond)
        assert "최근 3개월" in result

        # 1일
        cond = "created_at >= NOW() - INTERVAL '1 day'"
        result = humanize_where_condition(cond)
        assert "최근 1일" in result

    def test_humanize_equality_condition(self):
        """등호 조건 humanize 테스트"""
        cond = "status = 'DONE'"
        result = humanize_where_condition(cond)
        assert "상태" in result
        assert "완료" in result

    def test_humanize_merchant_condition(self):
        """가맹점 조건 humanize 테스트"""
        cond = "merchant_id = 'mer_008'"
        result = humanize_where_condition(cond)
        assert "가맹점" in result
        assert "mer_008" in result

    def test_humanize_amount_condition(self):
        """금액 조건 humanize 테스트"""
        cond = "amount >= 100000"
        result = humanize_where_condition(cond)
        assert "금액" in result
        assert "이상" in result


class TestFullPromptWithConversation:
    """TC-005-4: 대화 컨텍스트가 있을 때 전체 프롬프트 테스트"""

    @pytest.fixture
    def service(self):
        return TextToSqlService()

    def test_full_prompt_with_previous_query(self, service):
        """
        시나리오: "최근 3개월 결제건 조회" 후 "mer_008 가맹점만"
        기대: 프롬프트에 이전 WHERE 조건과 암시적 참조 가이드라인이 모두 포함
        """
        context = ConversationContext(
            previous_question="최근 3개월 결제건 조회",
            previous_sql="SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months' LIMIT 1000;",
            previous_result_summary="1000건 조회됨",
            accumulated_where_conditions=["created_at >= NOW() - INTERVAL '3 months'"],
            is_refinement=False,
            conversation_history=[
                {"role": "user", "content": "최근 3개월 결제건 조회"},
                {
                    "role": "assistant",
                    "content": "결과입니다",
                    "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '3 months' LIMIT 1000;",
                    "rowCount": 1000,
                    "whereConditions": ["created_at >= NOW() - INTERVAL '3 months'"]
                }
            ]
        )

        prompt = service._build_prompt(
            question="mer_008 가맹점만",
            conversation_context=context,
            rag_context=""
        )

        # 1. 암시적 참조 가이드라인 포함 확인
        assert "암시적 참조 표현" in prompt

        # 2. 직전 쿼리 정보 포함 확인
        assert "직전 쿼리 요약" in prompt
        assert "payments" in prompt

        # 3. 이전 WHERE 조건 포함 확인
        assert "INTERVAL '3 months'" in prompt

        # 4. 현재 질문 포함 확인
        assert "mer_008 가맹점만" in prompt

    def test_full_prompt_scenarios(self, service):
        """
        다양한 암시적 참조 시나리오 테스트
        """
        scenarios = [
            {
                "previous": "최근 1개월 결제건",
                "previous_sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '1 months' LIMIT 1000;",
                "current": "mer_008 가맹점만",
                "expected_in_prompt": ["payments", "1 months", "mer_008"]
            },
            {
                "previous": "오늘 결제 내역",
                "previous_sql": "SELECT * FROM payments WHERE created_at >= CURRENT_DATE LIMIT 1000;",
                "current": "DONE 상태만",
                "expected_in_prompt": ["payments", "DONE 상태"]
            },
            {
                "previous": "이번 달 매출",
                "previous_sql": "SELECT * FROM payments WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE) LIMIT 1000;",
                "current": "10만원 이상만",
                "expected_in_prompt": ["payments", "10만원"]
            },
        ]

        for scenario in scenarios:
            context = ConversationContext(
                previous_question=scenario["previous"],
                previous_sql=scenario["previous_sql"],
                previous_result_summary="100건 조회됨",
                accumulated_where_conditions=[],
                is_refinement=False,
                conversation_history=[
                    {"role": "user", "content": scenario["previous"]},
                    {
                        "role": "assistant",
                        "content": "결과입니다",
                        "sql": scenario["previous_sql"],
                        "rowCount": 100
                    }
                ]
            )

            prompt = service._build_prompt(
                question=scenario["current"],
                conversation_context=context,
                rag_context=""
            )

            for expected in scenario["expected_in_prompt"]:
                assert expected in prompt, \
                    f"'{expected}'가 프롬프트에 없음. 시나리오: {scenario['previous']} -> {scenario['current']}"


class TestExtractTableFromSql:
    """TC-005-5: SQL에서 테이블명 추출 테스트"""

    def test_extract_table_from_simple_select(self):
        """간단한 SELECT문에서 테이블명 추출"""
        sql = "SELECT * FROM payments WHERE created_at >= NOW() LIMIT 100;"
        match = re.search(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
        assert match is not None
        assert match.group(1) == "payments"

    def test_extract_table_from_join(self):
        """JOIN이 있는 SQL에서 메인 테이블명 추출"""
        sql = """
        SELECT p.*, m.business_name
        FROM payments p
        JOIN merchants m ON p.merchant_id = m.merchant_id
        WHERE p.status = 'DONE'
        """
        match = re.search(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
        assert match is not None
        assert match.group(1) == "payments"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
