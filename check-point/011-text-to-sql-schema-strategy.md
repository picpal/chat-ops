# 011. Text-to-SQL 스키마 제공 전략

## 날짜
2026-01-14

## 관련
- [010-text-to-sql-migration.md](./010-text-to-sql-migration.md)

---

## 현재 구현 방식

### 테이블 스키마: 하드코딩

**파일**: `services/ai-orchestrator/app/services/text_to_sql.py` (lines 25-178)

```python
SCHEMA_PROMPT = """
## PostgreSQL Database Schema

### payments (결제 트랜잭션)
| Column | Type | Description |
|--------|------|-------------|
| payment_key | VARCHAR(50) PK | 결제 고유 키 |
...
"""
```

- 10개 테이블 전체 명세가 상수로 프롬프트에 포함
- 약 4KB 크기

### RAG: 비즈니스 로직/FAQ 문서용

```python
async def _get_rag_context(self, question: str) -> str:
    rag_service = get_rag_service()
    results = await rag_service.search(question, top_k=3)
```

- 테이블 스키마가 아닌 비즈니스 규칙, FAQ 검색용
- entity, business_logic, error_code, faq 문서 26개

---

## 검토: RAG로 스키마 조회하면?

### 문제점 1: 임베딩 유사도의 한계

```
사용자 질문: "이번 달 매출 알려줘"

RAG 검색 결과:
- payments 테이블 ✅ (매출 = 결제)
- settlements 테이블 ❓ (정산에도 매출 정보)
- balance_transactions ❓ (잔액 거래도 관련?)
```

"매출"이 여러 테이블과 연관 → 정확한 테이블 선택 어려움

### 문제점 2: JOIN 관계 파악 불가

```
질문: "가맹점별 환불율"

필요한 테이블:
- merchants (가맹점)
- payments (결제 - 분모)
- refunds (환불 - 분자)
```

RAG는 "환불"과 유사한 `refunds`는 찾지만, JOIN에 필요한 `merchants`, `payments` 누락 가능

### 문제점 3: 누락 시 치명적

```
RAG가 payments만 반환 → merchants 누락
→ LLM이 merchant_id로 JOIN 시도
→ merchants 스키마 모름 → 잘못된 SQL 생성
```

---

## 대안 방식 비교

### Option 1: 2단계 LLM 호출

```
1단계: "이 질문에 필요한 테이블은?" → LLM이 테이블명 반환
2단계: 해당 테이블 스키마만 포함하여 SQL 생성
```

| 장점 | 단점 |
|------|------|
| 정확도 높음 | API 호출 2회 |
| 동적 테이블 선택 | 지연 시간 증가 |
| | 비용 증가 |

### Option 2: 테이블 그룹화

```python
TABLE_GROUPS = {
    "결제": ["payments", "merchants", "pg_customers"],
    "환불": ["refunds", "payments", "merchants"],
    "정산": ["settlements", "settlement_details", "merchants"],
}
```

| 장점 | 단점 |
|------|------|
| 빠름 | 수동 관리 필요 |
| JOIN 관계 보장 | 키워드 유지보수 |
| 구현 단순 | |

### Option 3: 전체 스키마 요약 + 상세 RAG

```
프롬프트 구성:
1. 전체 테이블 목록 (이름 + 한 줄 설명만) - ~500B
2. RAG로 관련 테이블의 상세 컬럼 정보
```

| 장점 | 단점 |
|------|------|
| 전체 그림 유지 | 구현 복잡 |
| 상세 정보 최적화 | 2단계 처리 |

### Option 4: 전체 스키마 하드코딩 (현재)

```python
SCHEMA_PROMPT = "..." # 전체 포함
```

| 장점 | 단점 |
|------|------|
| 가장 안정적 | 토큰 낭비 (~4KB) |
| JOIN 관계 보장 | 스키마 변경 시 코드 수정 |
| 구현 단순 | 테이블 많으면 한계 |

---

## 결론: 규모별 추천 전략

| 테이블 수 | 추천 방식 | 이유 |
|----------|----------|------|
| ~20개 | **전체 스키마 하드코딩** | 안정성, 단순함 |
| 20~50개 | 테이블 그룹화 + 키워드 매칭 | 토큰 최적화 |
| 50개 이상 | 2단계 LLM 또는 전문 솔루션 | 복잡도 관리 |

### 현재 프로젝트 결정

- **테이블 수**: 10개 (고정적)
- **선택**: 전체 스키마 하드코딩 유지
- **RAG 용도**: 비즈니스 규칙/FAQ 문서 (스키마 아님)

### 향후 확장 시

테이블이 50개 이상으로 증가하면:
1. 테이블 그룹화 방식으로 전환
2. 또는 전문 Text-to-SQL 솔루션 검토 (Vanna, SQLCoder 등)

---

## 참고: 전문 Text-to-SQL 솔루션

| 솔루션 | 특징 |
|--------|------|
| [Vanna](https://vanna.ai) | RAG 기반, 자동 스키마 학습 |
| [SQLCoder](https://github.com/defog-ai/sqlcoder) | 오픈소스 SQL 특화 모델 |
| [DIN-SQL](https://github.com/MohammadrezaBanaworte/DIN-SQL) | 분해 기반 접근 |

대규모 스키마에서는 범용 LLM보다 SQL 특화 모델이 더 정확할 수 있음.
