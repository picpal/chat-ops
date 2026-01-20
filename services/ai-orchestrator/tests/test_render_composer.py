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
