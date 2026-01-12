# Clarification 프롬프트 엔지니어링 한계와 대응 전략

**작성일**: 2026-01-12
**관련 작업**: Clarification 트리거 조건 개선 (프롬프트 엔지니어링)

---

## 1. 현재 상황

### 구현한 개선사항
1. **컨텍스트 강화** (`chat.py` - `build_conversation_context()`)
   - 다중 결과 현황 명시 섹션 추가
   - ⚠️ 이모지로 다중 결과 상황 강조
   - 결과별 entity, 건수, 필터 조건 표시

2. **Few-shot 예시** (`query_planner.py`)
   - 5개의 구체적 판단 예시 추가
   - Chain of Thought (판단 이유 포함)
   - 판단 체크리스트 제공

### 테스트 결과
| 시나리오 | 입력 | 기대 결과 | 실제 결과 |
|----------|------|----------|----------|
| 참조 없음 + 다중 결과 | "합산해줘" | Clarification 표시 | ❌ 바로 집계 |
| 명확한 참조 | "이중에 합산" | 바로 집계 | ✅ 바로 집계 |

---

## 2. 문제점 분석

### 핵심 문제: LLM이 프롬프트 지침을 따르지 않음

프롬프트에 **정확한 예시**가 있음에도 불구하고:
```markdown
예시 3: 참조 없음 + 같은 entity 다른 조건 → true
세션 결과: [Payment 30건], [Payment 도서 7건]
사용자: "합산해줘"
→ needs_result_clarification: **true**
```

실제 LLM 판단:
```
needs_result_clarification: false (직전 결과로 자동 집계)
```

### 원인 추정

**1. 기본값 편향 (Default Value Bias)**
- 프롬프트에 "기본값은 false"라는 문구가 있음
- LLM이 불확실할 때 기본값으로 회귀하는 경향

**2. 예시 우선순위 문제**
- Few-shot 예시 중 false 케이스가 먼저 나옴 (예시 1, 4, 5)
- true 케이스 (예시 2, 3)가 상대적으로 덜 강조됨

**3. 컨텍스트 길이 문제**
- 프롬프트가 길어지면 LLM이 중요한 부분을 놓칠 수 있음
- 판단 체크리스트가 예시보다 뒤에 위치

**4. 모델의 보수적 경향**
- gpt-4o-mini가 비용 효율적이지만 복잡한 판단에서 보수적
- 명시적으로 "true로 해야 한다"는 강한 지시가 필요할 수 있음

---

## 3. 고민거리

### 3.1 프롬프트 엔지니어링의 한계

**질문**: 프롬프트만으로 LLM의 판단을 100% 제어할 수 있는가?

- Claude Code 같은 고품질 도구도 내부적으로 많은 휴리스틱과 규칙을 사용
- 프롬프트 엔지니어링만으로는 엣지 케이스를 모두 커버하기 어려움
- **결론**: 프롬프트 + 규칙 기반 백업이 현실적인 접근

### 3.2 휴리스틱의 범위

**질문**: 휴리스틱을 어디까지 적용해야 하는가?

**Option A: 최소한의 휴리스틱**
```python
# 아주 명백한 케이스만
if "합산" in msg and "이중" not in msg and len(results) > 1:
    force_clarification = True
```
- 장점: 간단, 예측 가능
- 단점: 커버리지 제한적

**Option B: 광범위한 휴리스틱**
```python
# 모든 집계 키워드 + 참조 표현 체크
ambiguous_keywords = ["합산", "합계", "총액", "평균", "개수", "몇 건", ...]
reference_keywords = ["이중", "여기서", "직전", "방금", "위", ...]
```
- 장점: 커버리지 높음
- 단점: 키워드 유지보수, 오탐 가능성

**Option C: LLM 판단 신뢰 + 사용자 피드백**
```python
# LLM 판단 그대로 사용, 사용자가 잘못되면 "다시" 요청
# UI에 "다른 결과로 집계" 버튼 제공
```
- 장점: 자연스러운 대화 흐름
- 단점: 사용자 경험 저하 가능

### 3.3 기본 동작의 선택

**질문**: 모호한 상황에서 기본 동작은?

| 선택지 | 장점 | 단점 |
|--------|------|------|
| 직전 결과 자동 사용 | 빠른 응답, 대부분 정답 | 사용자 의도 오해 가능 |
| 항상 Clarification | 정확한 의도 파악 | UX 저하, 대화 길어짐 |
| 휴리스틱 기반 판단 | 균형잡힌 접근 | 구현/유지보수 복잡 |

**현재 선택**: 직전 결과 자동 사용 (LLM 기본값)
**고민**: 집계/필터 같은 비가역적 작업은 Clarification이 나을 수 있음

---

## 4. 다음 단계: 프롬프트 + 휴리스틱 병행

### 4.1 프롬프트 추가 강화

**부정 예시 (실패 사례) 추가**:
```markdown
### ❌ 잘못된 판단 사례 - 절대 피할 것!

세션 결과: [Payment 30건], [Payment 도서 7건]
사용자: "합산해줘"

❌ 잘못: needs_result_clarification=false
  (이유: 직전 결과로 가정 - 틀림!)

✅ 정답: needs_result_clarification=**true**
  (이유: 30건? 7건? 참조 표현이 없어서 불명확!)
```

**참조 표현 없음 강조**:
```markdown
⚠️ 중요: 참조 표현이 없으면 무조건 모호함으로 간주!

참조 표현 없음 = "합산해줘", "총액", "평균" (단독 사용)
→ 다중 결과 있으면 needs_result_clarification=**true**
```

### 4.2 휴리스틱 백업 로직

```python
# chat.py에 추가
def should_force_clarification(user_message: str, result_count: int) -> bool:
    """LLM 판단과 별개로 명백한 모호 케이스 감지"""
    if result_count <= 1:
        return False

    msg_lower = user_message.lower()

    # 집계/필터 의도 키워드
    ambiguous_patterns = ["합산", "합계", "총액", "평균", "개수", "몇 건"]

    # 명확한 참조 표현
    reference_patterns = ["이중", "여기서", "직전", "방금", "위 결과", "조회된"]

    has_ambiguous = any(p in msg_lower for p in ambiguous_patterns)
    has_reference = any(p in msg_lower for p in reference_patterns)

    # 집계 의도 있고 + 참조 표현 없으면 → clarification 필요
    return has_ambiguous and not has_reference
```

---

## 5. 장기적 고민

### 5.1 LLM 모델 선택
- gpt-4o-mini vs gpt-4o: 비용 vs 정확도 트레이드오프
- 복잡한 판단이 필요한 부분만 상위 모델 사용?

### 5.2 사용자 피드백 루프
- Clarification이 불필요하게 뜬 경우 사용자 피드백 수집
- 피드백 기반으로 휴리스틱 튜닝

### 5.3 테스트 자동화
- Clarification 판단 정확도 측정 테스트 스위트 구축
- 회귀 방지를 위한 CI 통합

---

## 6. 참고 파일

| 파일 | 역할 |
|------|------|
| `chat.py:49-126` | `build_conversation_context()` - 컨텍스트 생성 |
| `chat.py:401-446` | Clarification 처리 로직 |
| `query_planner.py:612-658` | Few-shot 예시 및 판단 기준 |
| `ClarificationRenderer.tsx` | UI 컴포넌트 |

---

## 7. 결론

**프롬프트 엔지니어링만으로는 한계가 있다.**

- Few-shot 예시, Chain of Thought, 체크리스트 등을 적용해도 LLM은 100% 지침을 따르지 않음
- 특히 "기본값"이 명시된 경우 LLM이 그쪽으로 편향됨
- **프롬프트 + 휴리스틱 병행**이 현실적인 해결책

**다음 액션**:
1. 프롬프트에 부정 예시 추가 (더 강한 경고)
2. `should_force_clarification()` 휴리스틱 함수 추가
3. 동일 시나리오로 재테스트
