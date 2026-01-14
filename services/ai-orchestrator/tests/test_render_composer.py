"""
RenderComposerService tests
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.render_composer import RenderComposerService, get_render_composer


class TestRenderComposerService:
    """RenderComposerService tests"""

    def setup_method(self):
        self.composer = RenderComposerService()

    def test_compose_table_spec(self):
        """Test table RenderSpec composition"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"orderId": 1, "status": "PAID", "totalAmount": 1000}
                ]
            },
            "metadata": {"executionTimeMs": 10}
        }
        query_plan = {
            "entity": "Order",
            "operation": "list",
            "limit": 10
        }

        spec = self.composer.compose(query_result, query_plan, "최근 주문 보여줘")

        assert spec["type"] == "table"
        assert "title" in spec
        assert "table" in spec
        assert "columns" in spec["table"]
        assert "data" in spec

    def test_compose_error_spec(self):
        """Test error RenderSpec composition"""
        query_result = {
            "status": "error",
            "error": {
                "code": "TEST_ERROR",
                "message": "Test error message"
            }
        }
        query_plan = {
            "entity": "Order",
            "operation": "list"
        }

        spec = self.composer.compose(query_result, query_plan, "테스트")

        assert spec["type"] == "text"
        assert "오류" in spec["title"]

    def test_compose_aggregate_chart_spec(self):
        """Test aggregate chart RenderSpec composition with preferredRenderType"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"status": "DONE", "count": 10},
                    {"status": "CANCELED", "count": 5}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}],
            "preferredRenderType": "chart"  # 명시적 차트 요청
        }

        spec = self.composer.compose(query_result, query_plan, "상태별 결제 현황 차트로")

        assert spec["type"] == "chart"
        assert "chart" in spec

    def test_compose_aggregate_defaults_to_table(self):
        """Test aggregate without preferredRenderType defaults to table"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"status": "DONE", "count": 10},
                    {"status": "CANCELED", "count": 5}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        spec = self.composer.compose(query_result, query_plan, "상태별 결제 현황")

        assert spec["type"] == "table"
        assert "table" in spec

    def test_compose_payment_history_list(self):
        """Test PaymentHistory list RenderSpec composition"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"historyId": 1, "paymentKey": "pay_001", "previousStatus": "READY", "newStatus": "DONE"}
                ]
            }
        }
        query_plan = {
            "entity": "PaymentHistory",
            "operation": "list"
        }

        spec = self.composer.compose(query_result, query_plan, "결제 이력 보여줘")

        assert spec["type"] == "table"
        assert "table" in spec

    def test_compose_aggregate_table_spec(self):
        """Test aggregate query rendered as table with dynamic columns"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchantId": "M001", "count": 10, "totalAmount": 50000},
                    {"merchantId": "M002", "count": 5, "totalAmount": 25000}
                ]
            },
            "metadata": {"executionTimeMs": 15}
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchantId"],
            "aggregations": [
                {"function": "count", "field": "*", "alias": "count"},
                {"function": "sum", "field": "amount", "alias": "totalAmount"}
            ],
            "preferredRenderType": "table"
        }

        spec = self.composer.compose(
            query_result,
            query_plan,
            "최근 3개월 결제를 가맹점별로 표로 보여줘"
        )

        assert spec["type"] == "table"
        assert "table" in spec

        columns = spec["table"]["columns"]
        assert len(columns) == 3  # merchantId, count, totalAmount

        # 컬럼 키가 데이터와 일치하는지 확인 (camelCase)
        column_keys = [col["key"] for col in columns]
        assert "merchantId" in column_keys
        assert "count" in column_keys
        assert "totalAmount" in column_keys

        # 데이터 행의 키와 일치하는지 확인
        data_keys = set(spec["data"]["rows"][0].keys())
        assert set(column_keys) == data_keys

    def test_compose_aggregate_table_spec_with_explicit_table_render(self):
        """Test aggregate query explicitly requesting table format via message"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"status": "PAID", "count": 100},
                    {"status": "PENDING", "count": 30}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [
                {"function": "count", "field": "*", "alias": "count"}
            ]
        }

        # "표로" 키워드가 있으면 테이블로 렌더링
        spec = self.composer.compose(
            query_result,
            query_plan,
            "상태별 결제 현황을 표로 보여줘"
        )

        assert spec["type"] == "table"
        columns = spec["table"]["columns"]
        column_keys = [col["key"] for col in columns]
        assert "status" in column_keys
        assert "count" in column_keys

    def test_get_render_composer_singleton(self):
        """Test singleton instance"""
        instance1 = get_render_composer()
        instance2 = get_render_composer()
        assert instance1 is instance2
