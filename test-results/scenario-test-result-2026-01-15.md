# 시나리오 테스트 결과 (2026-01-15)

## 테스트 환경
- 테스트 일시: 2026-01-15
- AI Orchestrator: http://localhost:8000
- 테스트 방식: API 직접 호출 + conversationHistory 전달

## 시나리오 A: 결제 데이터 분석 (연속 필터링 + 집계)

### 테스트 결과 요약

| Step | 사용자 입력 | 기대 동작 | 실제 SQL | 결과 |
|------|------------|----------|----------|------|
| 1 | "최근 1개월 결제건" | 기본 조회 | `WHERE created_at >= NOW() - INTERVAL '1 month'` | ✅ PASS |
| 2 | "이중에 DONE 상태만" | 조건 추가 | `WHERE ... AND status = 'DONE'` | ✅ PASS |
| 3 | "이중에 카드결제만" | 조건 추가 | `WHERE ... AND status = 'DONE' AND method = 'CARD'` | ✅ PASS |
| 4 | "금액이 10만원 이상인 것만" | 조건 추가 | `WHERE amount >= 100000` | ❌ **FAIL** (이전 조건 유실) |
| 5 | "결제금액 합계 알려줘" | 집계 쿼리 | `SELECT SUM(amount) WHERE ... 모든 조건` | ✅ PASS |
| 6 | "평균 결제금액은?" | 집계 쿼리 | `SELECT AVG(amount) WHERE ... 모든 조건` | ✅ PASS |
| 8 | "mer_001 가맹점 건만 보여줘" | 조건 추가 | `WHERE merchant_id = 'mer_001'` | ❌ **FAIL** (이전 조건 유실) |

### 상세 분석

#### ✅ 성공 케이스

**Step 1-3: 연속 필터링**
```sql
-- Step 1
WHERE created_at >= NOW() - INTERVAL '1 month'

-- Step 2
WHERE created_at >= NOW() - INTERVAL '1 month' AND status = 'DONE'

-- Step 3
WHERE created_at >= NOW() - INTERVAL '1 month' AND status = 'DONE' AND method = 'CARD'
```
→ 조건이 순차적으로 누적됨

**Step 5-6: 집계 쿼리**
```sql
-- Step 5 (합계)
SELECT SUM(amount) AS total_amount
FROM payments
WHERE created_at >= NOW() - INTERVAL '1 month'
  AND status = 'DONE'
  AND method = 'CARD'
  AND amount >= 100000

-- Step 6 (평균)
SELECT AVG(amount) AS average_amount
FROM payments
WHERE created_at >= NOW() - INTERVAL '1 month'
  AND status = 'DONE'
  AND method = 'CARD'
  AND amount >= 100000
```
→ 집계 쿼리 시 이전 조건 모두 유지됨 (Step 4 조건 포함)

#### ❌ 실패 케이스

**Step 4: 금액 조건 추가 시 이전 조건 유실**
```sql
-- 기대값
WHERE created_at >= NOW() - INTERVAL '1 month'
  AND status = 'DONE'
  AND method = 'CARD'
  AND amount >= 100000

-- 실제값
WHERE amount >= 100000  -- 이전 조건 모두 사라짐
```
→ 총 898건 조회 (실제로는 ~30건이어야 함)

**Step 8: 가맹점 필터 추가 시 이전 조건 유실**
```sql
-- 기대값
WHERE created_at >= NOW() - INTERVAL '1 month'
  AND status = 'DONE'
  AND method = 'CARD'
  AND amount >= 100000
  AND merchant_id = 'mer_001'

-- 실제값
WHERE merchant_id = 'mer_001'  -- 이전 조건 모두 사라짐
```
→ 총 125건 조회 (실제로는 ~5건이어야 함)

### 발견된 패턴

1. **집계 쿼리 시 컨텍스트 유지 성공** (Step 5, 6)
   - "합계 알려줘", "평균은?" 등의 질문에 이전 조건 유지됨
   - 이전 문제점 해결됨 ✅

2. **필터 추가 시 컨텍스트 유실 발생** (Step 4, 8)
   - "금액이 X 이상", "가맹점 Y만" 등의 필터 추가 시 이전 조건 사라짐
   - **핵심 버그 확인** ⚠️

3. **부분적 개선**
   - 초기 3단계 필터링은 정상 작동 (Step 1-3)
   - 집계 쿼리 컨텍스트 유지는 개선됨
   - 하지만 4번째 필터부터 문제 발생

## 시나리오 B: 날짜 인식 테스트

### 테스트 결과 요약

| Step | 사용자 입력 | 기대 날짜 | 실제 SQL | 결과 |
|------|------------|----------|----------|------|
| 1 | "이번달 결제건 조회" | 2026-01 | `WHERE created_at >= '2026-01-01' AND created_at < '2026-02-01'` | ✅ PASS |
| 2 | "이중에 DONE 상태만" | 2026-01 유지 | `WHERE created_at >= '2026-01-01' ... AND status = 'DONE'` | ✅ PASS |
| 3 | "총 매출액은?" | 2026-01 유지 | `SELECT SUM(amount) WHERE created_at >= '2026-01-01' ... AND status = 'DONE'` | ✅ PASS |

### 상세 분석

**날짜 인식 개선 확인**
```sql
-- Step 1: 이번달 (2026년 1월)
WHERE created_at >= '2026-01-01' AND created_at < '2026-02-01'
```
→ 이전에 2024-01로 인식되던 문제 해결됨 ✅

**날짜 조건 유지 확인**
```sql
-- Step 2
WHERE created_at >= '2026-01-01' AND created_at < '2026-02-01' AND status = 'DONE'

-- Step 3
SELECT SUM(amount) FROM payments
WHERE created_at >= '2026-01-01' AND created_at < '2026-02-01' AND status = 'DONE'
```
→ 날짜 조건이 연속 대화에서 유지됨 ✅

## 이전 테스트 대비 개선 사항

### ✅ 개선된 부분

1. **집계 쿼리 컨텍스트 유지**
   - 이전: "합계 알려줘" → 전체 테이블 집계
   - 현재: "합계 알려줘" → 이전 필터 조건 유지하여 집계
   - **핵심 문제 해결됨**

2. **날짜 인식 정확도**
   - 이전: "이번달" → 2024-01로 인식
   - 현재: "이번달" → 2026-01로 정확히 인식
   - **날짜 처리 개선됨**

3. **초기 필터 체이닝**
   - Step 1-3까지 필터 누적이 안정적으로 작동

### ❌ 여전히 남아있는 문제

1. **다중 필터 체이닝 불안정**
   - 3번째 필터까지는 정상, 4번째부터 이전 조건 유실
   - 원인: conversationHistory 처리 로직 문제로 추정

2. **특정 필터 타입에서 컨텍스트 유실**
   - 금액 필터 (amount >= 100000)
   - 가맹점 필터 (merchant_id = 'mer_001')
   - 패턴: 테이블 필드 직접 참조 시 문제 발생 가능성

## 권장 조치

### 우선순위 1: 필터 체이닝 안정화

**문제 원인 추정**
- conversationHistory에서 이전 SQL 추출 로직 불완전
- 특정 조건에서 WHERE 절 병합 실패
- LLM 프롬프트에서 "이전 조건 유지" 지시 불충분

**해결 방향**
```python
# services/ai-orchestrator/app/services/text_to_sql_service.py
# 이전 SQL의 WHERE 조건을 명시적으로 추출하여 병합
def extract_where_conditions(previous_sql: str) -> List[str]:
    """이전 SQL에서 WHERE 조건 추출"""
    # SQL 파싱하여 WHERE 절 분리
    # 각 조건을 리스트로 반환
    pass

def merge_conditions(previous_conditions: List[str], new_condition: str) -> str:
    """기존 조건 + 새 조건 병합"""
    all_conditions = previous_conditions + [new_condition]
    return " AND ".join(all_conditions)
```

### 우선순위 2: 컨텍스트 전달 검증

**검증 포인트**
1. conversationHistory에 queryPlan.sql이 올바르게 포함되는가?
2. LLM에게 이전 SQL이 명확히 전달되는가?
3. 프롬프트에서 "기존 WHERE 조건 유지" 지시가 명확한가?

**테스트 방법**
```bash
# LLM에게 전달되는 프롬프트 로깅
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "...", "conversationHistory": [...], "debug": true}'
```

### 우선순위 3: 통합 테스트 추가

**테스트 케이스**
- 5단계 이상 필터 체이닝
- 금액, 날짜, 문자열 필터 혼합
- 필터 → 집계 → 필터 → 집계 순서

## 결론

### 긍정적 평가
- 집계 쿼리 컨텍스트 유지 문제 해결 ✅
- 날짜 인식 정확도 개선 ✅
- 초기 필터 체이닝 안정화 ✅

### 여전히 해결 필요
- 다중 필터 체이닝 시 컨텍스트 유실 ❌
- 특정 필터 타입에서 조건 누락 ❌

### 다음 단계
1. where_condition_merge 로직 강화
2. conversationHistory 처리 디버깅
3. LLM 프롬프트 개선
4. 통합 테스트 케이스 추가
