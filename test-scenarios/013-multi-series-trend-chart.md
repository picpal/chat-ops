# Test Scenario 013: 멀티 시리즈 추이 차트

**작성일:** 2026-01-21
**기능:** 가맹점별/상태별 추이를 멀티 시리즈 차트로 표시
**상태:** 테스트 대기

---

## 1. 테스트 목적

다중 groupBy(카테고리+시계열)일 때 추이 차트가 멀티 시리즈로 올바르게 생성되는지 검증합니다.

### 배경
- 기존 문제: X축에 가맹점이 나열되어 추이 파악 불가
- 해결: 시계열 필드를 X축, 카테고리 필드를 시리즈로 분리

---

## 2. 사전 조건

- [ ] AI Orchestrator: Docker container 실행 중 (최신 코드 반영)
- [ ] Core API: http://localhost:8080 실행 중
- [ ] PostgreSQL: payments 테이블 데이터 존재

---

## 3. 테스트 시나리오

### TC-013-1: 가맹점별 월별 결제금액 추이

**입력:**
```
가맹점별 결제금액 추이 그래프 (최근 3개월)
```

**기대 결과:**
- renderSpec.type: "chart"
- renderSpec.chart.chartType: "line"
- renderSpec.chart.xAxis.dataKey: "month" (시계열)
- renderSpec.chart.series: 가맹점별 시리즈 배열
- renderSpec.metadata.isMultiSeries: true

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "가맹점별 결제금액 추이 그래프 (최근 3개월)"}' | jq '{
    type: .renderSpec.type,
    chartType: .renderSpec.chart.chartType,
    xAxisKey: .renderSpec.chart.xAxis.dataKey,
    seriesCount: (.renderSpec.chart.series | length),
    isMultiSeries: .renderSpec.metadata.isMultiSeries
  }'
```

---

### TC-013-2: 상태별 월별 결제 추이

**입력:**
```
상태별 월별 결제 건수 추이 차트
```

**기대 결과:**
- xAxis.dataKey: "month"
- series: 상태별 시리즈 (DONE, CANCELED 등)

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "상태별 월별 결제 건수 추이 차트"}' | jq '{
    xAxisKey: .renderSpec.chart.xAxis.dataKey,
    seriesKeys: [.renderSpec.chart.series[].dataKey]
  }'
```

---

### TC-013-3: 단일 groupBy는 멀티 시리즈 아님

**입력:**
```
월별 결제 추이 그래프
```

**기대 결과:**
- renderSpec.chart.series: 없거나 단일 요소
- renderSpec.metadata.isMultiSeries: false 또는 없음

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "월별 결제 추이 그래프"}' | jq '{
    xAxisKey: .renderSpec.chart.xAxis.dataKey,
    seriesCount: (.renderSpec.chart.series // [] | length),
    isMultiSeries: .renderSpec.metadata.isMultiSeries
  }'
```

---

### TC-013-4: 추이 키워드 없으면 멀티 시리즈 아님

**입력:**
```
가맹점별 월별 결제 금액 그래프
```

**기대 결과:**
- renderSpec.metadata.isMultiSeries: false
- 기본 bar chart 또는 grouped bar chart

**검증 방법:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "가맹점별 월별 결제 금액 그래프"}' | jq '{
    type: .renderSpec.type,
    chartType: .renderSpec.chart.chartType,
    isMultiSeries: .renderSpec.metadata.isMultiSeries
  }'
```

---

### TC-013-5: 시리즈 개수 제한 (상위 5개 + 기타)

**입력:**
```
가맹점별 결제금액 추이 그래프 (모든 가맹점)
```

**기대 결과:**
- 가맹점이 5개 초과일 경우 상위 5개 + "기타"로 그룹화
- 시리즈 최대 6개

**검증 포인트:**
- series 배열 길이가 6 이하
- 마지막 시리즈가 "기타"인지 확인

---

## 4. 검증 포인트

| 시나리오 | 검증 필드 | 기대값 |
|---------|----------|--------|
| TC-013-1 | xAxis.dataKey | month (시계열) |
| TC-013-1 | series | 가맹점별 배열 |
| TC-013-1 | isMultiSeries | true |
| TC-013-2 | series | 상태별 배열 |
| TC-013-3 | isMultiSeries | false/없음 |
| TC-013-4 | isMultiSeries | false |
| TC-013-5 | series.length | <= 6 |

---

## 5. 데이터 피벗 확인

멀티 시리즈 차트에서 데이터가 올바르게 피벗되었는지 확인:

**원본 데이터:**
```json
[
  {"merchantId": "M001", "month": "2024-01", "totalAmount": 1000000},
  {"merchantId": "M002", "month": "2024-01", "totalAmount": 800000},
  {"merchantId": "M001", "month": "2024-02", "totalAmount": 1200000},
  {"merchantId": "M002", "month": "2024-02", "totalAmount": 900000}
]
```

**피벗 후 (renderSpec.data.rows):**
```json
[
  {"month": "2024-01", "M001": 1000000, "M002": 800000},
  {"month": "2024-02", "M001": 1200000, "M002": 900000}
]
```

---

## 6. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `render_composer.py` | `_identify_multi_series_axis()` | 멀티 시리즈 축 식별 |
| `render_composer.py` | `_pivot_data_for_multi_series()` | 데이터 피벗 |
| `render_composer.py` | `_compose_chart_spec()` | 차트 스펙 생성 |
| `sql_render_composer.py` | 동일 함수들 | Text-to-SQL 모드 지원 |

---

## 7. UI 확인 포인트

차트가 UI에서 올바르게 렌더링되는지 확인:

1. **X축**: 시간(월) 순서로 표시
2. **시리즈**: 각 가맹점/상태가 별도 선으로 표시
3. **범례**: 각 시리즈 이름(가맹점ID, 상태명)이 표시
4. **툴팁**: 호버 시 해당 시점의 모든 시리즈 값 표시

---

## 8. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-21 | - | 대기 | 시나리오 작성 완료 |
