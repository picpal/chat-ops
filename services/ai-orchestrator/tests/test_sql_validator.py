"""
SqlValidator 단위 테스트
"""

import pytest
from app.services.sql_validator import SqlValidator, ValidationResult


@pytest.fixture
def validator():
    """SqlValidator 인스턴스"""
    return SqlValidator(max_rows=1000, default_limit=100)


class TestBasicValidation:
    """기본 검증 테스트"""

    def test_valid_select_query(self, validator):
        """유효한 SELECT 쿼리"""
        sql = "SELECT * FROM payments WHERE status = 'DONE'"
        result = validator.validate(sql)

        assert result.is_valid
        assert not result.issues
        assert result.sanitized_sql is not None

    def test_empty_query(self, validator):
        """빈 쿼리 거부"""
        result = validator.validate("")
        assert not result.is_valid
        assert "Empty SQL query" in result.issues

    def test_whitespace_only_query(self, validator):
        """공백만 있는 쿼리 거부"""
        result = validator.validate("   \n\t  ")
        assert not result.is_valid

    def test_with_clause(self, validator):
        """WITH 절 허용"""
        sql = """
        WITH monthly_sales AS (
            SELECT merchant_id, SUM(amount) as total
            FROM payments
            WHERE approved_at >= '2024-01-01'
            GROUP BY merchant_id
        )
        SELECT * FROM monthly_sales
        """
        result = validator.validate(sql)
        assert result.is_valid


class TestBlockedKeywords:
    """차단 키워드 테스트"""

    @pytest.mark.parametrize("sql,keyword", [
        ("INSERT INTO payments VALUES (1, 2)", "INSERT"),
        ("UPDATE payments SET amount = 0", "UPDATE"),
        ("DELETE FROM payments", "DELETE"),
        ("DROP TABLE payments", "DROP"),
        ("TRUNCATE payments", "TRUNCATE"),
        ("ALTER TABLE payments ADD col INT", "ALTER"),
        ("CREATE TABLE test (id INT)", "CREATE"),
        ("GRANT SELECT ON payments TO user", "GRANT"),
        ("BEGIN; SELECT 1; COMMIT;", "BEGIN"),
    ])
    def test_blocked_dml_ddl(self, validator, sql, keyword):
        """DML/DDL 키워드 차단"""
        result = validator.validate(sql)
        assert not result.is_valid
        assert any(keyword in issue for issue in result.issues)


class TestBlockedTables:
    """차단 테이블 테스트"""

    def test_documents_table_blocked(self, validator):
        """documents 테이블 접근 차단"""
        sql = "SELECT * FROM documents WHERE status = 'approved'"
        result = validator.validate(sql)

        assert not result.is_valid
        assert any("documents" in issue for issue in result.issues)

    def test_pg_catalog_blocked(self, validator):
        """시스템 카탈로그 접근 차단"""
        sql = "SELECT * FROM pg_catalog.pg_tables"
        result = validator.validate(sql)

        assert not result.is_valid
        assert any("pg_catalog" in issue for issue in result.issues)

    def test_information_schema_blocked(self, validator):
        """information_schema 접근 차단"""
        sql = "SELECT * FROM information_schema.tables"
        result = validator.validate(sql)

        assert not result.is_valid
        assert any("information_schema" in issue for issue in result.issues)


class TestBlockedFunctions:
    """차단 함수 테스트"""

    def test_pg_read_file_blocked(self, validator):
        """pg_read_file 함수 차단"""
        sql = "SELECT pg_read_file('/etc/passwd')"
        result = validator.validate(sql)

        assert not result.is_valid
        assert any("pg_read_file" in issue for issue in result.issues)

    def test_pg_sleep_blocked(self, validator):
        """pg_sleep 함수 차단 (DoS 방지)"""
        sql = "SELECT pg_sleep(10), * FROM payments"
        result = validator.validate(sql)

        assert not result.is_valid
        assert any("pg_sleep" in issue for issue in result.issues)


class TestMultipleStatements:
    """다중 쿼리 테스트"""

    def test_multiple_statements_blocked(self, validator):
        """세미콜론으로 분리된 다중 쿼리 차단"""
        sql = "SELECT 1; SELECT 2"
        result = validator.validate(sql)

        assert not result.is_valid
        assert any("Multiple statements" in issue for issue in result.issues)

    def test_trailing_semicolon_allowed(self, validator):
        """끝의 세미콜론은 허용"""
        sql = "SELECT * FROM payments;"
        result = validator.validate(sql)

        assert result.is_valid

    def test_semicolon_in_string_allowed(self, validator):
        """문자열 내 세미콜론은 허용"""
        sql = "SELECT * FROM payments WHERE note = 'a;b'"
        result = validator.validate(sql)

        assert result.is_valid


class TestInjectionPatterns:
    """SQL 인젝션 패턴 테스트"""

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM payments -- WHERE status='DONE'",
        "SELECT * FROM payments /* comment */",
        "SELECT * FROM payments WHERE id = 1 OR '1'='1'",
        "SELECT * FROM payments WHERE 1=1",
    ])
    def test_injection_patterns_blocked(self, validator, sql):
        """인젝션 패턴 차단"""
        result = validator.validate(sql)
        assert not result.is_valid
        assert any("injection" in issue.lower() for issue in result.issues)


class TestLimitEnforcement:
    """LIMIT 적용 테스트"""

    def test_default_limit_added(self, validator):
        """LIMIT 없으면 기본값 추가"""
        sql = "SELECT * FROM payments"
        result = validator.validate(sql)

        assert result.is_valid
        assert "LIMIT 100" in result.sanitized_sql

    def test_existing_limit_preserved(self, validator):
        """기존 LIMIT 값 유지 (max_rows 이내)"""
        sql = "SELECT * FROM payments LIMIT 50"
        result = validator.validate(sql)

        assert result.is_valid
        assert "LIMIT 50" in result.sanitized_sql

    def test_excessive_limit_reduced(self, validator):
        """과도한 LIMIT 값 축소"""
        sql = "SELECT * FROM payments LIMIT 5000"
        result = validator.validate(sql)

        assert result.is_valid
        assert "LIMIT 1000" in result.sanitized_sql

    def test_limit_with_offset(self, validator):
        """LIMIT ... OFFSET 처리"""
        sql = "SELECT * FROM payments LIMIT 50 OFFSET 100"
        result = validator.validate(sql)

        assert result.is_valid
        assert "LIMIT 50" in result.sanitized_sql
        assert "OFFSET 100" in result.sanitized_sql


class TestTableExtraction:
    """테이블 추출 테스트"""

    def test_extract_single_table(self, validator):
        """단일 테이블 추출"""
        sql = "SELECT * FROM payments"
        tables = validator.extract_tables(sql)

        assert "payments" in tables

    def test_extract_multiple_tables(self, validator):
        """다중 테이블 추출 (JOIN)"""
        sql = """
        SELECT p.*, m.business_name
        FROM payments p
        JOIN merchants m ON p.merchant_id = m.merchant_id
        """
        tables = validator.extract_tables(sql)

        assert "payments" in tables
        assert "merchants" in tables


class TestComplexQueries:
    """복잡한 쿼리 테스트"""

    def test_aggregate_query(self, validator):
        """집계 쿼리"""
        sql = """
        SELECT merchant_id,
               COUNT(*) as payment_count,
               SUM(amount) as total_amount
        FROM payments
        WHERE status = 'DONE'
          AND approved_at >= '2024-01-01'
        GROUP BY merchant_id
        HAVING SUM(amount) > 1000000
        ORDER BY total_amount DESC
        """
        result = validator.validate(sql)

        assert result.is_valid

    def test_subquery(self, validator):
        """서브쿼리"""
        sql = """
        SELECT * FROM payments
        WHERE merchant_id IN (
            SELECT merchant_id FROM merchants WHERE status = 'ACTIVE'
        )
        """
        result = validator.validate(sql)

        assert result.is_valid

    def test_window_function(self, validator):
        """윈도우 함수"""
        sql = """
        SELECT payment_key,
               amount,
               SUM(amount) OVER (PARTITION BY merchant_id ORDER BY approved_at) as running_total
        FROM payments
        """
        result = validator.validate(sql)

        assert result.is_valid


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_case_insensitivity(self, validator):
        """대소문자 구분 없이 키워드 차단"""
        sql = "insert INTO payments VALUES (1, 2)"
        result = validator.validate(sql)
        assert not result.is_valid

    def test_newlines_handled(self, validator):
        """줄바꿈 처리"""
        sql = """
        SELECT
            *
        FROM
            payments
        """
        result = validator.validate(sql)
        assert result.is_valid

    def test_boolean_conversion(self, validator):
        """ValidationResult의 bool 변환"""
        valid_result = ValidationResult(is_valid=True, issues=[], sanitized_sql="SELECT 1")
        invalid_result = ValidationResult(is_valid=False, issues=["error"], sanitized_sql=None)

        assert bool(valid_result) is True
        assert bool(invalid_result) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
