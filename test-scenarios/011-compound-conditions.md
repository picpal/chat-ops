# Test Scenario 011: 복합 조건

**작성일:** 2026-01-16
**기능:** 여러 WHERE 조건을 AND/OR로 결합한 복합 쿼리
**상태:** ⏳ 테스트 대기

---

## 1. 테스트 목적

"DONE이면서 카드결제", "mer_001 또는 mer_002" 등 복합 조건이 SQL WHERE 절에 올바르게 표현되는지 검증합니다.

### 배경
- 실무 쿼리: "상태가 DONE이면서 금액이 10만원 이상"
- SQL: `WHERE status = 'DONE' AND amount >= 100000`
- AND/OR 연산자 조합 및 괄호 처리

---

## 2. 사전 조건

- [x] AI Orchestrator: Docker container 실행 중
- [x] Core API: http://localhost:8080 실행 중
- [x] PostgreSQL: payments 테이블 데이터 존재

---

## 3. 테스트 시나리오

### TC-011-1: AND 조건 (상태 + 결제수단)

**입력:**
```
"DONE 상태이면서 카드 결제인 건"
```

**기대 결과:**
- SQL: `WHERE status = 'DONE' AND payment_method = 'CARD'`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "DONE 상태이면서 카드 결제인 건"}' | jq '{
    sql: .queryPlan.sql,
    rowCount: (.queryResult.data | length)
  }'
```

---

### TC-011-2: AND 조건 (상태 + 금액 범위)

**입력:**
```
"최근 1개월 DONE 상태이면서 금액이 10만원 이상인 결제"
```

**기대 결과:**
- SQL: `WHERE status = 'DONE' AND amount >= 100000`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 DONE 상태이면서 금액이 10만원 이상인 결제"}' | jq '{
    sql: .queryPlan.sql,
    rowCount: (.queryResult.data | length),
    minAmount: ([.queryResult.data[].amount] | min)
  }'
```

---

### TC-011-3: OR 조건 (가맹점)

**입력:**
```
"mer_001 또는 mer_002 가맹점의 결제 내역"
```

**기대 결과:**
- SQL: `WHERE merchant_id IN ('mer_001', 'mer_002')`
- 또는: `WHERE merchant_id = 'mer_001' OR merchant_id = 'mer_002'`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "mer_001 또는 mer_002 가맹점의 결제 내역"}' | jq '{
    sql: .queryPlan.sql,
    merchants: [.queryResult.data[].merchant_id] | unique
  }'
```

---

### TC-011-4: OR 조건 (상태)

**입력:**
```
"DONE 또는 CANCELED 상태인 결제 건수"
```

**기대 결과:**
- SQL: `WHERE status IN ('DONE', 'CANCELED')`
- 또는: `WHERE status = 'DONE' OR status = 'CANCELED'`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "DONE 또는 CANCELED 상태인 결제 건수"}' | jq '{
    sql: .queryPlan.sql,
    count: .queryResult.data[0]
  }'
```

---

### TC-011-5: 복합 조건 (AND + OR)

**입력:**
```
"카드 결제이면서 (DONE 또는 PARTIAL_CANCELED) 상태인 건"
```

**기대 결과:**
- SQL: `WHERE payment_method = 'CARD' AND status IN ('DONE', 'PARTIAL_CANCELED')`
- 또는: `WHERE payment_method = 'CARD' AND (status = 'DONE' OR status = 'PARTIAL_CANCELED')`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "카드 결제이면서 (DONE 또는 PARTIAL_CANCELED) 상태인 건"}' | jq '{
    sql: .queryPlan.sql,
    rowCount: (.queryResult.data | length)
  }'
```

---

### TC-011-6: 금액 범위 (BETWEEN)

**입력:**
```
"금액이 5만원 이상 10만원 이하인 결제"
```

**기대 결과:**
- SQL: `WHERE amount BETWEEN 50000 AND 100000`
- 또는: `WHERE amount >= 50000 AND amount <= 100000`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "금액이 5만원 이상 10만원 이하인 결제"}' | jq '{
    sql: .queryPlan.sql,
    rowCount: (.queryResult.data | length),
    minAmount: ([.queryResult.data[].amount] | min),
    maxAmount: ([.queryResult.data[].amount] | max)
  }'
```

---

### TC-011-7: NOT 조건

**입력:**
```
"DONE이 아닌 결제 건수"
```

**기대 결과:**
- SQL: `WHERE status != 'DONE'`
- 또는: `WHERE status <> 'DONE'`
- 또는: `WHERE NOT status = 'DONE'`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "DONE이 아닌 결제 건수"}' | jq '{
    sql: .queryPlan.sql,
    count: .queryResult.data[0]
  }'
```

---

## 4. API 테스트

```bash
# 전체 테스트 실행
bash test-scenarios/scripts/run-scenario-011.sh
```

---

## 5. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `text_to_sql_service.py` | `generate_query_plan()` | 복합 WHERE 조건 생성 |
| `sql_validator.py` | `validate_where_clause()` | WHERE 조건 검증 |

---

## 6. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-16 | tester | ⏳ 대기 | 시나리오 작성 완료 |

---

## 7. 검증 포인트

| 시나리오 | 검증 필드 | 기대값 |
|---------|----------|--------|
| TC-011-1 | `.queryPlan.sql` | `status = 'DONE' AND payment_method = 'CARD'` |
| TC-011-2 | `.queryPlan.sql` | `amount >= 100000` |
| TC-011-3 | `.queryPlan.sql` | `IN ('mer_001', 'mer_002')` 또는 OR |
| TC-011-4 | `.queryPlan.sql` | `IN ('DONE', 'CANCELED')` 또는 OR |
| TC-011-5 | `.queryPlan.sql` | `AND (status ... OR ...)` |
| TC-011-6 | `.queryPlan.sql` | `BETWEEN` 또는 `>= AND <=` |
| TC-011-7 | `.queryPlan.sql` | `!= 'DONE'` 또는 `<>` |
