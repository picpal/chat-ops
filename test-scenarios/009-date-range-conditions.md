# Test Scenario 009: 날짜 범위 조건

**작성일:** 2026-01-16
**기능:** "이번 달", "지난 주", "오늘" 등 상대적 날짜 표현 인식
**상태:** ⏳ 테스트 대기

---

## 1. 테스트 목적

절대 날짜("2025년 12월") 뿐만 아니라 상대적 날짜 표현("이번 달", "지난 주", "오늘")도 올바르게 SQL WHERE 조건으로 변환되는지 검증합니다.

### 배경
- 실무 사용자는 "이번 달", "오늘", "최근 3일" 등 상대적 표현을 자주 사용
- SQL: `WHERE created_at >= DATE_TRUNC('month', NOW())`
- Text-to-SQL 프롬프트가 상대 날짜 표현을 잘 처리하는지 확인

---

## 2. 사전 조건

- [x] AI Orchestrator: Docker container 실행 중
- [x] Core API: http://localhost:8080 실행 중
- [x] PostgreSQL: payments 테이블 데이터 존재 (현재 날짜 기준)

---

## 3. 테스트 시나리오

### TC-009-1: "이번 달"

**입력:**
```
"이번 달 결제 건수"
```

**기대 결과:**
- SQL: `WHERE created_at >= DATE_TRUNC('month', NOW())`
- 또는: `WHERE EXTRACT(YEAR FROM created_at) = 2026 AND EXTRACT(MONTH FROM created_at) = 1`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "이번 달 결제 건수"}' | jq '{
    sql: .queryPlan.sql,
    count: .queryResult.data[0]
  }'
```

---

### TC-009-2: "지난 주"

**입력:**
```
"지난 주 결제 금액 합계"
```

**기대 결과:**
- SQL: `WHERE created_at >= DATE_TRUNC('week', NOW()) - INTERVAL '1 week'`
- 또는: `WHERE created_at BETWEEN [지난주 월요일] AND [지난주 일요일]`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "지난 주 결제 금액 합계"}' | jq '{
    sql: .queryPlan.sql,
    sum: .queryResult.data[0]
  }'
```

---

### TC-009-3: "오늘"

**입력:**
```
"오늘 결제 내역"
```

**기대 결과:**
- SQL: `WHERE DATE(created_at) = CURRENT_DATE`
- 또는: `WHERE created_at >= DATE_TRUNC('day', NOW())`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "오늘 결제 내역"}' | jq '{
    sql: .queryPlan.sql,
    rowCount: (.queryResult.data | length)
  }'
```

---

### TC-009-4: "어제"

**입력:**
```
"어제 결제 건수"
```

**기대 결과:**
- SQL: `WHERE DATE(created_at) = CURRENT_DATE - INTERVAL '1 day'`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "어제 결제 건수"}' | jq '{
    sql: .queryPlan.sql,
    count: .queryResult.data[0]
  }'
```

---

### TC-009-5: "최근 3일"

**입력:**
```
"최근 3일 결제 내역"
```

**기대 결과:**
- SQL: `WHERE created_at >= NOW() - INTERVAL '3 days'`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 3일 결제 내역"}' | jq '{
    sql: .queryPlan.sql,
    rowCount: (.queryResult.data | length)
  }'
```

---

### TC-009-6: 절대 날짜 "2025년 12월"

**입력:**
```
"2025년 12월 결제 건수"
```

**기대 결과:**
- SQL: `WHERE created_at >= '2025-12-01' AND created_at < '2026-01-01'`
- 또는: `WHERE EXTRACT(YEAR FROM created_at) = 2025 AND EXTRACT(MONTH FROM created_at) = 12`

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "2025년 12월 결제 건수"}' | jq '{
    sql: .queryPlan.sql,
    count: .queryResult.data[0]
  }'
```

---

## 4. API 테스트

```bash
# 전체 테스트 실행
bash test-scenarios/scripts/run-scenario-009.sh
```

---

## 5. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `text_to_sql_service.py` | `generate_query_plan()` | 날짜 조건 SQL 생성 |
| `prompts/text_to_sql_prompt.py` | 시스템 프롬프트 | 날짜 표현 변환 규칙 |

---

## 6. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-16 | tester | ⏳ 대기 | 시나리오 작성 완료 |

---

## 7. 검증 포인트

| 시나리오 | 검증 필드 | 기대값 |
|---------|----------|--------|
| TC-009-1 | `.queryPlan.sql` | `DATE_TRUNC('month'` 또는 `MONTH = 1` |
| TC-009-2 | `.queryPlan.sql` | `INTERVAL '1 week'` 또는 지난주 날짜 |
| TC-009-3 | `.queryPlan.sql` | `CURRENT_DATE` 또는 `NOW()` |
| TC-009-4 | `.queryPlan.sql` | `INTERVAL '1 day'` |
| TC-009-5 | `.queryPlan.sql` | `INTERVAL '3 days'` |
| TC-009-6 | `.queryPlan.sql` | `'2025-12-01'` 또는 `2025` + `12` |
