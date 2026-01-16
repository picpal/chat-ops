# Test Scenario 007: 복잡한 집계 함수

**작성일:** 2026-01-16
**기능:** AVG, MAX, MIN 등 다양한 집계 함수 테스트
**상태:** ⏳ 테스트 대기

---

## 1. 테스트 목적

SUM, COUNT 외에 AVG(평균), MAX(최대), MIN(최소) 등 복잡한 집계 함수가 올바르게 생성되고 실행되는지 검증합니다.

### 배경
- 기존 시나리오는 SUM, COUNT 위주
- 실무에서는 평균 결제금액, 최대/최소 금액 등의 통계가 자주 요구됨
- SQL Validator가 다양한 집계 함수를 허용하는지 확인

---

## 2. 사전 조건

- [x] AI Orchestrator: Docker container 실행 중
- [x] Core API: http://localhost:8080 실행 중
- [x] PostgreSQL: payments 테이블 데이터 존재

---

## 3. 테스트 시나리오

### TC-007-1: 평균(AVG) 집계

**입력:**
```
"최근 1개월 평균 결제금액을 보여줘"
```

**기대 결과:**
- SQL에 `AVG(amount)` 포함
- 결과 데이터에 평균값 존재
- renderSpec.type: "table" 또는 "metric"

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 평균 결제금액을 보여줘"}' | jq '{
    sql: .queryPlan.sql,
    avg_value: .queryResult.data[0],
    renderType: .renderSpec.type
  }'
```

---

### TC-007-2: 최대값(MAX) 집계

**입력:**
```
"지난달 최대 결제금액은?"
```

**기대 결과:**
- SQL에 `MAX(amount)` 포함
- 결과 데이터에 최대값 존재

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "지난달 최대 결제금액은?"}' | jq '{
    sql: .queryPlan.sql,
    max_value: .queryResult.data[0]
  }'
```

---

### TC-007-3: 최소값(MIN) 집계

**입력:**
```
"최근 3개월 최소 결제금액"
```

**기대 결과:**
- SQL에 `MIN(amount)` 포함
- 결과 데이터에 최소값 존재

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 3개월 최소 결제금액"}' | jq '{
    sql: .queryPlan.sql,
    min_value: .queryResult.data[0]
  }'
```

---

### TC-007-4: 복합 집계 (AVG, MAX, MIN, COUNT, SUM)

**입력:**
```
"최근 1개월 결제 통계: 건수, 합계, 평균, 최대, 최소"
```

**기대 결과:**
- SQL에 5개 집계 함수 모두 포함
  - COUNT(*)
  - SUM(amount)
  - AVG(amount)
  - MAX(amount)
  - MIN(amount)
- 결과 데이터에 5개 값 존재

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 결제 통계: 건수, 합계, 평균, 최대, 최소"}' | jq '{
    sql: .queryPlan.sql,
    stats: .queryResult.data[0]
  }'
```

---

### TC-007-5: 그룹별 평균

**입력:**
```
"가맹점별 평균 결제금액 (최근 1개월)"
```

**기대 결과:**
- SQL에 `GROUP BY merchant_id` 포함
- SQL에 `AVG(amount)` 포함
- 결과: 여러 가맹점의 평균값 목록

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "가맹점별 평균 결제금액 (최근 1개월)"}' | jq '{
    sql: .queryPlan.sql,
    rowCount: (.queryResult.data | length),
    firstRow: .queryResult.data[0]
  }'
```

---

## 4. API 테스트

```bash
# 전체 테스트 실행
bash test-scenarios/scripts/run-scenario-007.sh
```

---

## 5. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `text_to_sql_service.py` | `generate_query_plan()` | 집계 함수 SQL 생성 |
| `sql_validator.py` | `validate_aggregate_functions()` | 집계 함수 검증 |

---

## 6. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-16 | tester | ⏳ 대기 | 시나리오 작성 완료 |

---

## 7. 검증 포인트

| 시나리오 | 검증 필드 | 기대값 |
|---------|----------|--------|
| TC-007-1 | `.queryPlan.sql` | `AVG(` 포함 |
| TC-007-2 | `.queryPlan.sql` | `MAX(` 포함 |
| TC-007-3 | `.queryPlan.sql` | `MIN(` 포함 |
| TC-007-4 | `.queryPlan.sql` | 5개 집계 함수 모두 포함 |
| TC-007-5 | `.queryPlan.sql` | `GROUP BY` + `AVG(` |
