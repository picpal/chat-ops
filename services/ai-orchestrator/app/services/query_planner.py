"""
QueryPlannerService: 자연어를 QueryPlan으로 변환
LangChain + OpenAI를 사용한 Structured Output
RAG 컨텍스트를 활용한 향상된 쿼리 생성
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)


# ============================================
# Operator Normalization (LLM 오류 방어)
# ============================================

OPERATOR_ALIASES = {
    ">=": "gte",
    ">": "gt",
    "<=": "lte",
    "<": "lt",
    "=": "eq",
    "==": "eq",
    "!=": "ne",
    "<>": "ne",
    "LIKE": "like",
    "IN": "in",
    "BETWEEN": "between",
}


def normalize_operator(operator: str) -> str:
    """
    잘못된 operator를 정규화
    LLM이 '>=' 같은 기호를 반환할 경우 'gte'로 변환
    """
    if operator in OPERATOR_ALIASES:
        normalized = OPERATOR_ALIASES[operator]
        logger.warning(f"Operator normalized: '{operator}' -> '{normalized}'")
        return normalized
    return operator.lower() if operator else operator


def escape_template_braces(text: str) -> str:
    """
    LangChain ChatPromptTemplate 변수 충돌 방지

    RAG 문서나 대화 컨텍스트에 포함된 JSON의 중괄호 {, }를
    템플릿 변수로 해석되지 않도록 {{ }} 로 이스케이프합니다.

    예: {"limits": 100} → {{"limits": 100}}
    """
    if not text:
        return text
    return text.replace("{", "{{").replace("}", "}}")


# ============================================
# Pydantic Models for Structured Output
# ============================================

class EntityType(str, Enum):
    # 기존 e-commerce 엔티티
    ORDER = "Order"
    # PG 결제 도메인 엔티티
    MERCHANT = "Merchant"
    PG_CUSTOMER = "PgCustomer"
    PAYMENT_METHOD = "PaymentMethod"
    PAYMENT = "Payment"
    PAYMENT_HISTORY = "PaymentHistory"
    REFUND = "Refund"
    BALANCE_TRANSACTION = "BalanceTransaction"
    SETTLEMENT = "Settlement"
    SETTLEMENT_DETAIL = "SettlementDetail"


class OperationType(str, Enum):
    LIST = "list"
    AGGREGATE = "aggregate"
    SEARCH = "search"


class QueryIntent(str, Enum):
    """사용자 질문의 의도"""
    NEW_QUERY = "new_query"              # 새로운 검색 (이전 컨텍스트 무시)
    REFINE_PREVIOUS = "refine_previous"  # 서버 재조회 (조건 변경)
    FILTER_LOCAL = "filter_local"        # 클라이언트에서 이전 결과 필터링
    AGGREGATE_LOCAL = "aggregate_local"  # 클라이언트에서 이전 결과 집계
    DIRECT_ANSWER = "direct_answer"      # LLM이 직접 답변 (DB 조회 없이)


class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    LIKE = "like"
    BETWEEN = "between"


class Filter(BaseModel):
    field: str = Field(description="논리 필드명 (예: status, customerId, orderDate)")
    operator: FilterOperator = Field(description="비교 연산자")
    value: Any = Field(description="비교 값")


class Aggregation(BaseModel):
    function: str = Field(description="집계 함수: count, sum, avg, min, max")
    field: str = Field(description="집계 대상 필드 (* 가능)")
    alias: Optional[str] = Field(default=None, description="결과 별칭")
    displayLabel: Optional[str] = Field(default=None, description="사용자에게 표시할 한글 레이블 (예: '결제 금액 합계')")
    currency: Optional[str] = Field(default=None, description="화폐 단위: KRW, USD, null(화폐 아님)")


class OrderBy(BaseModel):
    field: str = Field(description="정렬 필드")
    direction: str = Field(default="desc", description="정렬 방향: asc 또는 desc")


class TimeRange(BaseModel):
    start: str = Field(description="시작 시간 (ISO 8601)")
    end: str = Field(description="종료 시간 (ISO 8601)")


class QueryPlan(BaseModel):
    """AI가 생성하는 QueryPlan 구조"""
    entity: Optional[EntityType] = Field(default=None, description="조회할 엔티티")
    operation: OperationType = Field(default="list", description="작업 유형")
    filters: Optional[List[Filter]] = Field(default=None, description="필터 조건")
    aggregations: Optional[List[Aggregation]] = Field(default=None, description="집계 조건 (operation=aggregate일 때)")
    group_by: Optional[List[str]] = Field(default=None, description="그룹화 필드")
    order_by: Optional[List[OrderBy]] = Field(default=None, description="정렬 조건")
    limit: int = Field(default=10, ge=1, le=100, description="최대 조회 개수")
    time_range: Optional[TimeRange] = Field(default=None, description="시간 범위 (시계열 데이터)")
    # 의도 분류 필드 (LLM이 판단)
    query_intent: QueryIntent = Field(
        default=QueryIntent.NEW_QUERY,
        description="쿼리 의도: new_query(새 검색) 또는 refine_previous(이전 결과 필터링)"
    )
    # Clarification 필드 (LLM이 불확실할 때 사용)
    needs_clarification: bool = Field(default=False, description="추가 명확화 필요 여부")
    # 결과 선택 clarification (filter_local/aggregate_local에서 어떤 결과인지 모호할 때)
    needs_result_clarification: bool = Field(
        default=False,
        description="어떤 이전 결과를 대상으로 할지 모호할 때 true. 기본값 false면 직전 결과 사용"
    )
    clarification_question: Optional[str] = Field(default=None, description="사용자에게 할 질문")
    clarification_options: Optional[List[str]] = Field(default=None, description="선택지 (있는 경우)")
    # Direct Answer (DB 조회 없이 LLM이 직접 답변)
    direct_answer: Optional[str] = Field(
        default=None,
        description="query_intent가 direct_answer일 때, LLM이 생성한 답변 텍스트"
    )
    # 사용자가 명시적으로 요청한 렌더링 타입
    preferred_render_type: Optional[str] = Field(
        default=None,
        description="사용자가 명시한 렌더링 타입: 'table'(표로), 'chart'(그래프로), 'text'(텍스트로). 명시 없으면 null"
    )


# ============================================
# Intent Classification (2단계 분류용)
# ============================================

class IntentType(str, Enum):
    """1단계 분류: 질문 유형"""
    DIRECT_ANSWER = "direct_answer"    # 단순 계산/설명 → LLM 직접 답변
    QUERY_NEEDED = "query_needed"      # DB 조회 필요 → QueryPlan 생성
    FILTER_LOCAL = "filter_local"      # 이전 결과 필터링
    AGGREGATE_LOCAL = "aggregate_local"  # 이전 결과 집계


class IntentClassification(BaseModel):
    """1단계 Intent 분류 결과"""
    intent: IntentType = Field(description="분류된 의도")
    confidence: float = Field(description="확신도 (0.0 ~ 1.0)")
    reasoning: str = Field(description="판단 근거 (간단히)")
    direct_answer_text: Optional[str] = Field(
        default=None,
        description="intent가 direct_answer일 때, 생성된 답변"
    )


# ============================================
# Entity Schema Information (for Prompt)
# ============================================

ENTITY_SCHEMAS = {
    # ============================================
    # 기존 e-commerce 엔티티
    # ============================================
    "Order": {
        "description": "주문 정보",
        "fields": {
            "orderId": "주문 ID (정수)",
            "customerId": "고객 ID (정수)",
            "orderDate": "주문 일시 (날짜/시간)",
            "totalAmount": "총 주문 금액 (숫자)",
            "status": "주문 상태 (PENDING, PAID, SHIPPED, DELIVERED, CANCELLED)",
            "paymentGateway": "결제 수단 (Stripe, PayPal, Bank Transfer)"
        }
    },
    # ============================================
    # PG 결제 도메인 엔티티
    # ============================================
    "Payment": {
        "description": "결제 정보 - 결제 건별 상세 데이터 (timeRange 권장)",
        "fields": {
            "paymentKey": "결제 고유 키 (문자열)",
            "orderId": "주문번호 (문자열)",
            "merchantId": "가맹점 ID (문자열)",
            "customerId": "고객 ID (문자열, 선택)",
            "orderName": "주문명 (문자열)",
            "amount": "결제 금액 (숫자)",
            "method": "결제 수단 (CARD, VIRTUAL_ACCOUNT, EASY_PAY, TRANSFER, MOBILE)",
            "status": "결제 상태 (READY, IN_PROGRESS, DONE, CANCELED, PARTIAL_CANCELED, FAILED, EXPIRED)",
            "approvedAt": "결제 승인 시간 (날짜/시간)",
            "failureCode": "실패 코드 (문자열, 선택)",
            "failureMessage": "실패 메시지 (문자열, 선택)",
            "createdAt": "생성 시간 (날짜/시간)"
        },
        "statusValues": ["READY", "IN_PROGRESS", "DONE", "CANCELED", "PARTIAL_CANCELED", "FAILED", "EXPIRED"]
    },
    "Merchant": {
        "description": "가맹점 정보",
        "fields": {
            "merchantId": "가맹점 ID (문자열)",
            "businessName": "사업체명 (문자열)",
            "businessNumber": "사업자등록번호 (문자열)",
            "representativeName": "대표자명 (문자열)",
            "email": "이메일 (문자열)",
            "phone": "전화번호 (문자열)",
            "status": "가맹점 상태 (PENDING, ACTIVE, SUSPENDED, TERMINATED)",
            "feeRate": "수수료율 (숫자, 0~1, 예: 0.035 = 3.5%)",
            "settlementCycle": "정산 주기 (D+1, D+2 등)",
            "createdAt": "등록일 (날짜/시간)"
        }
    },
    "PgCustomer": {
        "description": "PG 고객 정보",
        "fields": {
            "customerId": "고객 ID (문자열)",
            "merchantId": "가맹점 ID (문자열)",
            "email": "이메일 (문자열)",
            "name": "고객명 (문자열)",
            "phone": "전화번호 (문자열)",
            "createdAt": "등록일 (날짜/시간)"
        }
    },
    "PaymentMethod": {
        "description": "결제 수단 정보 (등록된 카드/계좌)",
        "fields": {
            "paymentMethodId": "결제수단 ID (문자열)",
            "customerId": "고객 ID (문자열)",
            "type": "유형 (CARD, BANK_ACCOUNT)",
            "cardCompany": "카드사 (문자열, 선택)",
            "cardNumberMasked": "마스킹된 카드번호 (문자열, 선택)",
            "bankCode": "은행코드 (문자열, 선택)",
            "status": "상태 (ACTIVE, INACTIVE)",
            "isDefault": "기본 결제수단 여부 (불리언)",
            "createdAt": "등록일 (날짜/시간)"
        }
    },
    "PaymentHistory": {
        "description": "결제 상태 변경 이력 (timeRange 필수)",
        "fields": {
            "historyId": "이력 ID (정수)",
            "paymentKey": "결제 키 (문자열)",
            "previousStatus": "이전 상태 (문자열)",
            "newStatus": "변경 상태 (문자열)",
            "reason": "변경 사유 (문자열, 선택)",
            "processedBy": "처리자 (문자열, 선택)",
            "createdAt": "변경 시간 (날짜/시간)"
        }
    },
    "Refund": {
        "description": "환불 정보",
        "fields": {
            "refundKey": "환불 고유 키 (문자열)",
            "paymentKey": "원 결제 키 (문자열)",
            "amount": "환불 금액 (숫자)",
            "taxFreeAmount": "면세 금액 (숫자, 선택)",
            "reason": "환불 사유 (문자열)",
            "status": "환불 상태 (PENDING, DONE, FAILED)",
            "approvedAt": "환불 승인 시간 (날짜/시간, 선택)",
            "createdAt": "환불 요청 시간 (날짜/시간)"
        }
    },
    "BalanceTransaction": {
        "description": "잔액 거래 내역 (timeRange 필수)",
        "fields": {
            "transactionId": "거래 ID (문자열)",
            "merchantId": "가맹점 ID (문자열)",
            "sourceType": "거래 유형 (PAYMENT, REFUND, PAYOUT, ADJUSTMENT)",
            "sourceId": "원 거래 ID (문자열)",
            "amount": "거래 금액 (숫자)",
            "fee": "수수료 (숫자)",
            "net": "순 금액 (숫자)",
            "balanceBefore": "거래 전 잔액 (숫자)",
            "balanceAfter": "거래 후 잔액 (숫자)",
            "status": "상태 (PENDING, AVAILABLE)",
            "createdAt": "거래 시간 (날짜/시간)"
        }
    },
    "Settlement": {
        "description": "정산 정보 - 가맹점별 정산 내역",
        "fields": {
            "settlementId": "정산 ID (문자열)",
            "merchantId": "가맹점 ID (문자열)",
            "settlementDate": "정산일 (날짜)",
            "periodStart": "정산 기간 시작 (날짜)",
            "periodEnd": "정산 기간 종료 (날짜)",
            "totalPaymentAmount": "총 결제 금액 (숫자)",
            "totalRefundAmount": "총 환불 금액 (숫자)",
            "totalFee": "총 수수료 (숫자)",
            "netAmount": "정산 금액 (숫자)",
            "paymentCount": "결제 건수 (정수)",
            "refundCount": "환불 건수 (정수)",
            "status": "정산 상태 (PENDING, PROCESSED, PAID_OUT, FAILED)"
        }
    },
    "SettlementDetail": {
        "description": "정산 상세 내역",
        "fields": {
            "detailId": "상세 ID (문자열)",
            "settlementId": "정산 ID (문자열)",
            "paymentKey": "결제 키 (문자열)",
            "amount": "결제 금액 (숫자)",
            "fee": "수수료 (숫자)",
            "netAmount": "정산 금액 (숫자)",
            "type": "유형 (PAYMENT, REFUND)"
        }
    }
}


class QueryPlannerService:
    """
    자연어를 QueryPlan으로 변환하는 서비스
    LangChain + Claude/OpenAI의 Structured Output 사용
    RAG 컨텍스트로 쿼리 생성 품질 향상
    """

    def __init__(self, api_key: Optional[str] = None):
        # LLM Provider 설정 (openai 또는 anthropic)
        self._llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()

        if self._llm_provider == "anthropic":
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        self._llm = None
        self._chain = None
        self._rag_enabled = os.getenv("RAG_ENABLED", "true").lower() == "true"
        self._rag_top_k = int(os.getenv("RAG_TOP_K", "3"))

    def _get_llm(self):
        """LLM 인스턴스 지연 초기화"""
        if self._llm is None:
            if not self.api_key:
                key_name = "ANTHROPIC_API_KEY" if self._llm_provider == "anthropic" else "OPENAI_API_KEY"
                raise ValueError(f"{key_name} is not set")

            if self._llm_provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                # claude-3-5-haiku: 가장 저렴하고 빠른 모델
                self._llm = ChatAnthropic(
                    model=os.getenv("LLM_MODEL", "claude-3-5-haiku-20241022"),
                    temperature=0,
                    api_key=self.api_key
                )
                logger.info(f"Using Anthropic LLM: {os.getenv('LLM_MODEL', 'claude-3-5-haiku-20241022')}")
            else:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                    temperature=0,
                    api_key=self.api_key
                )
                logger.info(f"Using OpenAI LLM: {os.getenv('LLM_MODEL', 'gpt-4o-mini')}")
        return self._llm

    def _get_clarification_llm(self):
        """Clarification 판단용 LLM (상위 모델 사용)"""
        clarification_model = os.getenv("CLARIFICATION_MODEL", "gpt-4o")

        if self._llm_provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                model=clarification_model if "claude" in clarification_model else "claude-sonnet-4-20250514",
                temperature=0,
                api_key=self.api_key
            )
        else:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=clarification_model,
                temperature=0,
                api_key=self.api_key
            )

        logger.info(f"Using Clarification LLM: {clarification_model}")
        return llm

    async def classify_intent(
        self,
        user_message: str,
        conversation_context: str,
        previous_results: List[Dict[str, Any]]
    ) -> IntentClassification:
        """
        1단계 분류: 사용자 질문의 의도를 먼저 분류

        Args:
            user_message: 사용자 입력 메시지
            conversation_context: 이전 대화 컨텍스트 (build_conversation_context 결과)
            previous_results: 이전 조회 결과 요약 목록

        Returns:
            IntentClassification: 분류 결과 (intent, confidence, reasoning, direct_answer_text)
        """
        import time
        start_time = time.time()

        llm = self._get_llm()  # 가벼운 모델 사용

        # 이전 결과 요약 생성 (실제 금액 데이터 포함)
        results_summary = ""
        latest_amount = None  # 가장 최근 금액 (계산용)

        if previous_results:
            results_summary = "\n### 이전 조회 결과:\n"
            for i, r in enumerate(previous_results):
                entity = r.get("entity", "unknown")
                count = r.get("count", 0)
                aggregation = r.get("aggregation", "")
                total_amount = r.get("total_amount")
                data_summary = r.get("data_summary", "")

                results_summary += f"- 결과 #{i+1}: {entity} {count}건"

                # 실제 금액 데이터 포함
                if total_amount:
                    results_summary += f" | **금액 합계: ${total_amount:,.0f}**"
                    latest_amount = total_amount  # 가장 최근 금액 저장

                if aggregation:
                    results_summary += f" | 집계 결과: {aggregation}"

                if data_summary and not total_amount:
                    results_summary += f" | {data_summary}"

                results_summary += "\n"

            # 가장 최근 금액 강조
            if latest_amount:
                results_summary += f"\n⚠️ **계산에 사용할 금액: ${latest_amount:,.0f}**\n"
                results_summary += "이 금액을 기준으로 수수료, 나눗셈 등 계산을 수행하세요!\n"

        # conversation_context에 JSON {..}이 있을 수 있으므로 escape (안전성 확보)
        safe_conversation_context = escape_template_braces(conversation_context) if conversation_context else ""
        safe_results_summary = escape_template_braces(results_summary) if results_summary else ""

        classification_prompt = f"""당신은 사용자 질문의 의도를 분류하는 AI입니다.

{safe_conversation_context}
{safe_results_summary}

## 사용자 질문
"{user_message}"

## 분류 기준

### 1. direct_answer (LLM 직접 답변) - 우선 체크!
다음 경우 **반드시** direct_answer 선택:
- 이전 결과에 대한 **산술 연산** (%, 나누기, 곱하기, 더하기, 빼기)
- "수수료 X% 적용", "VAT 계산", "X로 나누면", "평균 계산"
- 단순 설명 요청 ("이게 뭐야?", "설명해줘")
- **이미 집계 결과가 있고** 그에 대한 추가 계산 요청

**예시:**
| 상황 | 질문 | 분류 |
|------|------|------|
| 합계 $1,949,000 있음 | "수수료 0.6% 적용해줘" | direct_answer |
| 합계 있음 | "5로 나누면?" | direct_answer |
| 합계 있음 | "VAT 10% 포함하면?" | direct_answer |
| 결과 있음 | "이게 무슨 의미야?" | direct_answer |

### 2. filter_local (클라이언트 필터링)
- "이중에", "여기서", "~만" 등으로 **기존 결과를 필터링**
- DB 재조회 없이 클라이언트에서 처리

### 3. aggregate_local (클라이언트 집계) - 중요!
- "합산", "합계", "평균", "건수", "총액" 등 **테이블 결과를 집계**
- 이전에 **테이블(목록) 결과**가 있고, 그것을 집계하는 요청 → aggregate_local
- 예: "금액 합산해줘", "총액 계산", "몇 건이야?"
- ⚠️ 집계 결과가 아직 없으면 **절대 direct_answer가 아님!**

### 4. query_needed (DB 조회 필요)
- 새로운 데이터 조회 필요
- "최근 거래 30건", "환불 내역 조회"

## 중요한 판단 규칙 - 반드시 순서대로 확인!

**Step 1**: 이전 결과가 **테이블(목록)**인가, **집계 결과(텍스트)**인가?
- 테이블이면 → "합산", "평균" 요청 시 **aggregate_local**
- 집계 결과(예: "결제 금액 합계: $5,000,000")이면 → 추가 계산 시 **direct_answer**

**Step 2**: direct_answer 조건 (모두 충족해야 함!)
1. 이미 **집계 결과(숫자가 포함된 텍스트)**가 있어야 함
2. 그 숫자에 대한 추가 계산 요청 (%, 나누기, 곱하기)
3. 예: "수수료 0.6%", "5로 나누면?", "VAT 10%"

**Step 3**: aggregate_local 조건
1. 이전에 **테이블/목록 결과**가 있음
2. "합산", "합계", "평균", "건수" 등 기본 집계 요청
3. 아직 집계가 수행되지 않은 상태

## ⚠️ 매우 중요: direct_answer_text 생성 규칙
intent가 "direct_answer"이면 **반드시** direct_answer_text에 계산된 답변을 작성하세요!

**예시 (집계 결과: 결제 금액 합계: $5,035,000):**
- 질문: "수수료 0.6% 적용해서 수수료와 순금액 보여줘"
- direct_answer_text 예시:
  "결제 금액 **$5,035,000** 기준:
  - **수수료 (0.6%)**: $30,210
  - **수수료 제외 금액**: $5,004,790"

- 질문: "5로 나누면?"
- direct_answer_text 예시:
  "$5,035,000을 5로 나누면 **$1,007,000**입니다."

**절대 direct_answer_text를 null로 두지 마세요! 반드시 계산 결과를 포함하세요.**

응답은 반드시 JSON 형식으로:
{{
    "intent": "direct_answer" | "query_needed" | "filter_local" | "aggregate_local",
    "confidence": 0.0 ~ 1.0,
    "reasoning": "판단 근거 (1-2문장)",
    "direct_answer_text": "direct_answer인 경우 **반드시 계산된 답변** 작성, 다른 intent면 null"
}}
"""

        try:
            # Structured output 사용
            structured_llm = llm.with_structured_output(IntentClassification)
            result = await structured_llm.ainvoke(classification_prompt)

            elapsed = int((time.time() - start_time) * 1000)
            logger.info(f"[Intent Classification] intent={result.intent}, confidence={result.confidence:.2f}, time={elapsed}ms")
            logger.info(f"[Intent Classification] reasoning: {result.reasoning}")

            return result

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # 실패 시 기본값: query_needed
            return IntentClassification(
                intent=IntentType.QUERY_NEEDED,
                confidence=0.5,
                reasoning=f"Classification failed: {str(e)}",
                direct_answer_text=None
            )

    async def check_clarification_needed(
        self,
        user_message: str,
        result_summaries: List[Dict[str, Any]],
        query_intent: str
    ) -> bool:
        """
        2단계 판단: Clarification이 필요한지 상위 모델로 판단

        Args:
            user_message: 사용자 입력 메시지
            result_summaries: 이전 결과 요약 목록 [{"entity": "Payment", "count": 30, "filters": "..."}, ...]
            query_intent: 현재 query_intent (filter_local, aggregate_local 등)

        Returns:
            bool: True면 clarification 필요, False면 직전 결과 사용
        """
        # 결과가 1개 이하면 clarification 불필요
        if len(result_summaries) <= 1:
            logger.info(f"[Clarification Check] Single result, no clarification needed")
            return False

        # filter_local, aggregate_local이 아니면 clarification 불필요
        if query_intent not in ["filter_local", "aggregate_local"]:
            logger.info(f"[Clarification Check] Intent '{query_intent}' doesn't need clarification")
            return False

        try:
            llm = self._get_clarification_llm()

            # 결과 요약 텍스트 생성
            results_text = "\n".join([
                f"- 결과 #{i+1}: {r.get('entity', 'unknown')} {r.get('count', '?')}건" +
                (f" (필터: {r.get('filters', '')})" if r.get('filters') else "")
                for i, r in enumerate(result_summaries)
            ])

            prompt = f"""당신은 사용자 의도 판단 전문가입니다.

## 현재 상황
- 사용자가 이전에 여러 데이터를 조회했습니다.
- 지금 사용자가 집계/필터 요청을 했습니다.
- 어떤 데이터를 대상으로 하는지 명확한지 판단해주세요.

## 이전 조회 결과 (세션 내)
{results_text}

## 사용자 입력
"{user_message}"

## 판단 기준
1. "이중에", "여기서", "직전", "방금", "위 결과" 등 **참조 표현이 있으면** → 명확함 (NO)
2. 참조 표현 없이 "합산해줘", "필터링해줘" 등만 있고 **다중 결과가 있으면** → 모호함 (YES)
3. 특정 결과를 명시적으로 지정하면 ("30건에서", "도서 결과에서") → 명확함 (NO)

## 응답
clarification이 필요하면 "YES", 필요 없으면 "NO"만 응답하세요.
다른 설명 없이 YES 또는 NO만 답하세요."""

            from langchain_core.messages import HumanMessage
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            answer = response.content.strip().upper()

            needs_clarification = answer == "YES"
            logger.info(f"[Clarification Check] LLM decision: {answer} -> needs_clarification={needs_clarification}")

            return needs_clarification

        except Exception as e:
            logger.error(f"[Clarification Check] Error: {e}, defaulting to False")
            return False

    def _build_system_prompt(self) -> str:
        """결제 도메인 특화 시스템 프롬프트 생성"""
        schema_info = json.dumps(ENTITY_SCHEMAS, ensure_ascii=False, indent=2)
        # LangChain 프롬프트에서 중괄호를 escape (변수로 인식되지 않도록)
        schema_info_escaped = schema_info.replace("{", "{{").replace("}", "}}")

        # 현재 날짜 정보 (LLM이 시간 표현을 정확히 해석하기 위해 필요)
        now = datetime.now()
        current_date_info = f"""## 현재 날짜 정보 (중요!)

오늘 날짜: {now.strftime('%Y-%m-%d')} ({now.strftime('%A')})
현재 시간: {now.strftime('%H:%M:%S')}
이번 주 월요일: {(now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')}
이번 달 1일: {now.replace(day=1).strftime('%Y-%m-%d')}

**시간 표현 변환 시 반드시 위 날짜를 기준으로 계산하세요.**

"""
        return f"""당신은 PG(Payment Gateway) 결제 백오피스 쿼리 어시스턴트입니다.
사용자의 자연어 요청을 분석하여 적절한 QueryPlan을 생성합니다.

## ⚠️ 최우선 규칙 (반드시 먼저 읽으세요!)

### 1. 도메인 용어 자동 매핑 (clarification 금지!)
다음 단어가 포함되면 **무조건** 해당 엔티티로 처리하세요. **절대로 needs_clarification을 true로 설정하지 마세요!**

| 사용자 표현 | 엔티티 | 예시 |
|------------|--------|------|
| 거래, 트랜잭션, 결제, 이력, 내역 | **Payment** | "최근 거래 30건" → Payment, limit:30 |
| 환불, 취소환불, 반품 | **Refund** | "환불 내역" → Refund |
| 가맹점, 상점, 업체, merchant | **Merchant** | "가맹점 목록" → Merchant |
| 정산, settlement | **Settlement** | "정산 내역" → Settlement |

### 2. clarification이 필요한 경우 (매우 드묾)
**오직 다음 경우에만** needs_clarification=true:
- "정보 보여줘", "데이터 조회해줘" (무엇을?)
- 도메인 용어가 전혀 없는 모호한 요청

### 3. "최근 거래 30건 조회" 처리 예시 (정답)
```json
{{{{
  "entity": "Payment",
  "operation": "list",
  "limit": 30,
  "orderBy": [{{{{"field": "createdAt", "direction": "desc"}}}}],
  "query_intent": "new_query",
  "needs_clarification": false
}}}}
```
**needs_clarification: false, clarification_question: null** 이어야 합니다!

{current_date_info}

## 사용 가능한 엔티티 및 필드

{schema_info_escaped}

## 엔티티 선택 가이드

### 결제 관련
- "결제", "결제 내역", "결제 현황", "거래", "트랜잭션" → **Payment**
- "결제 추이", "결제 추세", "매출 추이", "일별 결제" → **Payment** (aggregate + groupBy 날짜)
- "정상 결제", "성공 결제", "완료된 결제" → **Payment** (filters: status = "DONE")
- "실패 결제", "결제 오류", "결제 실패" → **Payment** (filters: status = "FAILED")
- "취소 결제", "취소된 결제" → **Payment** (filters: status = "CANCELED" 또는 "PARTIAL_CANCELED")

### 환불 관련
- "환불", "환불 내역", "취소 환불" → **Refund**

### 가맹점 관련
- "가맹점", "상점", "merchant", "업체" → **Merchant**
- "특정 가맹점의 거래", "가맹점 결제 현황" → **Payment** (filters: merchantId = 값)

### 정산 관련
- "정산", "정산 내역", "settlement" → **Settlement**
- "정산 상세", "정산 세부" → **SettlementDetail**

### 기타
- "결제 이력", "상태 변경 이력" → **PaymentHistory**
- "잔액 거래", "정산 전 거래" → **BalanceTransaction**
- "결제 수단", "등록된 카드" → **PaymentMethod**

## 작업 유형 (operation 필드) - 중요!

**operation 필드는 Core API 작업 유형이며, 다음 3가지만 가능:**
1. **list**: 데이터 목록 조회 (기본값)
2. **aggregate**: 서버에서 집계/통계 (DB에서 집계)
3. **search**: 텍스트 검색 (LIKE 연산)

**주의: filter_local, aggregate_local, direct_answer는 operation이 아닌 query_intent 필드에 설정!**
- operation: "list" | "aggregate" | "search" (Core API용)
- query_intent: "new_query" | "refine_previous" | "filter_local" | "aggregate_local" | "direct_answer" (클라이언트 처리용)

**예시:**
- 클라이언트에서 필터링 → operation: "list", query_intent: "filter_local"
- 클라이언트에서 집계 → operation: "list", query_intent: "aggregate_local"
- LLM 직접 답변 → operation: "list", query_intent: "direct_answer"

## 시나리오별 쿼리 패턴

### 시나리오 1: 최근 1개월간 결제 추이
- entity: Payment
- operation: aggregate
- aggregations: count(*) as count, sum(amount) as totalAmount
- groupBy: approvedAt
- timeRange: 1개월 전 ~ 현재
- orderBy: approvedAt ASC

### 시나리오 2: 특정 가맹점 거래 데이터
- entity: Payment
- operation: list
- filters: merchantId eq "가맹점ID"
- orderBy: createdAt DESC
- limit: 50

### 시나리오 3: 정상/오류 결제 비율
- entity: Payment
- operation: aggregate
- aggregations: count(*) as count
- groupBy: status

### 시나리오 4: 특정 주문번호 상태 조회
- entity: Payment
- operation: list
- filters: orderId eq "주문번호"
- limit: 1

### 시나리오 5: 특정 시간대 거래 건수
- entity: Payment
- operation: aggregate
- aggregations: count(*) as count
- timeRange: 시작시간 ~ 종료시간

## 도메인별 Few-shot 예시 (반드시 참고!)

### Payment (결제) 예시

**예시 P1: 특정 가맹점 결제 현황**
- 입력: "가맹점 mer_001 최근 3개월 결제 조회"
- entity: Payment
- filters: [merchantId eq "mer_001"]
- timeRange: 3개월 전 ~ 현재
- orderBy: createdAt DESC
- limit: 10

**예시 P2: 상태별 결제 집계**
- 입력: "이번 달 결제 상태별 건수와 금액"
- entity: Payment
- operation: aggregate
- aggregations: count(*), sum(amount)
- groupBy: [status]
- timeRange: 이번 달 1일 ~ 현재

**예시 P3: 고액 결제 조회**
- 입력: "100만원 이상 결제 건 조회"
- entity: Payment
- filters: [amount gte 1000000]
- timeRange: 최근 7일
- orderBy: amount DESC

**예시 P4: 결제 수단별 통계**
- 입력: "결제 수단별 건수 비교"
- entity: Payment
- operation: aggregate
- aggregations: count(*), sum(amount)
- groupBy: [method]
- timeRange: 최근 30일

**예시 P5: 카드 할부 결제**
- 입력: "할부 결제 건 조회 (무이자 포함)"
- entity: Payment
- filters: [cardInstallmentMonths gt 0]
- timeRange: 최근 30일

**예시 P6: 취소된 결제 목록**
- 입력: "취소된 결제 내역"
- entity: Payment
- filters: [status in ["CANCELED", "PARTIAL_CANCELED"]]
- timeRange: 최근 7일
- orderBy: canceledAt DESC

**예시 P7: 일별 매출 추이**
- 입력: "일별 결제 금액 추이 보여줘"
- entity: Payment
- operation: aggregate
- aggregations: sum(amount) as dailyAmount, count(*) as count
- groupBy: [approvedAt]
- timeRange: 최근 30일
- orderBy: approvedAt ASC

**예시 P8: 가상계좌 입금대기**
- 입력: "가상계좌 입금 대기 건"
- entity: Payment
- filters: [status eq "WAITING_FOR_DEPOSIT", method eq "VIRTUAL_ACCOUNT"]
- timeRange: 최근 7일

**예시 P9: 평균 결제 금액**
- 입력: "가맹점별 평균 결제 금액"
- entity: Payment
- operation: aggregate
- aggregations: avg(amount) as avgAmount
- groupBy: [merchantId]
- timeRange: 최근 30일

**예시 P10: 간편결제 사용 현황**
- 입력: "간편결제(카카오페이, 네이버페이) 결제 건"
- entity: Payment
- filters: [method eq "EASY_PAY"]
- timeRange: 최근 7일

### Settlement (정산) 예시

**예시 S1: 가맹점별 정산 현황**
- 입력: "가맹점별 정산 현황 조회"
- entity: Settlement
- orderBy: settlementDate DESC
- limit: 20

**예시 S2: 특정 가맹점 정산 내역**
- 입력: "mer_001 정산 내역"
- entity: Settlement
- filters: [merchantId eq "mer_001"]
- orderBy: settlementDate DESC

**예시 S3: 정산 상태별 현황**
- 입력: "정산 대기 건 조회"
- entity: Settlement
- filters: [status eq "PENDING"]
- orderBy: settlementDate DESC

**예시 S4: 정산 금액 집계**
- 입력: "가맹점별 총 정산 금액"
- entity: Settlement
- operation: aggregate
- aggregations: sum(netAmount) as totalSettlement
- groupBy: [merchantId]

**예시 S5: 지급 완료 정산**
- 입력: "지급 완료된 정산 내역"
- entity: Settlement
- filters: [status eq "COMPLETED"]
- orderBy: paidOutAt DESC

**예시 S6: 월별 정산 추이**
- 입력: "월별 정산 금액 추이"
- entity: Settlement
- operation: aggregate
- aggregations: sum(netAmount), sum(totalFee)
- groupBy: [settlementDate]
- orderBy: settlementDate ASC

**예시 S7: 수수료 높은 정산**
- 입력: "수수료가 가장 높은 정산 건"
- entity: Settlement
- orderBy: totalFee DESC
- limit: 10

**예시 S8: 정산 실패 건**
- 입력: "정산 실패한 건 확인"
- entity: Settlement
- filters: [status eq "FAILED"]

### Refund (환불) 예시

**예시 R1: 최근 환불 내역**
- 입력: "최근 환불 내역 조회"
- entity: Refund
- orderBy: createdAt DESC
- limit: 20

**예시 R2: 환불 사유별 통계**
- 입력: "환불 사유별 건수"
- entity: Refund
- operation: aggregate
- aggregations: count(*) as count
- groupBy: [cancelReasonCode]

**예시 R3: 대기 중인 환불**
- 입력: "환불 대기 건"
- entity: Refund
- filters: [status eq "PENDING"]
- orderBy: createdAt DESC

**예시 R4: 환불 금액 집계**
- 입력: "이번 달 총 환불 금액"
- entity: Refund
- operation: aggregate
- aggregations: sum(amount) as totalRefund, count(*) as count
- filters: [status eq "SUCCEEDED"]

**예시 R5: 특정 결제 환불**
- 입력: "결제키 pay_xxx의 환불 내역"
- entity: Refund
- filters: [paymentKey eq "pay_xxx"]

**예시 R6: 가맹점별 환불율**
- 입력: "가맹점별 환불 건수"
- entity: Refund
- operation: aggregate
- aggregations: count(*) as refundCount, sum(amount) as refundAmount
- groupBy: [paymentKey]

### 복합 조건 예시

**예시 C1: 고액 + 상태 조합**
- 입력: "100만원 이상 DONE 결제 중 카드 결제"
- entity: Payment
- filters: [amount gte 1000000, status eq "DONE", method eq "CARD"]
- timeRange: 최근 30일

**예시 C2: 기간 + 가맹점 조합**
- 입력: "지난 주 mer_001, mer_002 결제 비교"
- entity: Payment
- filters: [merchantId in ["mer_001", "mer_002"]]
- timeRange: 지난 주 월~일
- operation: aggregate
- groupBy: [merchantId]
- aggregations: sum(amount), count(*)

**예시 C3: 부정적 조건**
- 입력: "실패하지 않은 결제 건"
- entity: Payment
- filters: [status ne "FAILED", status ne "ABORTED"]
- timeRange: 최근 7일

**예시 C4: 범위 조건**
- 입력: "10만원에서 50만원 사이 결제"
- entity: Payment
- filters: [amount between [100000, 500000]]
- timeRange: 최근 7일

**예시 C5: 패턴 매칭**
- 입력: "주문명에 '도서' 포함된 결제"
- entity: Payment
- filters: [orderName like "도서"]
- timeRange: 최근 30일

## 시간 표현 해석 (ISO 8601 형식으로 변환)

- "최근 1개월", "지난 달" → start: 1개월 전, end: 현재
- "오늘", "금일" → start: 오늘 00:00:00, end: 오늘 23:59:59
- "어제" → start: 어제 00:00:00, end: 어제 23:59:59
- "이번 주" → start: 이번 주 월요일 00:00:00, end: 현재
- "지난 주" → start: 지난 주 월요일, end: 지난 주 일요일
- "이번 달" → start: 이번 달 1일, end: 현재
- 시간 미지정 시 → 최근 7일 기본 적용

## 결제 상태 값

- **READY**: 결제 준비 (결제창 호출됨)
- **IN_PROGRESS**: 결제 진행 중
- **DONE**: 결제 완료 (정상 승인) - "정상", "성공", "완료"
- **CANCELED**: 전체 취소
- **PARTIAL_CANCELED**: 부분 취소
- **FAILED**: 결제 실패 - "실패", "오류"
- **EXPIRED**: 만료 (가상계좌 기한 초과)

## 필터 연산자 (반드시 문자열 코드 사용!)

| 코드 | 의미 | 예시 |
|------|------|------|
| eq | 같음 | status eq "DONE" |
| ne | 같지 않음 | status ne "FAILED" |
| gt | 초과 | amount gt 10000 |
| gte | 이상 | amount gte 50000 |
| lt | 미만 | amount lt 1000 |
| lte | 이하 | amount lte 100000 |
| in | 포함 | status in ["DONE", "CANCELED"] |
| like | 패턴 매칭 | orderName like "도서" |
| between | 범위 | amount between [10000, 50000] |

**중요**: 기호(>=, <=, >, <, =, != 등)를 사용하지 마세요. 반드시 문자열 코드(eq, gte 등)만 사용하세요.

## 정렬 규칙

- "최근", "최신" → createdAt DESC 또는 approvedAt DESC
- "오래된" → createdAt ASC
- "높은 금액", "큰 금액" → amount DESC
- "낮은 금액", "작은 금액" → amount ASC
- "추이", "추세" → 날짜 ASC (시계열 차트용)

## 필수 timeRange 엔티티

다음 엔티티는 대용량 시계열 데이터이므로 **timeRange 지정을 강력히 권장**합니다:
- Payment, PaymentHistory, BalanceTransaction

시간 범위가 명시되지 않은 경우 **최근 7일**로 기본 설정하세요.

## 주의사항

1. 물리적 테이블명이나 컬럼명을 사용하지 마세요 (논리명만 사용)
2. limit의 기본값은 10, 최대값은 100
3. 집계 쿼리(aggregate)에서 groupBy 없이 단순 집계만 할 경우 결과는 단일 값
4. 가맹점ID나 주문번호가 구체적으로 명시되면 해당 값으로 필터링

## ❌ Negative Examples (하면 안 되는 것들)

아래 예시들은 **잘못된** QueryPlan 생성 패턴입니다. 이런 실수를 피하세요.

### NE1: entity 누락
❌ 틀린 예:
- 입력: "최근 결제 조회"
- entity: null ← **오류! entity는 필수**

⭕ 올바른 예:
- entity: Payment
- timeRange: 최근 7일

### NE2: 시계열 데이터에 timeRange 누락
❌ 틀린 예:
- 입력: "결제 목록 보여줘"
- entity: Payment
- timeRange: null ← **오류! Payment는 timeRange 필수**

⭕ 올바른 예:
- entity: Payment
- timeRange: 최근 7일 (기본값 적용)

### NE3: 기호 연산자 사용
❌ 틀린 예:
- filters: [{{{{field: "amount", operator: ">=", value: 100000}}}}] ← **오류! >= 대신 gte 사용**

⭕ 올바른 예:
- filters: [{{{{field: "amount", operator: "gte", value: 100000}}}}]

### NE4: 물리적 컬럼명 사용
❌ 틀린 예:
- filters: [{{{{field: "created_at", ...}}}}] ← **오류! 물리명 created_at 사용**

⭕ 올바른 예:
- filters: [{{{{field: "createdAt", ...}}}}] ← 논리명 createdAt 사용

### NE5: aggregate인데 aggregations 누락
❌ 틀린 예:
- operation: "aggregate"
- groupBy: ["merchantId"]
- aggregations: null ← **오류! aggregate면 aggregations 필수**

⭕ 올바른 예:
- operation: "aggregate"
- groupBy: ["merchantId"]
- aggregations: [{{{{function: "count", field: "*"}}}}]

### NE6: 불필요한 clarification 요청
❌ 틀린 예:
- 입력: "거래 조회"
- needs_clarification: true ← **오류! "거래"는 명확히 Payment**

⭕ 올바른 예:
- entity: Payment (도메인 용어로 바로 판단)
- needs_clarification: false

### NE7: filter_local인데 entity 설정
❌ 틀린 예:
- 입력: "이중에 DONE만"
- query_intent: "filter_local"
- entity: Payment ← **오류! filter_local은 entity 불필요**

⭕ 올바른 예:
- query_intent: "filter_local"
- filters: [{{{{field: "status", operator: "eq", value: "DONE"}}}}]
- entity: null (생략)

### NE8: 이전 결과 없이 aggregate_local
❌ 틀린 예:
- 입력: "합산해줘" (대화 컨텍스트 없음)
- query_intent: "aggregate_local" ← **오류! 이전 결과가 없음**

⭕ 올바른 예:
- query_intent: "new_query"
- entity: Payment
- operation: "aggregate"
- aggregations: [{{{{function: "sum", field: "amount"}}}}]

### NE9: between 값 형식 오류
❌ 틀린 예:
- filters: [{{{{operator: "between", value: "100000~500000"}}}}] ← **오류! 문자열 형식**

⭕ 올바른 예:
- filters: [{{{{operator: "between", value: [100000, 500000]}}}}] ← 배열 형식

### NE10: 잘못된 상태값
❌ 틀린 예:
- filters: [{{{{field: "status", operator: "eq", value: "완료"}}}}] ← **오류! 한글 상태값**

⭕ 올바른 예:
- filters: [{{{{field: "status", operator: "eq", value: "DONE"}}}}] ← 영문 상태값

## 렌더링 타입 (preferredRenderType) - 매우 중요!

사용자가 특정 렌더링 형식을 명시적으로 요청하면 반드시 **preferredRenderType** 필드를 설정하세요:

### 키워드 → preferredRenderType 매핑

| 사용자 표현 | preferredRenderType |
|------------|---------------------|
| "표로", "테이블로", "목록으로", "리스트로" | "table" |
| "그래프로", "차트로", "그림으로", "시각화로" | "chart" |
| "텍스트로", "글로", "요약으로" | "text" |

### 예시

**예시 1: 표로 요청**
- 입력: "최근 3개월 거래를 가맹점별로 그룹화해서 **표로** 보여줘"
- 결과: operation=aggregate, groupBy=["merchantId"], **preferredRenderType="table"**

**예시 2: 차트로 요청**
- 입력: "결제 현황을 **그래프로** 보여줘"
- 결과: operation=aggregate, **preferredRenderType="chart"**

**예시 3: 명시 없음**
- 입력: "최근 결제 내역 조회해줘"
- 결과: operation=list, **preferredRenderType 생략** (시스템이 자동 결정)

### 중요 규칙
- 사용자가 "표로"라고 명시하면 groupBy가 있더라도 **반드시 preferredRenderType="table"** 설정
- 사용자가 렌더링 타입을 명시하지 않으면 preferredRenderType 필드를 생략 (시스템이 자동 결정)
- preferredRenderType은 operation과 독립적 (aggregate 작업도 표로 표시 가능)

## 쿼리 의도 분류 (query_intent) - 매우 중요!

모든 요청에 **query_intent** 필드를 반드시 설정하세요:

### new_query (새로운 검색)
다음 경우 query_intent를 "new_query"로 설정:
- 첫 질문 또는 대화 컨텍스트가 없는 경우
- 다른 엔티티를 조회하는 경우 (예: Payment → Refund)
- "새로", "다른", "별도로" 등 새 검색 의도 표현
- 이전 결과와 관련 없는 완전히 새로운 요청

### refine_previous (서버 재조회)
다음 경우 query_intent를 "refine_previous"로 설정:
- 필터 조건을 변경하여 DB에서 새로 조회해야 하는 경우
- **"다시 조회"**, **"새로 검색"**, **"조건 변경"** 등의 표현
- 명시적인 "전체 데이터에서", "DB에서", "처음부터" 등의 표현

### filter_local (클라이언트 필터링) - 중요!
다음 경우 query_intent를 "filter_local"로 설정:
- **"이중"**, **"이중에"**, **"이 중에서"**, **"여기서"**, **"그 중에서"**, **"그중에"**, **"그중"** 등 이전 결과 참조 표현
- **"이전 결과에서"**, **"조회된 결과에서"**, **"방금 결과에서"** 등 명시적 참조
- "화면에 있는 데이터에서", "위 결과에서", "받은 데이터에서" 등
- 이미 조회된 데이터를 클라이언트에서 재가공하려는 의도
- 서버 재조회 없이 메모리에 있는 결과만 필터링

**filter_local에서 entity 처리 규칙 (매우 중요!):**
- filter_local일 때 **entity는 생략 가능** (이전 대화 컨텍스트에서 자동 추론)
- entity를 명시하지 않아도 시스템이 이전 queryPlan의 entity를 자동 상속
- **절대로 needs_clarification을 true로 설정하지 마세요!**
- filters 필드는 반드시 설정해야 함 (필터 조건 필수)

**filter_local 설정 시 filters 필드도 반드시 설정! (매우 중요)**
필터링할 조건을 filters 배열에 포함해야 합니다:
- "이중에 도서만" → filters 배열에 field=orderName, operator=like, value=도서 추가
- "여기서 DONE만" → filters 배열에 field=status, operator=eq, value=DONE 추가
- "이중에 mer_001만" → filters 배열에 field=merchantId, operator=eq, value=mer_001 추가
- "도서 관련 거래만" → filters 배열에 field=orderName, operator=like, value=도서 추가
필터 조건 없이 filter_local만 설정하면 안 됨!

**filter_local vs refine_previous 구분:**
- "이중에 도서만" → filter_local (이전 결과 참조)
- "이전 결과에서 도서만" → filter_local (명시적 참조)
- "도서만 다시 조회" → refine_previous (서버 재조회)
- "처음부터 도서만 검색" → new_query 또는 refine_previous

### aggregate_local (클라이언트 집계) - 중요!
다음 경우 query_intent를 "aggregate_local"로 설정:
- **이전 대화에서 조회/필터링된 결과가 있는 상태**에서
- **"합산", "합계", "총액", "총합", "평균", "개수", "몇 건" 등 집계 표현**이 있고
- **명시적으로 "전체 데이터"라고 하지 않은 경우**
- 예: "금액 합산해줘", "총액 얼마야", "평균 금액", "몇 건이야"

**aggregate_local 설정 시 aggregations 필드도 반드시 설정:**
- "합산", "합계", "총액" → aggregations 배열에 포함:
  - function: "sum", field: "amount", alias: "totalAmount"
  - displayLabel: "결제 금액 합계" (한글로 자연스럽게)
  - currency: "USD" 또는 "KRW" (데이터 화폐 단위에 맞게)
- "평균" → function: "avg", displayLabel: "평균 결제 금액", currency 설정
- "개수", "몇 건" → function: "count", field: "*", displayLabel: "총 건수", currency: null

**중요: displayLabel과 currency는 LLM이 문맥에 맞게 자연스럽게 설정**
- Payment 엔티티의 amount 필드는 일반적으로 USD (달러)
- displayLabel은 사용자에게 보여줄 한글 표현 (예: "결제 금액 합계", "평균 거래액")

**aggregate_local vs new_query(aggregate) 구분:**
- "금액 합산해줘" (이전 결과 있음) → aggregate_local (이전 결과 집계)
- "전체 결제 금액 합산" → new_query + operation:aggregate (서버에서 전체 집계)
- "처음부터 합산" → new_query + operation:aggregate (서버에서 전체 집계)

## 결과 선택 clarification (needs_result_clarification) - 매우 중요!

**기본 원칙**: filter_local이나 aggregate_local일 때, **기본적으로 직전(가장 최근) 결과를 사용**합니다.
- needs_result_clarification의 **기본값은 false**
- 단, **다중 결과 + 참조 표현 없음** 상황에서는 **true로 설정**

### 🎯 Few-shot 예시 (판단 기준) - 반드시 참고!

**예시 1: 명확한 참조 표현 있음 → false**
세션 결과: [Payment 30건], [Refund 15건]
사용자: "이중에 합산해줘"
판단: "이중에"가 직전 결과(Refund 15건)를 명확히 참조
→ needs_result_clarification: **false**

**예시 2: 참조 없음 + 다른 entity 다중 결과 → true**
세션 결과: [Payment 30건], [Refund 15건]
사용자: "금액 합산해줘"
판단: 참조 표현 없음 + Payment/Refund 둘 다 금액 있음 → 어떤 결과인지 모호
→ needs_result_clarification: **true**

**예시 3: 참조 없음 + 같은 entity 다른 조건 → true**
세션 결과: [Payment 30건], [Payment 도서 7건 (필터링됨)]
사용자: "합산해줘"
판단: 같은 Payment지만 30건 전체인지 도서 7건인지 불명확
→ needs_result_clarification: **true**

**예시 4: 명확한 직전 참조 → false**
세션 결과: [Payment 30건], [Payment 도서 7건]
사용자: "여기서 mer_001만 필터링"
판단: "여기서"가 직전 결과(도서 7건)를 명확히 참조
→ needs_result_clarification: **false**

**예시 5: 단일 결과만 있음 → false**
세션 결과: [Payment 30건]
사용자: "금액 합산해줘"
판단: 결과가 1개뿐이므로 당연히 그것 대상
→ needs_result_clarification: **false**

### 판단 체크리스트 (순서대로 확인!)
1. 세션에 결과가 **1개뿐**인가? → **false** (선택지 없음)
2. "이중에", "여기서", "직전", "방금" 등 **참조 표현**이 있는가? → **false** (직전 결과)
3. 참조 표현 없고 + 다중 결과 + **서로 다른 entity** → **true** (모호함)
4. 참조 표현 없고 + 다중 결과 + **같은 entity 다른 조건** → **true** (모호함)

### 참조 표현 예시
- 직전 결과 참조: "이중에", "이중", "여기서", "직전", "방금", "위 결과에서", "조회된 결과에서"
- 특정 결과 참조: "아까 30건에서", "처음 결과에서", "두 번째 결과"

## direct_answer (LLM 직접 답변) - 매우 중요!

다음 경우 query_intent를 "direct_answer"로 설정하고, **direct_answer 필드에 답변을 작성**하세요:

1. **이전 집계 결과에 대한 산술 연산**:
   - "5로 나누면?", "10을 곱하면?", "반으로 나누면?"
   - 이전 대화에서 집계 결과(예: $1,451,000)가 있으면, 직접 계산해서 답변
   - 예: direct_answer = "결제 금액 합계 $1,451,000을 5로 나누면 **$290,200**입니다."

2. **단순 질문/설명 요청**:
   - "이게 뭐야?", "설명해줘", "어떤 의미야?"
   - DB 조회 없이 답변 가능한 질문

3. **계산 결과 포맷**:
   - 화폐 단위 유지 (USD면 $, KRW면 원)
   - 큰 숫자는 읽기 쉽게 (예: $290,200, 29만 200달러)
   - 마크다운 볼드(**결과값**)로 강조

**direct_answer 예시:**
| 사용자 입력 | 이전 컨텍스트 | direct_answer |
|------------|--------------|---------------|
| "5로 나누면?" | 집계 결과 $1,451,000 | "결제 금액 합계 $1,451,000을 5로 나누면 **$290,200**입니다." |
| "반으로 나누면?" | 집계 결과 $1,451,000 | "$1,451,000의 절반은 **$725,500**입니다." |
| "10% 수수료 빼면?" | 집계 결과 $1,451,000 | "10% 수수료($145,100)를 제외하면 **$1,305,900**입니다." |
| "수수료 0.6% 적용해서 수수료와 순금액 보여줘" | 집계 결과 $1,949,000 | "결제 금액 $1,949,000 기준:\n- **수수료 (0.6%)**: $11,694\n- **수수료 제외 금액**: $1,937,306" |
| "결제금액에 수수료 0.6% 적용해서 보여줘" | 집계 결과 $1,949,000 | "결제 금액 $1,949,000에 0.6% 수수료 적용:\n- **수수료**: $11,694\n- **순 금액**: $1,937,306" |
| "VAT 10% 계산해줘" | 집계 결과 $1,000,000 | "금액 $1,000,000 기준:\n- **VAT (10%)**: $100,000\n- **VAT 포함 금액**: $1,100,000" |

**중요**: "보여줘", "알려줘", "계산해줘" 같은 표현이 있어도, 이미 조회된 결과에 대한 **백분율/수수료/세금 계산**은 direct_answer입니다!

### 의도 분류 예시
| 사용자 입력 | 대화 컨텍스트 | query_intent |
|------------|--------------|--------------|
| "최근 결제 30건" | 없음 | new_query |
| "DONE 상태만 다시 조회" | 결제 목록 조회 후 | refine_previous |
| "처음부터 100만원 이상만" | 결제 목록 조회 후 | refine_previous |
| "이중에 도서만" | 결제 목록 조회 후 | **filter_local** (entity 생략 OK) |
| "이중 도서만" | 결제 목록 조회 후 | **filter_local** (entity 생략 OK) |
| "이중에 mer_001만" | 결제 목록 조회 후 | **filter_local** (entity 생략 OK) |
| "이중 mer_001만" | 결제 목록 조회 후 | **filter_local** (entity 생략 OK) |
| "여기서 DONE만" | 결제 목록 조회 후 | **filter_local** |
| "이전 결과에서 도서만" | 결제 목록 조회 후 | **filter_local** |
| "조회된 결과에서 DONE만" | 결제 목록 조회 후 | **filter_local** |
| "방금 결과에서 카드 결제만" | 결제 목록 조회 후 | **filter_local** |
| "금액 합산해줘" | 결제 목록 조회 후 | **aggregate_local** |
| "총액 얼마야" | 필터링된 결과 조회 후 | **aggregate_local** |
| "평균 금액" | 결제 목록 조회 후 | **aggregate_local** |
| "몇 건이야" | 결제 목록 조회 후 | **aggregate_local** |
| "전체 결제 금액 합산" | 결제 목록 조회 후 | new_query (명시적 전체) |
| "환불 내역 조회해줘" | 결제 목록 조회 후 | new_query (다른 엔티티) |
| "다른 가맹점 결제" | 특정 가맹점 결제 조회 후 | new_query |

### 중요 주의사항
1. refine_previous일 때 **새로 추가할 필터만** filters에 포함 (기존 필터는 시스템이 병합)
2. refine_previous일 때 **entity는 이전과 동일하게** 유지
3. 불확실한 경우 기본값은 **new_query** (안전한 선택)

## 기본 엔티티 규칙 (상단 최우선 규칙 참조)

**⚠️ 다시 한번 강조: "거래", "결제", "트랜잭션", "내역" = Payment 엔티티!**
- needs_clarification은 **절대로** true로 설정하지 마세요!
- 도메인 용어가 있으면 바로 해당 엔티티로 QueryPlan을 생성하세요."""

    async def _get_rag_context(self, user_message: str) -> str:
        """RAG 서비스에서 관련 문서 검색"""
        if not self._rag_enabled:
            return ""

        try:
            rag_service = get_rag_service()
            documents = await rag_service.search_docs(
                query=user_message,
                k=self._rag_top_k
            )

            if documents:
                context = rag_service.format_context(documents)
                logger.info(f"RAG context retrieved: {len(documents)} documents")
                return context
            else:
                logger.info("No RAG documents found")
                return ""

        except Exception as e:
            logger.warning(f"Failed to get RAG context: {e}")
            return ""

    async def generate_query_plan(
        self,
        user_message: str,
        conversation_context: Optional[str] = None,
        enable_validation: bool = True
    ) -> Dict[str, Any]:
        """
        자연어 메시지를 QueryPlan으로 변환 (2단계 검증 포함)

        Args:
            user_message: 사용자 입력 메시지
            conversation_context: 이전 대화 컨텍스트 (선택)
            enable_validation: 2단계 검증 활성화 여부 (기본: True)

        Returns:
            QueryPlan 딕셔너리
        """
        logger.info(f"Generating QueryPlan for: {user_message}")

        # 1단계: Generator - QueryPlan 생성
        query_plan = await self._generate_initial_plan(user_message, conversation_context)

        # 2단계: Validator - 품질 검증 (활성화된 경우)
        if enable_validation:
            query_plan = await self._validate_and_correct(
                user_message, query_plan, conversation_context
            )

        return query_plan

    async def _generate_initial_plan(
        self,
        user_message: str,
        conversation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """1단계: Generator - 초기 QueryPlan 생성"""
        # RAG 컨텍스트 검색
        rag_context = await self._get_rag_context(user_message)

        try:
            llm = self._get_llm()

            # Structured output을 위한 chain 구성
            # method="function_calling"으로 Any 타입 필드 지원
            structured_llm = llm.with_structured_output(QueryPlan, method="function_calling")

            # 프롬프트 구성 (RAG 컨텍스트 포함)
            from langchain_core.prompts import ChatPromptTemplate

            system_prompt = self._build_system_prompt()

            # RAG 컨텍스트가 있으면 시스템 프롬프트에 추가
            # (JSON 중괄호를 escape하여 ChatPromptTemplate 변수 충돌 방지)
            if rag_context:
                rag_context_escaped = escape_template_braces(rag_context)
                system_prompt = f"{system_prompt}\n\n{rag_context_escaped}"

            # 대화 컨텍스트가 있으면 시스템 프롬프트에 추가
            # (사용자 입력에 {변수} 패턴이 있을 수 있음)
            if conversation_context:
                conversation_context_escaped = escape_template_braces(conversation_context)
                system_prompt = f"{system_prompt}\n\n{conversation_context_escaped}"
                logger.info("Added conversation context to system prompt")

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{user_message}")
            ])

            chain = prompt | structured_llm

            # 실행
            result: QueryPlan = await chain.ainvoke({"user_message": user_message})

            # Pydantic 모델을 딕셔너리로 변환
            query_plan = self._convert_to_dict(result)

            logger.info(f"Generated initial QueryPlan: {query_plan}")
            return query_plan

        except Exception as e:
            logger.error(f"Failed to generate QueryPlan: {e}")
            # 폴백: 기본 QueryPlan 반환
            return self._create_fallback_plan(user_message)

    async def _validate_and_correct(
        self,
        user_message: str,
        query_plan: Dict[str, Any],
        conversation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """2단계: Validator - 품질 검증 및 자동 수정"""
        from app.services.query_plan_validator import get_query_plan_validator

        try:
            validator = get_query_plan_validator()
            validation_result = await validator.validate(
                user_message, query_plan, conversation_context
            )

            logger.info(
                f"Validation result: score={validation_result.quality_score:.2f}, "
                f"valid={validation_result.is_valid}, "
                f"issues={len(validation_result.issues)}"
            )

            # 자동 수정된 plan이 있으면 우선 사용
            if validation_result.corrected_plan:
                logger.info("Using auto-corrected plan")
                corrected = validation_result.corrected_plan
                corrected["_validation"] = {
                    "score": validation_result.quality_score,
                    "issues_count": len(validation_result.issues),
                    "time_ms": validation_result.validation_time_ms,
                    "auto_corrected": True
                }
                return corrected

            # 검증 통과 (corrected_plan 없이)
            if validation_result.is_valid:
                query_plan["_validation"] = {
                    "score": validation_result.quality_score,
                    "issues_count": len(validation_result.issues),
                    "time_ms": validation_result.validation_time_ms
                }
                return query_plan

            # clarification 필요
            if validation_result.clarification_needed:
                return {
                    "needs_clarification": True,
                    "clarification_question": validation_result.clarification_question,
                    "clarification_options": validation_result.clarification_options or [],
                    "_validation": {
                        "score": validation_result.quality_score,
                        "issues": [
                            {"type": i.type.value, "message": i.message}
                            for i in validation_result.issues
                        ]
                    }
                }

            # 검증 실패했지만 clarification도 불필요한 경우 (원본 반환)
            query_plan["_validation"] = {
                "score": validation_result.quality_score,
                "issues_count": len(validation_result.issues),
                "time_ms": validation_result.validation_time_ms,
                "warning": "Validation failed but no clarification needed"
            }
            return query_plan

        except Exception as e:
            logger.error(f"Validation failed with error: {e}")
            # 검증 실패 시 원본 반환
            query_plan["_validation"] = {"error": str(e)}
            return query_plan

    # 시계열 데이터 엔티티 (timeRange 필수)
    TIME_SERIES_ENTITIES = {"Payment", "PaymentHistory", "BalanceTransaction"}

    def _get_default_time_range(self) -> Dict[str, str]:
        """기본 시간 범위 반환 (최근 7일)"""
        now = datetime.now()
        start = now - timedelta(days=7)
        return {
            "start": start.strftime("%Y-%m-%dT00:00:00Z"),
            "end": now.strftime("%Y-%m-%dT23:59:59Z")
        }

    def _get_enum_value(self, val) -> Any:
        """enum 또는 string에서 값 추출"""
        if val is None:
            return None
        if hasattr(val, 'value'):
            return val.value
        return val

    def _convert_to_dict(self, plan: QueryPlan) -> Dict[str, Any]:
        """QueryPlan Pydantic 모델을 API용 딕셔너리로 변환"""
        # Clarification 요청인 경우
        if plan.needs_clarification:
            return {
                "needs_clarification": True,
                "clarification_question": plan.clarification_question,
                "clarification_options": plan.clarification_options or []
            }

        # 일반 쿼리 (entity가 필수)
        result = {
            "entity": self._get_enum_value(plan.entity),
            "operation": self._get_enum_value(plan.operation) or "list",
            "limit": plan.limit,
            "query_intent": self._get_enum_value(plan.query_intent) or "new_query",
            "needs_result_clarification": plan.needs_result_clarification,
            "direct_answer": plan.direct_answer
        }

        if plan.filters:
            result["filters"] = [
                {
                    "field": f.field if hasattr(f, 'field') else f.get('field'),
                    "operator": normalize_operator(
                        self._get_enum_value(f.operator if hasattr(f, 'operator') else f.get('operator'))
                    ),
                    "value": f.value if hasattr(f, 'value') else f.get('value')
                }
                for f in plan.filters
            ]

        if plan.aggregations:
            result["aggregations"] = [
                {
                    "function": a.function,
                    "field": a.field,
                    "alias": a.alias,
                    "displayLabel": a.displayLabel,
                    "currency": a.currency
                }
                for a in plan.aggregations
            ]

        if plan.group_by:
            result["groupBy"] = plan.group_by

        if plan.order_by:
            result["orderBy"] = [
                {"field": o.field, "direction": o.direction}
                for o in plan.order_by
            ]

        if plan.time_range:
            result["timeRange"] = {
                "start": plan.time_range.start,
                "end": plan.time_range.end
            }
        # limit이 있으면 timeRange 없이도 동작 (ORDER BY + LIMIT으로 최신 N건 조회)

        # 사용자가 명시한 렌더링 타입 (표로, 차트로 등)
        if plan.preferred_render_type:
            result["preferredRenderType"] = plan.preferred_render_type

        return result

    def _create_fallback_plan(self, user_message: str) -> Dict[str, Any]:
        """LLM 실패 시 clarification 요청 반환 (키워드 기반 추측 제거)"""
        logger.warning("LLM failed, requesting clarification")

        return {
            "needs_clarification": True,
            "clarification_question": f"'{user_message}'에 대해 어떤 데이터를 조회하시겠습니까?",
            "clarification_options": [
                "결제 내역 (Payment)",
                "환불 내역 (Refund)",
                "가맹점 정보 (Merchant)",
                "정산 내역 (Settlement)"
            ]
        }


# 싱글톤 인스턴스
_query_planner_instance: Optional[QueryPlannerService] = None


def get_query_planner() -> QueryPlannerService:
    """QueryPlannerService 싱글톤 인스턴스 반환"""
    global _query_planner_instance
    if _query_planner_instance is None:
        _query_planner_instance = QueryPlannerService()
    return _query_planner_instance
