"""
Tests for Text-to-SQL LLM Chart Type Detection

LLM 기반 차트 타입 결정 로직 테스트
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestParseLLMResponse:
    """_parse_llm_response 메서드 테스트"""

    @pytest.fixture
    def text_to_sql_service(self):
        """TextToSqlService 인스턴스 생성"""
        # DATABASE_URL 환경변수 설정
        with patch.dict(os.environ, {"DATABASE_READONLY_URL": "postgresql://test:test@localhost/test"}):
            from app.services.text_to_sql import TextToSqlService
            return TextToSqlService()

    def test_parse_json_with_code_block(self, text_to_sql_service):
        """JSON 코드 블록 형식 파싱"""
        response = '''```json
{
  "sql": "SELECT * FROM payments;",
  "chartType": "line",
  "chartReason": "시계열 데이터 + 추이 키워드"
}
```'''
        sql, chart_type, chart_reason = text_to_sql_service._parse_llm_response(response)

        assert sql == "SELECT * FROM payments;"
        assert chart_type == "line"
        assert chart_reason == "시계열 데이터 + 추이 키워드"

    def test_parse_direct_json(self, text_to_sql_service):
        """직접 JSON 형식 파싱"""
        response = '''{"sql": "SELECT COUNT(*) FROM refunds;", "chartType": "bar", "chartReason": "카테고리 비교"}'''

        sql, chart_type, chart_reason = text_to_sql_service._parse_llm_response(response)

        assert sql == "SELECT COUNT(*) FROM refunds;"
        assert chart_type == "bar"
        assert chart_reason == "카테고리 비교"

    def test_parse_none_chart_type(self, text_to_sql_service):
        """chartType이 none인 경우"""
        response = '''```json
{
  "sql": "SELECT * FROM merchants;",
  "chartType": "none",
  "chartReason": "차트 요청 키워드 없음"
}
```'''
        sql, chart_type, chart_reason = text_to_sql_service._parse_llm_response(response)

        assert sql == "SELECT * FROM merchants;"
        assert chart_type == "none"
        assert chart_reason == "차트 요청 키워드 없음"

    def test_parse_fallback_sql_only(self, text_to_sql_service):
        """JSON 파싱 실패 시 폴백 - SQL만 추출"""
        response = '''```sql
SELECT * FROM payments WHERE status = 'DONE';
```'''
        sql, chart_type, chart_reason = text_to_sql_service._parse_llm_response(response)

        assert "SELECT * FROM payments" in sql
        assert chart_type is None
        assert chart_reason is None

    def test_parse_plain_sql(self, text_to_sql_service):
        """순수 SQL 문자열 (폴백)"""
        response = "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id;"

        sql, chart_type, chart_reason = text_to_sql_service._parse_llm_response(response)

        assert sql == "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id;"
        assert chart_type is None
        assert chart_reason is None

    def test_parse_pie_chart_type(self, text_to_sql_service):
        """pie 차트 타입 파싱"""
        response = '''```json
{
  "sql": "SELECT status, COUNT(*) FROM payments GROUP BY status;",
  "chartType": "pie",
  "chartReason": "비율/분포 키워드"
}
```'''
        sql, chart_type, chart_reason = text_to_sql_service._parse_llm_response(response)

        assert chart_type == "pie"


class TestDetectChartTypeFallback:
    """_detect_chart_type 폴백 로직 테스트"""

    def test_line_chart_with_time_column_and_keyword(self):
        """시계열 컬럼 + line 키워드 → line"""
        from app.api.v1.chat import _detect_chart_type

        data = [
            {"month": "2024-01", "count": 10},
            {"month": "2024-02", "count": 15},
        ]
        columns = ["month", "count"]
        user_message = "월별 결제건수 추이를 보여줘"

        chart_type = _detect_chart_type(data, columns, user_message)
        assert chart_type == "line"

    def test_line_chart_with_time_column_only(self):
        """시계열 컬럼 + 2행 이상 → line (키워드 없어도)"""
        from app.api.v1.chat import _detect_chart_type

        data = [
            {"created_at": "2024-01-01", "amount": 1000},
            {"created_at": "2024-01-02", "amount": 2000},
        ]
        columns = ["created_at", "amount"]
        user_message = "그래프로 보여줘"  # line 키워드 없음

        chart_type = _detect_chart_type(data, columns, user_message)
        assert chart_type == "line"

    def test_pie_chart_with_keyword(self):
        """pie 키워드 + 적은 데이터 → pie"""
        from app.api.v1.chat import _detect_chart_type

        data = [
            {"status": "DONE", "count": 100},
            {"status": "CANCELED", "count": 20},
        ]
        columns = ["status", "count"]
        user_message = "상태별 비율을 차트로 보여줘"

        chart_type = _detect_chart_type(data, columns, user_message)
        assert chart_type == "pie"

    def test_bar_chart_default(self):
        """기본 차트 타입 → bar"""
        from app.api.v1.chat import _detect_chart_type

        data = [
            {"merchant_id": "mer_001", "total": 5000000},
            {"merchant_id": "mer_002", "total": 3000000},
            {"merchant_id": "mer_003", "total": 2000000},
            {"merchant_id": "mer_004", "total": 1500000},
            {"merchant_id": "mer_005", "total": 1000000},
            {"merchant_id": "mer_006", "total": 800000},
        ]
        columns = ["merchant_id", "total"]
        user_message = "가맹점별 매출 그래프로"

        chart_type = _detect_chart_type(data, columns, user_message)
        assert chart_type == "bar"

    def test_line_keyword_prevents_pie(self):
        """line 키워드가 있으면 적은 데이터여도 pie 안됨"""
        from app.api.v1.chat import _detect_chart_type

        data = [
            {"month": "2024-10", "count": 10},
            {"month": "2024-11", "count": 15},
        ]
        columns = ["month", "count"]
        user_message = "월별 추이 그래프로 보여줘"  # "추이" = line 키워드

        chart_type = _detect_chart_type(data, columns, user_message)
        assert chart_type == "line"

    def test_empty_data(self):
        """빈 데이터 → bar (기본값)"""
        from app.api.v1.chat import _detect_chart_type

        chart_type = _detect_chart_type([], [], "그래프로 보여줘")
        assert chart_type == "bar"


class TestComposeChartRenderSpec:
    """_compose_chart_render_spec 테스트"""

    def test_llm_chart_type_priority(self):
        """LLM 차트 타입이 우선됨"""
        from app.api.v1.chat import _compose_chart_render_spec

        result = {
            "data": [
                {"month": "2024-01", "count": 10},
                {"month": "2024-02", "count": 15},
            ],
            "rowCount": 2,
            "sql": "SELECT ...",
        }

        # LLM이 bar 추천, 데이터는 시계열
        render_spec = _compose_chart_render_spec(result, "월별 조회", "bar")

        assert render_spec["type"] == "chart"
        assert render_spec["chart"]["chartType"] == "bar"

    def test_fallback_to_rule_based(self):
        """LLM 차트 타입 없으면 규칙 기반"""
        from app.api.v1.chat import _compose_chart_render_spec

        result = {
            "data": [
                {"month": "2024-01", "count": 10},
                {"month": "2024-02", "count": 15},
            ],
            "rowCount": 2,
            "sql": "SELECT ...",
        }

        # LLM 차트 타입 없음
        render_spec = _compose_chart_render_spec(result, "월별 추이 그래프로", None)

        assert render_spec["type"] == "chart"
        # 규칙 기반으로 line 결정 (시계열 컬럼 + "추이" 키워드)
        assert render_spec["chart"]["chartType"] == "line"

    def test_invalid_llm_chart_type_fallback(self):
        """LLM 차트 타입이 유효하지 않으면 폴백"""
        from app.api.v1.chat import _compose_chart_render_spec

        result = {
            "data": [
                {"month": "2024-01", "count": 10},
                {"month": "2024-02", "count": 15},
            ],
            "rowCount": 2,
            "sql": "SELECT ...",
        }

        # LLM이 "none" 반환 → 폴백
        render_spec = _compose_chart_render_spec(result, "월별 추이 그래프로", "none")

        assert render_spec["type"] == "chart"
        # "none"은 유효한 차트 타입이 아니므로 폴백
        assert render_spec["chart"]["chartType"] == "line"
