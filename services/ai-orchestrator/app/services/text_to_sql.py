"""
Text-to-SQL Service: 자연어를 SQL로 변환하고 실행
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from app.services.sql_validator import SqlValidator, ValidationResult, get_sql_validator
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)


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
| status | VARCHAR(30) | 상태: READY, IN_PROGRESS, DONE, CANCELED, PARTIAL_CANCELED, FAILED, EXPIRED |
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

### JOIN 관계
- payments.merchant_id -> merchants.merchant_id
- payments.payment_key -> refunds.payment_key
- settlements.merchant_id -> merchants.merchant_id
- settlement_details.settlement_id -> settlements.settlement_id
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
            results = await rag_service.search(question, top_k=self._rag_top_k)

            if not results:
                return ""

            context_parts = []
            for doc in results:
                context_parts.append(f"[{doc['type']}] {doc['title']}: {doc['content'][:500]}")

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
        """SQL 생성 프롬프트 구성"""
        prompt_parts = []

        # 시스템 지시
        prompt_parts.append("""당신은 PostgreSQL SQL 전문가입니다.
사용자의 자연어 질문을 분석하여 정확한 SELECT 쿼리를 생성합니다.

규칙:
1. SELECT 문만 생성 (INSERT, UPDATE, DELETE 금지)
2. 테이블/컬럼명은 snake_case 사용 (예: payment_key, merchant_id)
3. 문자열 비교 시 정확한 값 사용 (예: status = 'DONE')
4. 날짜 필터 시 적절한 범위 지정
5. LIMIT 규칙:
   - 사용자가 명시적으로 건수를 지정한 경우에만 LIMIT 추가 (예: "10건만", "상위 100개")
   - 건수 지정이 없으면 LIMIT 없이 생성 (시스템이 자동으로 처리함)
6. 금액 집계 시 SUM, COUNT, AVG 등 적절히 활용

응답 형식:
- SQL 쿼리만 반환 (코드 블록, 설명 없이)
- 세미콜론으로 끝내기
""")

        # 스키마 정보
        prompt_parts.append(SCHEMA_PROMPT)

        # RAG 컨텍스트
        if rag_context:
            prompt_parts.append(f"\n## 참고 문서\n{rag_context}")

        # 연속 대화 컨텍스트
        if conversation_context and conversation_context.previous_sql:
            prompt_parts.append(f"""
## 이전 대화 컨텍스트
이전 질문: {conversation_context.previous_question}
이전 SQL:
```sql
{conversation_context.previous_sql}
```
이전 결과 요약: {conversation_context.previous_result_summary or '결과 있음'}

위 컨텍스트를 참고하여, 현재 질문이 이전 쿼리의 조건 변경/추가를 요청하는 경우 이전 SQL을 수정하세요.
""")

        # 현재 질문
        prompt_parts.append(f"\n## 현재 질문\n{question}")

        return "\n".join(prompt_parts)

    async def generate_sql(
        self,
        question: str,
        conversation_context: Optional[ConversationContext] = None
    ) -> Tuple[str, ValidationResult]:
        """
        자연어를 SQL로 변환

        Args:
            question: 사용자 질문
            conversation_context: 연속 대화 컨텍스트

        Returns:
            (생성된 SQL, 검증 결과) 튜플
        """
        # RAG 컨텍스트 조회
        rag_context = await self._get_rag_context(question)

        # 프롬프트 구성
        prompt = self._build_prompt(question, conversation_context, rag_context)

        # LLM 호출
        llm = self._get_llm()
        response = await llm.ainvoke(prompt)

        # SQL 추출 (코드 블록 제거)
        raw_sql = response.content.strip()
        if raw_sql.startswith("```"):
            # ```sql ... ``` 형식 처리
            lines = raw_sql.split("\n")
            sql_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block or not line.startswith("```"):
                    sql_lines.append(line)
            raw_sql = "\n".join(sql_lines).strip()

        logger.info(f"Generated SQL: {raw_sql[:200]}...")

        # SQL 검증
        validation_result = self.validator.validate(raw_sql)

        return raw_sql, validation_result

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
        retry_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        자연어 질문 처리 (생성 + 검증 + 실행)

        Args:
            question: 사용자 질문
            conversation_history: 대화 이력 [{"role": "user/assistant", "content": "..."}]
            retry_on_error: 에러 시 재시도 여부

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
        # 대화 컨텍스트 구성
        conversation_context = self._build_conversation_context(conversation_history)

        # SQL 생성
        raw_sql, validation_result = await self.generate_sql(question, conversation_context)

        if not validation_result.is_valid:
            return {
                "success": False,
                "data": [],
                "rowCount": 0,
                "sql": raw_sql,
                "error": f"SQL validation failed: {', '.join(validation_result.issues)}",
                "executionTimeMs": 0
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

            raw_sql, validation_result = await self.generate_sql(
                f"{question}\n\n(이전 SQL 오류: {result.error}. 다른 방법으로 시도해주세요.)",
                retry_context
            )

            if validation_result.is_valid:
                result = self.execute_sql(validation_result.sanitized_sql)

        return {
            "success": result.success,
            "data": result.data,
            "rowCount": result.row_count,
            "totalCount": result.total_count,       # 전체 건수
            "isTruncated": result.is_truncated,     # max_rows 초과 여부
            "sql": result.sql,
            "error": result.error,
            "executionTimeMs": result.execution_time_ms
        }

    def _build_conversation_context(
        self,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> Optional[ConversationContext]:
        """대화 이력에서 컨텍스트 추출"""
        if not conversation_history or len(conversation_history) < 2:
            return None

        # 마지막 assistant 메시지에서 SQL 추출
        previous_sql = None
        previous_question = None

        for msg in reversed(conversation_history):
            if msg.get("role") == "assistant" and "sql" in msg:
                previous_sql = msg.get("sql")
            if msg.get("role") == "user" and not previous_question:
                previous_question = msg.get("content")
                break

        if not previous_sql or not previous_question:
            return None

        return ConversationContext(
            previous_question=previous_question,
            previous_sql=previous_sql,
            previous_result_summary=None
        )

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
