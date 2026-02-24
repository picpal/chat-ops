"""
Tests for classify_intent SQL context enhancements (TODO-002)
- _build_results_summary() method extraction
- sql_summary field inclusion in results_summary
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.query_planner import QueryPlannerService


class TestBuildResultsSummary:
    """Tests for _build_results_summary() method"""

    def setup_method(self):
        """Initialize QueryPlannerService for each test"""
        self.planner = QueryPlannerService()

    def test_returns_empty_string_when_no_previous_results(self):
        """_build_results_summary should return empty string for empty list"""
        result = self.planner._build_results_summary([])
        assert result == ""

    def test_returns_empty_string_when_none(self):
        """_build_results_summary should return empty string for None"""
        result = self.planner._build_results_summary(None)
        assert result == ""

    def test_basic_result_without_sql_summary(self):
        """_build_results_summary should work without sql_summary field"""
        previous_results = [
            {
                "index": 0,
                "entity": "payments",
                "count": 30,
                "aggregation": None,
                "data_summary": "결제 목록",
                "total_amount": None,
                "groupByColumns": [],
                "groupByValues": [],
            }
        ]
        result = self.planner._build_results_summary(previous_results)

        assert "payments" in result
        assert "30건" in result
        assert "이전 조회 결과" in result

    def test_results_summary_includes_sql_summary(self):
        """
        RED test: _build_results_summary should include sql_summary when present.
        When previous_results has a sql_summary field, results_summary should
        contain "SQL 로직" text with the sql_summary content.
        """
        previous_results = [
            {
                "index": 0,
                "entity": "settlements",
                "count": 2,
                "aggregation": None,
                "data_summary": "정산 집계 결과",
                "total_amount": None,
                "groupByColumns": ["merchant_id"],
                "groupByValues": [{"merchant_id": "mer_001"}],
                "sql_summary": "집계: AVG(payment_count) | FROM settlements | GROUP BY merchant_id",
            }
        ]
        result = self.planner._build_results_summary(previous_results)

        # Should include "SQL 로직" section with the sql_summary content
        assert "SQL 로직" in result, f"Expected 'SQL 로직' in result, got: {result}"
        assert "AVG(payment_count)" in result, f"Expected sql_summary content in result, got: {result}"

    def test_results_summary_with_multiple_results_some_with_sql_summary(self):
        """
        results_summary should include sql_summary only for results that have it
        """
        previous_results = [
            {
                "index": 0,
                "entity": "payments",
                "count": 10,
                "aggregation": None,
                "data_summary": "결제 목록",
                "total_amount": None,
                "groupByColumns": [],
                "groupByValues": [],
                # No sql_summary field
            },
            {
                "index": 1,
                "entity": "settlements",
                "count": 3,
                "aggregation": None,
                "data_summary": "정산 집계",
                "total_amount": None,
                "groupByColumns": ["merchant_id"],
                "groupByValues": [],
                "sql_summary": "집계: SUM(amount) | FROM settlements | GROUP BY merchant_id",
            }
        ]
        result = self.planner._build_results_summary(previous_results)

        # sql_summary from second result should appear
        assert "SQL 로직" in result
        assert "SUM(amount)" in result

        # Both entities should be in result
        assert "payments" in result
        assert "settlements" in result

    def test_results_summary_with_total_amount(self):
        """_build_results_summary should include total_amount info"""
        previous_results = [
            {
                "index": 0,
                "entity": "payments",
                "count": 5,
                "aggregation": None,
                "data_summary": "",
                "total_amount": 1949000,
                "groupByColumns": [],
                "groupByValues": [],
            }
        ]
        result = self.planner._build_results_summary(previous_results)

        assert "1,949,000" in result
        assert "계산에 사용할 금액" in result

    def test_results_summary_sql_summary_format(self):
        """
        sql_summary should appear with '| **SQL 로직**: {sql_summary}' format
        """
        sql_summary_text = "집계: AVG(payment_count) | FROM settlements | GROUP BY merchant_id"
        previous_results = [
            {
                "index": 0,
                "entity": "settlements",
                "count": 2,
                "aggregation": None,
                "data_summary": "",
                "total_amount": None,
                "groupByColumns": [],
                "groupByValues": [],
                "sql_summary": sql_summary_text,
            }
        ]
        result = self.planner._build_results_summary(previous_results)

        # Check format: "| **SQL 로직**: {sql_summary}"
        expected_fragment = f"**SQL 로직**: {sql_summary_text}"
        assert expected_fragment in result, f"Expected '{expected_fragment}' in result, got: {result}"

    def test_results_summary_empty_sql_summary_not_included(self):
        """
        sql_summary that is None or empty string should not add SQL 로직 section
        """
        previous_results = [
            {
                "index": 0,
                "entity": "payments",
                "count": 10,
                "aggregation": None,
                "data_summary": "결제 목록",
                "total_amount": None,
                "groupByColumns": [],
                "groupByValues": [],
                "sql_summary": None,
            }
        ]
        result = self.planner._build_results_summary(previous_results)
        assert "SQL 로직" not in result
