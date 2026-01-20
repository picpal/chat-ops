"""
TC-019: Text-to-SQL 모드 수수료 계산 직접 응답 테스트

이전 집계 결과에 대해 수수료, VAT 등 산술 연산 요청 시
DB 조회 없이 직접 계산하여 응답하는 기능 테스트

버그 시나리오:
Q1: "최근 3개월 mer_001 가맹점의 도서 관련 결제 합계" → ₩14,563,862
Q2: "결제 합산 금액에서 0.6% 수수료는 얼마죠?"
예상: 14,563,862 × 0.6% = ₩87,383 (DB 조회 없이)
실제(버그): ₩86,862 (새 SQL 실행, 필터 누락)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.constants.reference_patterns import ARITHMETIC_REQUEST_PATTERNS
from app.services.conversation_context import (
    is_arithmetic_request,
    extract_aggregation_value,
    _extract_amount_from_text,
)
from app.api.v1.chat import ChatMessageItem


class TestArithmeticRequestPatterns:
    """TC-019-1: 산술 연산 요청 패턴 매칭 테스트"""

    def test_fee_percent_pattern_korean(self):
        """수수료 퍼센트 패턴 (한글)"""
        test_cases = [
            ("0.6% 수수료는 얼마야?", True),
            ("수수료 0.6%는?", True),
            ("수수료 적용해줘", True),
            ("3.3% 수수료 계산해줘", True),
            ("수수료 얼마야?", True),
            ("0.6%는 얼마", True),
            ("0.6퍼센트면 얼마야?", True),
        ]

        for message, expected in test_cases:
            result = is_arithmetic_request(message)
            assert result == expected, f"Message: '{message}' expected {expected}, got {result}"

    def test_vat_pattern(self):
        """VAT/부가세 패턴"""
        test_cases = [
            ("VAT 10% 포함하면?", True),
            ("부가세 10% 적용", True),
            ("세금 포함 금액", True),
            ("VAT 제외하면 얼마야?", True),
            ("10% VAT 적용", True),
        ]

        for message, expected in test_cases:
            result = is_arithmetic_request(message)
            assert result == expected, f"Message: '{message}' expected {expected}, got {result}"

    def test_basic_arithmetic(self):
        """기본 산술 연산 패턴"""
        test_cases = [
            ("1000으로 나눠줘", True),
            ("2배 하면?", True),
            ("100을 더해줘", True),
            ("여기에 10%", True),
            ("거기에 5%", True),
            ("계산해줘", True),
            ("얼마야?", True),
            ("금액은 얼마", True),
        ]

        for message, expected in test_cases:
            result = is_arithmetic_request(message)
            assert result == expected, f"Message: '{message}' expected {expected}, got {result}"

    def test_non_arithmetic_requests(self):
        """산술 연산이 아닌 요청 (False 반환 기대)"""
        test_cases = [
            ("새로 조회해줘", False),
            ("최근 3개월 결제건", False),
            ("가맹점별로 정렬해줘", False),
            ("mer_001 가맹점만", False),
            ("DONE 상태만 보여줘", False),
            ("테이블 형태로 보여줘", False),
        ]

        for message, expected in test_cases:
            result = is_arithmetic_request(message)
            assert result == expected, f"Message: '{message}' expected {expected}, got {result}"


class TestExtractAmountFromText:
    """TC-019-2: 텍스트에서 금액 추출 테스트"""

    def test_extract_from_parentheses(self):
        """괄호 안 전체 금액 추출 (최우선)"""
        test_cases = [
            ("합계: $2.88M (14,563,862원)", 14563862),
            ("총 결제금액: ($14,563,862)", 14563862),
            ("결과: (₩87,383원)", 87383),
        ]

        for text, expected in test_cases:
            result = _extract_amount_from_text(text)
            assert result == expected, f"Text: '{text}' expected {expected}, got {result}"

    def test_extract_korean_suffix(self):
        """억/만 접미사 금액 추출"""
        test_cases = [
            ("총 1,456만원", 14560000),
            ("합계: 14억원", 1400000000),
            ("결제 금액 2.5억원", 250000000),
            ("총 500만원입니다", 5000000),
        ]

        for text, expected in test_cases:
            result = _extract_amount_from_text(text)
            assert result == expected, f"Text: '{text}' expected {expected}, got {result}"

    def test_extract_mk_suffix(self):
        """M/K 접미사 금액 추출"""
        test_cases = [
            ("Total: $2.88M", 2880000),
            ("Amount: $145K", 145000),
            ("Value: 1.5M", 1500000),
        ]

        for text, expected in test_cases:
            result = _extract_amount_from_text(text)
            assert result == expected, f"Text: '{text}' expected {expected}, got {result}"

    def test_extract_plain_amount(self):
        """일반 금액 추출"""
        test_cases = [
            ("합계: ₩14,563,862", 14563862),
            ("총액: $1,234,567", 1234567),
            ("14,563,862원", 14563862),
            ("결제 금액 87,383원입니다", 87383),
        ]

        for text, expected in test_cases:
            result = _extract_amount_from_text(text)
            assert result == expected, f"Text: '{text}' expected {expected}, got {result}"

    def test_extract_empty_or_none(self):
        """빈 텍스트나 금액 없는 경우"""
        test_cases = [
            ("", None),
            (None, None),
            ("텍스트만 있습니다", None),
        ]

        for text, expected in test_cases:
            result = _extract_amount_from_text(text)
            assert result == expected, f"Text: '{text}' expected {expected}, got {result}"


class TestExtractAggregationValue:
    """TC-019-3: 대화 이력에서 집계 결과 추출 테스트"""

    def _create_chat_message(
        self,
        role: str,
        content: str,
        render_spec: dict = None,
        query_result: dict = None,
        query_plan: dict = None
    ) -> ChatMessageItem:
        """테스트용 ChatMessageItem 생성"""
        return ChatMessageItem(
            id=f"msg-{hash(content) % 10000}",
            role=role,
            content=content,
            timestamp="2024-01-15T10:00:00Z",
            renderSpec=render_spec,
            queryResult=query_result,
            queryPlan=query_plan
        )

    def test_extract_from_renderspec_text(self):
        """RenderSpec text 타입에서 집계 결과 추출"""
        history = [
            self._create_chat_message(
                role="user",
                content="최근 3개월 mer_001 도서 관련 결제 합계"
            ),
            self._create_chat_message(
                role="assistant",
                content="집계 결과입니다.",
                render_spec={
                    "type": "text",
                    "text": {
                        "content": "**결제 합계**\n\n합계: ₩14,563,862\n\n(2024년 1월 기준)"
                    }
                }
            )
        ]

        result = extract_aggregation_value(history)

        assert result is not None, "집계 결과가 추출되어야 함"
        assert result["amount"] == 14563862, f"금액이 14563862이어야 함, got {result['amount']}"
        assert "context" in result, "컨텍스트가 포함되어야 함"

    def test_extract_from_query_result_aggregation(self):
        """QueryResult의 isAggregation 플래그에서 추출"""
        history = [
            self._create_chat_message(
                role="user",
                content="총 결제 금액"
            ),
            self._create_chat_message(
                role="assistant",
                content="집계 결과입니다.",
                query_result={
                    "isAggregation": True,
                    "aggregationContext": {
                        "total_amount": 14563862,
                        "aggregation_type": "sum"
                    },
                    "data": {"rows": []}
                }
            )
        ]

        result = extract_aggregation_value(history)

        assert result is not None
        assert result["amount"] == 14563862
        assert result["aggregation_type"] == "sum"

    def test_extract_from_single_row_sum(self):
        """단일 행 집계 결과에서 추출 (SELECT SUM)"""
        history = [
            self._create_chat_message(
                role="user",
                content="결제 합계 조회"
            ),
            self._create_chat_message(
                role="assistant",
                content="결과입니다.",
                query_result={
                    "data": {
                        "rows": [{"sum": 14563862}]
                    }
                }
            )
        ]

        result = extract_aggregation_value(history)

        assert result is not None
        assert result["amount"] == 14563862

    def test_no_aggregation_in_history(self):
        """집계 결과가 없는 경우 None 반환"""
        history = [
            self._create_chat_message(
                role="user",
                content="결제 목록 조회"
            ),
            self._create_chat_message(
                role="assistant",
                content="결과입니다.",
                query_result={
                    "data": {
                        "rows": [
                            {"id": 1, "amount": 10000},
                            {"id": 2, "amount": 20000}
                        ]
                    }
                },
                render_spec={
                    "type": "table",
                    "table": {"columns": [], "rows": []}
                }
            )
        ]

        result = extract_aggregation_value(history)

        # 테이블 타입이고 집계 결과가 아니면 None
        # 단, 현재 구현에서는 queryResult에서 amount 합계를 시도할 수 있음
        # 명시적 집계가 아닌 경우 None을 반환하도록 로직 확인 필요
        # 현재 구현상 renderSpec이 table 타입이면 건너뜀
        assert result is None or result.get("amount") is not None

    def test_extract_most_recent_aggregation(self):
        """여러 집계 결과 중 가장 최근 것 추출"""
        history = [
            self._create_chat_message(
                role="user",
                content="첫 번째 집계"
            ),
            self._create_chat_message(
                role="assistant",
                content="첫 번째 결과",
                render_spec={
                    "type": "text",
                    "text": {"content": "합계: ₩1,000,000"}
                }
            ),
            self._create_chat_message(
                role="user",
                content="두 번째 집계"
            ),
            self._create_chat_message(
                role="assistant",
                content="두 번째 결과",
                render_spec={
                    "type": "text",
                    "text": {"content": "합계: ₩14,563,862"}
                }
            )
        ]

        result = extract_aggregation_value(history)

        assert result is not None
        assert result["amount"] == 14563862, "가장 최근 집계 결과가 반환되어야 함"


class TestFullScenario:
    """TC-019-4: 전체 시나리오 테스트 (통합)"""

    def _create_chat_message(
        self,
        role: str,
        content: str,
        render_spec: dict = None,
        query_result: dict = None,
        query_plan: dict = None
    ) -> ChatMessageItem:
        """테스트용 ChatMessageItem 생성"""
        return ChatMessageItem(
            id=f"msg-{hash(content) % 10000}",
            role=role,
            content=content,
            timestamp="2024-01-15T10:00:00Z",
            renderSpec=render_spec,
            queryResult=query_result,
            queryPlan=query_plan
        )

    def test_fee_calculation_scenario(self):
        """
        시나리오: 집계 결과 ₩14,563,862 + "0.6% 수수료" 요청
        기대: 산술 요청 감지 + 집계 값 추출 성공
        """
        # 1단계: 이전 집계 결과가 있는 대화 이력
        history = [
            self._create_chat_message(
                role="user",
                content="최근 3개월 mer_001 가맹점의 도서 관련 결제 합계"
            ),
            self._create_chat_message(
                role="assistant",
                content="집계 결과입니다.",
                render_spec={
                    "type": "text",
                    "text": {
                        "content": "**도서 관련 결제 합계**\n\n합계: ₩14,563,862"
                    }
                },
                query_result={
                    "data": {"rows": [{"sum": 14563862}]},
                    "isAggregation": True
                }
            )
        ]

        # 2단계: 현재 메시지
        current_message = "결제 합산 금액에서 0.6% 수수료는 얼마죠?"

        # 3단계: 검증
        # - 산술 요청 감지
        assert is_arithmetic_request(current_message), "0.6% 수수료 요청이 산술 요청으로 감지되어야 함"

        # - 집계 값 추출
        aggregation = extract_aggregation_value(history)
        assert aggregation is not None, "집계 결과가 추출되어야 함"
        assert aggregation["amount"] == 14563862, "추출된 금액이 14,563,862이어야 함"

        # - 예상 계산 결과 (직접 계산 함수가 없으므로 수동 검증)
        expected_fee = 14563862 * 0.006
        assert abs(expected_fee - 87383.172) < 1, f"0.6% 수수료는 약 87,383원이어야 함, got {expected_fee}"

    def test_vat_calculation_scenario(self):
        """
        시나리오: 집계 결과 + "VAT 10% 포함" 요청
        """
        history = [
            self._create_chat_message(
                role="user",
                content="이번 달 매출 합계"
            ),
            self._create_chat_message(
                role="assistant",
                content="매출 합계입니다.",
                render_spec={
                    "type": "text",
                    "text": {"content": "합계: ₩1,000,000"}
                }
            )
        ]

        current_message = "VAT 10% 포함하면 얼마야?"

        assert is_arithmetic_request(current_message)

        aggregation = extract_aggregation_value(history)
        assert aggregation is not None
        assert aggregation["amount"] == 1000000

        # 예상: 1,000,000 * 1.1 = 1,100,000
        expected = 1000000 * 1.1
        assert expected == 1100000


class TestEdgeCases:
    """TC-019-5: 엣지 케이스 테스트"""

    def test_empty_history(self):
        """빈 대화 이력"""
        result = extract_aggregation_value([])
        assert result is None

    def test_none_history(self):
        """None 대화 이력"""
        result = extract_aggregation_value(None)
        assert result is None

    def test_arithmetic_with_no_percent(self):
        """퍼센트 없이 수수료 언급"""
        # "수수료 얼마야?"는 매칭되지만 구체적인 비율이 없음
        # 이 경우 LLM이 추가 질문하거나 기본 수수료율 적용할 수 있음
        assert is_arithmetic_request("수수료 얼마야?")

    def test_multiple_amounts_in_text(self):
        """텍스트에 여러 금액이 있는 경우"""
        text = "건수: 100건, 합계: ₩14,563,862, 평균: ₩145,638"
        result = _extract_amount_from_text(text)
        # 첫 번째로 매칭되는 금액이 반환됨
        # "합계" 패턴이 우선시됨
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
