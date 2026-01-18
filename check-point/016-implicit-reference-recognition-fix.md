# TC-005: 암시적 참조 표현 인식 개선

**작성일**: 2026-01-18
**작성자**: Claude
**상태**: Completed
**테스트 시나리오**: TC-005

## 1. 개요

사용자가 "mer_008 가맹점만"처럼 명시적 참조 키워드("이중", "여기서") 없이 필터를 추가 요청할 때, 이전 WHERE 조건이 유지되지 않는 문제를 해결했습니다.

## 2. 문제 상황

### 증상
```
Step 1: "최근 3개월 결제건 조회"
→ WHERE created_at >= NOW() - INTERVAL '3 months'

Step 2: "mer_008 가맹점만"
→ WHERE merchant_id = 'mer_008'  ❌
   (created_at 조건이 사라짐)
```

### 근본 원인
- `text_to_sql.py`의 `_build_conversation_flow()`에서 이전 QueryPlan을 "참고용"으로만 전달
- LLM이 이전 WHERE 조건을 선택적으로 해석하여 무시
- 프롬프트에 강제성이 부족

## 3. 해결 방법

### 3.1. 프롬프트 강화

**파일**: `services/ai-orchestrator/app/services/text_to_sql.py`
**위치**: `_build_conversation_flow()` 함수 (라인 914-943)

#### 변경 전
```python
system_msg += f"""
[이전 쿼리 참고]
{json.dumps(previous_qp_dict, ensure_ascii=False, indent=2)}

사용자가 '이것도', '이중' 등의 표현을 사용하면 위 조건을 유지하면서 추가 필터를 적용하세요.
"""
```

#### 변경 후
```python
system_msg += f"""
[이전 쿼리 - 필수 유지]
{json.dumps(previous_qp_dict, ensure_ascii=False, indent=2)}

**중요**: 사용자가 암시적으로 이전 결과를 참조하는 경우(예: "가맹점만", "것만" 등),
위 WHERE 조건을 **반드시 포함**하고 추가 조건을 AND로 연결하세요.
절대로 이전 조건을 생략하지 마세요.
"""
```

#### 핵심 변경 사항
1. **"참고"** → **"필수 유지"**로 변경
2. **"유지하면서"** → **"반드시 포함"**으로 강화
3. **"절대로 생략하지 마세요"** 추가 (강한 금지 명령)

### 3.2. 기존 메커니즘 유지

- **암시적 참조 패턴 감지**: `chat.py`의 `detect_reference_expression()`
  ```python
  patterns = [
      r'(가맹점|merchant).{0,10}(만|것만)',
      r'(상태|status).{0,10}(만|것만)',
      ...
  ]
  ```
- 감지 시 `is_refinement=True` 설정하여 Text-to-SQL에 전달

## 4. 테스트 결과

### 4.1. 기본 시나리오 (2단계 체이닝)

```
Step 1: "최근 1개월 결제건 조회"
→ WHERE created_at >= NOW() - INTERVAL '1 months'

Step 2: "mer_008 가맹점만"
→ WHERE created_at >= NOW() - INTERVAL '1 months'
    AND merchant_id = 'mer_008' ✅
```

### 4.2. 3단계 체이닝

```
Step 3: "DONE 상태만"
→ WHERE created_at >= NOW() - INTERVAL '1 months'
    AND merchant_id = 'mer_008'
    AND status = 'DONE' ✅
```

### 4.3. timeRange 변경 시나리오

```
Step 4: "최근 1개월 결제건 조회" (기존 3개월에서 변경)
→ 새 쿼리로 인식, 조건 리셋
   WHERE created_at >= NOW() - INTERVAL '1 month' ✅

Step 5: "이중에 mer_008 가맹점만"
→ WHERE created_at >= NOW() - INTERVAL '1 month'
    AND merchant_id = 'mer_008' ✅
```

## 5. 영향 범위

### 수정된 파일
- `services/ai-orchestrator/app/services/text_to_sql.py`
  - `_build_conversation_flow()` 함수의 프롬프트 로직

### 영향받는 기능
- ✅ 암시적 참조 표현 처리 (예: "가맹점만", "것만")
- ✅ 다단계 WHERE 조건 체이닝
- ✅ 명시적 참조 표현 (예: "이중", "여기서") - 기존 동작 유지

### 영향 없는 기능
- ❌ 새로운 쿼리 시작 (timeRange 변경 등)
- ❌ SELECT 절 변경 (groupBy, aggregation)
- ❌ LIMIT 조정

## 6. 후속 작업 제안

### 6.1. LLM 응답 검증 강화
- `SqlValidator`에서 이전 WHERE 조건 포함 여부 체크
- 누락 시 자동 복구 또는 경고

### 6.2. 다국어 패턴 확장
- 영어 패턴: `r'only\s+(merchant|status)'`
- 현재는 한국어 패턴만 지원

### 6.3. 모니터링
- 프로덕션 로그에서 WHERE 조건 누락 케이스 추적
- `is_refinement=True`인데 이전 조건이 사라지는 경우 알림

## 7. 학습 내용

### 7.1. LLM 프롬프트 설계 원칙
- **"참고"는 선택적, "필수"는 강제적**: 단어 선택이 중요
- **부정 명령어 추가**: "~하지 마세요"가 효과적
- **구체적 예시 제공**: 추상적 지시보다 명확

### 7.2. Text-to-SQL 파이프라인 구조
```
User Input
  ↓
detect_reference_expression() → is_refinement 플래그
  ↓
_build_conversation_flow() → 프롬프트 생성
  ↓
LLM (OpenAI/Anthropic)
  ↓
QueryPlan
```

### 7.3. 대화형 쿼리 체이닝 패턴
- **암시적 참조**: "~만", "것만" → 이전 조건 유지
- **명시적 참조**: "이중", "여기서" → 이전 조건 유지
- **새 쿼리**: timeRange 변경, 다른 테이블 → 조건 리셋

## 8. 참고 자료

- **테스트 시나리오**: `test-scenarios/TC-005-implicit-reference-chaining.md`
- **관련 코드**:
  - `services/ai-orchestrator/app/services/text_to_sql.py` (L914-943)
  - `services/ai-orchestrator/app/api/v1/chat.py` (detect_reference_expression)
- **이전 작업**:
  - TC-004: 명시적 참조 표현 WHERE 체이닝 (`check-point/015-where-chaining-fix.md`)
