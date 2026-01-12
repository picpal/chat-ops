# Issue: Operator Validation Error

## Date
2026-01-11

## Problem Description
LLM이 QueryPlan 생성 시 `>=`, `<` 같은 기호를 사용하여 Pydantic 검증 오류 발생

## Symptoms
로그에서 발견된 오류:
```
2026-01-11 00:56:16,749 - ERROR - Failed to generate QueryPlan: 1 validation error for QueryPlan
filters.0.operator
  Input should be 'eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'like' or 'between'
  [type=enum, input_value='>=', input_type=str]
```

## Root Cause Analysis

### 원인 1: 프롬프트 기호 혼동
- 프롬프트에 `gte: 이상 (>=)` 형식으로 기호가 포함되어 있어 LLM이 기호를 직접 사용하는 경우 발생
- 위치: `query_planner.py` 라인 424-434

```markdown
## 필터 연산자
- **gte**: 이상 (>=)   ← LLM이 (>=)를 직접 사용
```

### 원인 2: 자동 정규화 부재
- 잘못된 operator를 올바른 enum 값으로 변환하는 로직이 없음
- LangChain의 `with_structured_output`이 enum을 100% 강제하지 못하는 경우 있음

### 결과
Pydantic 검증 실패 → 예외 처리 → `_create_fallback_plan()` 호출 → clarification 반환

## Current Safeguards

| 레이어 | 검증 로직 | 상태 |
|--------|----------|------|
| Python Pydantic | `FilterOperator` enum | ✅ 정확함 |
| Chat API | exception 처리 → clarification | ✅ 있음 |
| Core API (Java) | `VALID_OPERATORS` Set 검증 | ✅ 있음 |
| Fallback | `_create_fallback_plan()` | ✅ 있음 |

## Proposed Solution

### Fix 1: Operator 자동 정규화 함수 추가

**파일**: `services/ai-orchestrator/app/services/query_planner.py`

```python
OPERATOR_ALIASES = {
    ">=": "gte",
    ">": "gt",
    "<=": "lte",
    "<": "lt",
    "=": "eq",
    "==": "eq",
    "!=": "ne",
    "<>": "ne",
    "LIKE": "like",
    "IN": "in",
    "BETWEEN": "between",
}

def normalize_operator(operator: str) -> str:
    """잘못된 operator를 정규화"""
    return OPERATOR_ALIASES.get(operator, operator.lower())
```

LLM 응답 파싱 후, Pydantic 검증 전에 적용

### Fix 2: 프롬프트 개선

**파일**: `services/ai-orchestrator/app/services/query_planner.py` (라인 424-434)

**Before**:
```markdown
- **gte**: 이상 (>=)
```

**After**:
```markdown
- **gte**: 이상 (예: amount gte 1000)

**주의**: 반드시 문자열 코드(eq, gte 등)를 사용하세요. 기호(>=, < 등)는 사용하지 마세요.
```

## Files to Modify
- `services/ai-orchestrator/app/services/query_planner.py`
  - operator 정규화 함수 추가
  - LLM 응답 파싱 후 정규화 적용
  - 프롬프트 기호 표현 수정 및 주의사항 추가
  - 정규화 발생 시 warning 로깅

## Verification Plan
1. AI Orchestrator 재시작
2. 테스트 요청: "최근 결제 30건 보여줘"
3. 로그 확인: 정규화 없이 정상 처리 확인
4. 의도적 테스트: LLM이 `>=` 생성 시 자동 정규화 동작 확인

## Status
✅ **RESOLVED** - 2026-01-11

### 적용된 수정사항
1. `normalize_operator()` 함수 추가 (라인 39-48)
2. `_convert_to_dict()`에서 operator 정규화 적용 (라인 676-678)
3. 프롬프트 개선: 기호 제거, 테이블 형식 예시 추가, 경고 문구 추가 (라인 455-469)
