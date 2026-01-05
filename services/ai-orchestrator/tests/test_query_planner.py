"""
QueryPlannerService 단위 테스트
LLM 호출 없이 순수 로직 테스트 + Mock 기반 통합 테스트
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.query_planner import (
    QueryPlannerService,
    QueryPlan,
    EntityType,
    OperationType,
    Filter,
    FilterOperator,
    Aggregation,
    OrderBy,
    TimeRange,
    ENTITY_SCHEMAS,
    get_query_planner,
)


class TestQueryPlannerService:
    """QueryPlannerService 단위 테스트"""

    def setup_method(self):
        """각 테스트 전 새로운 인스턴스 생성"""
        self.planner = QueryPlannerService(api_key="test-api-key")

    # ========================================
    # Fallback Plan Tests
    # ========================================

    class TestFallbackPlan:
        """_create_fallback_plan 메서드 테스트"""

        def setup_method(self):
            self.planner = QueryPlannerService(api_key="test-api-key")

        def test_fallback_default_entity_is_order(self):
            """기본 엔티티는 Order"""
            result = self.planner._create_fallback_plan("뭔가 보여줘")
            assert result["entity"] == "Order"
            assert result["operation"] == "list"
            assert result["limit"] == 10

        def test_fallback_detects_customer_keywords(self):
            """고객 관련 키워드 감지"""
            test_cases = ["고객 정보 보여줘", "customer list", "고객 목록"]
            for message in test_cases:
                result = self.planner._create_fallback_plan(message)
                assert result["entity"] == "Customer", f"Failed for: {message}"

        def test_fallback_detects_product_keywords(self):
            """상품 관련 키워드 감지"""
            test_cases = ["상품 조회", "product list", "상품 목록"]
            for message in test_cases:
                result = self.planner._create_fallback_plan(message)
                assert result["entity"] == "Product", f"Failed for: {message}"

        def test_fallback_detects_inventory_keywords(self):
            """재고 관련 키워드 감지"""
            test_cases = ["재고 현황", "inventory status", "재고 확인"]
            for message in test_cases:
                result = self.planner._create_fallback_plan(message)
                assert result["entity"] == "Inventory", f"Failed for: {message}"

        def test_fallback_detects_payment_log_keywords(self):
            """결제 로그 관련 키워드 감지"""
            test_cases = ["결제 로그 보여줘", "에러 로그", "오류 내역"]
            for message in test_cases:
                result = self.planner._create_fallback_plan(message)
                assert result["entity"] == "PaymentLog", f"Failed for: {message}"

    # ========================================
    # Convert to Dict Tests
    # ========================================

    class TestConvertToDict:
        """_convert_to_dict 메서드 테스트"""

        def setup_method(self):
            self.planner = QueryPlannerService(api_key="test-api-key")

        def test_convert_basic_plan(self):
            """기본 QueryPlan 변환"""
            plan = QueryPlan(
                entity=EntityType.ORDER,
                operation=OperationType.LIST,
                limit=10
            )
            result = self.planner._convert_to_dict(plan)

            assert result["entity"] == "Order"
            assert result["operation"] == "list"
            assert result["limit"] == 10
            assert "filters" not in result
            assert "aggregations" not in result

        def test_convert_plan_with_filters(self):
            """필터가 있는 QueryPlan 변환"""
            plan = QueryPlan(
                entity=EntityType.ORDER,
                operation=OperationType.LIST,
                filters=[
                    Filter(field="status", operator=FilterOperator.EQ, value="PAID"),
                    Filter(field="totalAmount", operator=FilterOperator.GT, value=1000)
                ],
                limit=20
            )
            result = self.planner._convert_to_dict(plan)

            assert len(result["filters"]) == 2
            assert result["filters"][0]["field"] == "status"
            assert result["filters"][0]["operator"] == "eq"
            assert result["filters"][0]["value"] == "PAID"
            assert result["filters"][1]["operator"] == "gt"

        def test_convert_plan_with_aggregations(self):
            """집계가 있는 QueryPlan 변환"""
            plan = QueryPlan(
                entity=EntityType.ORDER,
                operation=OperationType.AGGREGATE,
                aggregations=[
                    Aggregation(function="count", field="*", alias="total_count"),
                    Aggregation(function="sum", field="totalAmount", alias="revenue")
                ],
                group_by=["status"],
                limit=100
            )
            result = self.planner._convert_to_dict(plan)

            assert len(result["aggregations"]) == 2
            assert result["aggregations"][0]["function"] == "count"
            assert result["aggregations"][0]["alias"] == "total_count"
            assert result["groupBy"] == ["status"]

        def test_convert_plan_with_order_by(self):
            """정렬이 있는 QueryPlan 변환"""
            plan = QueryPlan(
                entity=EntityType.ORDER,
                operation=OperationType.LIST,
                order_by=[
                    OrderBy(field="orderDate", direction="desc"),
                    OrderBy(field="totalAmount", direction="asc")
                ],
                limit=10
            )
            result = self.planner._convert_to_dict(plan)

            assert len(result["orderBy"]) == 2
            assert result["orderBy"][0]["field"] == "orderDate"
            assert result["orderBy"][0]["direction"] == "desc"

        def test_convert_plan_with_time_range(self):
            """시간 범위가 있는 QueryPlan 변환"""
            plan = QueryPlan(
                entity=EntityType.PAYMENT_LOG,
                operation=OperationType.LIST,
                time_range=TimeRange(
                    start="2024-01-01T00:00:00Z",
                    end="2024-01-31T23:59:59Z"
                ),
                limit=50
            )
            result = self.planner._convert_to_dict(plan)

            assert "timeRange" in result
            assert result["timeRange"]["start"] == "2024-01-01T00:00:00Z"
            assert result["timeRange"]["end"] == "2024-01-31T23:59:59Z"

    # ========================================
    # System Prompt Tests
    # ========================================

    class TestSystemPrompt:
        """_build_system_prompt 메서드 테스트"""

        def setup_method(self):
            self.planner = QueryPlannerService(api_key="test-api-key")

        def test_system_prompt_contains_entity_schemas(self):
            """시스템 프롬프트에 엔티티 스키마 포함"""
            prompt = self.planner._build_system_prompt()

            assert "Order" in prompt
            assert "Customer" in prompt
            assert "Product" in prompt
            assert "Inventory" in prompt
            assert "PaymentLog" in prompt

        def test_system_prompt_contains_field_info(self):
            """시스템 프롬프트에 필드 정보 포함"""
            prompt = self.planner._build_system_prompt()

            assert "orderId" in prompt
            assert "customerId" in prompt
            assert "status" in prompt
            assert "totalAmount" in prompt

        def test_system_prompt_contains_operation_types(self):
            """시스템 프롬프트에 작업 유형 설명 포함"""
            prompt = self.planner._build_system_prompt()

            assert "list" in prompt
            assert "aggregate" in prompt
            assert "search" in prompt


class TestEntitySchemas:
    """ENTITY_SCHEMAS 상수 테스트"""

    def test_all_entities_defined(self):
        """모든 엔티티 정의됨"""
        expected_entities = ["Order", "Customer", "Product", "Inventory", "PaymentLog"]
        for entity in expected_entities:
            assert entity in ENTITY_SCHEMAS

    def test_entity_has_description(self):
        """각 엔티티에 description 포함"""
        for entity, schema in ENTITY_SCHEMAS.items():
            assert "description" in schema, f"{entity} missing description"

    def test_entity_has_fields(self):
        """각 엔티티에 fields 포함"""
        for entity, schema in ENTITY_SCHEMAS.items():
            assert "fields" in schema, f"{entity} missing fields"
            assert len(schema["fields"]) > 0, f"{entity} has no fields"


class TestPydanticModels:
    """Pydantic 모델 테스트"""

    def test_query_plan_default_values(self):
        """QueryPlan 기본값"""
        plan = QueryPlan(
            entity=EntityType.ORDER,
            operation=OperationType.LIST
        )
        assert plan.limit == 10
        assert plan.filters is None
        assert plan.aggregations is None

    def test_query_plan_limit_validation(self):
        """QueryPlan limit 범위 검증"""
        # 최소값 테스트
        plan = QueryPlan(
            entity=EntityType.ORDER,
            operation=OperationType.LIST,
            limit=1
        )
        assert plan.limit == 1

        # 최대값 테스트
        plan = QueryPlan(
            entity=EntityType.ORDER,
            operation=OperationType.LIST,
            limit=100
        )
        assert plan.limit == 100

    def test_filter_operators(self):
        """Filter 연산자 테스트"""
        operators = [op.value for op in FilterOperator]
        expected = ["eq", "ne", "gt", "gte", "lt", "lte", "in", "like", "between"]
        assert set(operators) == set(expected)

    def test_entity_types(self):
        """EntityType 값 테스트"""
        entities = [e.value for e in EntityType]
        expected = ["Order", "Customer", "Product", "Inventory", "PaymentLog"]
        assert set(entities) == set(expected)


class TestQueryPlannerSingleton:
    """싱글톤 인스턴스 테스트"""

    def test_get_query_planner_returns_singleton(self):
        """get_query_planner는 싱글톤 반환"""
        # 싱글톤 리셋
        import app.services.query_planner as qp_module
        qp_module._query_planner_instance = None

        instance1 = get_query_planner()
        instance2 = get_query_planner()
        assert instance1 is instance2


@pytest.mark.asyncio
class TestGenerateQueryPlanWithMock:
    """Mock을 사용한 generate_query_plan 테스트"""

    @patch('app.services.query_planner.get_rag_service')
    async def test_generate_query_plan_uses_fallback_on_error(self, mock_rag):
        """LLM 오류 시 fallback 사용"""
        # RAG mock 설정
        mock_rag_instance = MagicMock()
        mock_rag_instance.search_docs = AsyncMock(return_value=[])
        mock_rag_instance.format_context = MagicMock(return_value="")
        mock_rag.return_value = mock_rag_instance

        planner = QueryPlannerService(api_key=None)  # API key 없으면 LLM 실패

        result = await planner.generate_query_plan("최근 주문 보여줘")

        # fallback이 사용됨
        assert result["entity"] == "Order"
        assert result["operation"] == "list"

    @patch('app.services.query_planner.get_rag_service')
    async def test_generate_query_plan_customer_fallback(self, mock_rag):
        """고객 관련 메시지의 fallback"""
        mock_rag_instance = MagicMock()
        mock_rag_instance.search_docs = AsyncMock(return_value=[])
        mock_rag.return_value = mock_rag_instance

        planner = QueryPlannerService(api_key=None)

        result = await planner.generate_query_plan("고객 목록 조회")

        assert result["entity"] == "Customer"
