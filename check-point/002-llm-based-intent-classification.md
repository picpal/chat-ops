# Feature: LLM-based Intent Classification

## Date
2026-01-11

## Problem
키워드 기반 후속 질문 감지 방식의 한계:
- "이중", "여기서" 등 키워드 없으면 후속 질문 감지 못함
- "100만원 이상만" 같은 필터링 요청이 새 쿼리로 처리됨

## Solution
LLM이 QueryPlan 생성 시 `query_intent` 필드도 함께 분류하도록 변경

### 의도 종류
- `new_query`: 새로운 검색 (이전 컨텍스트 무시)
- `refine_previous`: 이전 결과 필터링/정제

## Implementation

### 1. query_planner.py 변경

#### QueryIntent Enum 추가
```python
class QueryIntent(str, Enum):
    NEW_QUERY = "new_query"
    REFINE_PREVIOUS = "refine_previous"
```

#### QueryPlan 모델에 query_intent 필드 추가
```python
query_intent: QueryIntent = Field(
    default=QueryIntent.NEW_QUERY,
    description="쿼리 의도: new_query(새 검색) 또는 refine_previous(이전 결과 필터링)"
)
```

#### 시스템 프롬프트에 의도 분류 지시사항 추가
- new_query: 첫 질문, 다른 엔티티, "새로/다른/별도로" 표현
- refine_previous: 동일 엔티티 + 조건 추가, "이중/여기서/~만" 표현

### 2. chat.py 변경

#### 제거된 코드
```python
# 삭제됨
FOLLOW_UP_KEYWORDS = ["이중", "이 중", ...]
def is_follow_up_query(message: str) -> bool:
    ...
```

#### Intent 기반 필터 병합
```python
query_intent = query_plan.get("query_intent", "new_query")

if query_intent == "refine_previous":
    if request.conversation_history:
        previous_plan = get_previous_query_plan(request.conversation_history)
        if previous_plan:
            query_plan = merge_filters(previous_plan, query_plan)
```

## Test Results

| 테스트 | 입력 | 기대 | 결과 |
|--------|------|------|------|
| 첫 질문 | "최근 결제 30건" | new_query | ✅ |
| 키워드 있는 필터링 | "이중 DONE 상태만" | refine_previous | ✅ |
| 연속 필터링 | "mer_001 가맹점 건만" | refine_previous + 필터 병합 | ✅ |
| 다른 엔티티 | "환불 내역 보여줘" | new_query | ✅ |

## Files Modified
- `services/ai-orchestrator/app/services/query_planner.py`
  - Line 45-48: QueryIntent enum 추가
  - Line 95-99: QueryPlan에 query_intent 필드 추가
  - Line 458-490: 시스템 프롬프트에 의도 분류 지시사항 추가
  - Line 638: _convert_to_dict()에서 query_intent 처리

- `services/ai-orchestrator/app/api/v1/chat.py`
  - Line 75-81: 키워드 기반 코드 제거
  - Line 211-224: intent 기반 필터 병합 로직 구현

## Status
✅ **COMPLETED** - 2026-01-11
