# Test Scenario 008: 다중 GROUP BY

**작성일:** 2026-01-16
**기능:** 2개 이상의 컬럼으로 GROUP BY 하는 복합 집계
**상태:** ⏳ 테스트 대기

---

## 1. 테스트 목적

단일 컬럼이 아닌 2~3개 컬럼으로 그룹화하는 복합 집계 쿼리가 올바르게 생성되는지 검증합니다.

### 배경
- 실무 분석: "상태별 + 결제수단별", "가맹점별 + 상태별" 등 다중 차원 분석 필요
- SQL: `GROUP BY status, payment_method` 형태
- RenderSpec: 다중 그룹 컬럼을 테이블로 올바르게 표현

---

## 2. 사전 조건

- [x] AI Orchestrator: Docker container 실행 중
- [x] Core API: http://localhost:8080 실행 중
- [x] PostgreSQL: payments 테이블 데이터 존재

---

## 3. 테스트 시나리오

### TC-008-1: 상태별 + 결제수단별

**입력:**
```
"최근 1개월 결제를 상태별, 결제수단별로 건수와 금액 합계를 보여줘"
```

**기대 결과:**
- SQL: `GROUP BY status, payment_method`
- SQL: `COUNT(*), SUM(amount)`
- 결과: (DONE, CARD), (DONE, TRANSFER), (CANCELED, CARD) 등 조합

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 결제를 상태별, 결제수단별로 건수와 금액 합계를 보여줘"}' | jq '{
    sql: .queryPlan.sql,
    columns: [.renderSpec.table.columns[].key],
    rowCount: (.queryResult.data | length),
    sampleRow: .queryResult.data[0]
  }'
```

---

### TC-008-2: 가맹점별 + 상태별

**입력:**
```
"최근 3개월 가맹점별, 상태별 결제 건수"
```

**기대 결과:**
- SQL: `GROUP BY merchant_id, status`
- SQL: `COUNT(*)`
- 결과: (mer_001, DONE), (mer_001, CANCELED), (mer_002, DONE) 등

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 3개월 가맹점별, 상태별 결제 건수"}' | jq '{
    sql: .queryPlan.sql,
    columns: [.renderSpec.table.columns[].key],
    rowCount: (.queryResult.data | length)
  }'
```

---

### TC-008-3: 3차원 그룹화 (가맹점 + 상태 + 결제수단)

**입력:**
```
"최근 1개월 가맹점별, 상태별, 결제수단별 금액 합계"
```

**기대 결과:**
- SQL: `GROUP BY merchant_id, status, payment_method`
- SQL: `SUM(amount)`
- 결과: 다중 차원 조합

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 가맹점별, 상태별, 결제수단별 금액 합계"}' | jq '{
    sql: .queryPlan.sql,
    groupByCount: (.queryPlan.sql | scan("GROUP BY ([^\\n]+)") | split(",") | length),
    rowCount: (.queryResult.data | length)
  }'
```

---

### TC-008-4: 날짜별 + 가맹점별

**입력:**
```
"최근 1주일 일자별, 가맹점별 결제 건수와 금액"
```

**기대 결과:**
- SQL: `GROUP BY DATE(created_at), merchant_id`
- SQL: `COUNT(*), SUM(amount)`
- 결과: (2026-01-16, mer_001), (2026-01-16, mer_002), (2026-01-15, mer_001) 등

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1주일 일자별, 가맹점별 결제 건수와 금액"}' | jq '{
    sql: .queryPlan.sql,
    columns: [.renderSpec.table.columns[].key],
    rowCount: (.queryResult.data | length)
  }'
```

---

## 4. API 테스트

```bash
# 전체 테스트 실행
bash test-scenarios/scripts/run-scenario-008.sh
```

---

## 5. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `text_to_sql_service.py` | `generate_query_plan()` | 다중 GROUP BY SQL 생성 |
| `render_spec_builder.py` | `build_table_spec()` | 다중 그룹 컬럼 렌더링 |

---

## 6. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-16 | tester | ⏳ 대기 | 시나리오 작성 완료 |

---

## 7. 검증 포인트

| 시나리오 | 검증 필드 | 기대값 |
|---------|----------|--------|
| TC-008-1 | `.queryPlan.sql` | `GROUP BY status, payment_method` |
| TC-008-2 | `.queryPlan.sql` | `GROUP BY merchant_id, status` |
| TC-008-3 | `.queryPlan.sql` | `GROUP BY` 3개 컬럼 |
| TC-008-4 | `.queryPlan.sql` | `DATE(` + `GROUP BY` |
