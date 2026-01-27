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

    def test_implicit_keywords_render_as_chart(self):
        """
        암시적 키워드 테스트 - 비율/분포: "비율 알려줘" -> chart (pie)
        '비율', '점유율', '분포' 등의 키워드는 시각화 의도가 있으므로 차트로 표시

        E2E 시나리오: 사용자가 "상태별 비율"이라고 하면 pie chart 기대
        테이블을 원하면 "표로 보여줘"라고 명시적으로 요청
        """
        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "상태별 비율 알려줘"
        )
        assert spec["type"] == "chart", "암시적 키워드 '비율'은 chart로 렌더링"
        assert spec["chart"]["chartType"] == "pie", "비율 키워드는 pie chart"

        spec = self.composer.compose(
            self.aggregate_result,
            self.aggregate_plan,
            "결제 분포 보여줘"
        )
        assert spec["type"] == "chart", "암시적 키워드 '분포'도 chart로 렌더링"

    def test_trend_keywords_render_as_line_chart(self):
        """
        추이 키워드 테스트 - 추이: "추이 보여줘" -> chart (line)
        '추이', '추세', '변화' 등의 키워드는 시계열 시각화 의도가 있으므로 line chart로 표시

        E2E 시나리오: 사용자가 "결제 추이"라고 하면 line chart 기대
        테이블을 원하면 "표로 보여줘"라고 명시적으로 요청
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

        # 암시적 키워드로 차트 렌더링
        spec = self.composer.compose(
            time_series_result,
            time_series_plan,
            "최근 결제 추이 보여줘"
        )
        assert spec["type"] == "chart", "암시적 키워드 '추이'는 chart로 렌더링"
        assert spec["chart"]["chartType"] == "line", "추이 키워드 + 시계열 데이터는 line chart"

        spec = self.composer.compose(
            time_series_result,
            time_series_plan,
            "결제 추세 분석해줘"
        )
        assert spec["type"] == "chart", "암시적 키워드 '추세'는 chart로 렌더링"

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


class TestChartTypeFieldBasedDetermination:
    """
    차트 타입 자동 결정 테스트 - 필드 타입 기반 로직
    핵심 원칙: 필드 타입 우선 → 키워드는 세부 조정
    """

    def setup_method(self):
        self.composer = RenderComposerService()

    def test_merchant_groupby_returns_bar(self):
        """
        merchantId 그룹화는 bar 차트
        카테고리 필드는 기본적으로 bar 차트로 표시
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchantId": "M001", "count": 100, "totalAmount": 500000},
                    {"merchantId": "M002", "count": 80, "totalAmount": 400000},
                    {"merchantId": "M003", "count": 60, "totalAmount": 300000}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchantId"],
            "aggregations": [
                {"function": "count", "field": "*", "alias": "count"},
                {"function": "sum", "field": "amount", "alias": "totalAmount"}
            ]
        }

        # "추이 그래프"라고 해도 merchantId는 카테고리이므로 bar
        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "가맹점별 매출 추이 그래프"
        )
        assert chart_type == "bar", "merchantId 그룹화는 '추이' 키워드가 있어도 bar"

    def test_merchant_groupby_explicit_bar_keyword(self):
        """
        merchantId 그룹화 + 명시적 bar 키워드
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchantId": "M001", "count": 100},
                    {"merchantId": "M002", "count": 80}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchantId"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "가맹점별 매출 막대 그래프"
        )
        assert chart_type == "bar", "merchantId + '막대' 키워드 = bar"

    def test_date_groupby_returns_line(self):
        """
        시계열 필드 그룹화는 line 차트
        approvedAt, createdAt 등은 기본적으로 line 차트
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"approvedAt": "2024-01-01", "count": 100},
                    {"approvedAt": "2024-01-02", "count": 120},
                    {"approvedAt": "2024-01-03", "count": 90}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["approvedAt"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "일별 결제 현황 그래프"
        )
        assert chart_type == "line", "시계열 필드 groupBy는 line"

    def test_date_groupby_with_trend_keyword(self):
        """
        시계열 필드 + 추이 키워드는 line 차트
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"createdAt": "2024-01-01", "count": 100},
                    {"createdAt": "2024-01-02", "count": 120}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["createdAt"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "일별 결제 추이 그래프"
        )
        assert chart_type == "line", "시계열 + '추이' = line"

    def test_category_with_ratio_returns_pie(self):
        """
        카테고리 그룹화 + 비율 키워드는 pie 차트
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"status": "DONE", "count": 100},
                    {"status": "CANCELED", "count": 20},
                    {"status": "PENDING", "count": 10}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "상태별 비율 차트"
        )
        assert chart_type == "pie", "카테고리 + '비율' = pie"

    def test_method_groupby_returns_bar(self):
        """
        method (결제수단) 그룹화는 bar 차트
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"method": "CARD", "count": 500},
                    {"method": "TRANSFER", "count": 200},
                    {"method": "EASY_PAY", "count": 300}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["method"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "결제수단별 현황 그래프"
        )
        assert chart_type == "bar", "method 그룹화는 bar"

    def test_category_ignores_line_keywords(self):
        """
        카테고리 필드는 line 키워드를 무시 (핵심 테스트)
        "가맹점별 매출 추이 그래프"에서 "추이"가 있어도 bar 유지
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchantId": "M001", "count": 100},
                    {"merchantId": "M002", "count": 80},
                    {"merchantId": "M003", "count": 60},
                    {"merchantId": "M004", "count": 40},
                    {"merchantId": "M005", "count": 30},
                    {"merchantId": "M006", "count": 20},
                    {"merchantId": "M007", "count": 15},
                    {"merchantId": "M008", "count": 10}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchantId"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        # 8개 가맹점 데이터 + "추이" 키워드
        # 이전 로직: 5개 초과 + "추이" → line (❌ 잘못됨)
        # 새 로직: merchantId는 카테고리 → bar (✅ 올바름)
        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "가맹점별 매출 추이 그래프"
        )
        assert chart_type == "bar", "카테고리 필드는 line 키워드('추이')를 무시하고 bar 유지"

    def test_explicit_bar_overrides_date_field(self):
        """
        시계열 필드여도 명시적 bar 키워드가 있으면 bar
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"approvedAt": "2024-01-01", "count": 100},
                    {"approvedAt": "2024-01-02", "count": 120}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["approvedAt"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "일별 결제 막대 그래프로 보여줘"
        )
        assert chart_type == "bar", "시계열이어도 '막대' 키워드가 있으면 bar"

    def test_unknown_field_uses_row_count(self):
        """
        알 수 없는 필드는 행 수에 따라 결정
        5개 이하: bar, 6개 이상: line
        """
        query_result_small = {
            "status": "success",
            "data": {
                "rows": [
                    {"customField": "A", "count": 100},
                    {"customField": "B", "count": 80},
                    {"customField": "C", "count": 60}
                ]
            }
        }
        query_result_large = {
            "status": "success",
            "data": {
                "rows": [
                    {"customField": "A", "count": 100},
                    {"customField": "B", "count": 80},
                    {"customField": "C", "count": 60},
                    {"customField": "D", "count": 40},
                    {"customField": "E", "count": 30},
                    {"customField": "F", "count": 20}
                ]
            }
        }
        query_plan = {
            "entity": "Custom",
            "operation": "aggregate",
            "groupBy": ["customField"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        # 3개 (5개 이하) → bar
        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result_small["data"]["rows"],
            "커스텀 데이터 그래프"
        )
        assert chart_type == "bar", "5개 이하 데이터는 bar"

        # 6개 (5개 초과) → line
        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result_large["data"]["rows"],
            "커스텀 데이터 그래프"
        )
        assert chart_type == "line", "6개 이상 데이터는 line"


class TestChartTypeSnakeCaseFields:
    """
    snake_case 필드명과 SQL 파생 필드 테스트
    실제 SQL 결과에서 groupBy는 snake_case로 올 수 있음
    """

    def setup_method(self):
        self.composer = RenderComposerService()

    def test_snake_case_merchant_id_returns_bar(self):
        """
        snake_case merchant_id도 카테고리로 인식
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchant_id": "mer_001", "total_amount": 5000000},
                    {"merchant_id": "mer_002", "total_amount": 4000000},
                    {"merchant_id": "mer_003", "total_amount": 3000000}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchant_id"],
            "aggregations": [{"function": "sum", "field": "amount", "alias": "total_amount"}]
        }

        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "가맹점별 매출 그래프"
        )
        assert chart_type == "bar", "snake_case merchant_id도 카테고리로 bar"

    def test_month_field_returns_line(self):
        """
        DATE_TRUNC('month', ...) 결과인 month 필드는 시계열로 인식
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"month": "2024-01", "total_amount": 10000000},
                    {"month": "2024-02", "total_amount": 12000000},
                    {"month": "2024-03", "total_amount": 11000000}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["month"],
            "aggregations": [{"function": "sum", "field": "amount", "alias": "total_amount"}]
        }

        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "월별 매출 추이 그래프"
        )
        assert chart_type == "line", "month 필드는 시계열로 line"

    def test_merchant_and_month_with_trend_returns_line(self):
        """
        가맹점별 월별 추이 - 카테고리 + 시계열 + '추이' 키워드
        시계열 필드가 있고 '추이' 키워드가 있으면 line
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchant_id": "mer_001", "month": "2024-01", "total_amount": 5000000},
                    {"merchant_id": "mer_001", "month": "2024-02", "total_amount": 5500000},
                    {"merchant_id": "mer_002", "month": "2024-01", "total_amount": 4000000},
                    {"merchant_id": "mer_002", "month": "2024-02", "total_amount": 4200000}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchant_id", "month"],
            "aggregations": [{"function": "sum", "field": "amount", "alias": "total_amount"}]
        }

        # "추이" 키워드 + 시계열 필드(month)가 있으면 line
        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "최근 3개월, 가맹점별 월별로 추이를 그래프로 보여줘"
        )
        assert chart_type == "line", "카테고리+시계열 + '추이' 키워드 = line"

    def test_merchant_and_month_without_trend_returns_bar(self):
        """
        카테고리 + 시계열 + 명시적 키워드 없음
        기본값은 bar (grouped bar chart)
        NOTE: "월별"은 line 키워드이므로 테스트에서 제외
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchant_id": "mer_001", "month": "2024-01", "total_amount": 5000000},
                    {"merchant_id": "mer_001", "month": "2024-02", "total_amount": 5500000},
                    {"merchant_id": "mer_002", "month": "2024-01", "total_amount": 4000000},
                    {"merchant_id": "mer_002", "month": "2024-02", "total_amount": 4200000}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchant_id", "month"],
            "aggregations": [{"function": "sum", "field": "amount", "alias": "total_amount"}]
        }

        # 명시적 line/bar 키워드 없이 조회 (단, "월별" 등의 암시적 키워드도 제외)
        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "가맹점, 월 기준 매출 현황 그래프"
        )
        assert chart_type == "bar", "카테고리+시계열 기본값 = bar (grouped bar)"

    def test_week_field_returns_line(self):
        """
        DATE_TRUNC('week', ...) 결과인 week 필드도 시계열로 인식
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"week": "2024-W01", "count": 100},
                    {"week": "2024-W02", "count": 120},
                    {"week": "2024-W03", "count": 110}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["week"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        chart_type = self.composer._determine_chart_type(
            query_plan,
            query_result["data"]["rows"],
            "주간 결제 추이 그래프"
        )
        assert chart_type == "line", "week 필드는 시계열로 line"


class TestSummaryStatsGeneration:
    """
    Summary Stats 생성 테스트
    - _calculate_extended_stats()
    - _generate_rule_based_stats()
    - _generate_summary_stats()
    - compose_sql_render_spec()에서 summaryStats 포함 여부
    """

    def setup_method(self):
        from app.services.sql_render_composer import (
            _calculate_extended_stats,
            _generate_rule_based_stats,
            _generate_summary_stats,
            compose_sql_render_spec
        )
        self.calculate_extended_stats = _calculate_extended_stats
        self.generate_rule_based_stats = _generate_rule_based_stats
        self.generate_summary_stats = _generate_summary_stats
        self.compose_sql_render_spec = compose_sql_render_spec

    def test_calculate_extended_stats_pie_chart(self):
        """파이 차트용 확장 통계 계산 (비율, 집중도)"""
        data = [
            {"status": "DONE", "count": 100},
            {"status": "CANCELED", "count": 20},
            {"status": "PENDING", "count": 10}
        ]
        stats = self.calculate_extended_stats(
            data=data,
            x_key="status",
            y_key="count",
            chart_type="pie"
        )

        assert stats["count"] == 3
        assert stats["total"] == 130
        assert stats["max"] == 100
        assert stats["max_category"] == "DONE"
        assert stats["min"] == 10
        assert stats["min_category"] == "PENDING"
        # 파이 차트 전용 필드
        assert "max_share" in stats
        assert stats["max_share"] > 75  # 100/130 = ~76.9%
        assert "concentration" in stats

    def test_calculate_extended_stats_line_chart(self):
        """라인 차트용 확장 통계 계산 (추세, 변동성, 성장률)"""
        data = [
            {"approvedAt": "2024-01-01", "count": 100},
            {"approvedAt": "2024-01-02", "count": 120},
            {"approvedAt": "2024-01-03", "count": 150},
            {"approvedAt": "2024-01-04", "count": 140}
        ]
        stats = self.calculate_extended_stats(
            data=data,
            x_key="approvedAt",
            y_key="count",
            chart_type="line"
        )

        assert stats["count"] == 4
        assert "growth_rate" in stats
        assert "trend" in stats
        assert stats["trend"] in ["증가", "감소", "유지"]
        assert "volatility" in stats
        assert "peak_time" in stats
        assert "period_start" in stats
        assert "period_end" in stats
        assert stats["period_start"] == "2024-01-01"
        assert stats["period_end"] == "2024-01-04"

    def test_calculate_extended_stats_bar_chart(self):
        """바 차트용 확장 통계 계산 (범위, 평균 대비)"""
        data = [
            {"merchantId": "M001", "totalAmount": 500000},
            {"merchantId": "M002", "totalAmount": 400000},
            {"merchantId": "M003", "totalAmount": 300000}
        ]
        stats = self.calculate_extended_stats(
            data=data,
            x_key="merchantId",
            y_key="totalAmount",
            chart_type="bar"
        )

        assert stats["count"] == 3
        assert stats["max"] == 500000
        assert stats["min"] == 300000
        assert "range" in stats
        assert stats["range"] == 200000
        assert "max_vs_avg" in stats
        assert stats["max_vs_avg"] > 0

    def test_generate_rule_based_stats_pie(self):
        """규칙 기반 Summary Stats 생성 - 파이 차트"""
        stats = {
            "count": 3,
            "total": 130,
            "max": 100,
            "min": 10,
            "max_category": "DONE",
            "min_category": "PENDING",
            "max_share": 76.9,
            "min_share": 7.7,
            "concentration": 92.3
        }
        result = self.generate_rule_based_stats(
            stats=stats,
            chart_type="pie",
            x_key="status",
            y_key="count"
        )

        assert "items" in result
        assert "source" in result
        assert result["source"] == "rule"
        assert len(result["items"]) == 5  # max_share, min_share, total, count, concentration

        # 첫 번째 항목은 max_share (highlight=True)
        first_item = result["items"][0]
        assert first_item["key"] == "max_share"
        assert first_item["highlight"] is True
        assert "DONE" in first_item["value"]

    def test_generate_rule_based_stats_line(self):
        """규칙 기반 Summary Stats 생성 - 라인 차트"""
        stats = {
            "count": 4,
            "total": 510,
            "avg": 127.5,
            "max": 150,
            "peak_time": "2024-01-03",
            "growth_rate": 18.5,
            "trend": "증가",
            "period_start": "2024-01-01",
            "period_end": "2024-01-04"
        }
        result = self.generate_rule_based_stats(
            stats=stats,
            chart_type="line",
            x_key="approvedAt",
            y_key="count"
        )

        assert "items" in result
        assert len(result["items"]) == 5  # trend, peak_time, growth_rate, period, avg

        # 첫 번째 항목은 trend (highlight=True)
        first_item = result["items"][0]
        assert first_item["key"] == "trend"
        assert first_item["value"] == "증가"
        assert first_item["highlight"] is True

    def test_generate_rule_based_stats_bar(self):
        """규칙 기반 Summary Stats 생성 - 바 차트"""
        stats = {
            "count": 3,
            "total": 1200000,
            "avg": 400000,
            "max": 500000,
            "min": 300000,
            "max_category": "M001",
            "min_category": "M003",
            "range": 200000,
            "max_vs_avg": 1.25
        }
        result = self.generate_rule_based_stats(
            stats=stats,
            chart_type="bar",
            x_key="merchantId",
            y_key="totalAmount"
        )

        assert "items" in result
        assert len(result["items"]) == 5  # rank_1, rank_last, avg, range, max_vs_avg

        # 첫 번째 항목은 rank_1 (highlight=True)
        first_item = result["items"][0]
        assert first_item["key"] == "rank_1"
        assert "M001" in first_item["value"]
        assert first_item["highlight"] is True

    def test_generate_summary_stats_fallback(self):
        """Summary Stats 생성 - 규칙 기반 폴백 (템플릿 없음)"""
        data = [
            {"status": "DONE", "count": 100},
            {"status": "CANCELED", "count": 20}
        ]
        result = self.generate_summary_stats(
            data=data,
            x_key="status",
            y_key="count",
            chart_type="pie",
            template=None
        )

        assert "items" in result
        assert "source" in result
        assert result["source"] == "rule"
        assert len(result["items"]) > 0

    def test_generate_summary_stats_with_llm_template(self):
        """Summary Stats 생성 - LLM 템플릿 적용"""
        data = [
            {"status": "DONE", "count": 100},
            {"status": "CANCELED", "count": 20}
        ]
        template = [
            {
                "key": "top_category",
                "label": "최다 항목",
                "value": "{maxCategory} ({maxShare})",
                "type": "text",
                "highlight": True,
                "icon": "star"
            },
            {
                "key": "total_count",
                "label": "총 건수",
                "value": "{total}",
                "type": "number",
                "icon": "functions"
            }
        ]
        result = self.generate_summary_stats(
            data=data,
            x_key="status",
            y_key="count",
            chart_type="pie",
            template=template
        )

        assert "items" in result
        assert "source" in result
        assert result["source"] == "llm"
        assert len(result["items"]) == 2

        # 템플릿의 플레이스홀더가 치환되었는지 확인
        first_item = result["items"][0]
        assert first_item["key"] == "top_category"
        assert "DONE" in first_item["value"]
        assert "%" in first_item["value"]  # maxShare가 치환됨

    def test_compose_sql_render_spec_includes_summary_stats(self):
        """compose_sql_render_spec()가 차트 렌더링 시 summaryStats를 포함하는지 확인"""
        result = {
            "data": [
                {"status": "DONE", "count": 100},
                {"status": "CANCELED", "count": 20},
                {"status": "PENDING", "count": 10}
            ],
            "rowCount": 3,
            "sql": "SELECT status, COUNT(*) as count FROM payments GROUP BY status",
            "executionTimeMs": 15
        }

        # 차트로 렌더링
        render_spec = self.compose_sql_render_spec(
            result=result,
            question="상태별 결제 비율 차트로",
            llm_chart_type="pie"
        )

        assert render_spec["type"] == "chart"
        assert "chart" in render_spec
        assert "summaryStats" in render_spec["chart"]

        summary_stats = render_spec["chart"]["summaryStats"]
        assert "items" in summary_stats
        assert "source" in summary_stats
        assert len(summary_stats["items"]) > 0

        # 파이 차트이므로 max_share 항목이 있어야 함
        keys = [item["key"] for item in summary_stats["items"]]
        assert "max_share" in keys

    def test_compose_sql_render_spec_chart_with_insight_and_stats(self):
        """차트 렌더링 시 insight와 summaryStats가 모두 포함되는지 확인"""
        result = {
            "data": [
                {"approvedAt": "2024-01-01", "count": 100},
                {"approvedAt": "2024-01-02", "count": 120},
                {"approvedAt": "2024-01-03", "count": 150}
            ],
            "rowCount": 3,
            "sql": "SELECT approved_at, COUNT(*) FROM payments GROUP BY approved_at",
            "executionTimeMs": 20
        }

        render_spec = self.compose_sql_render_spec(
            result=result,
            question="일별 결제 추이 그래프",
            llm_chart_type="line"
        )

        assert render_spec["type"] == "chart"
        assert "chart" in render_spec

        # insight 확인
        assert "insight" in render_spec["chart"]
        insight = render_spec["chart"]["insight"]
        assert "content" in insight
        assert "source" in insight

        # summaryStats 확인
        assert "summaryStats" in render_spec["chart"]
        summary_stats = render_spec["chart"]["summaryStats"]
        assert "items" in summary_stats
        assert "source" in summary_stats
        assert len(summary_stats["items"]) > 0

        # 라인 차트이므로 trend 항목이 있어야 함
        keys = [item["key"] for item in summary_stats["items"]]
        assert "trend" in keys


class TestMultiSeriesChart:
    """
    멀티 시리즈 차트 테스트
    다중 groupBy(카테고리+시계열) + 추이 키워드일 때 멀티 시리즈 line chart 생성
    """

    def setup_method(self):
        self.composer = RenderComposerService()

    def test_merchant_monthly_trend_multi_series(self):
        """
        가맹점별 월별 추이 -> 멀티 시리즈 line chart
        X축: month (시계열), 시리즈: 가맹점별 line
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchantId": "M001", "month": "2024-01", "totalAmount": 1000000},
                    {"merchantId": "M002", "month": "2024-01", "totalAmount": 800000},
                    {"merchantId": "M001", "month": "2024-02", "totalAmount": 1200000},
                    {"merchantId": "M002", "month": "2024-02", "totalAmount": 900000},
                    {"merchantId": "M001", "month": "2024-03", "totalAmount": 1100000},
                    {"merchantId": "M002", "month": "2024-03", "totalAmount": 850000}
                ]
            },
            "metadata": {"executionTimeMs": 20}
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchantId", "month"],
            "aggregations": [{"function": "sum", "field": "amount", "alias": "totalAmount"}]
        }

        spec = self.composer.compose(
            query_result,
            query_plan,
            "가맹점별 결제금액 추이 그래프 (최근 3개월)"
        )

        assert spec["type"] == "chart", "멀티 시리즈 요청은 chart 타입"
        assert spec["chart"]["chartType"] == "line", "추이 요청은 line chart"
        assert spec["chart"]["xAxis"]["dataKey"] == "month", "X축은 시계열(month)"
        assert "series" in spec["chart"], "시리즈 설정이 있어야 함"
        assert len(spec["chart"]["series"]) == 2, "가맹점 2개 = 시리즈 2개"

        # 시리즈 키 확인
        series_keys = [s["dataKey"] for s in spec["chart"]["series"]]
        assert "M001" in series_keys, "M001 시리즈가 있어야 함"
        assert "M002" in series_keys, "M002 시리즈가 있어야 함"

        # 메타데이터 확인
        assert spec["metadata"]["isMultiSeries"] is True
        assert spec["metadata"]["seriesKey"] == "merchantId"

        # 데이터가 피벗되었는지 확인
        pivoted_rows = spec["data"]["rows"]
        assert len(pivoted_rows) == 3, "3개월 데이터 = 3행"
        first_row = pivoted_rows[0]
        assert "month" in first_row
        assert "M001" in first_row or "M002" in first_row

    def test_status_monthly_trend_multi_series(self):
        """
        상태별 월별 결제 추이 -> 멀티 시리즈 line chart
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"status": "DONE", "month": "2024-01", "count": 100},
                    {"status": "CANCELED", "month": "2024-01", "count": 10},
                    {"status": "DONE", "month": "2024-02", "count": 120},
                    {"status": "CANCELED", "month": "2024-02", "count": 15}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["status", "month"],
            "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
        }

        spec = self.composer.compose(
            query_result,
            query_plan,
            "상태별 월별 결제 건수 추이 차트"
        )

        assert spec["type"] == "chart"
        assert spec["chart"]["chartType"] == "line"
        assert spec["chart"]["xAxis"]["dataKey"] == "month"
        assert len(spec["chart"]["series"]) == 2  # DONE, CANCELED

    def test_single_groupby_no_multi_series(self):
        """
        단일 groupBy는 멀티 시리즈가 아님
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"month": "2024-01", "totalAmount": 1000000},
                    {"month": "2024-02", "totalAmount": 1200000},
                    {"month": "2024-03", "totalAmount": 1100000}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["month"],
            "aggregations": [{"function": "sum", "field": "amount", "alias": "totalAmount"}]
        }

        spec = self.composer.compose(
            query_result,
            query_plan,
            "월별 결제 추이 그래프"
        )

        assert spec["type"] == "chart"
        assert spec["chart"]["chartType"] == "line"
        # 단일 시리즈이므로 isMultiSeries가 False이거나 없음
        assert spec["metadata"].get("isMultiSeries") is False

    def test_no_trend_keyword_no_multi_series(self):
        """
        추이 키워드 없으면 멀티 시리즈 아님 (기본 bar chart)
        NOTE: "월별", "일별" 등도 line 키워드이므로 제외해야 함
        """
        query_result = {
            "status": "success",
            "data": {
                "rows": [
                    {"merchantId": "M001", "month": "2024-01", "totalAmount": 1000000},
                    {"merchantId": "M002", "month": "2024-01", "totalAmount": 800000}
                ]
            }
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchantId", "month"],
            "aggregations": [{"function": "sum", "field": "amount", "alias": "totalAmount"}]
        }

        spec = self.composer.compose(
            query_result,
            query_plan,
            "가맹점, 월 기준 결제 금액 그래프"  # 추이/월별 키워드 없음
        )

        # 추이 키워드 없으면 멀티 시리즈 변환 안 함
        assert spec["metadata"].get("isMultiSeries") is False

    def test_multi_series_top_5_limit(self):
        """
        시리즈가 5개 초과면 상위 5개 + 기타로 그룹화
        """
        # 8개 가맹점 데이터
        rows = []
        for i in range(1, 9):
            for month in ["2024-01", "2024-02"]:
                rows.append({
                    "merchantId": f"M00{i}",
                    "month": month,
                    "totalAmount": 1000000 - (i * 100000)
                })

        query_result = {
            "status": "success",
            "data": {"rows": rows}
        }
        query_plan = {
            "entity": "Payment",
            "operation": "aggregate",
            "groupBy": ["merchantId", "month"],
            "aggregations": [{"function": "sum", "field": "amount", "alias": "totalAmount"}]
        }

        spec = self.composer.compose(
            query_result,
            query_plan,
            "가맹점별 결제금액 추이 그래프"
        )

        # 시리즈는 최대 6개 (상위 5개 + 기타)
        assert len(spec["chart"]["series"]) <= 6

        # "그 외" 시리즈가 있어야 함
        series_keys = [s["dataKey"] for s in spec["chart"]["series"]]
        assert any("그 외" in key for key in series_keys), f"Expected '그 외' in series_keys but got {series_keys}"

    def test_identify_multi_series_axis_function(self):
        """
        _identify_multi_series_axis 함수 직접 테스트
        """
        # 카테고리 + 시계열 + 추이 키워드 -> 멀티 시리즈
        x_axis, series_key, is_multi = self.composer._identify_multi_series_axis(
            ["merchantId", "month"],
            "가맹점별 결제금액 추이 그래프"
        )
        assert is_multi is True
        assert x_axis == "month"
        assert series_key == "merchantId"

        # 시계열만 -> 멀티 시리즈 아님
        x_axis, series_key, is_multi = self.composer._identify_multi_series_axis(
            ["month"],
            "월별 결제 추이 그래프"
        )
        assert is_multi is False

        # 카테고리만 -> 멀티 시리즈 아님
        x_axis, series_key, is_multi = self.composer._identify_multi_series_axis(
            ["merchantId"],
            "가맹점별 결제 추이 그래프"
        )
        assert is_multi is False

        # 추이 키워드 없음 -> 멀티 시리즈 아님
        # NOTE: "월별"은 line 키워드이므로 제외
        x_axis, series_key, is_multi = self.composer._identify_multi_series_axis(
            ["merchantId", "month"],
            "가맹점, 월 기준 결제 금액"  # 추이/월별 키워드 없음
        )
        assert is_multi is False

    def test_pivot_data_for_multi_series_function(self):
        """
        _pivot_data_for_multi_series 함수 직접 테스트
        """
        rows = [
            {"merchantId": "M001", "month": "2024-01", "totalAmount": 1000000},
            {"merchantId": "M002", "month": "2024-01", "totalAmount": 800000},
            {"merchantId": "M001", "month": "2024-02", "totalAmount": 1200000},
            {"merchantId": "M002", "month": "2024-02", "totalAmount": 900000}
        ]

        pivoted, series_keys = self.composer._pivot_data_for_multi_series(
            rows,
            x_axis_key="month",
            series_key="merchantId",
            value_key="totalAmount"
        )

        # 피벗 결과 확인
        assert len(pivoted) == 2, "2개월 데이터 = 2행"
        assert "M001" in series_keys
        assert "M002" in series_keys

        # 첫 번째 행 (2024-01) 확인
        jan_row = next(r for r in pivoted if r["month"] == "2024-01")
        assert jan_row["M001"] == 1000000
        assert jan_row["M002"] == 800000


class TestMultiSeriesSqlRenderComposer:
    """
    sql_render_composer.py의 멀티 시리즈 테스트
    """

    def setup_method(self):
        from app.services.sql_render_composer import (
            compose_sql_render_spec,
            _identify_multi_series_axis,
            _pivot_data_for_multi_series
        )
        self.compose = compose_sql_render_spec
        self.identify_multi_series_axis = _identify_multi_series_axis
        self.pivot_data = _pivot_data_for_multi_series

    def test_sql_multi_series_merchant_monthly_trend(self):
        """
        SQL 결과에서 가맹점별 월별 추이 멀티 시리즈 차트
        """
        result = {
            "data": [
                {"merchant_id": "M001", "month": "2024-01", "total_amount": 1000000},
                {"merchant_id": "M002", "month": "2024-01", "total_amount": 800000},
                {"merchant_id": "M001", "month": "2024-02", "total_amount": 1200000},
                {"merchant_id": "M002", "month": "2024-02", "total_amount": 900000}
            ],
            "rowCount": 4,
            "sql": "SELECT merchant_id, month, SUM(amount) FROM payments GROUP BY merchant_id, month",
            "executionTimeMs": 25
        }

        spec = self.compose(
            result,
            "가맹점별 결제금액 추이 그래프",
            llm_chart_type="line"
        )

        assert spec["type"] == "chart"
        assert spec["chart"]["chartType"] == "line"
        assert spec["metadata"]["isMultiSeries"] is True
        assert "series" in spec["chart"]

    def test_sql_identify_multi_series_axis(self):
        """
        SQL 결과 컬럼에서 멀티 시리즈 축 식별
        """
        columns = ["merchant_id", "month", "total_amount"]

        x_axis, series_key, is_multi = self.identify_multi_series_axis(
            columns,
            "가맹점별 결제금액 추이 그래프"
        )

        assert is_multi is True
        assert x_axis == "month"
        assert series_key == "merchant_id"

    def test_sql_pivot_data(self):
        """
        SQL 결과 데이터 피벗 테스트
        """
        rows = [
            {"merchant_id": "M001", "month": "2024-01", "total_amount": 1000000},
            {"merchant_id": "M002", "month": "2024-01", "total_amount": 800000},
            {"merchant_id": "M001", "month": "2024-02", "total_amount": 1200000},
            {"merchant_id": "M002", "month": "2024-02", "total_amount": 900000}
        ]

        pivoted, series_keys = self.pivot_data(
            rows,
            x_axis_key="month",
            series_key="merchant_id",
            value_key="total_amount"
        )

        assert len(pivoted) == 2
        assert "M001" in series_keys
        assert "M002" in series_keys


class TestMultiSeriesSummaryStats:
    """멀티 시리즈 차트 Summary Stats 테스트"""

    def setup_method(self):
        from app.services.sql_render_composer import (
            _calculate_multi_series_stats,
            _generate_multi_series_summary_stats,
            _extract_table_from_sql,
            compose_sql_render_spec
        )
        self.calculate_multi_series_stats = _calculate_multi_series_stats
        self.generate_multi_series_summary_stats = _generate_multi_series_summary_stats
        self.extract_table_from_sql = _extract_table_from_sql
        self.compose = compose_sql_render_spec

    def test_calculate_multi_series_stats(self):
        """
        멀티 시리즈 통계 계산 - 피벗된 데이터 기준
        """
        # 피벗된 데이터 (각 행에 시리즈별 값이 있음)
        chart_data = [
            {"month": "2025-08", "가맹점A": 100000000, "가맹점B": 80000000},
            {"month": "2025-09", "가맹점A": 120000000, "가맹점B": 90000000},
            {"month": "2025-10", "가맹점A": 150000000, "가맹점B": 100000000},
            {"month": "2025-11", "가맹점A": 180000000, "가맹점B": 120000000},
            {"month": "2025-12", "가맹점A": 500000000, "가맹점B": 480000000},  # 피크
            {"month": "2026-01", "가맹점A": 200000000, "가맹점B": 150000000},
        ]

        stats = self.calculate_multi_series_stats(
            chart_data=chart_data,
            x_key="month",
            series_keys=["가맹점A", "가맹점B"],
            chart_type="line"
        )

        # 피크 시점 확인 (전체 합계가 가장 높은 월)
        assert stats["peak_time"] == "2025-12"  # 500M + 480M = 980M
        assert stats["max"] == 980000000

        # 기간 정보
        assert stats["period_start"] == "2025-08"
        assert stats["period_end"] == "2026-01"

        # 전체 통계
        assert stats["count"] == 6
        assert stats["total"] > 0
        assert "growth_rate" in stats
        assert "trend" in stats

    def test_generate_multi_series_summary_stats(self):
        """
        멀티 시리즈 Summary Stats 생성 테스트
        """
        chart_data = [
            {"month": "2025-10", "가맹점A": 100000000, "가맹점B": 80000000},
            {"month": "2025-11", "가맹점A": 150000000, "가맹점B": 100000000},
            {"month": "2025-12", "가맹점A": 200000000, "가맹점B": 150000000},
        ]

        summary_stats = self.generate_multi_series_summary_stats(
            chart_data=chart_data,
            x_key="month",
            series_keys=["가맹점A", "가맹점B"],
            chart_type="line"
        )

        assert "items" in summary_stats
        assert len(summary_stats["items"]) >= 4  # trend, peak_time, period, avg

        # 피크 시점 항목 확인
        peak_item = next((item for item in summary_stats["items"] if item["key"] == "peak_time"), None)
        assert peak_item is not None
        assert "2025-12" in peak_item["value"]

    def test_extract_table_from_sql(self):
        """
        SQL에서 테이블명 추출 테스트
        """
        # 기본 SELECT
        sql1 = "SELECT * FROM payments WHERE status = 'DONE'"
        assert self.extract_table_from_sql(sql1) == "payments"

        # 집계 쿼리
        sql2 = "SELECT merchant_id, SUM(amount) FROM settlements GROUP BY merchant_id"
        assert self.extract_table_from_sql(sql2) == "settlements"

        # 서브쿼리 (첫 번째 FROM만 추출)
        sql3 = "SELECT * FROM refunds r JOIN payments p ON r.payment_id = p.id"
        assert self.extract_table_from_sql(sql3) == "refunds"

        # 빈 문자열
        assert self.extract_table_from_sql("") is None
        assert self.extract_table_from_sql(None) is None

    def test_compose_sql_render_spec_includes_data_source(self):
        """
        SQL RenderSpec에 dataSource 포함 확인
        """
        result = {
            "data": [
                {"merchant_id": "M001", "month": "2024-01", "total_amount": 1000000},
                {"merchant_id": "M002", "month": "2024-01", "total_amount": 800000}
            ],
            "rowCount": 2,
            "sql": "SELECT merchant_id, month, SUM(amount) FROM payments GROUP BY merchant_id, month",
            "executionTimeMs": 25
        }

        spec = self.compose(result, "가맹점별 결제금액 추이 그래프", llm_chart_type="line")

        assert spec["type"] == "chart"
        assert "dataSource" in spec["chart"]
        assert spec["chart"]["dataSource"]["table"] == "payments"
        assert spec["chart"]["dataSource"]["rowCount"] == 2

    def test_multi_series_summary_stats_with_pivoted_data(self):
        """
        멀티 시리즈 차트에서 피벗된 데이터로 Summary Stats 생성
        - 그래프와 일치하는 통계 제공 확인
        """
        result = {
            "data": [
                {"merchant_id": "M001", "month": "2025-08", "total_amount": 100000000},
                {"merchant_id": "M002", "month": "2025-08", "total_amount": 80000000},
                {"merchant_id": "M001", "month": "2025-12", "total_amount": 500000000},
                {"merchant_id": "M002", "month": "2025-12", "total_amount": 480000000},
            ],
            "rowCount": 4,
            "sql": "SELECT merchant_id, month, SUM(amount) FROM payments GROUP BY merchant_id, month",
            "executionTimeMs": 25
        }

        spec = self.compose(result, "가맹점별 결제금액 추이 그래프", llm_chart_type="line")

        assert spec["type"] == "chart"
        assert spec["metadata"]["isMultiSeries"] is True

        # Summary Stats가 멀티 시리즈용으로 생성되었는지 확인
        summary_stats = spec["chart"]["summaryStats"]
        assert "items" in summary_stats

        # 피크 시점이 2025-12 (980M = 500M + 480M)
        peak_item = next((item for item in summary_stats["items"] if item["key"] == "peak_time"), None)
        if peak_item:
            assert "2025-12" in peak_item["value"]
