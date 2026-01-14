# Test Scenario 003: WHERE 조건 체이닝 (연속 대화)

**작성일:** 2025-01-15
**기능:** 연속 대화에서 이전 WHERE 조건 유지
**상태:** ✅ 테스트 통과

---

## 1. 테스트 목적

연속 대화에서 "이중에", "여기서" 등 참조 표현 사용 시 이전 SQL의 WHERE 조건이 누적되어 유지되는지 검증

### 배경
- 기존 문제: "최근 3개월 결제건" → "이중 mer_001만" 시 시간 조건 누락
- 해결: 참조 표현 감지 + WHERE 조건 병합 로직 추가

---

## 2. 사전 조건

- [ ] UI: http://localhost:3000 실행 중
- [ ] AI Orchestrator: Docker container 실행 중 (최신 코드 반영)
- [ ] Core API: http://localhost:8080 실행 중
- [ ] PostgreSQL: 테스트 데이터 존재
- [ ] Text-to-SQL 모드 활성화 (`SQL_ENABLE_TEXT_TO_SQL=true`)

---

## 3. 테스트 시나리오

### TC-003-1: 조건 누적 (핵심 테스트)

**순서:**
1. "최근 3개월 결제건"
2. "이중 mer_001 가맹점만"
3. "이중에 도서관련 상품만"

**기대 결과:**

| 단계 | 사용자 입력 | 예상 WHERE 절 | 예상 건수 |
|------|------------|---------------|----------|
| 1 | 최근 3개월 결제건 | `created_at >= NOW() - INTERVAL '3 months'` | 1000건 |
| 2 | 이중 mer_001 가맹점만 | `created_at >= ... AND merchant_id = 'mer_001'` | 125건 |
| 3 | 이중에 도서관련 상품만 | `created_at >= ... AND merchant_id = 'mer_001' AND order_name LIKE '%도서%'` | 25건 |

**검증 방법:**
1. 각 단계에서 생성된 SQL 확인 (queryPlan.sql)
2. WHERE 절에 이전 조건이 포함되어 있는지 확인
3. 반환 건수가 점진적으로 감소하는지 확인

---

### TC-003-2: 새 쿼리 전환

**순서:**
1. "최근 3개월 결제건" → "이중 mer_001만" (조건 누적 상태)
2. "최근 2개월간의 결제건 보여줘" (새 쿼리)

**기대 결과:**

| 단계 | 사용자 입력 | 참조 표현 | 예상 동작 |
|------|------------|----------|----------|
| 1 | 이중 mer_001만 | ✓ "이중" | 이전 조건 유지 |
| 2 | 최근 2개월간의 결제건 | ✗ 없음 | **새 쿼리 생성** (이전 조건 무시) |

**검증 방법:**
- 2번 SQL: `WHERE created_at >= NOW() - INTERVAL '2 months'`만 포함
- merchant_id 조건 없음 확인

---

### TC-003-3: 동일 필드 조건 변경

**순서:**
1. "DONE 상태 결제건"
2. "이중 CANCELED만"

**기대 결과:**

| 단계 | 예상 WHERE 절 | 설명 |
|------|---------------|------|
| 1 | `status = 'DONE'` | 초기 조건 |
| 2 | `status = 'CANCELED'` | 동일 필드 → 새 조건으로 **대체** |

**검증 방법:**
- 2번 SQL에서 `status = 'DONE'` 없음 확인
- `status = 'CANCELED'`만 존재

---

### TC-003-4: 참조 표현 키워드 테스트

| 입력 키워드 | 참조 감지 | 동작 |
|------------|----------|------|
| "이중에 ~" | ✓ | 이전 조건 유지 |
| "여기서 ~" | ✓ | 이전 조건 유지 |
| "그중에 ~" | ✓ | 이전 조건 유지 |
| "직전 결과에서 ~" | ✓ | 이전 조건 유지 |
| "방금 결과 중 ~" | ✓ | 이전 조건 유지 |
| "새로 조회해줘" | ✗ (new) | 새 쿼리 생성 |
| "다시 처음부터" | ✗ (new) | 새 쿼리 생성 |

---

## 4. API 테스트 (curl)

### 시나리오 1 실행

```bash
# Step 1: 최근 3개월 결제건
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 3개월 결제건"}' | jq '{sql: .queryPlan.sql, totalRows: .queryResult.metadata.totalRows}'

# Step 2: 이중 mer_001만 (conversationHistory 포함)
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "이중 mer_001 가맹점만",
    "conversationHistory": [
      {"id": "msg-1", "role": "user", "content": "최근 3개월 결제건", "timestamp": "2025-01-15T10:00:00Z"},
      {"id": "msg-2", "role": "assistant", "content": "결과입니다.", "timestamp": "2025-01-15T10:00:05Z",
       "queryPlan": {"mode": "text_to_sql", "sql": "SELECT * FROM payments WHERE created_at >= NOW() - INTERVAL '\''3 months'\'' LIMIT 1000"}}
    ]
  }' | jq '{sql: .queryPlan.sql, totalRows: .queryResult.metadata.totalRows}'
```

---

## 5. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `chat.py` | `detect_reference_expression()` | 참조 표현 감지 ("이중에", "여기서" 등) |
| `text_to_sql.py` | `extract_where_conditions()` | SQL에서 WHERE 조건 추출 |
| `text_to_sql.py` | `merge_where_conditions()` | 기존/새 조건 병합 (동일 필드 대체) |
| `text_to_sql.py` | `ConversationContext` | `accumulated_where_conditions`, `is_refinement` 필드 |
| `text_to_sql.py` | `_build_prompt()` | 참조 모드 시 조건 유지 지시 추가 |

---

## 6. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2025-01-15 | Claude | ✅ PASS | API 테스트 (curl), 4개 시나리오 모두 통과 |

### 실제 테스트 결과 (2025-01-15)

**TC-003-1 결과:**
| 단계 | SQL WHERE 절 | 건수 | 결과 |
|------|-------------|------|------|
| 1 | `created_at >= NOW() - INTERVAL '3 months'` | 1000 | ✅ |
| 2 | `created_at >= ... AND merchant_id = 'mer_001'` | 125 | ✅ |
| 3 | `created_at >= ... AND merchant_id = 'mer_001' AND order_name LIKE '%도서%'` | 25 | ✅ |

**TC-003-2 결과:**
| 입력 | SQL WHERE 절 | 결과 |
|------|-------------|------|
| 최근 2개월간의 결제건 | `created_at >= NOW() - INTERVAL '2 months'` (이전 조건 무시) | ✅ |

---

## 7. 관련 커밋

```
c88c047 feat(ai): implement WHERE condition chaining for consecutive queries
```
