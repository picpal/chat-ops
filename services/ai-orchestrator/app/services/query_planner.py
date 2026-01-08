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
# Pydantic Models for Structured Output
# ============================================

class EntityType(str, Enum):
    # 기존 e-commerce 엔티티
    ORDER = "Order"
    CUSTOMER = "Customer"
    PRODUCT = "Product"
    INVENTORY = "Inventory"
    PAYMENT_LOG = "PaymentLog"
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


class OrderBy(BaseModel):
    field: str = Field(description="정렬 필드")
    direction: str = Field(default="desc", description="정렬 방향: asc 또는 desc")


class TimeRange(BaseModel):
    start: str = Field(description="시작 시간 (ISO 8601)")
    end: str = Field(description="종료 시간 (ISO 8601)")


class QueryPlan(BaseModel):
    """AI가 생성하는 QueryPlan 구조"""
    entity: EntityType = Field(description="조회할 엔티티")
    operation: OperationType = Field(description="작업 유형")
    filters: Optional[List[Filter]] = Field(default=None, description="필터 조건")
    aggregations: Optional[List[Aggregation]] = Field(default=None, description="집계 조건 (operation=aggregate일 때)")
    group_by: Optional[List[str]] = Field(default=None, description="그룹화 필드")
    order_by: Optional[List[OrderBy]] = Field(default=None, description="정렬 조건")
    limit: int = Field(default=10, ge=1, le=100, description="최대 조회 개수")
    time_range: Optional[TimeRange] = Field(default=None, description="시간 범위 (시계열 데이터)")


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
    "Customer": {
        "description": "고객 정보",
        "fields": {
            "customerId": "고객 ID (정수)",
            "name": "고객명 (문자열)",
            "email": "이메일 (문자열)",
            "phone": "전화번호 (문자열)"
        }
    },
    "Product": {
        "description": "상품 정보",
        "fields": {
            "productId": "상품 ID (정수)",
            "name": "상품명 (문자열)",
            "description": "상품 설명 (문자열)",
            "price": "가격 (숫자)",
            "category": "카테고리 (문자열)"
        }
    },
    "Inventory": {
        "description": "재고 정보",
        "fields": {
            "inventoryId": "재고 ID (정수)",
            "productId": "상품 ID (정수)",
            "quantity": "수량 (정수)",
            "warehouse": "창고 (문자열)"
        }
    },
    "PaymentLog": {
        "description": "결제 로그 (시계열 데이터, timeRange 필수)",
        "fields": {
            "logId": "로그 ID (정수)",
            "orderId": "주문 ID (정수)",
            "timestamp": "로그 시간 (날짜/시간)",
            "level": "로그 레벨 (DEBUG, INFO, WARN, ERROR, FATAL)",
            "message": "로그 메시지 (문자열)",
            "errorCode": "에러 코드 (문자열, 선택)"
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
- "결제 로그", "에러 로그", "오류 로그" → **PaymentLog**
- "결제 수단", "등록된 카드" → **PaymentMethod**

## 작업 유형

1. **list**: 데이터 목록 조회 (기본값)
2. **aggregate**: 집계/통계
   - "몇 건", "건수", "개수" → count
   - "총합", "합계", "총" → sum
   - "평균" → avg
   - "최대", "최고" → max
   - "최소", "최저" → min
3. **search**: 텍스트 검색 (LIKE 연산)

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

## 필터 연산자

- **eq**: 같음 (=)
- **ne**: 같지 않음 (!=)
- **gt**: 초과 (>)
- **gte**: 이상 (>=)
- **lt**: 미만 (<)
- **lte**: 이하 (<=)
- **in**: 포함 (IN [...])
- **like**: 패턴 매칭 (LIKE)
- **between**: 범위 (BETWEEN)

## 정렬 규칙

- "최근", "최신" → createdAt DESC 또는 approvedAt DESC
- "오래된" → createdAt ASC
- "높은 금액", "큰 금액" → amount DESC
- "낮은 금액", "작은 금액" → amount ASC
- "추이", "추세" → 날짜 ASC (시계열 차트용)

## 필수 timeRange 엔티티

다음 엔티티는 대용량 시계열 데이터이므로 **timeRange 지정을 강력히 권장**합니다:
- Payment, PaymentHistory, PaymentLog, BalanceTransaction

시간 범위가 명시되지 않은 경우 **최근 7일**로 기본 설정하세요.

## 주의사항

1. 물리적 테이블명이나 컬럼명을 사용하지 마세요 (논리명만 사용)
2. limit의 기본값은 10, 최대값은 100
3. 집계 쿼리(aggregate)에서 groupBy 없이 단순 집계만 할 경우 결과는 단일 값
4. 가맹점ID나 주문번호가 구체적으로 명시되면 해당 값으로 필터링"""

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
        conversation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        자연어 메시지를 QueryPlan으로 변환

        Args:
            user_message: 사용자 입력 메시지
            conversation_context: 이전 대화 컨텍스트 (선택)

        Returns:
            QueryPlan 딕셔너리
        """
        logger.info(f"Generating QueryPlan for: {user_message}")

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
            if rag_context:
                system_prompt = f"{system_prompt}\n\n{rag_context}"

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{user_message}")
            ])

            chain = prompt | structured_llm

            # 실행
            result: QueryPlan = await chain.ainvoke({"user_message": user_message})

            # Pydantic 모델을 딕셔너리로 변환
            query_plan = self._convert_to_dict(result)

            logger.info(f"Generated QueryPlan: {query_plan}")
            return query_plan

        except Exception as e:
            logger.error(f"Failed to generate QueryPlan: {e}")
            # 폴백: 기본 QueryPlan 반환
            return self._create_fallback_plan(user_message)

    def _convert_to_dict(self, plan: QueryPlan) -> Dict[str, Any]:
        """QueryPlan Pydantic 모델을 API용 딕셔너리로 변환"""
        result = {
            "entity": plan.entity.value,
            "operation": plan.operation.value,
            "limit": plan.limit
        }

        if plan.filters:
            result["filters"] = [
                {
                    "field": f.field,
                    "operator": f.operator.value,
                    "value": f.value
                }
                for f in plan.filters
            ]

        if plan.aggregations:
            result["aggregations"] = [
                {
                    "function": a.function,
                    "field": a.field,
                    "alias": a.alias
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

        return result

    def _create_fallback_plan(self, user_message: str) -> Dict[str, Any]:
        """LLM 실패 시 결제 도메인 특화 폴백 QueryPlan 생성"""
        logger.warning("Using fallback QueryPlan")

        message_lower = user_message.lower()

        # 결제 도메인이므로 기본값을 Payment로 설정
        entity = "Payment"

        # 엔티티 키워드 매핑 (우선순위 순)
        entity_keywords = {
            "Refund": ["환불", "refund", "취소환불"],
            "Settlement": ["정산", "settlement", "지급"],
            "Merchant": ["가맹점", "merchant", "상점", "업체"],
            "PaymentHistory": ["이력", "history", "상태 변경"],
            "PaymentLog": ["로그", "log", "에러", "error"],
            "PaymentMethod": ["결제수단", "카드등록", "payment method"],
            "BalanceTransaction": ["잔액", "balance", "거래내역"],
            "Payment": ["결제", "payment", "거래", "트랜잭션", "transaction"],
            # 기존 e-commerce 엔티티
            "Customer": ["고객", "customer"],
            "Order": ["주문", "order"],
            "Product": ["상품", "product"],
            "Inventory": ["재고", "inventory"],
        }

        for ent, keywords in entity_keywords.items():
            if any(kw in message_lower for kw in keywords):
                entity = ent
                break

        # 집계 키워드 감지
        aggregate_keywords = ["통계", "현황", "추이", "추세", "비율", "몇 건", "몇건", "얼마나", "총", "합계", "평균", "건수"]
        operation = "aggregate" if any(kw in message_lower for kw in aggregate_keywords) else "list"

        result = {
            "entity": entity,
            "operation": operation,
            "limit": 10
        }

        # aggregate 연산이면 기본 집계 추가
        if operation == "aggregate":
            result["aggregations"] = [
                {"function": "count", "field": "*", "alias": "count"}
            ]

        return result


# 싱글톤 인스턴스
_query_planner_instance: Optional[QueryPlannerService] = None


def get_query_planner() -> QueryPlannerService:
    """QueryPlannerService 싱글톤 인스턴스 반환"""
    global _query_planner_instance
    if _query_planner_instance is None:
        _query_planner_instance = QueryPlannerService()
    return _query_planner_instance
