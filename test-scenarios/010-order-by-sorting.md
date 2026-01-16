# Test Scenario 010: 정렬 (ORDER BY)

**작성일:** 2026-01-16
**기능:** "금액 높은 순", "최신순", "내림차순" 등 정렬 조건 인식
**상태:** ⏳ 테스트 대기

---

## 1. 테스트 목적

자연어로 표현된 정렬 요구사항이 SQL ORDER BY 절로 올바르게 변환되는지 검증합니다.

### 배경
- 실무 쿼리: "금액이 큰 순서대로", "최신 순", "오래된 것부터"
- SQL: `ORDER BY amount DESC`, `ORDER BY created_at DESC`
- 집계 쿼리와 결합 시: `ORDER BY SUM(amount) DESC`

---

## 2. 사전 조건

- [x] AI Orchestrator: Docker container 실행 중
- [x] Core API: http://localhost:8080 실행 중
- [x] PostgreSQL: payments 테이블 데이터 존재

---

## 3. 테스트 시나리오

### TC-010-1: 금액 내림차순

**입력:**
```
"최근 1개월 결제 내역을 금액 높은 순으로 보여줘"
```

**기대 결과:**
- SQL: `ORDER BY amount DESC`
- 결과: 첫 번째 row가 가장 큰 금액

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 결제 내역을 금액 높은 순으로 보여줘"}' | jq '{
    sql: .queryPlan.sql,
    firstAmount: .queryResult.data[0].amount,
    secondAmount: .queryResult.data[1].amount
  }'
```

---

### TC-010-2: 금액 오름차순

**입력:**
```
"최근 1개월 결제 내역을 금액 낮은 순으로"
```

**기대 결과:**
- SQL: `ORDER BY amount ASC`
- 결과: 첫 번째 row가 가장 작은 금액

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 결제 내역을 금액 낮은 순으로"}' | jq '{
    sql: .queryPlan.sql,
    firstAmount: .queryResult.data[0].amount,
    secondAmount: .queryResult.data[1].amount
  }'
```

---

### TC-010-3: 최신순 (날짜 내림차순)

**입력:**
```
"최근 1개월 결제 내역 최신순"
```

**기대 결과:**
- SQL: `ORDER BY created_at DESC`
- 결과: 첫 번째 row가 가장 최근 날짜

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 결제 내역 최신순"}' | jq '{
    sql: .queryPlan.sql,
    firstDate: .queryResult.data[0].created_at,
    secondDate: .queryResult.data[1].created_at
  }'
```

---

### TC-010-4: 오래된 순 (날짜 오름차순)

**입력:**
```
"최근 1개월 결제 내역을 오래된 것부터 보여줘"
```

**기대 결과:**
- SQL: `ORDER BY created_at ASC`
- 결과: 첫 번째 row가 가장 오래된 날짜

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 결제 내역을 오래된 것부터 보여줘"}' | jq '{
    sql: .queryPlan.sql,
    firstDate: .queryResult.data[0].created_at
  }'
```

---

### TC-010-5: 집계 결과 정렬

**입력:**
```
"가맹점별 결제 금액 합계를 큰 순서대로"
```

**기대 결과:**
- SQL: `GROUP BY merchant_id`
- SQL: `ORDER BY SUM(amount) DESC`
- 결과: 첫 번째 row가 가장 큰 합계

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "가맹점별 결제 금액 합계를 큰 순서대로"}' | jq '{
    sql: .queryPlan.sql,
    firstRow: .queryResult.data[0],
    secondRow: .queryResult.data[1]
  }'
```

---

### TC-010-6: 다중 정렬 기준

**입력:**
```
"결제 내역을 상태별로 정렬하고, 같은 상태 내에서는 금액 높은 순으로"
```

**기대 결과:**
- SQL: `ORDER BY status, amount DESC`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "결제 내역을 상태별로 정렬하고, 같은 상태 내에서는 금액 높은 순으로"}' | jq '{
    sql: .queryPlan.sql,
    firstRow: .queryResult.data[0]
  }'
```

---

## 4. API 테스트

```bash
# 전체 테스트 실행
bash test-scenarios/scripts/run-scenario-010.sh
```

---

## 5. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `text_to_sql_service.py` | `generate_query_plan()` | ORDER BY 절 생성 |
| `sql_validator.py` | `validate_order_by()` | 정렬 조건 검증 |

---

## 6. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-16 | tester | ⏳ 대기 | 시나리오 작성 완료 |

---

## 7. 검증 포인트

| 시나리오 | 검증 필드 | 기대값 |
|---------|----------|--------|
| TC-010-1 | `.queryPlan.sql` | `ORDER BY amount DESC` |
| TC-010-2 | `.queryPlan.sql` | `ORDER BY amount ASC` |
| TC-010-3 | `.queryPlan.sql` | `ORDER BY created_at DESC` |
| TC-010-4 | `.queryPlan.sql` | `ORDER BY created_at ASC` |
| TC-010-5 | `.queryPlan.sql` | `ORDER BY SUM(` + `DESC` |
| TC-010-6 | `.queryPlan.sql` | `ORDER BY status, amount DESC` |
