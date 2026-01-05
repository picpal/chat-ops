"""
QueryPlannerService: 자연어를 QueryPlan으로 변환
LangChain + OpenAI를 사용한 Structured Output
RAG 컨텍스트를 활용한 향상된 쿼리 생성
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)


# ============================================
# Pydantic Models for Structured Output
# ============================================

class EntityType(str, Enum):
    ORDER = "Order"
    CUSTOMER = "Customer"
    PRODUCT = "Product"
    INVENTORY = "Inventory"
    PAYMENT_LOG = "PaymentLog"


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
    }
}


class QueryPlannerService:
    """
    자연어를 QueryPlan으로 변환하는 서비스
    LangChain + OpenAI의 Structured Output 사용
    RAG 컨텍스트로 쿼리 생성 품질 향상
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._llm = None
        self._chain = None
        self._rag_enabled = os.getenv("RAG_ENABLED", "true").lower() == "true"
        self._rag_top_k = int(os.getenv("RAG_TOP_K", "3"))

    def _get_llm(self):
        """LLM 인스턴스 지연 초기화"""
        if self._llm is None:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY is not set")

            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=self.api_key
            )
        return self._llm

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        schema_info = json.dumps(ENTITY_SCHEMAS, ensure_ascii=False, indent=2)

        return f"""당신은 전자상거래 백오피스 쿼리 어시스턴트입니다.
사용자의 자연어 요청을 분석하여 적절한 QueryPlan을 생성합니다.

## 사용 가능한 엔티티 및 필드

{schema_info}

## 규칙

1. **엔티티 선택**: 사용자 요청에 가장 적합한 엔티티를 선택하세요.
   - "주문", "order" → Order
   - "고객", "customer" → Customer
   - "상품", "product" → Product
   - "재고", "inventory" → Inventory
   - "결제 로그", "payment log", "에러", "오류" → PaymentLog

2. **작업 유형**:
   - list: 데이터 목록 조회 (기본값)
   - aggregate: 집계/통계 (예: "몇 개", "총합", "평균")
   - search: 텍스트 검색

3. **필터 조건**:
   - 상태 필터: status = "PAID", "PENDING" 등
   - 날짜 필터: orderDate와 between 연산자 사용
   - 고객 필터: customerId = 값
   - 금액 필터: totalAmount와 gt, lt, gte, lte 연산자

4. **정렬**:
   - "최근" → orderDate DESC
   - "오래된" → orderDate ASC
   - "높은 금액" → totalAmount DESC
   - "낮은 금액" → totalAmount ASC

5. **Limit**:
   - 명시된 개수가 있으면 해당 값 사용
   - 없으면 기본값 10

6. **PaymentLog 엔티티**:
   - 시계열 데이터이므로 time_range 필수
   - 명시되지 않으면 최근 24시간으로 설정

## 예시

사용자: "최근 주문 5개 보여줘"
→ entity: Order, operation: list, limit: 5, order_by: [orderDate DESC]

사용자: "결제 완료된 주문만 보여줘"
→ entity: Order, operation: list, filters: [status = PAID]

사용자: "어제 결제 오류 로그 보여줘"
→ entity: PaymentLog, operation: list, filters: [level = ERROR], time_range: 어제 00:00 ~ 23:59"""

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
            structured_llm = llm.with_structured_output(QueryPlan)

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
        """LLM 실패 시 폴백 QueryPlan 생성"""
        logger.warning("Using fallback QueryPlan")

        # 간단한 키워드 기반 폴백
        message_lower = user_message.lower()

        entity = "Order"  # 기본값
        if "고객" in message_lower or "customer" in message_lower:
            entity = "Customer"
        elif "상품" in message_lower or "product" in message_lower:
            entity = "Product"
        elif "재고" in message_lower or "inventory" in message_lower:
            entity = "Inventory"
        elif "로그" in message_lower or "에러" in message_lower or "오류" in message_lower:
            entity = "PaymentLog"

        return {
            "entity": entity,
            "operation": "list",
            "limit": 10
        }


# 싱글톤 인스턴스
_query_planner_instance: Optional[QueryPlannerService] = None


def get_query_planner() -> QueryPlannerService:
    """QueryPlannerService 싱글톤 인스턴스 반환"""
    global _query_planner_instance
    if _query_planner_instance is None:
        _query_planner_instance = QueryPlannerService()
    return _query_planner_instance
