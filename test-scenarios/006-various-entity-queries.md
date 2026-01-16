# Test Scenario 006: 다양한 엔티티 조회

**작성일:** 2026-01-16
**기능:** Payment 외 Merchant, Refund, Settlement 등 다양한 엔티티 조회
**상태:** ⏳ 테스트 대기

---

## 1. 테스트 목적

Payment 테이블 외에 Merchant, Refund, Settlement, Order 등 다른 비즈니스 엔티티도 자연어로 조회할 수 있는지 검증합니다.

### 배경
- 기존 시나리오는 대부분 Payment 테이블 중심
- 실제 백오피스는 가맹점, 환불, 정산 등 다양한 엔티티 조회 필요
- RAG 문서(entity 타입)에 정의된 테이블들이 올바르게 인식되는지 확인

---

## 2. 사전 조건

- [x] AI Orchestrator: Docker container 실행 중
- [x] Core API: http://localhost:8080 실행 중
- [x] PostgreSQL: merchants, refunds, settlements 테이블 데이터 존재

---

## 3. 테스트 시나리오

### TC-006-1: 가맹점(Merchant) 조회

**입력:**
```
"활성 상태인 가맹점 목록을 보여줘"
```

**기대 결과:**
- `queryPlan.mode`: "text_to_sql"
- SQL에 `merchants` 테이블 포함
- WHERE 조건에 status = 'ACTIVE' 포함
- 컬럼: merchant_id, merchant_name, status, fee_rate 등

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "활성 상태인 가맹점 목록을 보여줘"}' | jq '{
    mode: .queryPlan.mode,
    sql: .queryPlan.sql,
    columns: [.renderSpec.table.columns[].key],
    rowCount: (.queryResult.data | length)
  }'
```

---

### TC-006-2: 환불(Refund) 조회

**입력:**
```
"최근 1개월 환불 건수와 환불 금액 합계를 보여줘"
```

**기대 결과:**
- SQL에 `refunds` 테이블 포함
- 시간 범위 조건: 최근 1개월
- 집계: COUNT, SUM(refund_amount)

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 환불 건수와 환불 금액 합계를 보여줘"}' | jq '{
    mode: .queryPlan.mode,
    sql: .queryPlan.sql,
    data: .queryResult.data[0]
  }'
```

---

### TC-006-3: 정산(Settlement) 조회

**입력:**
```
"2025년 12월 정산 현황을 보여줘"
```

**기대 결과:**
- SQL에 `settlements` 테이블 포함
- WHERE 조건: settlement_date BETWEEN '2025-12-01' AND '2025-12-31'
- 컬럼: settlement_id, merchant_id, settlement_date, total_amount 등

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "2025년 12월 정산 현황을 보여줘"}' | jq '{
    mode: .queryPlan.mode,
    sql: .queryPlan.sql,
    rowCount: (.queryResult.data | length)
  }'
```

---

### TC-006-4: 주문(Order) 조회

**입력:**
```
"최근 1주일 주문 목록"
```

**기대 결과:**
- SQL에 `orders` 테이블 포함
- WHERE 조건: created_at >= NOW() - INTERVAL '7 days'

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1주일 주문 목록"}' | jq '{
    mode: .queryPlan.mode,
    sql: .queryPlan.sql,
    rowCount: (.queryResult.data | length)
  }'
```

---

## 4. API 테스트

```bash
# 전체 테스트 실행
bash test-scenarios/scripts/run-scenario-006.sh
```

---

## 5. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `rag_service.py` | `search_similar()` | RAG 문서 검색 (entity 타입) |
| `text_to_sql_service.py` | `generate_query_plan()` | SQL 생성 |
| `db/migration/V1__init.sql` | 테이블 정의 | merchants, refunds, settlements, orders |

---

## 6. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-16 | tester | ⏳ 대기 | 시나리오 작성 완료 |

---

## 7. 검증 포인트

| 시나리오 | 검증 필드 | 기대값 |
|---------|----------|--------|
| TC-006-1 | `.queryPlan.sql` | `merchants` 포함 |
| TC-006-1 | `.queryPlan.sql` | `WHERE status = 'ACTIVE'` |
| TC-006-2 | `.queryPlan.sql` | `refunds` 포함 |
| TC-006-2 | `.queryResult.data[0]` | COUNT, SUM 값 존재 |
| TC-006-3 | `.queryPlan.sql` | `settlements` 포함 |
| TC-006-3 | `.queryPlan.sql` | `2025-12` 날짜 조건 |
| TC-006-4 | `.queryPlan.sql` | `orders` 포함 |
