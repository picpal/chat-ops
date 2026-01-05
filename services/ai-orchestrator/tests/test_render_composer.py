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
        """Test aggregate chart RenderSpec composition"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"status": "PAID", "count": 10},
                    {"status": "PENDING", "count": 5}
                ]
            }
        }
        query_plan = {
            "entity": "Order",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        spec = self.composer.compose(query_result, query_plan, "상태별 주문 현황")

        assert spec["type"] == "chart"
        assert "chart" in spec

    def test_compose_log_spec(self):
        """Test log RenderSpec composition"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"timestamp": "2024-01-01T00:00:00Z", "level": "ERROR", "message": "test"}
                ]
            }
        }
        query_plan = {
            "entity": "PaymentLog",
            "operation": "list"
        }

        spec = self.composer.compose(query_result, query_plan, "로그 보여줘")

        assert spec["type"] == "log"
        assert "log" in spec

    def test_get_render_composer_singleton(self):
        """Test singleton instance"""
        instance1 = get_render_composer()
        instance2 = get_render_composer()
        assert instance1 is instance2
