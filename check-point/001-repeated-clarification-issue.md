# Issue: Repeated Clarification Request Bug

## Date
2026-01-11

## Problem Description
AI 오케스트레이터가 명확한 사용자 요청에도 불구하고 계속 clarification(추가 정보 필요)을 반복 요청하는 문제

## Symptoms
1. "최근 거래 30건 조회" → "'최근 거래 30건 조회'에 대해 어떤 데이터를 조회하시겠습니까?" 반복
2. "결제 데이터" → "'결제 데이터'에 대해 어떤 데이터를 조회하시겠습니까?" 반복
3. 후속 필터링 질문도 동일하게 clarification 요청

## Root Cause Analysis

### 원인 1: LangChain 프롬프트 변수 파싱 에러
- `query_planner.py`의 시스템 프롬프트에서 JSON 예시 코드 블록 내의 중괄호가 LangChain 템플릿 변수로 잘못 인식됨
- 에러 메시지:
```
Input to ChatPromptTemplate is missing variables {'\\n  "needs_clarification"'}
```
- JSON 예시에서 줄바꿈 후 `"needs_clarification"`이 변수로 파싱됨

### 원인 2: Enum 값 변환 에러
- LLM이 올바른 QueryPlan을 반환해도 `_convert_to_dict()` 함수에서 enum 값 변환 시 에러 발생
- 에러 메시지:
```
'str' object has no attribute 'value'
```
- LangChain structured output이 Pydantic enum이 아닌 plain string으로 반환되는 경우가 있음

### 결과
두 에러 모두 예외 처리 후 `_create_fallback_plan()`이 호출되어 항상 clarification을 반환

## Solution

### Fix 1: JSON 예시를 마크다운 리스트로 변경 (line 472-477)
```python
# Before (JSON 블록 - 문제 발생)
### 명확화 요청 시 (드문 경우):
```json
{{
  "needs_clarification": true,
  ...
}}
```

# After (마크다운 리스트 - 안전)
### 명확화 요청 시 (드문 경우):
- needs_clarification: true
- clarification_question: "..."
```

### Fix 2: enum/string 방어적 변환 헬퍼 추가 (line 584-590)
```python
def _get_enum_value(self, val) -> Any:
    """enum 또는 string에서 값 추출"""
    if val is None:
        return None
    if hasattr(val, 'value'):
        return val.value
    return val
```

### Fix 3: `_convert_to_dict()`에서 헬퍼 사용 (line 603-617)
```python
result = {
    "entity": self._get_enum_value(plan.entity),
    "operation": self._get_enum_value(plan.operation) or "list",
    "limit": plan.limit
}
```

## Test Cases & Verification

### 테스트 1: 최근 결제 이력 30건 조회
- 입력: `"최근 결제 이력 30건 조회"`
- 기대: Payment 엔티티, limit:30
- 결과: ✅ 성공
```json
{"entity": "Payment", "operation": "list", "limit": 30}
```

### 테스트 2: 도서 관련 주문건 필터링
- 입력: `"이중 도서 관련 주문건만 조회"` (with conversation history)
- 기대: Payment + orderName LIKE '도서' 필터
- 결과: ✅ 성공
```json
{"entity": "Payment", "operation": "list", "limit": 10, "filters": [{"field": "orderName", "operator": "like", "value": "도서"}]}
```

### 테스트 3: 특정 가맹점 필터링
- 입력: `"이중 mer_001 가맹점만 조회"` (with conversation history)
- 기대: Payment + merchantId EQ 'mer_001' 필터
- 결과: ✅ 성공
```json
{"entity": "Payment", "operation": "list", "limit": 10, "filters": [{"field": "merchantId", "operator": "eq", "value": "mer_001"}]}
```

## Files Modified
- `services/ai-orchestrator/app/services/query_planner.py`
  - Line 472-484: JSON 예시를 마크다운 리스트로 변경 + 강화된 가이드라인 추가
  - Line 584-590: `_get_enum_value()` 헬퍼 함수 추가
  - Line 603-617: `_convert_to_dict()`에서 enum 안전 변환 적용

- `services/ai-orchestrator/app/api/v1/chat.py`
  - Line 75-131: 후속 질문 필터 병합 로직 추가
    - `FOLLOW_UP_KEYWORDS`: 후속 질문 키워드 목록
    - `is_follow_up_query()`: 후속 질문 감지 함수
    - `get_previous_query_plan()`: 이전 queryPlan 추출 함수
    - `merge_filters()`: 이전/새 필터 병합 함수
  - Line 220-227: chat() 함수에서 후속 질문 시 필터 자동 병합 적용

## Status
✅ **RESOLVED** - 2026-01-11

### Issue 1: Repeated Clarification
모든 테스트 케이스에서 clarification 없이 올바른 QueryPlan 생성 확인

### Issue 2: Filter Accumulation (추가 수정)
후속 질문("이중", "그 중에서" 등)에서 이전 필터가 누적되지 않는 문제 해결
- 테스트 3에서 `merchantId eq 'mer_001'` + `orderName like '도서'` 두 필터 모두 적용 확인
