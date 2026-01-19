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


class TestRenderTypeDetection:
    """
    렌더링 타입 감지 테스트 - 키워드 기반 차트/테이블 감지
    Phase 5: 단독 키워드, 혼합 표현, 부정 표현, 암시적 키워드 테스트
    """

    def setup_method(self):
        self.composer = RenderComposerService()
        # 기본 쿼리 결과 (집계 데이터)
        self.aggregate_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"status": "DONE", "count": 100},
                    {"status": "CANCELED", "count": 20},
                    {"status": "PENDING", "count": 10}
                ]
            }
        }
        self.aggregate_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

    def test_chart_keyword_standalone(self):
        """
        단독 키워드 테스트: "그래프 보여줘" -> chart
        조사 없이 "그래프", "차트" 단독으로 사용해도 차트로 인식
        """
        # "그래프" 단독 키워드
        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "그래프 보여줘"
        )
        assert spec["type"] == "chart", "단독 키워드 '그래프'가 chart로 인식되어야 함"

        # "차트" 단독 키워드
        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "차트 만들어줘"
        )
        assert spec["type"] == "chart", "단독 키워드 '차트'가 chart로 인식되어야 함"

        # "시각화" 단독 키워드
        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "시각화 해줘"
        )
        assert spec["type"] == "chart", "단독 키워드 '시각화'가 chart로 인식되어야 함"

    def test_chart_keyword_mixed(self):
        """
        혼합 표현 테스트: "결제 차트로 볼래" -> chart
        문장 중간에 차트 키워드가 포함된 경우
        """
        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "결제 차트로 볼래"
        )
        assert spec["type"] == "chart", "혼합 표현 '결제 차트로 볼래'가 chart로 인식되어야 함"

        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "상태별 결제 그래프로 보여줘"
        )
        assert spec["type"] == "chart", "혼합 표현 '상태별 결제 그래프로 보여줘'가 chart로 인식되어야 함"

        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "이거 시각화로 표현해줘"
        )
        assert spec["type"] == "chart", "혼합 표현 '이거 시각화로 표현해줘'가 chart로 인식되어야 함"

    def test_table_priority(self):
        """
        부정 표현 테스트: "그래프 말고 표로" -> table
        테이블 키워드에 부정 표현이 포함되어 있으면 테이블 우선
        """
        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "그래프 말고 표로 보여줘"
        )
        assert spec["type"] == "table", "부정 표현 '그래프 말고 표로'가 table로 인식되어야 함"

        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "차트 대신 테이블로 보여줘"
        )
        assert spec["type"] == "table", "부정 표현 '차트 대신 테이블로'가 table로 인식되어야 함"

    def test_implicit_keywords_default_to_table(self):
        """
        암시적 키워드 테스트 - 비율: "비율 알려줘" -> table (기본값)
        '비율', '점유율', '분포' 등의 키워드는 명시적 차트 요청이 아니므로 테이블로 표시

        사용자 피드백: "보고용 자료는 표가 좋다"
        "그래프로 보여줘"라고 명시적으로 요청할 때만 차트 사용
        """
        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "상태별 비율 알려줘"
        )
        assert spec["type"] == "table", "암시적 키워드 '비율'은 table이 기본"

        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "결제 분포 보여줘"
        )
        assert spec["type"] == "table", "암시적 키워드 '분포'도 table이 기본"

    def test_trend_keywords_default_to_table(self):
        """
        추이 키워드 테스트 - 추이: "추이 보여줘" -> table (기본값)
        '추이', '추세', '변화' 등의 키워드는 명시적 차트 요청이 아니므로 테이블로 표시

        사용자 피드백: "추이만 있으면 테이블, 그래프로 보여줘라고 할 때만 차트"
        """
        # 시계열 데이터용 결과
        time_series_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"approvedAt": "2024-01-01", "count": 100},
                    {"approvedAt": "2024-01-02", "count": 120},
                    {"approvedAt": "2024-01-03", "count": 90}
                ]
            }
        }
        time_series_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["approvedAt"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}],
            "timeRange": {"start": "2024-01-01", "end": "2024-01-03"}
        }

        # 암시적 키워드만 있으면 테이블
        spec = self.composer.compose(
            time_series_result,
            time_series_plan,
            "최근 결제 추이 보여줘"
        )
        assert spec["type"] == "table", "암시적 키워드 '추이'만 있으면 table이 기본"

        spec = self.composer.compose(
            time_series_result,
            time_series_plan,
            "결제 추세 분석해줘"
        )
        assert spec["type"] == "table", "암시적 키워드 '추세'만 있으면 table이 기본"

    def test_explicit_chart_with_trend(self):
        """
        명시적 차트 요청 테스트 - "추이를 그래프로" -> chart
        암시적 키워드와 명시적 차트 키워드가 함께 있으면 차트 사용
        """
        time_series_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"approvedAt": "2024-01-01", "count": 100},
                    {"approvedAt": "2024-01-02", "count": 120},
                    {"approvedAt": "2024-01-03", "count": 90}
                ]
            }
        }
        time_series_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["approvedAt"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}],
            "timeRange": {"start": "2024-01-01", "end": "2024-01-03"}
        }

        # 명시적 차트 키워드가 있으면 차트
        spec = self.composer.compose(
            time_series_result,
            time_series_plan,
            "최근 결제 추이를 그래프로 보여줘"
        )
        assert spec["type"] == "chart", "명시적 '그래프' 키워드가 있으면 chart"
        assert spec["chart"]["chartType"] == "line", "'추이' + '그래프' = line 차트"

    def test_table_standalone_keyword(self):
        """
        테이블 키워드 테스트: "표 보여줘", "표로" -> table
        NOTE: 단독 "표"는 "표현" 등과 혼동을 피하기 위해 "표 보여", "표로" 형태 사용
        """
        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "표 보여줘"
        )
        assert spec["type"] == "table", "키워드 '표 보여'가 table로 인식되어야 함"

        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "테이블 만들어줘"
        )
        assert spec["type"] == "table", "키워드 '테이블 만들어'가 table로 인식되어야 함"

        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "목록으로 보여줘"
        )
        assert spec["type"] == "table", "키워드 '목록으로'가 table로 인식되어야 함"

        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "표로 정리해줘"
        )
        assert spec["type"] == "table", "키워드 '표로'가 table로 인식되어야 함"

    def test_no_explicit_render_type(self):
        """
        명시적 렌더링 타입이 없는 경우 기본 동작 테스트
        집계 쿼리 + 그룹화 + 여러 행 -> 테이블 기본
        """
        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "상태별 결제 현황 보여줘"  # 명시적 렌더링 키워드 없음
        )
        # groupBy가 있고 여러 행이 있으면 테이블이 기본
        assert spec["type"] == "table", "명시적 키워드 없이 집계 결과는 table이 기본"
