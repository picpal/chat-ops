# Test Scenario 005: 집계 결과 컨텍스트 표시

**작성일:** 2025-01-15
**기능:** 집계 쿼리 결과에 출처/기준 정보 명시
**상태:** ⏳ 테스트 대기

---

## 1. 테스트 목적

연속 대화에서 집계 요청(합계, 평균 등) 시 결과가 어떤 조건을 기반으로 했는지 명확히 표시되는지 검증

### 배경
- 기존 문제: "결제금액 합산해서 보여줘" 응답에서 어떤 데이터 기반인지 불명확
- 해결: 집계 쿼리 응답에 aggregationContext 메타데이터 추가

---

## 2. 사전 조건

- [ ] UI: http://localhost:3000 실행 중
- [ ] AI Orchestrator: Docker container 실행 중 (최신 코드 반영)
- [ ] Core API: http://localhost:8080 실행 중
- [ ] PostgreSQL: 테스트 데이터 존재
- [ ] Text-to-SQL 모드 활성화 (`SQL_ENABLE_TEXT_TO_SQL=true`)

---

## 3. 테스트 시나리오

### TC-005-1: 연속 조회 후 집계 (핵심 테스트)

**순서:**
1. "최근 3개월 결제건"
2. "이중 mer_001 가맹점만"
3. "이중에 도서관련 상품만"
4. "결제금액 합산해서 보여줘"

**기대 결과:**

| 단계 | 사용자 입력 | 예상 응답 |
|------|------------|----------|
| 4 | 결제금액 합산해서 보여줘 | 집계 결과 + aggregationContext 포함 |

**4단계 응답 검증:**
```json
{
  "queryPlan": {
    "sql": "SELECT SUM(amount) AS total_amount FROM payments WHERE ...",
    "isAggregation": true
  },
  "queryResult": {
    "aggregationContext": {
      "queryType": "NEW_QUERY",
      "basedOnFilters": [
        "created_at >= NOW() - INTERVAL '3 months'",
        "merchant_id = 'mer_001'",
        "order_name LIKE '%도서%'"
      ],
      "sourceRowCount": 25,
      "aggregationFunction": "SUM",
      "targetColumn": "amount"
    }
  }
}
```

**검증 방법:**
1. 응답에 `aggregationContext` 필드 존재 확인
2. `queryType`이 "NEW_QUERY" (새 SQL 실행)임 확인
3. `basedOnFilters`에 이전 3단계 조건 모두 포함 확인
4. `sourceRowCount`가 이전 결과 건수(25건)와 일치 확인

---

### TC-005-2: 다양한 집계 함수 테스트

**순서:**
1. "최근 1개월 mer_001 결제건" (기준 데이터)
2. 각각 다른 집계 요청

| 집계 입력 | 예상 aggregationFunction | 예상 targetColumn |
|----------|------------------------|------------------|
| "결제금액 합산해줘" | SUM | amount |
| "결제 건수 알려줘" | COUNT | * |
| "평균 결제금액은?" | AVG | amount |
| "최대 결제금액은?" | MAX | amount |
| "최소 결제금액은?" | MIN | amount |

**검증 방법:**
- 각 집계 요청에 맞는 함수가 응답에 표시되는지 확인

---

### TC-005-3: 집계 결과 UI 표시

**기대 UI 표시 형태:**

```
📊 집계 결과: 14,477,000원
━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 조회 기준:
  - 기간: 최근 3개월
  - 가맹점: mer_001
  - 조건: 도서 관련 상품
📌 대상: 25건
📌 처리: 데이터베이스 집계 쿼리 실행
```

**검증 방법:**
1. RenderSpec에 aggregationContext 정보가 반영되는지 확인
2. UI에서 집계 기준 정보가 표시되는지 확인

---

### TC-005-4: 첫 쿼리가 집계인 경우

**순서:**
1. "이번달 총 결제금액" (첫 질문부터 집계)

**기대 결과:**

```json
{
  "aggregationContext": {
    "queryType": "NEW_QUERY",
    "basedOnFilters": ["created_at >= DATE_TRUNC('month', NOW())"],
    "sourceRowCount": null,
    "aggregationFunction": "SUM",
    "targetColumn": "amount"
  }
}
```

**검증 방법:**
- `sourceRowCount`가 null (이전 결과 없음)
- 조건 정보는 정상 표시

---

### TC-005-5: 그룹별 집계

**순서:**
1. "최근 1개월 결제건"
2. "상태별로 금액 합계 보여줘"

**기대 결과:**
- GROUP BY 집계도 aggregationContext 포함
- `groupByColumns: ["status"]` 추가 정보

---

## 4. API 테스트 (curl)

### 시나리오 1 실행

```bash
# Step 1-3: 조건 누적 (생략, TC-003과 동일)

# Step 4: 집계 요청
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "결제금액 합산해서 보여줘",
    "conversationHistory": [
      {"id": "msg-1", "role": "user", "content": "최근 3개월 결제건", "timestamp": "2025-01-15T10:00:00Z"},
      {"id": "msg-2", "role": "assistant", "content": "결과입니다.", "timestamp": "2025-01-15T10:00:05Z",
       "queryPlan": {"mode": "text_to_sql", "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '\''3 months'\''"}},
      {"id": "msg-3", "role": "user", "content": "이중 mer_001 가맹점만", "timestamp": "2025-01-15T10:01:00Z"},
      {"id": "msg-4", "role": "assistant", "content": "결과입니다.", "timestamp": "2025-01-15T10:01:05Z",
       "queryPlan": {"mode": "text_to_sql", "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '\''3 months'\'' AND merchant_id = '\''mer_001'\''"}},
      {"id": "msg-5", "role": "user", "content": "이중에 도서관련 상품만", "timestamp": "2025-01-15T10:02:00Z"},
      {"id": "msg-6", "role": "assistant", "content": "결과입니다.", "timestamp": "2025-01-15T10:02:05Z",
       "queryPlan": {"mode": "text_to_sql", "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '\''3 months'\'' AND merchant_id = '\''mer_001'\'' AND order_name LIKE '\''%도서%'\''"},
       "queryResult": {"metadata": {"totalRows": 25}}}
    ]
  }' | jq '{
    sql: .queryPlan.sql,
    isAggregation: .queryPlan.isAggregation,
    aggregationContext: .queryResult.aggregationContext
  }'
```

**예상 응답:**
```json
{
  "sql": "SELECT SUM(amount) AS total_amount FROM payments WHERE ...",
  "isAggregation": true,
  "aggregationContext": {
    "queryType": "NEW_QUERY",
    "basedOnFilters": [...],
    "sourceRowCount": 25,
    "aggregationFunction": "SUM",
    "targetColumn": "amount"
  }
}
```

---

## 5. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `text_to_sql.py` | `detect_aggregation_query()` | 집계 쿼리 여부 감지 |
| `text_to_sql.py` | `build_aggregation_context()` | aggregationContext 메타데이터 생성 |
| `chat.py` | `process_message()` | 응답에 aggregationContext 포함 |
| `render_spec_builder.py` | `build_aggregation_render()` | 집계 결과 RenderSpec 생성 |

---

## 6. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2025-01-15 | - | ⏳ 대기 | 기능 구현 후 테스트 예정 |

---

## 7. 관련 이슈

- 문제 발견: 2025-01-15 19:34 테스트 중
- 원인: 집계 결과가 어떤 데이터 기반인지 표시 없음
- 해결: aggregationContext 메타데이터 추가 구현 필요
