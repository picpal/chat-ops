"""
TC-030: _prepare_count_sql 단위 테스트

세미콜론 제거 및 COUNT 래핑 로직을 검증합니다.
DB 커넥션 없이 순수한 SQL 변환 로직만 테스트합니다.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.text_to_sql import TextToSqlService


class TestPrepareCountSql:
    """_prepare_count_sql 정적 메서드 테스트"""

    def test_prepare_count_sql_strips_semicolon(self):
        """세미콜론이 있는 SQL에서 세미콜론이 제거된 COUNT 쿼리가 생성됨"""
        sql = "SELECT * FROM payments WHERE status = 'DONE';"

        result = TextToSqlService._prepare_count_sql(sql)

        # 서브쿼리 내부에 세미콜론이 없어야 함
        assert ";" not in result
        # COUNT 래핑이 정상적으로 적용되어야 함
        assert result.startswith("SELECT COUNT(*) as cnt FROM (")
        assert result.endswith(") sub")

    def test_prepare_count_sql_without_semicolon(self):
        """세미콜론 없는 SQL에서도 기존 동작이 유지됨 (회귀 없음)"""
        sql = "SELECT * FROM payments WHERE status = 'DONE'"

        result = TextToSqlService._prepare_count_sql(sql)

        assert ";" not in result
        assert result.startswith("SELECT COUNT(*) as cnt FROM (")
        assert result.endswith(") sub")
        assert "SELECT * FROM payments WHERE status = 'DONE'" in result

    def test_prepare_count_sql_cte_with_semicolon(self):
        """CTE SQL 끝의 세미콜론이 제거됨"""
        sql = (
            "WITH top AS ("
            "SELECT merchant_id, COUNT(*) as cnt "
            "FROM payments "
            "GROUP BY merchant_id "
            "ORDER BY cnt DESC "
            "LIMIT 5"
            ") "
            "SELECT * FROM top;"
        )

        result = TextToSqlService._prepare_count_sql(sql)

        # 세미콜론이 서브쿼리 내부에 없어야 함
        inner_sql = result[len("SELECT COUNT(*) as cnt FROM ("):-len(") sub")]
        assert ";" not in inner_sql

        # COUNT 래핑 형태 확인
        assert result.startswith("SELECT COUNT(*) as cnt FROM (")
        assert result.endswith(") sub")

    def test_prepare_count_sql_removes_limit(self):
        """LIMIT 절이 제거됨"""
        sql = "SELECT * FROM payments LIMIT 100"

        result = TextToSqlService._prepare_count_sql(sql)

        assert "LIMIT" not in result.upper()

    def test_prepare_count_sql_removes_offset(self):
        """OFFSET 절이 제거됨"""
        sql = "SELECT * FROM payments LIMIT 100 OFFSET 200"

        result = TextToSqlService._prepare_count_sql(sql)

        assert "OFFSET" not in result.upper()

    def test_prepare_count_sql_removes_order_by(self):
        """ORDER BY 절이 제거됨"""
        sql = "SELECT * FROM payments ORDER BY created_at DESC"

        result = TextToSqlService._prepare_count_sql(sql)

        assert "ORDER BY" not in result.upper()

    def test_prepare_count_sql_wraps_in_count(self):
        """COUNT(*) 래핑이 올바르게 적용됨"""
        sql = "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id"

        result = TextToSqlService._prepare_count_sql(sql)

        assert result == (
            "SELECT COUNT(*) as cnt FROM ("
            "SELECT merchant_id, SUM(amount) FROM payments GROUP BY merchant_id"
            ") sub"
        )

    def test_prepare_count_sql_cte_semicolon_not_in_subquery(self):
        """CTE + 세미콜론 조합에서 서브쿼리 내 세미콜론 없음 (버그 재현 시나리오)"""
        # 버그 발생 예시와 동일한 SQL
        sql = (
            "WITH top AS ("
            "SELECT merchant_id, COUNT(*) as cnt "
            "FROM payments "
            "WHERE created_at >= NOW() - INTERVAL '3 months' "
            "GROUP BY merchant_id "
            "ORDER BY cnt DESC "
            "LIMIT 5"
            ") "
            "SELECT * FROM top;"
        )

        result = TextToSqlService._prepare_count_sql(sql)

        # PostgreSQL 구문 오류가 발생할 세미콜론이 ) sub 앞에 없어야 함
        assert result.endswith(") sub")
        assert "; ) sub" not in result
        assert ";) sub" not in result
