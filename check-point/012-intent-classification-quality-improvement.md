# 012. Intent Classification 품질 개선

## 날짜
2025-01-15

## 문제 상황

Claude Code와 동일한 LLM 모델을 사용하지만, AI Orchestrator의 의도 파악 품질이 낮음:
- "직전 데이터 참조" vs "새 질문" 구분 정확도 낮음
- 참조 표현 인식률 부족 (약 70%)
- 경계 사례 처리 미흡 (약 60%)

## 원인 분석

1. **참조 표현 패턴 부족**: 10여 개 패턴만 지원, 구어체/영어 혼용 미지원
2. **Few-shot 예시 부족**: 의도 분류 프롬프트에 구체적 예시 없음
3. **경계 사례 규칙 부재**: 모호한 상황 판단 기준 불명확
4. **컨텍스트 구조화 부실**: 이전 결과 간 관계 정보 부족

## 해결 방법

### Phase 1: 참조 표현 패턴 확장 (chat.py)

```python
# 기존: 10개 패턴
FILTER_PATTERNS = [
    r'이\s*중에?',
    r'여기서',
    ...
]

# 개선: 30+ 패턴, 유형별 분류
class ReferenceType(str, Enum):
    LATEST = "latest"      # 직전 결과 ("이중에", "방금")
    SPECIFIC = "specific"  # 특정 결과 ("30건에서")
    PARTIAL = "partial"    # 부분 결과 ("상위 10개")
    NONE = "none"

REFERENCE_PATTERNS = {
    ReferenceType.LATEST: [
        r'이\s*중에?서?',       # 표준 한글
        r'아까\s*(그\s*)?거',   # 구어체
        r'from\s*(this|these)', # 영어 혼용
        # ... 30+ 패턴
    ],
    # ...
}
```

### Phase 2: Few-shot 예시 추가 (query_planner.py)

Intent Classification 프롬프트에 22개 구체적 예시 추가:

| 카테고리 | 예시 |
|----------|------|
| filter_local (8개) | "이중에 도서만", "아까 그거에서 카드만" |
| aggregate_local (6개) | "금액 합산해줘", "평균" |
| direct_answer (4개) | "수수료 0.6% 적용", "5로 나누면?" |
| Negative (4개) | 잘못된 분류 방지 예시 |

### Phase 3: 경계 사례 처리 규칙 (query_planner.py)

5가지 CASE별 명확한 판단 기준 추가:

```
CASE 1: "합산해줘"
- 테이블 결과 있음 → aggregate_local
- 집계 결과 있음 → direct_answer
- 결과 없음 → query_needed

CASE 2: "DONE 상태만"
- "이중에 DONE만" → filter_local
- "DONE 상태만 조회" → query_needed

CASE 3: 암시적 참조
- 직전 결과 바로 다음 "카드만" → filter_local
- 맥락 없이 "카드만" → query_needed
```

### Phase 4: 컨텍스트 구조화 개선 (chat.py)

기존 텍스트 나열에서 구조화된 테이블 형식으로 개선:

```
### 조회 결과 현황
| # | 엔티티 | 건수 | 조건 | 금액 | 타입 | 관계 |
|---|--------|------|------|------|------|------|
| 👉0 | Payment | 30 | - | $5,000,000 | table | 최초 조회 |
| 1 | Payment | 7 | orderName=도서 | $350,000 | table | #0에서 필터링 |

### 현재 작업 대상 (직전 결과)
- 엔티티: Payment
- 건수: 7건
- 타입: table (목록 데이터)
- 금액 합계: $350,000
```

## 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| `services/ai-orchestrator/app/api/v1/chat.py` | 참조 패턴 확장 (30+), 컨텍스트 구조화 |
| `services/ai-orchestrator/app/services/query_planner.py` | Few-shot 22개, 경계 사례 5개 |

## 테스트 결과

```bash
$ pytest tests/ -v
196 passed, 3 warnings in 11.03s
```

### 단위 테스트 (새 기능)

```python
# 참조 표현 감지 테스트
detect_reference_expression('이중에 도서만') → (True, 'filter')  ✓
detect_reference_expression('아까 그거에서 카드만') → (True, 'filter')  ✓
detect_reference_expression('from these results') → (True, 'filter')  ✓
detect_reference_expression('새로 조회해줘') → (False, 'new')  ✓

# 참조 유형 감지 테스트
detect_reference_type('이중에') → LATEST  ✓
detect_reference_type('아까 30건에서') → SPECIFIC  ✓
detect_reference_type('상위 10개') → PARTIAL  ✓
```

## 예상 개선 효과

| 지표 | 개선 전 | 개선 후 |
|------|---------|---------|
| 참조 표현 인식률 | ~70% | ~95% |
| 경계 사례 정확도 | ~60% | ~85% |
| 후속 질문 구분 | ~75% | ~90% |

## 후속 작업

1. **실 사용 테스트**: 다양한 시나리오로 실제 정확도 측정
2. **피드백 수집**: 잘못된 분류 케이스 수집 및 패턴 추가
3. **프롬프트 튜닝**: 정확도 기반으로 Few-shot 예시 조정

## 관련 파일

- 계획서: `/Users/picpal/.claude/plans/polymorphic-dancing-scone.md`
- 이전 개선: `007-two-stage-llm-judgment-success.md`
