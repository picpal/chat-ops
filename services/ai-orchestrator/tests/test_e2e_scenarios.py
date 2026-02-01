"""
E2E 테스트 시나리오 - 결제 도메인 사용자 시나리오

주요 시나리오:
1. 최근 1개월간 결제 추이 → line chart
2. 특정 가맹점 거래 데이터 → table
3. 정상/오류 결제 비율 → pie chart
4. 특정 주문번호 상태 조회 → table/text
5. 특정 시간대 거래 건수 → text (단일 집계)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


class TestRenderComposerChartTypes:
    """RenderComposer 차트 타입 결정 테스트"""

    def test_payment_trend_renders_as_table_without_explicit_chart_keyword(self):
        """명시적 차트 키워드 없이 '추이'만 사용하면 테이블로 렌더링"""
        from app.services.render_composer import RenderComposerService

        render_composer = RenderComposerService()

        query_result = {
            "requestId": "test-123",
            "status": "success",
            "data": {
                "rows": [
                    {"approvedAt": "2025-12-01", "count": 100, "totalAmount": 10000000},
                    {"approvedAt": "2025-12-02", "count": 150, "totalAmount": 15000000},
                    {"approvedAt": "2025-12-03", "count": 120, "totalAmount": 12000000},
                    {"approvedAt": "2025-12-04", "count": 180, "totalAmount": 18000000},
                    {"approvedAt": "2025-12-05", "count": 200, "totalAmount": 20000000},
                    {"approvedAt": "2025-12-06", "count": 170, "totalAmount": 17000000},
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["approvedAt"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}],
            "timeRange": {"start": "2025-12-01T00:00:00Z", "end": "2025-12-31T23:59:59Z"}
        }

        spec = render_composer.compose(query_result, query_plan, "최근 1개월 결제 추이")

        assert spec["type"] == "table"

    def test_payment_trend_renders_as_chart_with_explicit_keyword(self):
        """명시적 차트 키워드('그래프')가 있으면 차트로 렌더링"""
        from app.services.render_composer import RenderComposerService

        render_composer = RenderComposerService()

        query_result = {
            "requestId": "test-123",
            "status": "success",
            "data": {
                "rows": [
                    {"approvedAt": "2025-12-01", "count": 100, "totalAmount": 10000000},
                    {"approvedAt": "2025-12-02", "count": 150, "totalAmount": 15000000},
                    {"approvedAt": "2025-12-03", "count": 120, "totalAmount": 12000000},
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["approvedAt"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}],
            "timeRange": {"start": "2025-12-01T00:00:00Z", "end": "2025-12-31T23:59:59Z"}
        }

        spec = render_composer.compose(query_result, query_plan, "최근 1개월 결제 추이 그래프로 보여줘")

        assert spec["type"] == "chart"
        assert spec["chart"]["chartType"] == "line"

    def test_status_ratio_renders_as_table_without_explicit_chart_keyword(self):
        """명시적 차트 키워드 없이 '비율'만 사용하면 테이블로 렌더링"""
        from app.services.render_composer import RenderComposerService

        render_composer = RenderComposerService()

        query_result = {
            "requestId": "test-456",
            "status": "success",
            "data": {
                "rows": [
                    {"status": "DONE", "count": 950},
                    {"status": "FAILED", "count": 50}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        spec = render_composer.compose(query_result, query_plan, "결제 상태별 비율")

        assert spec["type"] == "table"

    def test_merchant_transactions_render_as_table(self):
        """가맹점 거래 결과가 테이블로 렌더링"""
        from app.services.render_composer import RenderComposerService

        render_composer = RenderComposerService()

        query_result = {
            "requestId": "test-789",
            "status": "success",
            "data": {
                "rows": [
                    {
                        "paymentKey": "PK001",
                        "orderId": "O001",
                        "amount": 50000,
                        "status": "DONE",
                        "method": "CARD"
                    },
                    {
                        "paymentKey": "PK002",
                        "orderId": "O002",
                        "amount": 30000,
                        "status": "DONE",
                        "method": "EASY_PAY"
                    }
                ]
            },
            "metadata": {"executionTimeMs": 15}
        }
        query_plan = {
            "entity": "Payment",
            "operation": "list",
            "filters": [{"field": "merchantId", "operator": "eq", "value": "M001"}],
            "limit": 50
        }

        spec = render_composer.compose(query_result, query_plan, "가맹점 M001 거래")

        assert spec["type"] == "table"
        assert "columns" in spec["table"]
        # Payment 엔티티의 컬럼이 정의되어 있어야 함 (snake_case)
        column_keys = [col["key"] for col in spec["table"]["columns"]]
        assert "payment_key" in column_keys
        assert "amount" in column_keys

    def test_single_count_renders_as_text(self):
        """단순 건수 결과가 텍스트로 렌더링"""
        from app.services.render_composer import RenderComposerService

        render_composer = RenderComposerService()

        query_result = {
            "requestId": "test-count",
            "status": "success",
            "data": {
                "rows": [{"count": 1234}],
                "aggregations": {"count": 1234}
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}],
            "timeRange": {
                "start": "2025-01-05T00:00:00Z",
                "end": "2025-01-05T23:59:59Z"
            }
        }

        spec = render_composer.compose(query_result, query_plan, "오늘 거래 건수")

        assert spec["type"] == "text"
        assert "1,234" in spec["text"]["content"] or "1234" in spec["text"]["content"]


class TestRenderComposerPaymentEntities:
    """Payment 도메인 엔티티 렌더링 테스트"""

    def test_refund_list_has_correct_columns(self):
        """환불 목록이 올바른 컬럼으로 렌더링"""
        from app.services.render_composer import RenderComposerService

        render_composer = RenderComposerService()

        query_result = {
            "requestId": "test-refund",
            "status": "success",
            "data": {
                "rows": [
                    {
                        "refundKey": "RF001",
                        "paymentKey": "PK001",
                        "amount": 10000,
                        "reason": "고객 요청",
                        "status": "DONE"
                    }
                ]
            },
            "metadata": {"executionTimeMs": 10}
        }
        query_plan = {
            "entity": "Refund",
            "operation": "list",
            "limit": 10
        }

        spec = render_composer.compose(query_result, query_plan, "환불 내역")

        assert spec["type"] == "table"
        column_keys = [col["key"] for col in spec["table"]["columns"]]
        assert "refund_key" in column_keys
        assert "payment_key" in column_keys
        assert "amount" in column_keys

    def test_settlement_list_has_correct_columns(self):
        """정산 목록이 올바른 컬럼으로 렌더링"""
        from app.services.render_composer import RenderComposerService

        render_composer = RenderComposerService()

        query_result = {
            "requestId": "test-settlement",
            "status": "success",
            "data": {
                "rows": [
                    {
                        "settlementId": "ST001",
                        "merchantId": "M001",
                        "settlementDate": "2025-01-05",
                        "netAmount": 1000000,
                        "status": "PROCESSED"
                    }
                ]
            },
            "metadata": {"executionTimeMs": 10}
        }
        query_plan = {
            "entity": "Settlement",
            "operation": "list",
            "limit": 10
        }

        spec = render_composer.compose(query_result, query_plan, "정산 내역")

        assert spec["type"] == "table"
        column_keys = [col["key"] for col in spec["table"]["columns"]]
        assert "settlement_id" in column_keys
        assert "net_amount" in column_keys

    def test_merchant_list_has_correct_columns(self):
        """가맹점 목록이 올바른 컬럼으로 렌더링"""
        from app.services.render_composer import RenderComposerService

        render_composer = RenderComposerService()

        query_result = {
            "requestId": "test-merchant",
            "status": "success",
            "data": {
                "rows": [
                    {
                        "merchantId": "M001",
                        "businessName": "테스트 상점",
                        "status": "ACTIVE",
                        "feeRate": 0.035
                    }
                ]
            },
            "metadata": {"executionTimeMs": 10}
        }
        query_plan = {
            "entity": "Merchant",
            "operation": "list",
            "limit": 10
        }

        spec = render_composer.compose(query_result, query_plan, "가맹점 목록")

        assert spec["type"] == "table"
        column_keys = [col["key"] for col in spec["table"]["columns"]]
        assert "merchant_id" in column_keys
        assert "business_name" in column_keys


class TestQueryPlannerFallback:
    """QueryPlanner fallback 로직 테스트 (clarification 반환)"""

    def test_fallback_returns_clarification(self):
        """폴백 시 clarification 요청을 반환"""
        from app.services.query_planner import QueryPlannerService

        planner = QueryPlannerService()
        result = planner._create_fallback_plan("알 수 없는 질문")

        assert result["needs_clarification"] == True
        assert "clarification_question" in result
        assert "clarification_options" in result

    def test_fallback_includes_pg_domain_options(self):
        """폴백 옵션에 PG 도메인 엔티티 포함"""
        from app.services.query_planner import QueryPlannerService

        planner = QueryPlannerService()

        result = planner._create_fallback_plan("환불 내역 보여줘")
        options = result["clarification_options"]
        # PG 도메인 주요 엔티티 옵션 포함 확인
        assert any("Payment" in opt for opt in options)
        assert any("Refund" in opt for opt in options)

    def test_fallback_includes_settlement_option(self):
        """폴백 옵션에 정산 엔티티 포함"""
        from app.services.query_planner import QueryPlannerService

        planner = QueryPlannerService()

        result = planner._create_fallback_plan("정산 현황 알려줘")
        options = result["clarification_options"]
        assert any("Settlement" in opt for opt in options)

    def test_fallback_includes_merchant_option(self):
        """폴백 옵션에 가맹점 엔티티 포함"""
        from app.services.query_planner import QueryPlannerService

        planner = QueryPlannerService()

        result = planner._create_fallback_plan("가맹점 목록")
        options = result["clarification_options"]
        assert any("Merchant" in opt for opt in options)

    def test_fallback_includes_user_message_in_question(self):
        """폴백 질문에 사용자 메시지 포함"""
        from app.services.query_planner import QueryPlannerService

        planner = QueryPlannerService()

        user_message = "결제 건수 알려줘"
        result = planner._create_fallback_plan(user_message)
        assert user_message in result["clarification_question"]


class TestChartTypeDecision:
    """차트 타입 결정 로직 테스트"""

    def test_ratio_keyword_returns_pie(self):
        """비율 키워드가 pie 차트를 반환"""
        from app.services.render_composer import RenderComposerService

        composer = RenderComposerService()

        query_plan = {
            "groupBy": ["status"],
            "timeRange": None
        }
        rows = [{"status": "DONE", "count": 100}, {"status": "FAILED", "count": 10}]

        chart_type = composer._determine_chart_type(query_plan, rows, "결제 성공 비율")
        assert chart_type == "pie"

    def test_date_groupby_returns_line(self):
        """날짜 그룹화가 line 차트를 반환"""
        from app.services.render_composer import RenderComposerService

        composer = RenderComposerService()

        query_plan = {
            "groupBy": ["approvedAt"],
            "timeRange": {"start": "2025-01-01", "end": "2025-01-31"}
        }
        rows = [{"approvedAt": "2025-01-01", "count": 100}] * 10

        chart_type = composer._determine_chart_type(query_plan, rows, "결제 현황")
        assert chart_type == "line"

    def test_trend_keyword_returns_line(self):
        """추이 키워드가 line 차트를 반환"""
        from app.services.render_composer import RenderComposerService

        composer = RenderComposerService()

        query_plan = {
            "groupBy": ["date"],
            "timeRange": {"start": "2025-01-01", "end": "2025-01-31"}
        }
        rows = [{"date": f"2025-01-{i:02d}", "count": 100} for i in range(1, 11)]

        chart_type = composer._determine_chart_type(query_plan, rows, "결제 추이")
        assert chart_type == "line"

    def test_category_groupby_returns_bar(self):
        """카테고리 그룹화가 bar 차트를 반환"""
        from app.services.render_composer import RenderComposerService

        composer = RenderComposerService()

        query_plan = {
            "groupBy": ["method"],
            "timeRange": None
        }
        rows = [
            {"method": "CARD", "count": 100},
            {"method": "EASY_PAY", "count": 50},
            {"method": "TRANSFER", "count": 30}
        ]

        chart_type = composer._determine_chart_type(query_plan, rows, "결제수단별 건수")
        assert chart_type == "bar"


class TestEntitySchemas:
    """엔티티 스키마 정의 테스트"""

    def test_payment_entity_has_required_fields(self):
        """Payment 엔티티에 필수 필드가 정의됨"""
        from app.services.query_planner import ENTITY_SCHEMAS

        assert "Payment" in ENTITY_SCHEMAS
        payment_fields = ENTITY_SCHEMAS["Payment"]["fields"]

        required_fields = ["paymentKey", "orderId", "merchantId", "amount", "status", "method"]
        for field in required_fields:
            assert field in payment_fields, f"Missing field: {field}"

    def test_all_pg_entities_defined(self):
        """모든 PG 엔티티가 정의됨"""
        from app.services.query_planner import ENTITY_SCHEMAS

        pg_entities = [
            "Payment", "Merchant", "PgCustomer", "PaymentMethod",
            "PaymentHistory", "Refund", "BalanceTransaction",
            "Settlement", "SettlementDetail"
        ]

        for entity in pg_entities:
            assert entity in ENTITY_SCHEMAS, f"Missing entity: {entity}"

    def test_entity_columns_match_schemas(self):
        """ENTITY_COLUMNS가 스키마와 일치 (snake_case -> camelCase 변환)"""
        from app.services.render_composer import ENTITY_COLUMNS
        from app.services.query_planner import ENTITY_SCHEMAS

        def snake_to_camel(s: str) -> str:
            """snake_case를 camelCase로 변환"""
            components = s.split('_')
            return components[0] + ''.join(x.title() for x in components[1:])

        # Payment 엔티티 확인
        assert "Payment" in ENTITY_COLUMNS

        # snake_case 컬럼 키를 camelCase로 변환
        payment_column_keys_camel = {snake_to_camel(col["key"]) for col in ENTITY_COLUMNS["Payment"]}
        payment_schema_fields = set(ENTITY_SCHEMAS["Payment"]["fields"].keys())

        # 컬럼 키(camelCase 변환)가 스키마 필드에 있어야 함
        for key in payment_column_keys_camel:
            assert key in payment_schema_fields, f"Column {key} not in schema"


class TestEntityTypeEnum:
    """EntityType enum 테스트"""

    def test_all_pg_entities_in_enum(self):
        """모든 PG 엔티티가 EntityType에 정의됨"""
        from app.services.query_planner import EntityType

        expected_entities = [
            "Payment", "Merchant", "PgCustomer", "PaymentMethod",
            "PaymentHistory", "Refund", "BalanceTransaction",
            "Settlement", "SettlementDetail"
        ]

        enum_values = [e.value for e in EntityType]

        for entity in expected_entities:
            assert entity in enum_values, f"Missing entity in enum: {entity}"
