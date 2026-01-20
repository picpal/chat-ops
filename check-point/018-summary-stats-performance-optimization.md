# Check-point 018: Summary Stats 속도 최적화

## 작업 일자
2026-01-20

## 작업 목표
summaryStats 기능 구현 과정에서 발생한 LLM 응답 시간 증가 문제 해결

---

## 1. 문제 상황

### 증상
- summaryStatsTemplate 가이드를 LLM 프롬프트에 추가 후 응답 시간 급증
- **기존 응답 시간**: 약 3.4초
- **변경 후 응답 시간**: 약 6.8초 (2배 증가)

### 원인
- **입력 토큰 증가**: 차트별 상세 예시(약 50줄)가 프롬프트에 추가됨
- **출력 토큰 증가**: LLM이 summaryStatsTemplate 배열을 직접 생성해야 함

### 프롬프트에 추가했던 가이드 (문제 발생 원인)
```
## summaryStatsTemplate 생성 가이드
chartType별로 적절한 summaryStatsTemplate 배열을 생성하세요.

### chartType: "pie"
[차트 유형별 상세 예시 약 50줄...]
```

---

## 2. 해결 방법

### 접근 방식
LLM이 summaryStatsTemplate을 생성하지 않도록 변경하고, 백엔드에서 규칙 기반으로 자동 생성

### 변경 내용

#### Before (느림)
```
LLM 생성 항목:
- SQL
- chartType
- insightTemplate
- summaryStatsTemplate ← 제거
```

#### After (빠름)
```
LLM 생성 항목:
- SQL
- chartType
- insightTemplate

백엔드 자동 생성:
- summaryStats (규칙 기반)
```

### 핵심 코드: `_generate_rule_based_stats()`
```python
def _generate_rule_based_stats(self, chart_type: str, data: list[dict]) -> list[dict]:
    """차트 타입과 데이터를 기반으로 summaryStats 자동 생성"""

    if chart_type == "pie":
        # 상위 항목, 총합, 개수 통계
        return self._generate_pie_stats(data)

    elif chart_type == "bar":
        # 최대/최소값, 평균 통계
        return self._generate_bar_stats(data)

    elif chart_type in ("line", "area"):
        # 추세, 최대/최소, 변화율 통계
        return self._generate_trend_stats(data)

    # ... 기타 차트 타입
```

---

## 3. 최종 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                      LLM (gpt-4o)                       │
│  생성: SQL, chartType, insightTemplate                  │
│  생성하지 않음: summaryStatsTemplate                     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              AI Orchestrator (Python)                   │
│  1. LLM 응답 파싱                                        │
│  2. Core API 호출하여 데이터 조회                         │
│  3. _generate_rule_based_stats() 호출                   │
│  4. RenderSpec 조립                                      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    UI (React)                           │
│  summaryStats 렌더링                                     │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 성능 비교

| 항목 | Before | After | 개선율 |
|------|--------|-------|--------|
| 응답 시간 | ~6.8초 | ~3.4초 | 50% 감소 |
| 프롬프트 길이 | +50줄 | 기존 유지 | - |
| LLM 출력 토큰 | 증가 | 기존 유지 | - |

---

## 5. 교훈

### LLM 프롬프트 설계 원칙
1. **최소 필수 정보만 포함**: 예시가 많을수록 응답 시간 증가
2. **규칙 기반 가능한 작업은 백엔드로 이동**: LLM은 창의적/복잡한 판단에 집중
3. **출력 토큰 최소화**: JSON 배열 생성은 비용과 시간 모두 증가

### 트레이드오프
- **장점**: 빠른 응답, 일관된 결과, 비용 절감
- **단점**: 커스터마이징 유연성 감소 (대부분의 케이스에서는 문제 없음)

---

## 6. 관련 파일

- `services/ai-orchestrator/app/services/sql_render_composer.py`
  - `_generate_rule_based_stats()` 함수
- `services/ai-orchestrator/app/services/text_to_sql.py`
  - LLM 프롬프트 (summaryStatsTemplate 제거됨)

---

## 7. 향후 개선 가능 사항

1. **캐싱**: 동일 쿼리에 대한 summaryStats 캐싱
2. **차트별 통계 확장**: 더 다양한 차트 타입 지원
3. **사용자 설정**: 원하는 통계 항목 선택 기능 (필요시)
