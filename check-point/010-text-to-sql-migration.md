# 010. QueryPlan에서 Text-to-SQL 방식으로 전환

## 날짜
2026-01-14

## 브랜치
`feature/text-to-sql`

---

## 배경: QueryPlan 방식의 한계

### 1. LLM이 추상화 스키마를 정확히 생성하지 못함

**문제 (checkpoint 003 참조)**:
- LLM이 operator에 `>=`, `<` 같은 기호를 사용 → Pydantic 검증 오류
- 정규화 함수(`normalize_operator`)로 땜질했지만, 근본적 해결 아님

```python
# 추가해야 했던 정규화 로직
OPERATOR_ALIASES = {
    ">=": "gte", ">": "gt", "<=": "lte", "<": "lt",
    "=": "eq", "==": "eq", "!=": "ne", ...
}
```

**근본 원인**: QueryPlan은 자체 정의한 스키마이므로 LLM이 학습하지 않은 형식

### 2. Clarification 판단의 어려움

**문제 (checkpoint 006 참조)**:
- 다중 결과 상황에서 어떤 결과를 참조할지 판단이 부정확
- Few-shot, Chain of Thought, 체크리스트 등 프롬프트 엔지니어링으로 해결 시도
- **결론**: 프롬프트만으로는 LLM 판단을 100% 제어 불가

```
기대: "합산해줘" → needs_result_clarification: true
실제: LLM이 기본값(false)으로 응답하는 경향
```

### 3. 2단계 LLM 호출로 복잡도/비용 증가

**해결책 (checkpoint 007 참조)**:
- 1단계: gpt-4o-mini로 QueryPlan 생성
- 2단계: gpt-4o로 clarification 재판단

**문제점**:
- API 호출 2회 → 비용 증가, 지연시간 증가
- 로직 복잡도 상승
- 여전히 완벽하지 않음

### 4. Core API 의존성

QueryPlan 방식의 아키텍처:
```
AI → QueryPlan(JSON) → Core API → SQL 변환 → DB
```

- Core API가 QueryPlan을 SQL로 변환해야 함
- 새로운 쿼리 패턴마다 Core API 수정 필요
- AI와 Core API 간 스키마 동기화 부담

---

## 전환 동기: Text-to-SQL의 장점

### 1. LLM이 SQL을 잘 알고 있음

- SQL은 수십 년간 사용된 표준 언어
- LLM 학습 데이터에 SQL 예제가 풍부
- 별도 스키마 학습 없이 바로 생성 가능

### 2. 단순한 아키텍처

변경 전:
```
AI → QueryPlan(JSON) → Core API → SQL Builder → DB
```

변경 후:
```
AI → SQL → Read-only DB (직접 실행)
```

- 중간 변환 계층 제거
- Core API 의존성 감소
- 새로운 쿼리 패턴 추가 용이

### 3. Clarification 로직 단순화

- LLM이 자연어를 바로 SQL로 변환
- 모호한 요청 시 LLM이 직접 clarification 질문 생성
- 별도의 2단계 판단 로직 불필요

---

## 보안 대책 (3중 보호)

### 1. PostgreSQL Read-Only 사용자

**파일**: `V14__create_readonly_user.sql`

```sql
CREATE USER chatops_readonly WITH PASSWORD '...';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatops_readonly;
-- INSERT, UPDATE, DELETE 권한 없음
```

### 2. SQL Validator

**파일**: `sql_validator.py`

검증 항목:
- DML/DDL 차단 (INSERT, UPDATE, DELETE, DROP, ALTER, ...)
- 위험 함수 차단 (pg_read_file, dblink, ...)
- SQL Injection 패턴 차단
- LIMIT 강제

```python
# 37개 유닛 테스트로 검증
test_sql_validator.py
```

### 3. 실행 제한

- `SQL_QUERY_TIMEOUT_SECONDS`: 쿼리 타임아웃
- `SQL_MAX_ROWS`: 최대 반환 행 수
- Read-only 트랜잭션 강제

---

## 롤백 방법

Text-to-SQL 문제 발생 시:
```bash
# .env 설정
SQL_ENABLE_TEXT_TO_SQL=false
```

QueryPlan 방식으로 즉시 롤백 가능

---

## 비교 요약

| 항목 | QueryPlan 방식 | Text-to-SQL 방식 |
|------|---------------|-----------------|
| LLM 생성 대상 | 자체 정의 JSON 스키마 | 표준 SQL |
| LLM 정확도 | 낮음 (스키마 학습 필요) | 높음 (사전 학습됨) |
| API 호출 횟수 | 2회 (2단계 판단) | 1회 |
| 아키텍처 복잡도 | 높음 (AI→Core API→DB) | 낮음 (AI→DB) |
| 보안 | Core API에서 검증 | Read-only + Validator |
| 확장성 | Core API 수정 필요 | SQL만 변경하면 됨 |

---

## 관련 파일

### 신규 생성
- `services/ai-orchestrator/app/services/sql_validator.py` - SQL 보안 검증
- `services/ai-orchestrator/app/services/text_to_sql.py` - SQL 생성/실행
- `services/ai-orchestrator/tests/test_sql_validator.py` - 37개 테스트
- `services/core-api/src/main/resources/db/migration/V14__create_readonly_user.sql`

### 수정
- `services/ai-orchestrator/app/api/v1/chat.py` - Text-to-SQL 모드 분기
- `infra/docker/.env.example` - 환경 변수 추가
- `infra/docker/docker-compose.yml` - 환경 변수 전달

---

## 이전 체크포인트 참조

- [003-operator-validation-error.md](./003-operator-validation-error.md) - 연산자 검증 오류
- [006-clarification-prompt-engineering-challenge.md](./006-clarification-prompt-engineering-challenge.md) - 프롬프트 엔지니어링 한계
- [007-two-stage-llm-judgment-success.md](./007-two-stage-llm-judgment-success.md) - 2단계 LLM 판단
