"""
인사이트 생성 기능 단위 테스트

테스트 대상:
- _detect_trend(): 시계열 추세 감지
- _generate_insight(): 인사이트 생성 (LLM 템플릿 + 규칙 기반 폴백)
"""

import pytest
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.sql_render_composer import _detect_trend, _generate_insight


class TestDetectTrend:
    """_detect_trend 함수 테스트"""

    def test_increasing_trend(self):
        """증가 추세 감지"""
        values = [100, 120, 150, 180, 200, 250]
        result = _detect_trend(values)
        assert result == "증가"

    def test_decreasing_trend(self):
        """감소 추세 감지"""
        values = [250, 200, 180, 150, 120, 100]
        result = _detect_trend(values)
        assert result == "감소"

    def test_stable_trend(self):
        """유지 추세 감지"""
        values = [100, 102, 98, 101, 99, 100]
        result = _detect_trend(values)
        assert result == "유지"

    def test_insufficient_data(self):
        """데이터 부족 시 None 반환"""
        values = [100, 200]
        result = _detect_trend(values)
        assert result is None

    def test_empty_data(self):
        """빈 데이터 시 None 반환"""
        values = []
        result = _detect_trend(values)
        assert result is None

    def test_zero_first_half(self):
        """전반부 0인 경우 처리"""
        values = [0, 0, 0, 100, 200, 300]
        result = _detect_trend(values)
        assert result == "증가"


class TestGenerateInsight:
    """_generate_insight 함수 테스트"""

    @pytest.fixture
    def sample_bar_data(self):
        """막대 차트용 샘플 데이터"""
        return [
            {"merchant_id": "mer_001", "total_amount": 1000000},
            {"merchant_id": "mer_002", "total_amount": 500000},
            {"merchant_id": "mer_003", "total_amount": 1500000},
            {"merchant_id": "mer_004", "total_amount": 800000},
        ]

    @pytest.fixture
    def sample_line_data(self):
        """라인 차트용 샘플 데이터"""
        return [
            {"month": "2024-01", "total_amount": 1000000},
            {"month": "2024-02", "total_amount": 1200000},
            {"month": "2024-03", "total_amount": 1500000},
            {"month": "2024-04", "total_amount": 1800000},
            {"month": "2024-05", "total_amount": 2000000},
        ]

    @pytest.fixture
    def sample_pie_data(self):
        """파이 차트용 샘플 데이터"""
        return [
            {"status": "DONE", "count": 500},
            {"status": "CANCELED", "count": 50},
            {"status": "FAILED", "count": 30},
        ]

    def test_bar_chart_rule_based(self, sample_bar_data):
        """막대 차트 - 규칙 기반 인사이트 생성"""
        result = _generate_insight(
            data=sample_bar_data,
            x_key="merchant_id",
            y_key="total_amount",
            chart_type="bar",
            template=None
        )

        assert result["source"] == "template"
        assert result["content"] is not None
        assert "가맹점" in result["content"]
        assert "mer_003" in result["content"]  # 최대값 가맹점
        assert "₩" in result["content"]

    def test_line_chart_rule_based(self, sample_line_data):
        """라인 차트 - 규칙 기반 인사이트 생성"""
        result = _generate_insight(
            data=sample_line_data,
            x_key="month",
            y_key="total_amount",
            chart_type="line",
            template=None
        )

        assert result["source"] == "template"
        assert result["content"] is not None
        assert "월" in result["content"]
        assert "추세" in result["content"]

    def test_pie_chart_rule_based(self, sample_pie_data):
        """파이 차트 - 규칙 기반 인사이트 생성"""
        result = _generate_insight(
            data=sample_pie_data,
            x_key="status",
            y_key="count",
            chart_type="pie",
            template=None
        )

        assert result["source"] == "template"
        assert result["content"] is not None
        assert "상태" in result["content"]
        assert "DONE" in result["content"]  # 최대값 카테고리
        assert "분포" in result["content"]

    def test_llm_template_substitution(self, sample_bar_data):
        """LLM 템플릿 플레이스홀더 치환"""
        template = "{groupBy}별 {metric} 비교입니다. {maxCategory}가 {max}로 가장 높고, {minCategory}가 {min}로 가장 낮습니다."

        result = _generate_insight(
            data=sample_bar_data,
            x_key="merchant_id",
            y_key="total_amount",
            chart_type="bar",
            template=template
        )

        assert result["source"] == "llm"
        assert result["content"] is not None
        assert "가맹점" in result["content"]  # {groupBy} 치환됨
        assert "mer_003" in result["content"]  # {maxCategory} 치환됨
        assert "mer_002" in result["content"]  # {minCategory} 치환됨
        assert "₩" in result["content"]  # 금액 포맷팅

    def test_llm_template_with_trend(self, sample_line_data):
        """LLM 템플릿 - 추세 플레이스홀더"""
        template = "{groupBy}별 추이입니다. {trend} 추세를 보입니다."

        result = _generate_insight(
            data=sample_line_data,
            x_key="month",
            y_key="total_amount",
            chart_type="line",
            template=template
        )

        assert result["source"] == "llm"
        assert result["content"] is not None
        assert "증가" in result["content"]  # {trend} 치환됨

    def test_empty_data(self):
        """빈 데이터 처리"""
        result = _generate_insight(
            data=[],
            x_key="merchant_id",
            y_key="total_amount",
            chart_type="bar",
            template=None
        )

        assert result["source"] == "none"
        assert result["content"] is None

    def test_unsubstituted_placeholders_removed(self, sample_bar_data):
        """미치환 플레이스홀더 제거"""
        template = "{groupBy}별 분석입니다. {unknownPlaceholder} 테스트입니다."

        result = _generate_insight(
            data=sample_bar_data,
            x_key="merchant_id",
            y_key="total_amount",
            chart_type="bar",
            template=template
        )

        assert result["source"] == "llm"
        assert "{unknownPlaceholder}" not in result["content"]

    def test_currency_formatting(self, sample_bar_data):
        """금액 포맷팅 확인"""
        result = _generate_insight(
            data=sample_bar_data,
            x_key="merchant_id",
            y_key="total_amount",
            chart_type="bar",
            template="{max}"
        )

        # 1500000 → ₩1,500,000
        assert "₩" in result["content"]
        assert "1,500,000" in result["content"]

    def test_snake_case_field_labels(self):
        """snake_case 필드명 한글 라벨 변환"""
        data = [
            {"payment_count": 100, "merchant_id": "mer_001"},
            {"payment_count": 200, "merchant_id": "mer_002"},
        ]

        result = _generate_insight(
            data=data,
            x_key="merchant_id",
            y_key="payment_count",
            chart_type="bar",
            template="{metric}"
        )

        assert result["content"] is not None
        # payment_count → 결제건수
        assert "건수" in result["content"] or "Payment Count" in result["content"]


class TestGenerateInsightEdgeCases:
    """_generate_insight 엣지 케이스 테스트"""

    def test_non_numeric_y_values(self):
        """숫자가 아닌 Y값 처리"""
        data = [
            {"category": "A", "value": "invalid"},
            {"category": "B", "value": 100},
            {"category": "C", "value": None},
        ]

        result = _generate_insight(
            data=data,
            x_key="category",
            y_key="value",
            chart_type="bar",
            template=None
        )

        # 에러 없이 처리되어야 함
        assert result["source"] in ["template", "none"]

    def test_all_same_values(self):
        """모든 값이 동일한 경우"""
        data = [
            {"month": "2024-01", "amount": 1000},
            {"month": "2024-02", "amount": 1000},
            {"month": "2024-03", "amount": 1000},
        ]

        result = _generate_insight(
            data=data,
            x_key="month",
            y_key="amount",
            chart_type="line",
            template=None
        )

        assert result["source"] == "template"
        assert "유지" in result["content"]

    def test_single_data_point(self):
        """단일 데이터 포인트"""
        data = [{"category": "A", "value": 100}]

        result = _generate_insight(
            data=data,
            x_key="category",
            y_key="value",
            chart_type="bar",
            template=None
        )

        assert result["source"] == "template"
        assert result["content"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
