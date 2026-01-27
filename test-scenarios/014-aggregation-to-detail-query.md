# Test Scenario 014: 집계 결과 기반 상세 조회

**작성일:** 2026-01-27
**기능:** GROUP BY 집계 결과에서 특정 그룹값의 상세 데이터 조회 (꼬리 질문)
**상태:** ⏳ 테스트 대기

---

## 1. 테스트 목적

집계 쿼리(GROUP BY) 실행 후, 특정 그룹값에 대한 상세 조회(다른 엔티티 포함)가 올바르게 동작하는지 검증합니다.

### 배경
- 기존 문제: "오류 유형별 집계" 후 "INVALID_CARD 오류의 상세이력 조회" 요청 시 0건 반환
- 원인 1: GROUP BY 컬럼 값이 다음 쿼리의 WHERE 조건으로 변환되지 않음
- 원인 2: payment_history 테이블에는 failure_code 컬럼이 없어 payments와 JOIN 필요
- 해결: 프롬프트에 JOIN 관계 명시, 집계 컨텍스트 전달 강화

---

## 2. 사전 조건

- [ ] UI: http://localhost:3000 실행 중
- [ ] AI Orchestrator: Docker container 실행 중 (최신 코드 반영)
- [ ] Core API: http://localhost:8080 실행 중
- [ ] PostgreSQL: 테스트 데이터 존재
- [ ] payments 테이블에 status='ABORTED'인 결제 데이터 존재
- [ ] payment_history 테이블에 해당 결제의 이력 데이터 존재

---

## 3. 테스트 시나리오

### TC-014-1: 오류 유형별 집계 쿼리

**입력:**
```
최근 1개월 결제건에서 오류 유형별 집계
```

**기대 결과:**
- GROUP BY failure_code를 사용한 집계 쿼리 생성
- failure_code별 건수가 집계되어 표시
- aggregationContext에 hasGroupBy=true, groupByColumns=['failure_code'] 포함

**검증 방법:**
1. UI에서 쿼리 실행
2. 결과에 failure_code별 집계가 표시되는지 확인
3. 브라우저 DevTools에서 응답의 aggregationContext 확인

---

### TC-014-2: 집계 결과 기반 상세 이력 조회 (꼬리 질문)

**입력 (TC-014-1 직후):**
```
INVALID_CARD 오류로 집계된 결제건의 결제 상세이력 조회
```

**기대 결과:**

| 항목 | 기대값 |
|------|--------|
| SQL에 JOIN 포함 | `JOIN payment_history` 또는 `JOIN payments` |
| WHERE 조건 | `failure_code = 'INVALID_CARD'` |
| 결과 건수 | > 0 (데이터 존재 시) |
| 반환 테이블 | payment_history 데이터 |

**검증 방법:**
1. 생성된 SQL에 payments와 payment_history JOIN 확인
2. WHERE 조건에 failure_code = 'INVALID_CARD' 포함 확인
3. 결과 건수 > 0 확인

---

### TC-014-3: 다른 그룹값으로 상세 조회

**입력 (TC-014-1 직후):**
```
EXPIRED_CARD 오류 결제건의 상세 내역
```

**기대 결과:**
- WHERE failure_code = 'EXPIRED_CARD' 조건 포함
- 적절한 JOIN 사용 (필요시)
- 결과 반환

---

### TC-014-4: 상태별 집계 후 상세 조회

**입력:**
```
최근 1주일 결제 상태별 건수 집계
```

**기대 결과:**
- GROUP BY status 쿼리 생성
- 상태별 건수 표시

**후속 입력:**
```
CANCELED 상태의 결제 상세 조회
```

**기대 결과:**
- WHERE status = 'CANCELED' 조건 포함
- 결과 건수 > 0

---

## 4. API 테스트

### 1단계: 오류 유형별 집계

```bash
SESSION_ID="test-tc014-$(date +%s)"

# 오류 유형별 집계
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"최근 1개월 결제건에서 오류 유형별 집계\",
    \"session_id\": \"$SESSION_ID\"
  }" | jq '.queryResult.aggregationContext'
```

### 2단계: 꼬리 질문 - 상세 이력 조회

```bash
# 이전 대화 컨텍스트 포함하여 요청
# (실제로는 UI에서 conversation_history가 자동 전달됨)
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"INVALID_CARD 오류로 집계된 결제건의 결제 상세이력 조회\",
    \"session_id\": \"$SESSION_ID\"
  }" | jq '{sql: .queryResult.sql, rowCount: .queryResult.rowCount}'
```

---

## 5. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `text_to_sql.py` | `SCHEMA_PROMPT` (라인 612-630) | JOIN 관계 및 failure_code 위치 명시 |
| `conversation_context.py` | `extract_previous_results()` | groupBy 메타데이터 추출 |
| `conversation_context.py` | `build_conversation_context()` | 집계→상세 규칙 프롬프트 추가 |
| `query_planner.py` | `classify_intent()` | 집계→상세 패턴 감지 |

---

## 6. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-27 | - | ⏳ 대기 | 초기 작성 |

---

## 7. 핵심 SQL 패턴

### 올바른 SQL 예시

```sql
-- 집계 결과 기반 상세 이력 조회
SELECT ph.history_id, ph.payment_key, ph.previous_status, ph.new_status,
       ph.reason, ph.processed_by, ph.created_at
FROM payment_history ph
JOIN payments p ON ph.payment_key = p.payment_key
WHERE p.failure_code = 'INVALID_CARD'
  AND p.created_at >= NOW() - INTERVAL '1 month'
ORDER BY ph.created_at DESC;
```

### 잘못된 SQL 예시 (수정 전 문제)

```sql
-- 잘못: payment_history에 failure_code 없음
SELECT * FROM payment_history
WHERE failure_code = 'INVALID_CARD';  -- 컬럼 없음, 오류 발생

-- 잘못: 조건 누락
SELECT * FROM payment_history;  -- 0건 또는 전체 건수 반환
```

---

## 8. 체크리스트

- [ ] 집계 쿼리에서 groupByColumns 정보가 aggregationContext에 포함되는가?
- [ ] 꼬리 질문에서 groupBy 값이 WHERE 조건으로 변환되는가?
- [ ] 다른 엔티티(payment_history) 조회 시 적절한 JOIN이 생성되는가?
- [ ] failure_code 조건이 payments 테이블에 적용되는가?
- [ ] 결과 건수가 0이 아닌가?
