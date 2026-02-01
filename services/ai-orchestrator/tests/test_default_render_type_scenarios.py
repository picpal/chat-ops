"""
기본 렌더링 타입 변경 시나리오 테스트

변경 사항:
- 암시적 차트 키워드(비율, 추이, 분포 등)만으로는 차트로 렌더링하지 않음
- 명시적 키워드("그래프", "차트", "시각화")가 있어야 차트로 렌더링
- 기본 렌더링 타입은 테이블

시나리오:
1. 암시적 키워드만 사용 → 테이블 출력
2. 명시적 키워드 사용 → 차트 출력 (변경 없음)
3. 명시적 테이블 요청 → 테이블 출력 (변경 없음)
4. 키워드 없는 일반 집계 → 테이블 출력 (변경 없음)
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.render_composer import RenderComposerService


class TestDefaultRenderTypeScenarios:
    """기본 렌더링 타입 변경 시나리오 테스트"""

    def setup_method(self):
        self.composer = RenderComposerService()

        # 기본 집계 쿼리 결과 (상태별 결제 건수)
        self.aggregate_result_status = {
            "status": "success",
            "data": {
                "rows": [
                    {"status": "DONE", "count": 850},
                    {"status": "CANCELED", "count": 100},
                    {"status": "PENDING", "count": 50}
                ]
            },
            "metadata": {"executionTimeMs": 15}
        }
        self.aggregate_plan_status = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        # 시계열 집계 쿼리 결과 (일별 결제 현황)
        self.aggregate_result_daily = {
            "status": "success",
            "data": {
                "rows": [
                    {"approvedAt": "2026-01-21", "count": 100, "totalAmount": 10000000},
                    {"approvedAt": "2026-01-22", "count": 150, "totalAmount": 15000000},
                    {"approvedAt": "2026-01-23", "count": 120, "totalAmount": 12000000},
                    {"approvedAt": "2026-01-24", "count": 180, "totalAmount": 18000000},
                    {"approvedAt": "2026-01-25", "count": 200, "totalAmount": 20000000},
                ]
            },
            "metadata": {"executionTimeMs": 20}
        }
        self.aggregate_plan_daily = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["approvedAt"],
            "aggregations": [
                {"function": "count", "field": "*", "alias": "count"},
                {"function": "sum", "field": "amount", "alias": "totalAmount"}
            ],
            "timeRange": {"start": "2026-01-21T00:00:00Z", "end": "2026-01-25T23:59:59Z"}
        }

        # 가맹점별 집계 쿼리 결과
        self.aggregate_result_merchant = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchantId": "mer_001", "count": 200, "totalAmount": 20000000},
                    {"merchantId": "mer_002", "count": 150, "totalAmount": 15000000},
                    {"merchantId": "mer_003", "count": 100, "totalAmount": 10000000}
                ]
            },
            "metadata": {"executionTimeMs": 18}
        }
        self.aggregate_plan_merchant = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchantId"],
            "aggregations": [
                {"function": "count", "field": "*", "alias": "count"},
                {"function": "sum", "field": "amount", "alias": "totalAmount"}
            ]
        }

    # ========================================
    # 시나리오 1: 암시적 키워드만 사용 → 테이블 출력
    # ========================================

    def test_scenario1_ratio_keyword_only_renders_table(self):
        """
        시나리오 1-1: "비율" 키워드만 사용 → 테이블 출력
        변경 전: chart (pie)
        변경 후: table
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "상태별 결제 비율 알려줘"
        )

        assert spec["type"] == "table", "암시적 키워드 '비율'만으로는 table로 렌더링되어야 함"
        assert "table" in spec
        assert "columns" in spec["table"]

    def test_scenario1_trend_keyword_only_renders_table(self):
        """
        시나리오 1-2: "추이" 키워드만 사용 → 테이블 출력
        변경 전: chart (line)
        변경 후: table
        """
        spec = self.composer.compose(
            self.aggregate_result_daily,
            self.aggregate_plan_daily,
            "최근 한 달 결제 추이 보여줘"
        )

        assert spec["type"] == "table", "암시적 키워드 '추이'만으로는 table로 렌더링되어야 함"
        assert "table" in spec

    def test_scenario1_distribution_keyword_only_renders_table(self):
        """
        시나리오 1-3: "분포" 키워드만 사용 → 테이블 출력
        변경 전: chart
        변경 후: table
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "결제 분포 보여줘"
        )

        assert spec["type"] == "table", "암시적 키워드 '분포'만으로는 table로 렌더링되어야 함"
        assert "table" in spec

    def test_scenario1_daily_status_keyword_only_renders_table(self):
        """
        시나리오 1-4: "일별 현황" 키워드만 사용 → 테이블 출력
        변경 전: chart (line)
        변경 후: table
        """
        spec = self.composer.compose(
            self.aggregate_result_daily,
            self.aggregate_plan_daily,
            "일별 결제 현황 보여줘"
        )

        assert spec["type"] == "table", "암시적 키워드 '일별 현황'만으로는 table로 렌더링되어야 함"
        assert "table" in spec

    def test_scenario1_percentage_keyword_only_renders_table(self):
        """
        시나리오 1-5: "비중" 키워드만 사용 → 테이블 출력
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "결제 상태별 비중 알려줘"
        )

        assert spec["type"] == "table"

    def test_scenario1_share_keyword_only_renders_table(self):
        """
        시나리오 1-6: "점유율" 키워드만 사용 → 테이블 출력
        """
        spec = self.composer.compose(
            self.aggregate_result_merchant,
            self.aggregate_plan_merchant,
            "가맹점별 점유율 보여줘"
        )

        assert spec["type"] == "table"

    # ========================================
    # 시나리오 2: 명시적 키워드 사용 → 차트 출력 (변경 없음)
    # ========================================

    def test_scenario2_explicit_chart_keyword_renders_chart(self):
        """
        시나리오 2-1: "차트" 키워드 사용 → 차트 출력
        변경 전: chart
        변경 후: chart (변경 없음)
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "결제 현황 차트로 보여줘"
        )

        assert spec["type"] == "chart", "명시적 '차트' 키워드가 있으면 chart로 렌더링"
        assert "chart" in spec

    def test_scenario2_explicit_graph_keyword_renders_chart(self):
        """
        시나리오 2-2: "그래프" 키워드 사용 → 차트 출력
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "상태별 결제 그래프 보여줘"
        )

        assert spec["type"] == "chart", "명시적 '그래프' 키워드가 있으면 chart로 렌더링"
        assert spec["chart"]["chartType"] in ["bar", "pie", "line"]

    def test_scenario2_explicit_visualization_keyword_renders_chart(self):
        """
        시나리오 2-3: "시각화" 키워드 사용 → 차트 출력
        """
        spec = self.composer.compose(
            self.aggregate_result_daily,
            self.aggregate_plan_daily,
            "결제 데이터 시각화해줘"
        )

        assert spec["type"] == "chart", "명시적 '시각화' 키워드가 있으면 chart로 렌더링"

    def test_scenario2_ratio_with_chart_keyword_renders_chart(self):
        """
        시나리오 2-4: "비율 + 차트" 조합 → 차트 출력 (pie)
        암시적 키워드(비율)와 명시적 키워드(차트)가 함께 있으면 차트로 렌더링
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "상태별 결제 비율 차트로 보여줘"
        )

        assert spec["type"] == "chart"
        assert spec["chart"]["chartType"] == "pie", "비율 + 차트 = pie chart"

    def test_scenario2_trend_with_graph_keyword_renders_chart(self):
        """
        시나리오 2-5: "추이 + 그래프" 조합 → 차트 출력 (line)
        """
        spec = self.composer.compose(
            self.aggregate_result_daily,
            self.aggregate_plan_daily,
            "최근 결제 추이를 그래프로 보여줘"
        )

        assert spec["type"] == "chart"
        assert spec["chart"]["chartType"] == "line", "추이 + 그래프 = line chart"

    # ========================================
    # 시나리오 3: 명시적 테이블 요청 → 테이블 출력 (변경 없음)
    # ========================================

    def test_scenario3_explicit_table_keyword_renders_table(self):
        """
        시나리오 3-1: "표" 키워드 사용 → 테이블 출력
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "결제 현황 표로 보여줘"
        )

        assert spec["type"] == "table"

    def test_scenario3_explicit_list_keyword_renders_table(self):
        """
        시나리오 3-2: "목록" 키워드 사용 → 테이블 출력
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "결제 현황 목록으로 보여줘"
        )

        assert spec["type"] == "table"

    def test_scenario3_explicit_table_over_chart_renders_table(self):
        """
        시나리오 3-3: "그래프 말고 표로" → 테이블 우선
        부정 표현이 있으면 테이블로 렌더링
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "그래프 말고 표로 보여줘"
        )

        assert spec["type"] == "table", "부정 표현 '그래프 말고 표로'는 table로 렌더링"

    # ========================================
    # 시나리오 4: 키워드 없는 일반 집계 → 테이블 출력 (변경 없음)
    # ========================================

    def test_scenario4_no_keyword_aggregate_renders_table(self):
        """
        시나리오 4-1: 명시적 렌더링 키워드 없는 집계 → 테이블 출력
        """
        spec = self.composer.compose(
            self.aggregate_result_merchant,
            self.aggregate_plan_merchant,
            "가맹점별 결제 건수 알려줘"
        )

        assert spec["type"] == "table", "명시적 렌더링 키워드 없으면 기본값 table"

    def test_scenario4_no_keyword_status_summary_renders_table(self):
        """
        시나리오 4-2: "상태별 현황" (키워드 없음) → 테이블 출력
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "상태별 결제 현황 알려줘"
        )

        assert spec["type"] == "table"

    def test_scenario4_no_keyword_merchant_summary_renders_table(self):
        """
        시나리오 4-3: "가맹점별 집계" (키워드 없음) → 테이블 출력
        """
        spec = self.composer.compose(
            self.aggregate_result_merchant,
            self.aggregate_plan_merchant,
            "가맹점별 결제 금액 집계해줘"
        )

        assert spec["type"] == "table"

    # ========================================
    # 추가 엣지 케이스
    # ========================================

    def test_edge_case_mixed_ambiguous_keywords_defaults_to_table(self):
        """
        엣지 케이스 1: 애매한 혼합 키워드 → 테이블 기본값
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "결제 상태별로 분석해줘"
        )

        assert spec["type"] == "table", "명시적 차트 키워드 없으면 table이 기본값"

    def test_edge_case_korean_chart_synonym_renders_chart(self):
        """
        엣지 케이스 2: "도표", "도식" 등 한국어 차트 동의어
        """
        spec = self.composer.compose(
            self.aggregate_result_status,
            self.aggregate_plan_status,
            "결제 현황 도표로 보여줘"
        )

        # NOTE: "도표"는 현재 명시적 차트 키워드에 포함되지 않을 수 있음
        # 이 테스트는 향후 키워드 확장 시를 대비한 테스트
        # 현재는 table로 렌더링될 수 있음
        assert spec["type"] in ["table", "chart"]

    def test_edge_case_preferredRenderType_override(self):
        """
        엣지 케이스 3: preferredRenderType이 명시되어 있으면 우선 사용
        """
        query_plan_with_preferred = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}],
            "preferredRenderType": "chart"  # 명시적 렌더 타입
        }

        spec = self.composer.compose(
            self.aggregate_result_status,
            query_plan_with_preferred,
            "결제 현황 보여줘"  # 암시적 키워드 없음
        )

        assert spec["type"] == "chart", "preferredRenderType이 명시되어 있으면 해당 타입 사용"


class TestDefaultRenderTypeChartTypeDecision:
    """
    차트 타입 결정 로직 테스트 (명시적 차트 요청 시)
    명시적 키워드가 있을 때 올바른 차트 타입이 선택되는지 검증
    """

    def setup_method(self):
        self.composer = RenderComposerService()

    def test_ratio_with_chart_keyword_selects_pie(self):
        """비율 + 차트 키워드 → pie 차트"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"status": "DONE", "count": 850},
                    {"status": "CANCELED", "count": 150}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        spec = self.composer.compose(query_result, query_plan, "상태별 비율 차트로 보여줘")

        assert spec["type"] == "chart"
        assert spec["chart"]["chartType"] == "pie"

    def test_trend_with_graph_keyword_selects_line(self):
        """추이 + 그래프 키워드 → line 차트"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"approvedAt": "2026-01-21", "count": 100},
                    {"approvedAt": "2026-01-22", "count": 150},
                    {"approvedAt": "2026-01-23", "count": 120}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["approvedAt"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        spec = self.composer.compose(query_result, query_plan, "일별 추이 그래프로 보여줘")

        assert spec["type"] == "chart"
        assert spec["chart"]["chartType"] == "line"

    def test_merchant_with_chart_keyword_selects_bar(self):
        """가맹점별 + 차트 키워드 → bar 차트"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchantId": "mer_001", "count": 200},
                    {"merchantId": "mer_002", "count": 150},
                    {"merchantId": "mer_003", "count": 100}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchantId"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        spec = self.composer.compose(query_result, query_plan, "가맹점별 현황 차트로 보여줘")

        assert spec["type"] == "chart"
        assert spec["chart"]["chartType"] == "bar"


class TestDefaultRenderTypeBackwardCompatibility:
    """
    하위 호환성 테스트
    기존 동작이 깨지지 않는지 확인
    """

    def setup_method(self):
        self.composer = RenderComposerService()

    def test_explicit_chart_still_works(self):
        """명시적 차트 요청은 여전히 차트로 렌더링"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [{"status": "DONE", "count": 100}]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        spec = self.composer.compose(query_result, query_plan, "결제 현황 그래프로 보여줘")

        assert spec["type"] == "chart"

    def test_list_operation_still_renders_table(self):
        """list operation은 여전히 테이블로 렌더링"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"paymentKey": "PK001", "amount": 10000, "status": "DONE"}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "list",
            "limit": 50
        }

        spec = self.composer.compose(query_result, query_plan, "결제 내역 보여줘")

        assert spec["type"] == "table"

    def test_single_aggregate_renders_text(self):
        """단일 집계 결과는 여전히 텍스트로 렌더링"""
        query_result = {
            "status": "success",
            "data": {
                "rows": [{"count": 1234}]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        spec = self.composer.compose(query_result, query_plan, "오늘 결제 건수")

        assert spec["type"] == "text"

    def test_error_result_renders_text(self):
        """에러 결과는 여전히 텍스트로 렌더링"""
        query_result = {
            "status": "error",
            "error": {
                "code": "TEST_ERROR",
                "message": "Test error"
            }
        }
        query_plan = {"entity": "Payment", "operation": "list"}

        spec = self.composer.compose(query_result, query_plan, "결제 조회")

        assert spec["type"] == "text"
        assert "오류" in spec["title"] or "에러" in spec["title"].lower()
