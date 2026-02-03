"""
Text-to-SQL Service: 자연어를 SQL로 변환하고 실행
"""

import os
import json
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

import psycopg
from psycopg.rows import dict_row

from app.services.sql_validator import SqlValidator, ValidationResult, get_sql_validator
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)


# ============================================
# 집계 쿼리 감지 및 컨텍스트 생성
# ============================================

# 집계 함수 패턴 (대소문자 무관)
AGGREGATION_FUNCTIONS = {
    "SUM": r'\bSUM\s*\(\s*([^)]+)\s*\)',
    "COUNT": r'\bCOUNT\s*\(\s*([^)]+)\s*\)',
    "AVG": r'\bAVG\s*\(\s*([^)]+)\s*\)',
    "MAX": r'\bMAX\s*\(\s*([^)]+)\s*\)',
    "MIN": r'\bMIN\s*\(\s*([^)]+)\s*\)',
}


@dataclass
class AggregationInfo:
    """단일 집계 함수 정보"""
    function: str           # SUM, COUNT, AVG, MAX, MIN
    target_column: str      # 집계 대상 컬럼 (예: amount, *)
    alias: Optional[str]    # AS 별칭 (있으면)


@dataclass
class AggregationContext:
    """집계 쿼리 컨텍스트 메타데이터"""
    query_type: str                     # "NEW_QUERY" 또는 "REFINEMENT"
    based_on_filters: List[str]         # 적용된 WHERE 조건들 (원본 SQL)
    humanized_filters: List[str]        # 사용자 친화적 표현 (한글)
    source_row_count: Optional[int]     # 이전 쿼리 결과 건수 (있으면)
    aggregations: List[AggregationInfo] # 감지된 집계 함수들
    has_group_by: bool                  # GROUP BY 포함 여부
    group_by_columns: List[str]         # GROUP BY 컬럼들


def detect_aggregation_functions(sql: str) -> List[AggregationInfo]:
    """
    SQL에서 집계 함수들을 감지

    Args:
        sql: SQL 쿼리 문자열

    Returns:
        감지된 집계 함수 정보 리스트
    """
    aggregations = []

    # SELECT 절 추출
    select_match = re.search(r'\bSELECT\s+(.+?)\s+FROM\b', sql, re.IGNORECASE | re.DOTALL)
    if not select_match:
        return aggregations

    select_clause = select_match.group(1)

    for func_name, pattern in AGGREGATION_FUNCTIONS.items():
        # 해당 집계 함수 찾기
        matches = re.finditer(pattern, select_clause, re.IGNORECASE)
        for match in matches:
            target_column = match.group(1).strip()

            # AS 별칭 찾기 (집계 함수 뒤에 AS 또는 공백 후 별칭)
            # 예: SUM(amount) AS total_amount 또는 SUM(amount) total_amount
            full_expr = match.group(0)
            alias = None

            # select_clause에서 이 표현식 이후의 부분 찾기
            expr_end_pos = select_clause.find(full_expr) + len(full_expr)
            remaining = select_clause[expr_end_pos:].strip()

            # AS 키워드 확인
            as_match = re.match(r'^(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)', remaining, re.IGNORECASE)
            if as_match:
                potential_alias = as_match.group(1).upper()
                # FROM, WHERE 등 키워드가 아닌 경우만 별칭으로 인정
                if potential_alias not in ('FROM', 'WHERE', 'GROUP', 'ORDER', 'LIMIT', 'HAVING', 'AND', 'OR'):
                    alias = as_match.group(1)

            aggregations.append(AggregationInfo(
                function=func_name,
                target_column=target_column,
                alias=alias
            ))

    return aggregations


def detect_group_by(sql: str) -> Tuple[bool, List[str]]:
    """
    SQL에서 GROUP BY 절 감지

    Args:
        sql: SQL 쿼리 문자열

    Returns:
        (has_group_by, group_by_columns) 튜플
    """
    # GROUP BY 절 추출
    group_by_match = re.search(
        r'\bGROUP\s+BY\s+(.+?)(?=\s*(?:HAVING|ORDER\s+BY|LIMIT|OFFSET|;|$))',
        sql,
        re.IGNORECASE | re.DOTALL
    )

    if not group_by_match:
        return (False, [])

    group_by_clause = group_by_match.group(1).strip()

    # 컬럼 분리 (쉼표로)
    columns = [col.strip() for col in group_by_clause.split(',')]

    return (True, columns)


def build_aggregation_context(
    sql: str,
    is_refinement: bool = False,
    previous_row_count: Optional[int] = None
) -> Optional[AggregationContext]:
    """
    SQL에서 집계 컨텍스트 생성

    Args:
        sql: SQL 쿼리 문자열
        is_refinement: 이전 쿼리의 세분화 여부
        previous_row_count: 이전 쿼리 결과 건수

    Returns:
        AggregationContext 또는 None (집계 쿼리가 아닌 경우)
    """
    # 집계 함수 감지
    aggregations = detect_aggregation_functions(sql)

    if not aggregations:
        return None  # 집계 쿼리가 아님

    # WHERE 조건 추출
    where_conditions = extract_where_conditions(sql)

    # 사용자 친화적 표현 생성
    humanized_conditions = [humanize_where_condition(cond) for cond in where_conditions]

    # GROUP BY 감지
    has_group_by, group_by_columns = detect_group_by(sql)

    return AggregationContext(
        query_type="REFINEMENT" if is_refinement else "NEW_QUERY",
        based_on_filters=where_conditions,
        humanized_filters=humanized_conditions,
        source_row_count=previous_row_count,
        aggregations=aggregations,
        has_group_by=has_group_by,
        group_by_columns=group_by_columns
    )


def aggregation_context_to_dict(ctx: AggregationContext) -> Dict[str, Any]:
    """AggregationContext를 딕셔너리로 변환 (JSON 직렬화용)"""
    return {
        "queryType": ctx.query_type,
        "basedOnFilters": ctx.based_on_filters,
        "humanizedFilters": ctx.humanized_filters,
        "sourceRowCount": ctx.source_row_count,
        "aggregations": [
            {
                "function": agg.function,
                "targetColumn": agg.target_column,
                "alias": agg.alias
            }
            for agg in ctx.aggregations
        ],
        "hasGroupBy": ctx.has_group_by,
        "groupByColumns": ctx.group_by_columns
    }


# ============================================
# WHERE 조건 추출 및 병합 유틸리티
# ============================================

def extract_where_conditions(sql: str) -> List[str]:
    """
    SQL에서 WHERE 절의 개별 조건들을 추출

    Args:
        sql: SQL 쿼리 문자열

    Returns:
        개별 조건 문자열 리스트 (예: ["created_at >= '2024-01-01'", "status = 'DONE'"])
    """
    if not sql:
        return []

    # WHERE 절 추출 (WHERE ... 부터 GROUP BY/ORDER BY/LIMIT/; 전까지)
    where_pattern = r'\bWHERE\s+(.+?)(?=\s*(?:GROUP\s+BY|ORDER\s+BY|LIMIT|OFFSET|;|$))'
    match = re.search(where_pattern, sql, re.IGNORECASE | re.DOTALL)

    if not match:
        return []

    where_clause = match.group(1).strip()

    # AND로 분리 (단, 괄호 안의 AND는 무시)
    conditions = []
    current_condition = ""
    paren_depth = 0

    # 토큰 단위로 분리
    tokens = re.split(r'(\s+AND\s+)', where_clause, flags=re.IGNORECASE)

    for token in tokens:
        # AND 토큰인 경우
        if re.match(r'^\s*AND\s*$', token, re.IGNORECASE):
            if paren_depth == 0 and current_condition.strip():
                conditions.append(current_condition.strip())
                current_condition = ""
            else:
                current_condition += token
        else:
            # 괄호 깊이 추적
            paren_depth += token.count('(') - token.count(')')
            current_condition += token

    # 마지막 조건 추가
    if current_condition.strip():
        conditions.append(current_condition.strip())

    return conditions


def extract_condition_field(condition: str) -> Optional[str]:
    """
    조건에서 필드명 추출

    예: "created_at >= '2024-01-01'" → "created_at"
        "status = 'DONE'" → "status"
        "merchant_id IN ('mer_001', 'mer_002')" → "merchant_id"
    """
    # 일반적인 비교 연산자 패턴
    patterns = [
        r'^(\w+)\s*(?:=|!=|<>|>=|<=|>|<|LIKE|ILIKE|IN|NOT\s+IN|BETWEEN)',
        r'^(\w+)\s+IS\s+(?:NOT\s+)?NULL',
    ]

    for pattern in patterns:
        match = re.match(pattern, condition.strip(), re.IGNORECASE)
        if match:
            return match.group(1).lower()

    return None


def humanize_where_condition(condition: str) -> str:
    """
    SQL WHERE 조건을 사용자 친화적 표현으로 변환

    예: "created_at >= NOW() - INTERVAL '3 months'" → "기간: 최근 3개월"
        "status = 'DONE'" → "상태: 완료"
        "merchant_id = 'mer_001'" → "가맹점: mer_001"
    """
    # 필드명 → 한글 라벨 매핑
    FIELD_LABELS = {
        "created_at": "기간",
        "approved_at": "승인일",
        "merchant_id": "가맹점",
        "status": "상태",
        "method": "결제수단",
        "amount": "금액",
        "order_name": "상품명",
        "customer_id": "고객",
        "payment_key": "결제키",
        "settlement_date": "정산일",
    }

    # 상태값 한글 매핑
    STATUS_LABELS = {
        "DONE": "완료",
        "CANCELED": "취소",
        "PARTIAL_CANCELED": "부분취소",
        "IN_PROGRESS": "진행중",
        "READY": "대기",
        "FAILED": "실패",
        "EXPIRED": "만료",
        "PENDING": "대기중",
        "PROCESSED": "처리완료",
        "PAID_OUT": "지급완료",
        "ACTIVE": "활성",
        "SUSPENDED": "정지",
        "TERMINATED": "해지",
    }

    # 결제수단 한글 매핑
    METHOD_LABELS = {
        "CARD": "카드",
        "VIRTUAL_ACCOUNT": "가상계좌",
        "EASY_PAY": "간편결제",
        "TRANSFER": "계좌이체",
        "MOBILE": "모바일",
        "BANK_TRANSFER": "계좌이체",
    }

    # 시간 단위 한글 매핑
    TIME_UNIT_LABELS = {
        "months": "개월",
        "month": "개월",
        "days": "일",
        "day": "일",
        "weeks": "주",
        "week": "주",
        "years": "년",
        "year": "년",
        "hours": "시간",
        "hour": "시간",
    }

    # 필드명 추출
    field = extract_condition_field(condition)
    label = FIELD_LABELS.get(field, field) if field else None

    # 패턴 1: INTERVAL (시간 범위)
    # 예: "created_at >= NOW() - INTERVAL '3 months'"
    interval_match = re.search(r"INTERVAL\s+'(\d+)\s+(\w+)'", condition, re.IGNORECASE)
    if interval_match:
        num, unit = interval_match.groups()
        unit_kr = TIME_UNIT_LABELS.get(unit.lower(), unit)
        return f"{label}: 최근 {num}{unit_kr}"

    # 패턴 2: LIKE (부분 일치)
    # 예: "order_name LIKE '%도서%'"
    like_match = re.search(r"LIKE\s+'%([^%]+)%'", condition, re.IGNORECASE)
    if like_match:
        keyword = like_match.group(1)
        return f"{label}: {keyword} 포함"

    # 패턴 3: IN (다중 값)
    # 예: "status IN ('DONE', 'CANCELED')"
    in_match = re.search(r"IN\s*\(([^)]+)\)", condition, re.IGNORECASE)
    if in_match:
        values = in_match.group(1)
        # 값 추출 및 변환
        raw_values = re.findall(r"'([^']+)'", values)
        if field == "status":
            translated = [STATUS_LABELS.get(v, v) for v in raw_values]
        elif field == "method":
            translated = [METHOD_LABELS.get(v, v) for v in raw_values]
        else:
            translated = raw_values
        return f"{label}: {', '.join(translated)}"

    # 패턴 4: 범위 (BETWEEN)
    # 예: "amount BETWEEN 10000 AND 50000"
    between_match = re.search(r"BETWEEN\s+(\d+)\s+AND\s+(\d+)", condition, re.IGNORECASE)
    if between_match:
        low, high = between_match.groups()
        return f"{label}: {int(low):,} ~ {int(high):,}"

    # 패턴 5: 비교 연산자
    # >= 패턴: "amount >= 100000"
    gte_match = re.search(r">=\s*(\d+)", condition)
    if gte_match and "INTERVAL" not in condition.upper():
        value = int(gte_match.group(1))
        return f"{label}: {value:,} 이상"

    # <= 패턴
    lte_match = re.search(r"<=\s*(\d+)", condition)
    if lte_match:
        value = int(lte_match.group(1))
        return f"{label}: {value:,} 이하"

    # > 패턴
    gt_match = re.search(r"(?<!>)>\s*(\d+)", condition)
    if gt_match and "INTERVAL" not in condition.upper() and ">=" not in condition:
        value = int(gt_match.group(1))
        return f"{label}: {value:,} 초과"

    # < 패턴
    lt_match = re.search(r"(?<!<)<\s*(\d+)", condition)
    if lt_match and "<=" not in condition:
        value = int(lt_match.group(1))
        return f"{label}: {value:,} 미만"

    # 패턴 6: 등호 (=) - 마지막에 처리 (다른 패턴 우선)
    # 예: "status = 'DONE'" 또는 "merchant_id = 'mer_001'"
    eq_match = re.search(r"=\s*'([^']+)'", condition)
    if eq_match:
        value = eq_match.group(1)
        # 상태/결제수단 한글 변환
        if field == "status":
            value = STATUS_LABELS.get(value, value)
        elif field == "method":
            value = METHOD_LABELS.get(value, value)
        return f"{label}: {value}"

    # 기본: 원본 조건 반환 (변환 실패 시)
    return condition


def merge_where_conditions(existing: List[str], new: List[str]) -> List[str]:
    """
    기존 조건과 새 조건을 병합

    규칙:
    1. 동일 필드의 조건은 새 조건으로 대체
    2. 다른 필드의 조건은 AND로 병합

    Args:
        existing: 기존 WHERE 조건 리스트
        new: 새 WHERE 조건 리스트

    Returns:
        병합된 조건 리스트
    """
    if not existing:
        return new
    if not new:
        return existing

    # 기존 조건을 필드명으로 매핑
    existing_by_field: Dict[str, str] = {}
    for cond in existing:
        field_name = extract_condition_field(cond)
        if field_name:
            existing_by_field[field_name] = cond
        else:
            # 필드명 추출 실패 시 원본 유지
            existing_by_field[cond] = cond

    # 새 조건으로 덮어쓰기
    for cond in new:
        field_name = extract_condition_field(cond)
        if field_name:
            existing_by_field[field_name] = cond
        else:
            # 필드명 추출 실패 시 그냥 추가
            existing_by_field[cond] = cond

    return list(existing_by_field.values())


# ============================================
# PostgreSQL 스키마 정보 (프롬프트용)
# ============================================

SCHEMA_PROMPT = """
## PostgreSQL Database Schema

### payments (결제 트랜잭션)
| Column | Type | Description |
|--------|------|-------------|
| payment_key | VARCHAR(50) PK | 결제 고유 키 |
| order_id | VARCHAR(50) | 주문번호 |
| merchant_id | VARCHAR(20) FK | 가맹점 ID |
| customer_id | VARCHAR(20) | 고객 ID |
| order_name | VARCHAR(200) | 주문명 |
| amount | BIGINT | 결제 금액 |
| method | VARCHAR(30) | 결제 수단: CARD, VIRTUAL_ACCOUNT, EASY_PAY, TRANSFER, MOBILE |
| status | VARCHAR(30) | 상태: READY, IN_PROGRESS, WAITING_FOR_DEPOSIT, DONE, CANCELED, PARTIAL_CANCELED, ABORTED, EXPIRED |
| approved_at | TIMESTAMPTZ | 결제 승인 시간 |
| failure_code | VARCHAR(50) | 실패 코드 |
| failure_message | TEXT | 실패 메시지 |
| created_at | TIMESTAMPTZ | 생성 시간 |

### merchants (가맹점)
| Column | Type | Description |
|--------|------|-------------|
| merchant_id | VARCHAR(20) PK | 가맹점 ID |
| business_name | VARCHAR(100) | 사업체명 |
| business_number | VARCHAR(20) | 사업자등록번호 |
| representative_name | VARCHAR(50) | 대표자명 |
| email | VARCHAR(100) | 이메일 |
| phone | VARCHAR(20) | 전화번호 |
| status | VARCHAR(20) | 상태: PENDING, ACTIVE, SUSPENDED, TERMINATED |
| fee_rate | DECIMAL(5,4) | 수수료율 (0.033 = 3.3%) |
| settlement_cycle | VARCHAR(10) | 정산 주기: D+0, D+1, D+2, WEEKLY, MONTHLY |
| settlement_account_bank | VARCHAR(20) | 정산 계좌 은행 |
| settlement_account_number | VARCHAR(30) | 정산 계좌번호 |
| settlement_account_holder | VARCHAR(50) | 정산 계좌 예금주 |
| created_at | TIMESTAMPTZ | 등록일 |

### refunds (환불)
| Column | Type | Description |
|--------|------|-------------|
| refund_key | VARCHAR(50) PK | 환불 고유 키 |
| payment_key | VARCHAR(50) FK | 원 결제 키 |
| amount | BIGINT | 환불 금액 |
| tax_free_amount | BIGINT | 면세 금액 |
| reason | VARCHAR(500) | 환불 사유 |
| status | VARCHAR(20) | 상태: PENDING, DONE, FAILED |
| approved_at | TIMESTAMPTZ | 환불 승인 시간 |
| created_at | TIMESTAMPTZ | 환불 요청 시간 |

### settlements (정산)
| Column | Type | Description |
|--------|------|-------------|
| settlement_id | VARCHAR(30) PK | 정산 ID |
| merchant_id | VARCHAR(20) FK | 가맹점 ID |
| settlement_date | DATE | 정산일 |
| period_start | DATE | 정산 기간 시작 |
| period_end | DATE | 정산 기간 종료 |
| total_payment_amount | BIGINT | 총 결제 금액 |
| total_refund_amount | BIGINT | 총 환불 금액 |
| total_fee | BIGINT | 총 수수료 |
| net_amount | BIGINT | 정산 금액 |
| payment_count | INTEGER | 결제 건수 |
| refund_count | INTEGER | 환불 건수 |
| status | VARCHAR(20) | 상태: PENDING, PROCESSED, PAID_OUT, FAILED |
| created_at | TIMESTAMPTZ | 생성 시간 |

### settlement_details (정산 상세)
| Column | Type | Description |
|--------|------|-------------|
| detail_id | VARCHAR(30) PK | 상세 ID |
| settlement_id | VARCHAR(30) FK | 정산 ID |
| payment_key | VARCHAR(50) | 결제 키 |
| amount | BIGINT | 결제 금액 |
| fee | BIGINT | 수수료 |
| net_amount | BIGINT | 정산 금액 |
| type | VARCHAR(20) | 유형: PAYMENT, REFUND |

### pg_customers (고객)
| Column | Type | Description |
|--------|------|-------------|
| customer_id | VARCHAR(20) PK | 고객 ID |
| merchant_id | VARCHAR(20) FK | 가맹점 ID |
| email | VARCHAR(100) | 이메일 |
| name | VARCHAR(50) | 고객명 |
| phone | VARCHAR(20) | 전화번호 |
| created_at | TIMESTAMPTZ | 등록일 |

### payment_methods (결제 수단)
| Column | Type | Description |
|--------|------|-------------|
| payment_method_id | VARCHAR(30) PK | 결제수단 ID |
| customer_id | VARCHAR(20) FK | 고객 ID |
| type | VARCHAR(20) | 유형: CARD, BANK_ACCOUNT |
| card_company | VARCHAR(30) | 카드사 |
| card_number_masked | VARCHAR(20) | 마스킹된 카드번호 |
| bank_code | VARCHAR(10) | 은행코드 |
| status | VARCHAR(20) | 상태: ACTIVE, INACTIVE |
| is_default | BOOLEAN | 기본 결제수단 여부 |
| created_at | TIMESTAMPTZ | 등록일 |

### payment_history (결제 상태 이력)
| Column | Type | Description |
|--------|------|-------------|
| history_id | SERIAL PK | 이력 ID |
| payment_key | VARCHAR(50) FK | 결제 키 |
| previous_status | VARCHAR(30) | 이전 상태 |
| new_status | VARCHAR(30) | 변경 상태 |
| reason | TEXT | 변경 사유 |
| processed_by | VARCHAR(50) | 처리자 |
| created_at | TIMESTAMPTZ | 변경 시간 |

### balance_transactions (잔액 거래)
| Column | Type | Description |
|--------|------|-------------|
| transaction_id | VARCHAR(30) PK | 거래 ID |
| merchant_id | VARCHAR(20) FK | 가맹점 ID |
| source_type | VARCHAR(20) | 거래 유형: PAYMENT, REFUND, PAYOUT, ADJUSTMENT |
| source_id | VARCHAR(50) | 원 거래 ID |
| amount | BIGINT | 거래 금액 |
| fee | BIGINT | 수수료 |
| net | BIGINT | 순 금액 |
| balance_before | BIGINT | 거래 전 잔액 |
| balance_after | BIGINT | 거래 후 잔액 |
| status | VARCHAR(20) | 상태: PENDING, AVAILABLE |
| created_at | TIMESTAMPTZ | 거래 시간 |

### orders (주문 - 샘플)
| Column | Type | Description |
|--------|------|-------------|
| order_id | SERIAL PK | 주문 ID |
| customer_id | INTEGER | 고객 ID |
| order_date | TIMESTAMPTZ | 주문 일시 |
| total_amount | DECIMAL(10,2) | 총 금액 |
| status | VARCHAR(20) | 상태: PENDING, PAID, SHIPPED, DELIVERED, CANCELLED |
| payment_gateway | VARCHAR(50) | 결제 수단 |

## Common Patterns

### 금액 조회 시 포맷팅
- 금액 필드: amount, total_amount, net_amount, fee 등
- 원화 단위 (KRW), 별도 포맷팅 불필요

### 시간 범위 쿼리
- approved_at, created_at 등은 TIMESTAMPTZ 타입
- 예: WHERE approved_at >= '2024-01-01' AND approved_at < '2024-02-01'

### 상태 필터
- status 필드는 대문자 영문 (예: 'DONE', 'CANCELED')

### JOIN 관계 (중요!)
- payments.merchant_id -> merchants.merchant_id
- payments.payment_key -> refunds.payment_key
- payments.payment_key -> payment_history.payment_key (결제 → 상태이력)
- settlements.merchant_id -> merchants.merchant_id
- settlement_details.settlement_id -> settlements.settlement_id

### failure_code 필드 위치 (주의!)
- payments.failure_code: 결제 실패 코드 (status='ABORTED' 상태에서)
- refunds.failure_code: 환불 실패 코드 (없음)
- **payment_history에는 failure_code 컬럼 없음!**
  → 실패 결제의 상태 이력 조회 시 반드시 payments와 JOIN 필요
  → 예: SELECT ph.* FROM payment_history ph JOIN payments p ON ph.payment_key = p.payment_key WHERE p.failure_code = 'INVALID_CARD'

### 집계 결과 기반 상세 조회 규칙
이전 쿼리가 집계(GROUP BY)였고, 꼬리 질문이 특정 그룹값의 상세 조회인 경우:
- 집계에서 그룹핑된 컬럼 값을 WHERE 조건으로 변환
- 예: "INVALID_CARD 오류로 집계된 결제건의 상세이력"
  → WHERE p.failure_code = 'INVALID_CARD' 조건 적용
  → payments와 payment_history 조인
"""


@dataclass
class SqlResult:
    """SQL 실행 결과"""
    success: bool
    data: List[Dict[str, Any]]
    row_count: int                              # 반환된 행 수
    sql: str
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    total_count: Optional[int] = None           # 전체 건수 (COUNT 쿼리 결과)
    is_truncated: bool = False                  # max_rows 초과로 잘렸는지 여부


@dataclass
class ConversationContext:
    """연속 대화 컨텍스트"""
    previous_question: Optional[str]
    previous_sql: Optional[str]
    previous_result_summary: Optional[str]
    # 연속 대화용 추가 필드
    accumulated_where_conditions: List[str] = field(default_factory=list)
    is_refinement: bool = False  # True면 이전 WHERE 조건 유지 필요
    # 대화 기반 맥락 처리용 전체 대화 이력
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)


class TextToSqlService:
    """
    Text-to-SQL 서비스

    자연어 질문을 SQL로 변환하고, 읽기 전용 DB에서 실행합니다.

    보안 레이어:
    1. PostgreSQL 읽기 전용 계정 (DB 레벨)
    2. SqlValidator (애플리케이션 레벨)
    3. 실행 제한 (타임아웃, 행 수 제한)
    """

    def __init__(
        self,
        readonly_url: Optional[str] = None,
        timeout_seconds: int = 30,
        max_rows: int = 1000,
        default_limit: int = 1000
    ):
        """
        Args:
            readonly_url: 읽기 전용 DB 연결 URL
            timeout_seconds: 쿼리 실행 타임아웃 (초)
            max_rows: 최대 반환 행 수
            default_limit: LIMIT 기본값
        """
        self.readonly_url = readonly_url or os.getenv(
            "DATABASE_READONLY_URL",
            os.getenv("DATABASE_URL")  # 폴백: 기본 DB URL
        )
        self.timeout_ms = timeout_seconds * 1000
        self.max_rows = max_rows
        self.default_limit = default_limit

        self.validator = get_sql_validator(max_rows=max_rows, default_limit=default_limit)

        # LLM 설정
        self._llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self._llm = None

        # RAG 설정
        self._rag_enabled = os.getenv("RAG_ENABLED", "true").lower() == "true"
        self._rag_top_k = int(os.getenv("RAG_TOP_K", "3"))

    def _get_llm(self):
        """LLM 인스턴스 지연 초기화"""
        if self._llm is None:
            if self._llm_provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY is not set")
                self._llm = ChatAnthropic(
                    model=os.getenv("LLM_MODEL", "claude-3-5-haiku-20241022"),
                    temperature=0,
                    api_key=api_key
                )
            else:
                from langchain_openai import ChatOpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY is not set")
                self._llm = ChatOpenAI(
                    model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                    temperature=0,
                    api_key=api_key
                )
            logger.info(f"Text-to-SQL LLM initialized: {self._llm_provider}")
        return self._llm

    def _get_readonly_connection(self):
        """읽기 전용 DB 연결"""
        if not self.readonly_url:
            raise ValueError("DATABASE_READONLY_URL is not set")

        return psycopg.connect(
            self.readonly_url,
            row_factory=dict_row,
            options=f"-c statement_timeout={self.timeout_ms}"
        )

    async def _get_rag_context(self, question: str) -> str:
        """RAG 컨텍스트 조회"""
        if not self._rag_enabled:
            return ""

        try:
            rag_service = get_rag_service()
            # search_docs() 메서드 사용 (search()는 존재하지 않음)
            results = await rag_service.search_docs(query=question, k=self._rag_top_k)

            if not results:
                return ""

            context_parts = []
            for doc in results:
                # Document 객체의 속성 접근
                context_parts.append(f"[{doc.doc_type}] {doc.title}: {doc.content[:500]}")

            logger.info(f"RAG context retrieved: {len(results)} documents")
            return "\n\n".join(context_parts)
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {e}")
            return ""

    def _build_prompt(
        self,
        question: str,
        conversation_context: Optional[ConversationContext] = None,
        rag_context: str = ""
    ) -> str:
        """
        SQL 생성 프롬프트 구성

        대화 기반 맥락 처리 방식:
        - 규칙 기반 강제 대신 자연스러운 대화 흐름으로 컨텍스트 전달
        - Claude Code처럼 대화 이력을 명확하게 보여주어 LLM이 맥락을 이해하도록 함
        """
        prompt_parts = []

        # 현재 날짜 정보 추가
        current_date = datetime.now().strftime('%Y-%m-%d')
        prompt_parts.append(f"현재 날짜: {current_date}")

        # 시간 조회 규칙 (현재 날짜 주입) - f-string 사용
        time_rules = f"""
## 시간 조회 규칙 (매우 중요!)
- 기본: created_at 사용
- "승인일 기준", "매출 기준" → approved_at 사용
- **"오늘", "금일", "당일"** → created_at >= '{current_date}' AND created_at < '{current_date}'::date + 1
- "어제" → created_at >= '{current_date}'::date - 1 AND created_at < '{current_date}'
- "최근 N개월" → created_at >= NOW() - INTERVAL 'N months'

**필수**: 사용자가 "오늘"을 언급하면 반드시 날짜 조건 created_at >= '{current_date}'를 포함하세요!
"""

        # 시스템 지시 (간결하게) - 일반 문자열 사용 (플레이스홀더 충돌 방지)
        prompt_parts.append("""
당신은 PostgreSQL SQL 전문가입니다.
사용자의 자연어 질문을 분석하여 정확한 SELECT 쿼리를 생성합니다.

## 기본 규칙
- SELECT 문만 생성 (INSERT, UPDATE, DELETE 금지)
- 테이블/컬럼명은 snake_case 사용
- 문자열 비교 시 정확한 값 사용 (예: status = 'DONE')
- LIMIT: 사용자가 건수를 명시한 경우에만 추가
- 결제 실패/오류 조회: status='ABORTED' 사용, "상세" 키워드 시 failure_code와 failure_message 모두 SELECT, "건수" 키워드 시 COUNT(*) 집계 + GROUP BY 필수
""" + time_rules + """
## 시간 그룹핑 시 포맷팅 (중요!)
GROUP BY로 시간을 묶을 때, 사용자가 읽기 쉬운 형태로 포맷팅하세요:
- 월별: TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY-MM') AS month
- 일별: TO_CHAR(DATE_TRUNC('day', created_at), 'YYYY-MM-DD') AS date
- 주별: TO_CHAR(DATE_TRUNC('week', created_at), 'YYYY-MM-DD') AS week
- 연별: TO_CHAR(DATE_TRUNC('year', created_at), 'YYYY') AS year

예시:
- "월별 매출" → SELECT TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY-MM') AS month, SUM(amount)...
- 절대로 DATE_TRUNC만 사용하지 마세요 (전체 timestamp가 반환됨)

## 응답 형식 (JSON)
반드시 아래 JSON 형식으로만 응답하세요:

```json
{
  "sql": "SELECT ... ;",
  "chartType": "line | bar | pie | none",
  "chartReason": "판단 근거",
  "insightTemplate": "한국어 인사이트 템플릿 (chartType이 none이 아닐 때만)"
}
```

### chartType 결정 기준:
- **line**: 시계열 데이터 (날짜/시간 기준 GROUP BY) + 추이/변화/트렌드/일별/월별/주별 키워드
- **bar**: 카테고리별 비교 (가맹점별, 상태별 등)
- **pie**: 비율/점유율/분포 키워드 + 적은 카테고리 (≤10개)
- **none**: 차트 요청 키워드("그래프", "차트", "시각화") 없음 → 테이블로 표시

중요: 사용자가 "그래프", "차트", "시각화" 등을 명시적으로 요청한 경우에만 line/bar/pie 중 하나를 선택하세요.
그렇지 않으면 chartType은 "none"으로 설정하세요.

### insightTemplate 작성 가이드:
chartType이 line/bar/pie인 경우에만 작성하세요. 플레이스홀더를 사용하여 템플릿을 작성합니다.

**사용 가능한 플레이스홀더:**
- {count}: 데이터 포인트 수
- {total}: Y축 값 합계 (숫자만, 단위는 템플릿에 직접 작성)
- {avg}: 평균값 (숫자만, 단위는 템플릿에 직접 작성)
- {max}: 최대값 (숫자만, 단위는 템플릿에 직접 작성)
- {min}: 최소값 (숫자만, 단위는 템플릿에 직접 작성)
- {maxCategory}: 최대값을 가진 X축 항목
- {minCategory}: 최소값을 가진 X축 항목
- {trend}: 추세 (증가/감소/유지, line 차트에서만)
- {groupBy}: X축 필드명 (한글)
- {metric}: Y축 필드명 (한글)

**⚠️ 중요: 단위 표기는 메트릭 유형에 맞게 템플릿에 직접 작성하세요!**
- **금액 메트릭** (amount, fee, totalAmount 등): "₩{max}", "총 ₩{total}"
- **건수 메트릭** (count, paymentCount 등): "{max}건", "총 {total}건"
- **비율 메트릭** (rate, ratio 등): "{max}%"

**예시:**
- 건수 시계열(line): "{groupBy}별 {metric} 추이입니다. 총 {count}개 {groupBy}의 데이터를 분석한 결과, {trend} 추세를 보이며 최고점은 {max}건입니다."
- 금액 시계열(line): "{groupBy}별 {metric} 추이입니다. 총 {count}개 {groupBy}의 데이터를 분석한 결과, {trend} 추세를 보이며 최고점은 ₩{max}입니다."
- 건수 비교(bar): "{groupBy}별 {metric} 비교 결과, {maxCategory}가 {max}건으로 가장 많고, {minCategory}가 {min}건으로 가장 적습니다."
- 금액 비교(bar): "{groupBy}별 {metric} 비교 결과, {maxCategory}가 ₩{max}로 가장 높고, {minCategory}가 ₩{min}로 가장 낮습니다."
- 분포(pie): "{groupBy}별 {metric} 분포입니다. {maxCategory}가 가장 큰 비중을 차지하며, 총 {count}개 항목이 있습니다."
""")

        # 복잡한 쿼리 패턴 가이드
        prompt_parts.append("""
## 복잡한 쿼리 패턴 가이드

### 패턴 1: 상위 N개 엔티티의 세부 집계 (Top N + Secondary Aggregation)
**인식 키워드**: "상위 N개", "Top N", "가장 많은 N개", "오류가 많은 N개" + "~별 집계/조회"

**⚠️ 중요**: "상위 N개"가 포함된 질문에서 LIMIT N은 반드시 CTE 안에서 사용!

**올바른 SQL 구조**:
```sql
WITH top_entities AS (
    -- 1단계: 상위 N개 엔티티 식별
    SELECT entity_id, COUNT(*) as total_count
    FROM main_table
    WHERE [필터 조건]
    GROUP BY entity_id
    ORDER BY total_count DESC
    LIMIT N
)
SELECT t.entity_id, dimension_column, COUNT(*) AS count
FROM main_table t
JOIN top_entities te ON t.entity_id = te.entity_id
WHERE [동일 필터 조건]
GROUP BY t.entity_id, dimension_column
ORDER BY t.entity_id, dimension_column;
```

**실제 예시** (오류 많은 상위 5개 가맹점의 시간대별 오류):
```sql
WITH top_error_merchants AS (
    SELECT merchant_id, COUNT(*) as error_count
    FROM payments
    WHERE created_at >= NOW() - INTERVAL '3 months' AND status = 'ABORTED'
    GROUP BY merchant_id
    ORDER BY error_count DESC
    LIMIT 5
)
SELECT p.merchant_id, EXTRACT(HOUR FROM p.created_at) AS hour, COUNT(*) AS error_count
FROM payments p
JOIN top_error_merchants tem ON p.merchant_id = tem.merchant_id
WHERE p.created_at >= NOW() - INTERVAL '3 months' AND p.status = 'ABORTED'
GROUP BY p.merchant_id, EXTRACT(HOUR FROM p.created_at)
ORDER BY p.merchant_id, hour;
```

### 패턴 2: 조건부 집계 (Conditional Aggregation)
**인식 키워드**: "~별 성공/실패 건수", "상태별 비교"

```sql
SELECT
    merchant_id,
    COUNT(*) FILTER (WHERE status = 'DONE') AS success_count,
    COUNT(*) FILTER (WHERE status = 'ABORTED') AS error_count
FROM payments
WHERE created_at >= NOW() - INTERVAL '3 months'
GROUP BY merchant_id;
```

### 패턴 3: 비율/점유율 계산
**인식 키워드**: "비율", "점유율", "퍼센트"

```sql
SELECT
    merchant_id,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM payments
GROUP BY merchant_id
ORDER BY percentage DESC;
```

### 패턴 인식 규칙 요약
| 키워드 조합 | 사용할 패턴 |
|------------|-----------|
| "상위/하위 N개" + "~별 집계" | 패턴 1 (CTE 필수) |
| "상위/하위 N개" 단독 | 단순 ORDER BY + LIMIT |
| "성공/실패 동시 집계" | 패턴 2 (FILTER) |
| "비율/점유율" | 패턴 3 (윈도우 함수) |
""")

        # 스키마 정보
        prompt_parts.append(SCHEMA_PROMPT)

        # RAG 컨텍스트
        if rag_context:
            prompt_parts.append(f"\n## 참고 문서\n{rag_context}")

        # 대화 기반 컨텍스트 (자연스러운 대화 형태)
        if conversation_context and conversation_context.conversation_history:
            prompt_parts.append(self._build_conversation_flow(conversation_context))

        # SQL 생성 가이드라인 - LLM 기반 의도 판단 포함
        prompt_parts.append("""
## 1단계: 질문 유형 판단 (필수)
SQL을 생성하기 전에, 먼저 사용자 질문이 다음 중 어떤 유형인지 판단하세요:

### A) 새 쿼리 (new_query): 이전 조건과 관계없이 새로운 검색 시작
   - "최근 N개월/일 조회" (이전과 다른 새로운 시간 조건으로 조회 요청)
   - "새로", "다시", "처음부터" 등 명시적 리셋 표현
   - "잊어버리고", "무시하고" 등 이전 컨텍스트 무효화 표현
   - 이전 대화와 다른 엔티티(테이블)를 조회하는 경우
   - 완전히 독립적이고 자기 완결적인 질문 (시간 범위 + 대상 모두 명시)

### B) 꼬리질문 (refinement): 이전 결과에서 추가 필터링
   **명시적 참조 표현:**
   - "이중에", "여기서", "그중에", "위 결과에서" 등

   **암시적 참조 표현 (핵심!):**
   - "[값] ~만" 패턴: "mer_008 가맹점만", "DONE 상태만", "카드 결제만"
   - "[조건] 이상/이하/초과/미만": "10만원 이상만", "100건 이상만"
   - "[값] 제외", "[값] 빼고": "취소건 제외", "테스트 가맹점 빼고"

   **refinement 판단 기준:**
   1. 질문이 짧고 필터 조건만 언급 (시간 범위 없음)
   2. 이전 쿼리와 동일한 테이블/엔티티 대상
   3. 이전 결과를 좁히는 성격의 조건

   **예시:**
   - 이전: "최근 3개월 결제건 조회" → 현재: "mer_008 가맹점만" → refinement
   - 이전: "오늘 결제 내역" → 현재: "DONE 상태만" → refinement
   - 이전: "이번 달 매출" → 현재: "10만원 이상만" → refinement
   - 이전: "결제 조회" → 현재: "정산 현황" → new_query (다른 엔티티)

## 2단계: SQL 생성
- **new_query**: 이전 WHERE 조건 무시, 새로운 SQL 생성
- **refinement**: 직전 SQL의 WHERE 조건 유지 + 새 조건 추가

### 같은 컬럼 조건 처리 - 의도 판단 필수!

사용자가 같은 컬럼에 대해 새 조건을 언급할 때, **표현을 분석**하여 의도를 판단하세요:

**1. AND (둘 다 포함)**: "~이면서", "~이고", "둘 다", "그리고", "동시에"
   - 예: "도서이면서 가구도 포함된 것"
   - SQL: order_name LIKE '%도서%' AND order_name LIKE '%가구%'

**2. OR (둘 중 하나)**: "~또는", "~이거나", "~나", "혹은"
   - 예: "도서 또는 가구 관련"
   - SQL: (order_name LIKE '%도서%' OR order_name LIKE '%가구%')

**3. 교체 (기존 대체)**: "~만", "~로 바꿔", "대신", "말고", 단순 필터 변경
   - 예: "여기서 가구 소품만" (이전 도서 조건 대체)
   - SQL: order_name LIKE '%가구%' (기존 LIKE 조건 제거)

**기본 규칙**:
- 모호한 경우 "~만"은 교체로 처리
- **다른 컬럼** 조건은 항상 AND로 추가
  - 예: "mer_001 가맹점만" + "DONE 상태만" = merchant_id = 'mer_001' AND status = 'DONE'

중요: refinement 시에는 "직전 쿼리"의 조건만 유지하세요.
더 오래된 대화의 조건은 새 쿼리에서 리셋되었을 수 있습니다.
""")

        # 현재 질문
        prompt_parts.append(f"\n## 현재 질문\n{question}")

        return "\n".join(prompt_parts)

    def _build_conversation_flow(self, context: ConversationContext) -> str:
        """
        대화 이력을 자연스러운 흐름으로 구성

        Phase 4 개선:
        - 누적된 WHERE 조건을 명시적으로 강조
        - 4단계+ 체이닝에서도 모든 조건이 유지되도록 LLM에게 명확한 지시

        Phase 5 (TC-005) 개선:
        - 직전 쿼리의 WHERE 조건을 별도 섹션으로 강조
        - 암시적 참조 판단을 위한 컨텍스트 강화

        Claude Code처럼 대화 이력을 명확하게 보여주어
        LLM이 맥락을 자연스럽게 이해하도록 합니다.
        """
        if not context.conversation_history:
            return ""

        parts = ["\n## 대화 이력"]
        turn_number = 1
        last_sql = None
        last_where_conditions = []
        last_table = None

        for entry in context.conversation_history:
            role = entry.get("role", "")
            content = entry.get("content", "")
            sql = entry.get("sql")
            row_count = entry.get("rowCount")
            where_conditions = entry.get("whereConditions", [])

            if role == "user":
                parts.append(f"\n[{turn_number}] User: {content}")
            elif role == "assistant" and sql:
                # SQL과 결과 건수를 함께 표시
                result_info = f"결과: {row_count}건" if row_count is not None else "결과: 있음"
                parts.append(f"    -> SQL: {sql}")
                parts.append(f"    -> {result_info}")
                # Phase 4: WHERE 조건도 각 턴별로 표시 (LLM이 조건 흐름을 추적하도록)
                if where_conditions:
                    parts.append(f"    -> WHERE 조건: {where_conditions}")
                turn_number += 1
                # 직전 쿼리 정보 저장
                last_sql = sql
                last_where_conditions = where_conditions if where_conditions else extract_where_conditions(sql)
                # 테이블명 추출
                table_match = re.search(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
                if table_match:
                    last_table = table_match.group(1)

        # Phase 5 (TC-005): 직전 쿼리 정보를 별도 섹션으로 강조
        if last_sql:
            parts.append("\n" + "=" * 50)
            parts.append("## 직전 쿼리 요약 (refinement 판단용)")
            parts.append("=" * 50)
            if last_table:
                parts.append(f"- 테이블: {last_table}")
            if last_where_conditions:
                parts.append("- WHERE 조건:")
                for cond in last_where_conditions:
                    # 조건을 사람이 읽기 쉬운 형태로 변환
                    humanized = humanize_where_condition(cond)
                    parts.append(f"  * {humanized} (`{cond}`)")
            else:
                parts.append("- WHERE 조건: 없음")
            parts.append("")
            parts.append("**현재 질문이 위 결과를 필터링하는 것인지 판단하세요.**")
            parts.append("짧은 필터 표현(예: 'mer_008 가맹점만')은 refinement일 가능성이 높습니다.")
            parts.append("=" * 50)

        # Phase 5: 누적된 WHERE 조건 처리 (is_refinement 여부에 따라 강제/참고)
        if context.accumulated_where_conditions:
            parts.append("\n" + "=" * 50)

            if context.is_refinement:
                # TC-005: 암시적 참조 감지 시 이전 조건 강제 포함
                parts.append("### ⚠️ [필수] 이전 WHERE 조건을 반드시 유지하세요")
                parts.append("=" * 50)
                parts.append("**현재 질문은 이전 결과에 대한 추가 필터링입니다.**")
                parts.append("**아래 조건들을 WHERE 절에 반드시 포함하세요:**")
                parts.append("")
                for i, cond in enumerate(context.accumulated_where_conditions, 1):
                    parts.append(f"  {i}. `{cond}` ← 필수")
                parts.append("")
                parts.append("**작성 방법:**")
                parts.append("- 위 조건들을 유지하고, 새 조건을 AND로 추가")
                parts.append("- 예: `WHERE (기존조건1) AND (기존조건2) AND (새조건)`")
                parts.append("- 절대로 기존 조건을 생략하지 마세요!")
                parts.append("")
                parts.append("### 같은 컬럼 조건 처리 - 의도 판단!")
                parts.append("같은 컬럼에 새 조건 추가 시 사용자 표현을 분석:")
                parts.append("- '~이면서/이고/둘다' -> AND로 추가")
                parts.append("- '~또는/이거나' -> OR로 추가")
                parts.append("- '~만/대신/말고' -> 기존 조건 교체")
                parts.append("")
                parts.append("**다른 컬럼** 조건만 무조건 AND로 유지/추가합니다.")
            else:
                # 기존 로직: 참고용으로 표시
                parts.append("### [참고] 전체 대화에서 누적된 WHERE 조건")
                parts.append("-" * 50)
                for i, cond in enumerate(context.accumulated_where_conditions, 1):
                    parts.append(f"  {i}. `{cond}`")
                parts.append("")
                parts.append("**위 조건 사용 여부는 질문 유형에 따라 결정하세요:**")
                parts.append("- new_query: 위 조건 무시, 새로운 WHERE 절 작성")
                parts.append("- refinement: 직전 쿼리의 조건만 유지 + 새 조건 추가")

            parts.append("=" * 50)

        return "\n".join(parts)

    def _parse_llm_response(self, raw_response: str) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[List[Dict[str, Any]]]]:
        """
        LLM 응답에서 SQL, 차트 타입, 인사이트 템플릿, Summary Stats 템플릿 추출

        Args:
            raw_response: LLM 원본 응답

        Returns:
            (sql, chart_type, chart_reason, insight_template, summary_stats_template) 튜플
        """
        # JSON 블록 추출 시도
        json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                sql = data.get("sql", "").strip()
                chart_type = data.get("chartType")
                chart_reason = data.get("chartReason")
                insight_template = data.get("insightTemplate")
                summary_stats_template = data.get("summaryStatsTemplate")
                logger.info(f"Parsed JSON response - chartType: {chart_type}, reason: {chart_reason}, insightTemplate: {insight_template is not None}, summaryStatsTemplate: {summary_stats_template is not None}")
                return (sql, chart_type, chart_reason, insight_template, summary_stats_template)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON block: {e}")

        # JSON 직접 파싱 시도 (코드 블록 없이 JSON만 반환된 경우)
        try:
            data = json.loads(raw_response)
            sql = data.get("sql", "").strip()
            chart_type = data.get("chartType")
            chart_reason = data.get("chartReason")
            insight_template = data.get("insightTemplate")
            summary_stats_template = data.get("summaryStatsTemplate")
            logger.info(f"Parsed direct JSON - chartType: {chart_type}, reason: {chart_reason}, insightTemplate: {insight_template is not None}, summaryStatsTemplate: {summary_stats_template is not None}")
            return (sql, chart_type, chart_reason, insight_template, summary_stats_template)
        except json.JSONDecodeError:
            pass

        # 폴백: 기존 방식 (SQL만 추출)
        logger.warning("Failed to parse JSON response, falling back to SQL-only extraction")
        sql = raw_response
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block or not line.startswith("```"):
                    sql_lines.append(line)
            sql = "\n".join(sql_lines).strip()

        return (sql.strip(), None, None, None, None)

    async def generate_sql(
        self,
        question: str,
        conversation_context: Optional[ConversationContext] = None
    ) -> Tuple[str, ValidationResult, Optional[str], Optional[str], Optional[List[Dict[str, Any]]]]:
        """
        자연어를 SQL로 변환

        Args:
            question: 사용자 질문
            conversation_context: 연속 대화 컨텍스트

        Returns:
            (생성된 SQL, 검증 결과, 추천 차트 타입, 인사이트 템플릿, summaryStats 템플릿) 튜플
        """
        # RAG 컨텍스트 조회
        rag_context = await self._get_rag_context(question)

        # 프롬프트 구성
        prompt = self._build_prompt(question, conversation_context, rag_context)

        # LLM 호출
        llm = self._get_llm()
        response = await llm.ainvoke(prompt)

        # JSON 응답 파싱 (SQL + 차트 타입 + 인사이트 템플릿 + summaryStats 템플릿)
        raw_response = response.content.strip()
        raw_sql, chart_type, chart_reason, insight_template, summary_stats_template = self._parse_llm_response(raw_response)

        logger.info(f"Generated SQL: {raw_sql[:200]}...")
        if chart_type:
            logger.info(f"LLM chart type recommendation: {chart_type} (reason: {chart_reason})")
        if insight_template:
            logger.info(f"LLM insight template: {insight_template[:100]}...")
        if summary_stats_template:
            logger.info(f"LLM summaryStats template: {len(summary_stats_template)} items")

        # SQL 검증
        validation_result = self.validator.validate(raw_sql)

        return raw_sql, validation_result, chart_type, insight_template, summary_stats_template

    def _get_count(self, sql: str) -> int:
        """
        원본 SQL을 COUNT 쿼리로 변환하여 전체 건수 확인

        Args:
            sql: 원본 SELECT SQL

        Returns:
            전체 행 수
        """
        import re

        # LIMIT/OFFSET 제거
        count_sql = re.sub(r'\bLIMIT\s+\d+', '', sql, flags=re.IGNORECASE)
        count_sql = re.sub(r'\bOFFSET\s+\d+', '', count_sql, flags=re.IGNORECASE)

        # ORDER BY 제거 (COUNT에서 불필요)
        count_sql = re.sub(r'\bORDER\s+BY\s+[^)]+$', '', count_sql, flags=re.IGNORECASE)

        # SELECT ... → SELECT COUNT(*) FROM (...) sub
        count_sql = f"SELECT COUNT(*) as cnt FROM ({count_sql.strip()}) sub"

        try:
            with self._get_readonly_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(count_sql)
                    result = cur.fetchone()
                    count = result['cnt'] if result else 0
                    logger.info(f"COUNT query result: {count}")
                    return count
        except psycopg.Error as e:
            logger.warning(f"COUNT query failed, returning 0: {e}")
            return 0

    def execute_sql(self, sql: str) -> SqlResult:
        """
        SQL 실행 (동기)

        1. 먼저 COUNT 쿼리로 전체 건수 확인
        2. max_rows 초과 시 데이터 조회 스킵 (다운로드로 유도)
        3. max_rows 이하면 데이터 조회

        Args:
            sql: 실행할 SQL (검증 완료된 것)

        Returns:
            SqlResult: 실행 결과
        """
        import time
        start_time = time.time()

        try:
            # 1. 먼저 COUNT 쿼리로 전체 건수 확인
            total_count = self._get_count(sql)
            logger.info(f"Total count: {total_count}, max_rows: {self.max_rows}")

            # 2. max_rows 초과면 데이터 조회 스킵 (다운로드로 유도)
            if total_count > self.max_rows:
                execution_time_ms = (time.time() - start_time) * 1000
                logger.info(f"Data exceeds max_rows ({total_count} > {self.max_rows}), skipping data fetch")

                return SqlResult(
                    success=True,
                    data=[],                        # 데이터 없음
                    row_count=0,
                    sql=sql,
                    execution_time_ms=execution_time_ms,
                    total_count=total_count,        # 전체 건수만 제공
                    is_truncated=True               # 잘림 표시
                )

            # 3. max_rows 이하면 기존대로 실행
            with self._get_readonly_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()

                    execution_time_ms = (time.time() - start_time) * 1000

                    # dict_row 사용으로 이미 딕셔너리 형태
                    data = [dict(row) for row in rows]

                    # datetime 객체를 ISO 문자열로 변환
                    for row in data:
                        for key, value in row.items():
                            if isinstance(value, datetime):
                                row[key] = value.isoformat()

                    logger.info(f"SQL executed: {len(data)} rows in {execution_time_ms:.1f}ms")

                    return SqlResult(
                        success=True,
                        data=data,
                        row_count=len(data),
                        sql=sql,
                        execution_time_ms=execution_time_ms,
                        total_count=total_count,    # 전체 건수
                        is_truncated=False
                    )

        except psycopg.Error as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"SQL execution failed: {e}")
            return SqlResult(
                success=False,
                data=[],
                row_count=0,
                sql=sql,
                error=str(e),
                execution_time_ms=execution_time_ms
            )

    async def query(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        retry_on_error: bool = True,
        is_refinement: bool = False
    ) -> Dict[str, Any]:
        """
        자연어 질문 처리 (생성 + 검증 + 실행)

        Args:
            question: 사용자 질문
            conversation_history: 대화 이력 [{"role": "user/assistant", "content": "..."}]
            retry_on_error: 에러 시 재시도 여부
            is_refinement: 참조 표현 감지됨 (이전 WHERE 조건 유지 필요)

        Returns:
            {
                "success": bool,
                "data": [...],
                "rowCount": int,
                "sql": str,
                "error": str (optional),
                "executionTimeMs": float
            }
        """
        # 대화 컨텍스트 구성 (is_refinement 전달)
        conversation_context = self._build_conversation_context(
            conversation_history,
            is_refinement=is_refinement
        )

        # SQL 생성 (차트 타입 + 인사이트 템플릿 + summaryStats 템플릿 포함)
        raw_sql, validation_result, llm_chart_type, insight_template, summary_stats_template = await self.generate_sql(question, conversation_context)

        if not validation_result.is_valid:
            return {
                "success": False,
                "data": [],
                "rowCount": 0,
                "sql": raw_sql,
                "error": f"SQL validation failed: {', '.join(validation_result.issues)}",
                "executionTimeMs": 0,
                "llmChartType": llm_chart_type,  # 검증 실패 시에도 차트 타입 포함
                "insightTemplate": insight_template,  # 검증 실패 시에도 인사이트 템플릿 포함
                "summaryStatsTemplate": summary_stats_template  # 검증 실패 시에도 summaryStats 템플릿 포함
            }

        # SQL 실행
        result = self.execute_sql(validation_result.sanitized_sql)

        if not result.success and retry_on_error:
            # 에러 시 재시도 (에러 메시지를 컨텍스트에 포함)
            logger.info(f"Retrying SQL generation with error context: {result.error}")

            retry_context = ConversationContext(
                previous_question=question,
                previous_sql=raw_sql,
                previous_result_summary=f"ERROR: {result.error}"
            )

            raw_sql, validation_result, llm_chart_type, insight_template, summary_stats_template = await self.generate_sql(
                f"{question}\n\n(이전 SQL 오류: {result.error}. 다른 방법으로 시도해주세요.)",
                retry_context
            )

            if validation_result.is_valid:
                result = self.execute_sql(validation_result.sanitized_sql)

        # 집계 컨텍스트 생성 (집계 쿼리인 경우에만)
        aggregation_context = None
        previous_row_count = self._get_previous_row_count(conversation_history)

        agg_ctx = build_aggregation_context(
            sql=result.sql,
            is_refinement=is_refinement,
            previous_row_count=previous_row_count
        )

        if agg_ctx:
            aggregation_context = aggregation_context_to_dict(agg_ctx)
            logger.info(f"Aggregation query detected: {aggregation_context}")

        return {
            "success": result.success,
            "data": result.data,
            "rowCount": result.row_count,
            "totalCount": result.total_count,       # 전체 건수
            "isTruncated": result.is_truncated,     # max_rows 초과 여부
            "sql": result.sql,
            "error": result.error,
            "executionTimeMs": result.execution_time_ms,
            "isAggregation": agg_ctx is not None,   # 집계 쿼리 여부
            "aggregationContext": aggregation_context,  # 집계 컨텍스트 (None이면 일반 쿼리)
            "llmChartType": llm_chart_type,         # LLM 추천 차트 타입
            "insightTemplate": insight_template,    # LLM 생성 인사이트 템플릿
            "summaryStatsTemplate": summary_stats_template  # LLM 생성 summaryStats 템플릿
        }

    def _build_conversation_context(
        self,
        conversation_history: Optional[List[Dict[str, Any]]],
        is_refinement: bool = False
    ) -> Optional[ConversationContext]:
        """
        대화 이력에서 컨텍스트 추출

        대화 기반 맥락 처리 방식:
        - 전체 대화 이력을 저장하여 자연스러운 대화 흐름 구성
        - rowCount 정보를 포함하여 LLM이 맥락을 이해하도록 함

        Phase 2 개선:
        - is_refinement 조건 제거: 항상 조건을 누적하여 LLM에게 전달
        - whereConditions 필드 우선 사용 (Phase 1에서 명시적 저장된 값)
        - 폴백으로 SQL에서 동적 추출

        Args:
            conversation_history: 대화 이력 [{role, content, sql?, rowCount?, whereConditions?}, ...]
            is_refinement: True면 이전 WHERE 조건 누적 필요 (참조 표현 감지됨)

        Returns:
            ConversationContext 또는 None
        """
        if not conversation_history or len(conversation_history) < 2:
            return None

        # 마지막 assistant 메시지에서 SQL 추출
        previous_sql = None
        previous_question = None
        previous_row_count = None

        for msg in reversed(conversation_history):
            if msg.get("role") == "assistant" and "sql" in msg:
                if previous_sql is None:
                    previous_sql = msg.get("sql")
                    previous_row_count = msg.get("rowCount")
            if msg.get("role") == "user" and not previous_question:
                previous_question = msg.get("content")
                break

        if not previous_sql or not previous_question:
            return None

        # Phase 2: 항상 WHERE 조건 누적 (is_refinement 조건 제거)
        # 4단계+ 체이닝에서 조건 유실 방지를 위해 항상 누적된 조건을 LLM에 전달
        accumulated_conditions = []

        # 전체 대화 이력에서 WHERE 조건 누적
        for msg in conversation_history:
            if msg.get("role") == "assistant":
                # Phase 1: whereConditions 필드 우선 사용 (명시적 저장된 값)
                if "whereConditions" in msg and msg["whereConditions"]:
                    conditions = msg["whereConditions"]
                    logger.debug(f"Using pre-extracted whereConditions: {conditions}")
                # 폴백: SQL에서 동적 추출
                elif "sql" in msg:
                    sql = msg.get("sql", "")
                    conditions = extract_where_conditions(sql)
                    logger.debug(f"Extracted conditions from SQL: {conditions}")
                else:
                    conditions = []

                if conditions:
                    # 기존 조건과 병합 (동일 필드는 새 조건으로 대체)
                    accumulated_conditions = merge_where_conditions(
                        accumulated_conditions,
                        conditions
                    )

        if accumulated_conditions:
            logger.info(f"Accumulated WHERE conditions ({len(accumulated_conditions)} conditions): {accumulated_conditions}")

        # 결과 요약 생성 (rowCount 포함)
        result_summary = None
        if previous_row_count is not None:
            result_summary = f"{previous_row_count}건 조회됨"

        return ConversationContext(
            previous_question=previous_question,
            previous_sql=previous_sql,
            previous_result_summary=result_summary,
            accumulated_where_conditions=accumulated_conditions,
            is_refinement=is_refinement,
            conversation_history=conversation_history  # 전체 대화 이력 저장
        )

    def _get_previous_row_count(
        self,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> Optional[int]:
        """
        이전 쿼리 결과의 행 수 추출

        Args:
            conversation_history: 대화 이력

        Returns:
            이전 쿼리 결과 행 수 또는 None
        """
        if not conversation_history:
            return None

        # 역순으로 탐색하여 가장 최근 assistant 메시지의 결과 건수 찾기
        for msg in reversed(conversation_history):
            if msg.get("role") == "assistant":
                # rowCount 또는 totalCount 필드 확인
                row_count = msg.get("rowCount") or msg.get("totalCount")
                if row_count is not None:
                    return row_count

        return None

    def _summarize_result(self, data: List[Dict[str, Any]], max_rows: int = 3) -> str:
        """결과 요약 생성"""
        if not data:
            return "결과 없음"

        summary_parts = [f"총 {len(data)}건"]

        if len(data) <= max_rows:
            sample = data
        else:
            sample = data[:max_rows]

        # 첫 번째 행의 키들
        if sample:
            keys = list(sample[0].keys())[:5]  # 최대 5개 컬럼
            summary_parts.append(f"컬럼: {', '.join(keys)}")

        return "; ".join(summary_parts)


# 싱글톤 인스턴스
_service_instance: Optional[TextToSqlService] = None


def get_text_to_sql_service() -> TextToSqlService:
    """TextToSqlService 싱글톤 인스턴스 반환"""
    global _service_instance
    if _service_instance is None:
        _service_instance = TextToSqlService()
    return _service_instance
