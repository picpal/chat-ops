"""
SQL Validator for Text-to-SQL queries.
Ensures generated SQL is safe to execute on the read-only database.
"""

import re
from dataclasses import dataclass
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """SQL 검증 결과"""
    is_valid: bool
    issues: List[str]
    sanitized_sql: Optional[str]

    def __bool__(self) -> bool:
        return self.is_valid


class SqlValidator:
    """
    SQL 보안 검증기

    3중 보안 레이어 중 Layer 2 역할:
    - Layer 1: PostgreSQL 읽기 전용 계정 (DB 레벨)
    - Layer 2: SQL Validator (애플리케이션 레벨) <- 여기
    - Layer 3: 실행 제한 (타임아웃, 행 수 제한)
    """

    # DML/DDL 차단 키워드 (대소문자 무관)
    BLOCKED_KEYWORDS = [
        r'\bINSERT\b',
        r'\bUPDATE\b',
        r'\bDELETE\b',
        r'\bDROP\b',
        r'\bTRUNCATE\b',
        r'\bALTER\b',
        r'\bCREATE\b',
        r'\bGRANT\b',
        r'\bREVOKE\b',
        r'\bEXECUTE\b',
        r'\bCALL\b',
        r'\bCOPY\b',
        r'\bLOAD\b',
        r'\bVACUUM\b',
        r'\bANALYZE\b',
        r'\bREINDEX\b',
        r'\bCLUSTER\b',
        r'\bCOMMENT\b',
        r'\bLOCK\b',
        r'\bUNLOCK\b',
        r'\bSET\b',  # SET 명령어 차단
        r'\bRESET\b',
        r'\bBEGIN\b',
        r'\bCOMMIT\b',
        r'\bROLLBACK\b',
        r'\bSAVEPOINT\b',
        r'\bRELEASE\b',
        r'\bPREPARE\b',
        r'\bDEALLOCATE\b',
    ]

    # 접근 차단 테이블
    BLOCKED_TABLES = [
        'documents',           # RAG 민감 데이터
        'flyway_schema_history',  # 마이그레이션 히스토리
        'pg_catalog',          # 시스템 카탈로그
        'information_schema',  # 메타데이터 스키마
    ]

    # 위험한 함수 패턴
    BLOCKED_FUNCTIONS = [
        r'\bpg_read_file\b',
        r'\bpg_read_binary_file\b',
        r'\bpg_ls_dir\b',
        r'\blo_import\b',
        r'\blo_export\b',
        r'\bdblink\b',
        r'\bpg_sleep\b',        # DoS 방지
        r'\bcurrent_setting\b',
        r'\bset_config\b',
    ]

    def __init__(self, max_rows: int = 1000, default_limit: int = 100):
        """
        Args:
            max_rows: LIMIT 최대값 (초과 시 강제 조정)
            default_limit: LIMIT 없을 때 기본값
        """
        self.max_rows = max_rows
        self.default_limit = default_limit

        # 정규식 컴파일
        self._blocked_keyword_patterns = [
            re.compile(kw, re.IGNORECASE) for kw in self.BLOCKED_KEYWORDS
        ]
        self._blocked_function_patterns = [
            re.compile(fn, re.IGNORECASE) for fn in self.BLOCKED_FUNCTIONS
        ]

    def validate(self, sql: str) -> ValidationResult:
        """
        SQL 쿼리 검증

        Args:
            sql: 검증할 SQL 문자열

        Returns:
            ValidationResult: 검증 결과 (is_valid, issues, sanitized_sql)
        """
        if not sql or not sql.strip():
            return ValidationResult(
                is_valid=False,
                issues=["Empty SQL query"],
                sanitized_sql=None
            )

        issues: List[str] = []
        normalized_sql = self._normalize_sql(sql)

        # 1. SELECT 문으로 시작하는지 확인
        if not self._is_select_query(normalized_sql):
            issues.append("Query must start with SELECT")

        # 2. 다중 쿼리 차단 (세미콜론 분리)
        if self._has_multiple_statements(normalized_sql):
            issues.append("Multiple statements not allowed")

        # 3. 차단 키워드 검사
        blocked = self._check_blocked_keywords(normalized_sql)
        if blocked:
            issues.append(f"Blocked keywords found: {', '.join(blocked)}")

        # 4. 차단 테이블 검사
        blocked_tables = self._check_blocked_tables(normalized_sql)
        if blocked_tables:
            issues.append(f"Access to blocked tables: {', '.join(blocked_tables)}")

        # 5. 위험 함수 검사
        blocked_funcs = self._check_blocked_functions(normalized_sql)
        if blocked_funcs:
            issues.append(f"Blocked functions found: {', '.join(blocked_funcs)}")

        # 6. 주석 기반 인젝션 패턴 검사
        if self._has_injection_patterns(normalized_sql):
            issues.append("Suspicious injection pattern detected")

        # 검증 실패 시 반환
        if issues:
            logger.warning(f"SQL validation failed: {issues}")
            return ValidationResult(
                is_valid=False,
                issues=issues,
                sanitized_sql=None
            )

        # 7. LIMIT 적용/조정
        sanitized_sql = self._apply_limit(normalized_sql)

        logger.info(f"SQL validation passed. Sanitized SQL: {sanitized_sql[:100]}...")
        return ValidationResult(
            is_valid=True,
            issues=[],
            sanitized_sql=sanitized_sql
        )

    def _normalize_sql(self, sql: str) -> str:
        """SQL 정규화 (앞뒤 공백 제거, 줄바꿈 정리)"""
        # 여러 줄 공백을 단일 공백으로
        normalized = re.sub(r'\s+', ' ', sql.strip())
        return normalized

    def _is_select_query(self, sql: str) -> bool:
        """SELECT 문으로 시작하는지 확인"""
        # WITH ... SELECT 또는 SELECT로 시작해야 함
        select_pattern = re.compile(
            r'^(WITH\s+\w+\s+AS\s*\(.+\)\s*)?SELECT\s',
            re.IGNORECASE
        )
        return bool(select_pattern.match(sql))

    def _has_multiple_statements(self, sql: str) -> bool:
        """다중 쿼리 여부 확인"""
        # 문자열 리터럴 내의 세미콜론은 무시
        # 간단한 방법: 문자열 리터럴 제거 후 세미콜론 확인
        no_strings = re.sub(r"'[^']*'", '', sql)
        no_strings = re.sub(r'"[^"]*"', '', no_strings)

        # 끝의 세미콜론은 허용
        trimmed = no_strings.rstrip(';').strip()
        return ';' in trimmed

    def _check_blocked_keywords(self, sql: str) -> List[str]:
        """차단 키워드 검사"""
        found = []
        for pattern in self._blocked_keyword_patterns:
            if pattern.search(sql):
                # 매칭된 키워드 추출
                match = pattern.search(sql)
                if match:
                    found.append(match.group())
        return found

    def _check_blocked_tables(self, sql: str) -> List[str]:
        """차단 테이블 접근 검사"""
        found = []
        sql_lower = sql.lower()
        for table in self.BLOCKED_TABLES:
            # FROM, JOIN 등에서 테이블 접근 확인
            pattern = re.compile(
                rf'\b(FROM|JOIN|INTO|UPDATE|TABLE)\s+.*?\b{re.escape(table.lower())}\b',
                re.IGNORECASE
            )
            if pattern.search(sql_lower) or table.lower() in sql_lower:
                found.append(table)
        return found

    def _check_blocked_functions(self, sql: str) -> List[str]:
        """위험 함수 검사"""
        found = []
        for pattern in self._blocked_function_patterns:
            match = pattern.search(sql)
            if match:
                found.append(match.group())
        return found

    def _has_injection_patterns(self, sql: str) -> bool:
        """SQL 인젝션 패턴 검사"""
        injection_patterns = [
            r'--',              # 라인 주석
            r'/\*',             # 블록 주석 시작
            r'\*/',             # 블록 주석 끝
            r';\s*--',          # 세미콜론 후 주석
            r"'\s*OR\s+'",      # OR 인젝션
            r"'\s*OR\s+\d",     # OR 숫자 인젝션
            r"1\s*=\s*1",       # 항상 참 조건
            r"'\s*=\s*'",       # 항상 참 문자열 비교
        ]

        for pattern in injection_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return True
        return False

    def _apply_limit(self, sql: str) -> str:
        """LIMIT 적용 또는 조정"""
        # 기존 LIMIT 찾기
        limit_pattern = re.compile(
            r'\bLIMIT\s+(\d+)',
            re.IGNORECASE
        )

        match = limit_pattern.search(sql)

        if match:
            # 기존 LIMIT 값 확인
            current_limit = int(match.group(1))
            if current_limit > self.max_rows:
                # max_rows로 제한
                sql = limit_pattern.sub(f'LIMIT {self.max_rows}', sql)
                logger.info(f"LIMIT adjusted from {current_limit} to {self.max_rows}")
        else:
            # LIMIT 없으면 추가
            # ORDER BY 뒤에 있으면 그 뒤에, 아니면 쿼리 끝에
            sql = sql.rstrip(';')
            sql = f"{sql} LIMIT {self.default_limit}"
            logger.info(f"Default LIMIT {self.default_limit} added")

        return sql

    def extract_tables(self, sql: str) -> List[str]:
        """
        SQL에서 참조하는 테이블 목록 추출 (감사 로깅용)

        Args:
            sql: SQL 쿼리

        Returns:
            테이블 이름 목록
        """
        tables = []

        # FROM 절 테이블
        from_pattern = re.compile(
            r'\bFROM\s+(\w+)',
            re.IGNORECASE
        )
        tables.extend(from_pattern.findall(sql))

        # JOIN 절 테이블
        join_pattern = re.compile(
            r'\bJOIN\s+(\w+)',
            re.IGNORECASE
        )
        tables.extend(join_pattern.findall(sql))

        return list(set(tables))


# 싱글톤 인스턴스
_validator_instance: Optional[SqlValidator] = None


def get_sql_validator(max_rows: int = 1000, default_limit: int = 100) -> SqlValidator:
    """SqlValidator 싱글톤 인스턴스 반환"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SqlValidator(max_rows=max_rows, default_limit=default_limit)
    return _validator_instance
