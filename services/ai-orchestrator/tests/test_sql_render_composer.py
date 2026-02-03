"""
SqlRenderComposerService 테스트

암시적 차트 키워드 및 데이터 패턴 기반 렌더링 타입 감지 테스트
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.sql_render_composer import (
    compose_sql_render_spec,
    _detect_render_type_from_message,
    _detect_implicit_chart_type,
    _is_chart_suitable,
)


class TestImplicitChartKeywords:
    """
    암시적 차트 키워드 테스트

    명시적 키워드("그래프", "차트")가 없어도 암시적 키워드 + 적절한 데이터 패턴으로
    차트 렌더링을 트리거하는 기능 테스트
    """

    def test_detect_implicit_chart_type_bar_comparison(self):
        """'비교' 키워드 → bar 차트"""
        assert _detect_implicit_chart_type("가맹점별 매출 비교해줘") == "bar"
        assert _detect_implicit_chart_type("결제수단별 비교 보여줘") == "bar"
        assert _detect_implicit_chart_type("상태별 현황 보여줘") == "bar"

    def test_detect_implicit_chart_type_line_trend(self):
        """'추이' 키워드 → line 차트"""
        assert _detect_implicit_chart_type("일별 매출 추이 보여줘") == "line"
        assert _detect_implicit_chart_type("월별 결제 추세 분석해줘") == "line"
        assert _detect_implicit_chart_type("시간대별 결제 변화") == "line"
        assert _detect_implicit_chart_type("일별 결제 건수") == "line"
        assert _detect_implicit_chart_type("월별 매출 현황") == "line"
        assert _detect_implicit_chart_type("주별 결제 분석") == "line"

    def test_detect_implicit_chart_type_pie_distribution(self):
        """'분포' 키워드 → pie 차트"""
        assert _detect_implicit_chart_type("결제수단별 분포 보여줘") == "pie"
        assert _detect_implicit_chart_type("상태별 비율 알려줘") == "pie"
        assert _detect_implicit_chart_type("카드사별 점유율") == "pie"
        assert _detect_implicit_chart_type("결제수단 비중 분석") == "pie"

    def test_detect_implicit_chart_type_no_match(self):
        """암시적 키워드 없음 → None"""
        assert _detect_implicit_chart_type("최근 결제 10건 보여줘") is None
        assert _detect_implicit_chart_type("결제 내역 조회") is None
        assert _detect_implicit_chart_type("상세 내용 알려줘") is None


class TestChartSuitability:
    """차트 렌더링 적합성 판단 테스트"""

    def test_is_chart_suitable_valid_bar(self):
        """2~10행 데이터 → bar 차트 적합"""
        data = [
            {"status": "DONE", "count": 100},
            {"status": "CANCELED", "count": 20},
            {"status": "PENDING", "count": 10},
        ]
        assert _is_chart_suitable(data, "bar") is True

    def test_is_chart_suitable_valid_line(self):
        """2~10행 데이터 → line 차트 적합"""
        data = [
            {"date": "2024-01-01", "count": 100},
            {"date": "2024-01-02", "count": 120},
            {"date": "2024-01-03", "count": 90},
        ]
        assert _is_chart_suitable(data, "line") is True

    def test_is_chart_suitable_valid_pie(self):
        """2~7행 데이터 → pie 차트 적합"""
        data = [
            {"method": "CARD", "count": 500},
            {"method": "TRANSFER", "count": 200},
            {"method": "EASY_PAY", "count": 300},
        ]
        assert _is_chart_suitable(data, "pie") is True

    def test_is_chart_suitable_empty_data(self):
        """데이터 없음 → 차트 부적합"""
        assert _is_chart_suitable([], "bar") is False
        assert _is_chart_suitable([], "line") is False
        assert _is_chart_suitable([], "pie") is False

    def test_is_chart_suitable_single_row(self):
        """단일 행 → 차트 부적합 (집계 결과)"""
        data = [{"total_amount": 1000000, "count": 100}]
        assert _is_chart_suitable(data, "bar") is False
        assert _is_chart_suitable(data, "line") is False
        assert _is_chart_suitable(data, "pie") is False

    def test_is_chart_suitable_too_many_rows(self):
        """10행 초과 → 차트 부적합"""
        data = [{"status": f"STATUS_{i}", "count": 100 - i} for i in range(15)]
        assert _is_chart_suitable(data, "bar") is False
        assert _is_chart_suitable(data, "line") is False

    def test_is_chart_suitable_pie_too_many_categories(self):
        """pie 차트에서 7개 초과 → 부적합"""
        data = [{"category": f"CAT_{i}", "count": 100 - i} for i in range(8)]
        assert _is_chart_suitable(data, "pie") is False
        # bar와 line은 10개까지 허용
        assert _is_chart_suitable(data, "bar") is True


class TestComposeSqlRenderSpecImplicitChart:
    """
    compose_sql_render_spec()의 암시적 차트 렌더링 테스트

    핵심 시나리오:
    1. "비교" + 적합한 데이터 → bar 차트
    2. "추이" + 적합한 데이터 → line 차트
    3. "분포" + 적합한 데이터 → pie 차트
    4. 명시적 키워드 우선 (override)
    5. 행 제한 보호 (10행 초과 → 테이블)
    """

    def test_comparison_triggers_bar_chart(self):
        """'비교' 키워드 + 적합한 데이터 → bar 차트"""
        result = {
            "data": [
                {"merchant_id": "M001", "total_amount": 5000000},
                {"merchant_id": "M002", "total_amount": 4000000},
                {"merchant_id": "M003", "total_amount": 3000000},
            ],
            "rowCount": 3,
            "sql": "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id",
            "executionTimeMs": 15
        }

        spec = compose_sql_render_spec(result, "가맹점별 매출 비교해줘")

        assert spec["type"] == "chart", "비교 키워드 + 적합한 데이터 → 차트"
        assert spec["chart"]["chartType"] == "bar", "비교 → bar 차트"

    def test_trend_triggers_line_chart(self):
        """'추이' 키워드 + 적합한 데이터 → line 차트"""
        result = {
            "data": [
                {"date": "2024-01-01", "count": 100},
                {"date": "2024-01-02", "count": 120},
                {"date": "2024-01-03", "count": 90},
            ],
            "rowCount": 3,
            "sql": "SELECT date, COUNT(*) FROM payments GROUP BY date",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(result, "일별 오류 추이 보여줘")

        assert spec["type"] == "chart", "추이 키워드 + 적합한 데이터 → 차트"
        assert spec["chart"]["chartType"] == "line", "추이 → line 차트"

    def test_distribution_triggers_pie_chart(self):
        """'분포' 키워드 + 적합한 데이터 → pie 차트"""
        result = {
            "data": [
                {"method": "CARD", "count": 500},
                {"method": "TRANSFER", "count": 200},
                {"method": "EASY_PAY", "count": 300},
            ],
            "rowCount": 3,
            "sql": "SELECT method, COUNT(*) FROM payments GROUP BY method",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(result, "결제수단별 분포 보여줘")

        assert spec["type"] == "chart", "분포 키워드 + 적합한 데이터 → 차트"
        assert spec["chart"]["chartType"] == "pie", "분포 → pie 차트"

    def test_ratio_triggers_pie_chart(self):
        """'비율' 키워드 + 적합한 데이터 → pie 차트"""
        result = {
            "data": [
                {"status": "DONE", "count": 100},
                {"status": "CANCELED", "count": 20},
                {"status": "PENDING", "count": 10},
            ],
            "rowCount": 3,
            "sql": "SELECT status, COUNT(*) FROM payments GROUP BY status",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(result, "상태별 비율 알려줘")

        assert spec["type"] == "chart", "비율 키워드 + 적합한 데이터 → 차트"
        assert spec["chart"]["chartType"] == "pie", "비율 → pie 차트"

    def test_daily_triggers_line_chart(self):
        """'일별' 키워드 + 적합한 데이터 → line 차트"""
        result = {
            "data": [
                {"date": "2024-01-01", "amount": 1000000},
                {"date": "2024-01-02", "amount": 1200000},
                {"date": "2024-01-03", "amount": 900000},
            ],
            "rowCount": 3,
            "sql": "SELECT date, SUM(amount) FROM payments GROUP BY date",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(result, "일별 매출 현황")

        assert spec["type"] == "chart", "일별 키워드 + 적합한 데이터 → 차트"
        assert spec["chart"]["chartType"] == "line", "일별 → line 차트"


class TestExplicitOverridesImplicit:
    """명시적 키워드가 암시적 키워드보다 우선"""

    def test_explicit_table_overrides_implicit_comparison(self):
        """'표로' + '비교' → 테이블 (명시적 우선)"""
        result = {
            "data": [
                {"merchant_id": "M001", "total_amount": 5000000},
                {"merchant_id": "M002", "total_amount": 4000000},
            ],
            "rowCount": 2,
            "sql": "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(result, "가맹점별 매출 비교를 표로 보여줘")

        assert spec["type"] == "table", "명시적 '표로' 키워드가 암시적 '비교'보다 우선"

    def test_explicit_table_overrides_implicit_trend(self):
        """'테이블로' + '추이' → 테이블 (명시적 우선)"""
        result = {
            "data": [
                {"date": "2024-01-01", "count": 100},
                {"date": "2024-01-02", "count": 120},
            ],
            "rowCount": 2,
            "sql": "SELECT date, COUNT(*) FROM payments GROUP BY date",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(result, "일별 결제 추이를 테이블로 보여줘")

        assert spec["type"] == "table", "명시적 '테이블로' 키워드가 암시적 '추이'보다 우선"

    def test_explicit_chart_triggers_chart(self):
        """명시적 '그래프' 키워드 → 차트"""
        result = {
            "data": [
                {"merchant_id": "M001", "total_amount": 5000000},
                {"merchant_id": "M002", "total_amount": 4000000},
            ],
            "rowCount": 2,
            "sql": "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(result, "가맹점별 매출 그래프로 보여줘")

        assert spec["type"] == "chart", "명시적 '그래프' 키워드 → 차트"


class TestRowLimitProtection:
    """행 제한 보호 테스트 (10행 초과 → 테이블 유지)"""

    def test_too_many_rows_renders_table(self):
        """10행 초과 데이터 + 암시적 키워드 → 테이블 유지"""
        # 15개 가맹점 데이터
        data = [
            {"merchant_id": f"M{i:03d}", "total_amount": 5000000 - (i * 100000)}
            for i in range(15)
        ]

        result = {
            "data": data,
            "rowCount": 15,
            "sql": "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id",
            "executionTimeMs": 20
        }

        spec = compose_sql_render_spec(result, "가맹점별 매출 비교해줘")

        assert spec["type"] == "table", "10행 초과 → 암시적 키워드 있어도 테이블"

    def test_pie_category_limit_protection(self):
        """pie 차트에서 7개 초과 → 테이블 유지"""
        # 8개 상태 데이터
        data = [
            {"status": f"STATUS_{i}", "count": 100 - (i * 10)}
            for i in range(8)
        ]

        result = {
            "data": data,
            "rowCount": 8,
            "sql": "SELECT status, COUNT(*) FROM payments GROUP BY status",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(result, "상태별 분포 보여줘")

        assert spec["type"] == "table", "pie 차트 + 7개 초과 → 테이블"

    def test_boundary_10_rows_renders_chart(self):
        """정확히 10행 데이터 → 차트 허용"""
        data = [
            {"merchant_id": f"M{i:03d}", "total_amount": 5000000 - (i * 100000)}
            for i in range(10)
        ]

        result = {
            "data": data,
            "rowCount": 10,
            "sql": "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id",
            "executionTimeMs": 15
        }

        spec = compose_sql_render_spec(result, "가맹점별 매출 비교해줘")

        assert spec["type"] == "chart", "정확히 10행 → 차트 허용"


class TestNoImplicitKeyword:
    """암시적 키워드가 없는 경우 기본 동작 테스트"""

    def test_no_keyword_renders_table(self):
        """키워드 없음 → 기본 테이블"""
        result = {
            "data": [
                {"merchant_id": "M001", "total_amount": 5000000},
                {"merchant_id": "M002", "total_amount": 4000000},
            ],
            "rowCount": 2,
            "sql": "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(result, "가맹점별 매출 조회")

        assert spec["type"] == "table", "암시적 키워드 없음 → 테이블"

    def test_recent_n_renders_table(self):
        """'최근 N건' 조회 → 테이블"""
        result = {
            "data": [
                {"payment_id": "P001", "amount": 10000, "status": "DONE"},
                {"payment_id": "P002", "amount": 20000, "status": "DONE"},
                {"payment_id": "P003", "amount": 15000, "status": "CANCELED"},
            ],
            "rowCount": 3,
            "sql": "SELECT * FROM payments ORDER BY created_at DESC LIMIT 10",
            "executionTimeMs": 5
        }

        spec = compose_sql_render_spec(result, "최근 결제 10건 보여줘")

        assert spec["type"] == "table", "'최근 N건' 조회 → 테이블"


class TestSingleRowAggregation:
    """단일 행 집계 결과 테스트"""

    def test_single_row_aggregation_renders_text(self):
        """단일 행 집계 → 텍스트/테이블 (차트 아님)"""
        result = {
            "data": [
                {"total_amount": 1000000000, "count": 12345}
            ],
            "rowCount": 1,
            "sql": "SELECT SUM(amount), COUNT(*) FROM payments",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(result, "전체 매출 합계 비교해줘")

        # 단일 행 집계 + 5개 이하 컬럼 → text 타입
        assert spec["type"] == "text", "단일 행 집계 → text (차트 아님)"


class TestLlmChartTypeWithImplicitKeyword:
    """LLM chartType과 암시적 키워드 조합 테스트"""

    def test_llm_chart_type_used_when_explicit_chart_keyword(self):
        """명시적 차트 키워드 + LLM chartType → LLM 추천 타입 사용"""
        result = {
            "data": [
                {"status": "DONE", "count": 100},
                {"status": "CANCELED", "count": 20},
            ],
            "rowCount": 2,
            "sql": "SELECT status, COUNT(*) FROM payments GROUP BY status",
            "executionTimeMs": 10
        }

        spec = compose_sql_render_spec(
            result,
            "상태별 결제 차트로 보여줘",
            llm_chart_type="pie"
        )

        assert spec["type"] == "chart"
        assert spec["chart"]["chartType"] == "pie", "LLM 추천 타입(pie) 사용"

    def test_implicit_chart_type_used_when_no_explicit_keyword(self):
        """암시적 키워드만 있을 때 → 암시적 타입 사용"""
        result = {
            "data": [
                {"merchant_id": "M001", "total_amount": 5000000},
                {"merchant_id": "M002", "total_amount": 4000000},
            ],
            "rowCount": 2,
            "sql": "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id",
            "executionTimeMs": 10
        }

        # LLM이 pie를 추천해도 "비교" 키워드 → bar로 결정
        spec = compose_sql_render_spec(
            result,
            "가맹점별 매출 비교해줘",
            llm_chart_type="pie"  # LLM 추천이지만 암시적 키워드가 우선
        )

        assert spec["type"] == "chart"
        # 암시적 "비교" 키워드 → bar 차트
        assert spec["chart"]["chartType"] == "bar", "암시적 키워드(비교) → bar 차트"
