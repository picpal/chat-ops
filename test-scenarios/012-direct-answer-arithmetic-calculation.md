# Test Scenario 012: 산술 연산 직접 응답 (수수료/VAT 계산)

**작성일:** 2026-01-20
**기능:** 이전 집계 결과에 대한 수수료, VAT 등 산술 연산 요청 시 DB 조회 없이 직접 계산
**상태:** ⏳ 테스트 대기

---

## 1. 테스트 목적

이전 집계 결과(합계, 평균 등)에 대해 수수료, VAT, 비율 계산을 요청할 때:
- DB 조회 없이 이전 결과를 기반으로 직접 계산
- 필터 조건 누락으로 인한 계산 오류 방지

### 배경
- 기존 문제: "도서 관련 결제 합계 ₩14,563,862" 후 "0.6% 수수료는?" 질문 시 새 SQL 실행하여 필터 누락
- 해결: 산술 연산 패턴 감지 후 이전 집계 결과를 사용하여 LLM 직접 계산

---

## 2. 사전 조건

- [ ] UI: http://localhost:3000 실행 중
- [ ] AI Orchestrator: Docker container 실행 중 (최신 코드 반영)
- [ ] Core API: http://localhost:8080 실행 중
- [ ] PostgreSQL: payments 테이블에 테스트 데이터 존재
- [ ] Text-to-SQL 모드 활성화 (`SQL_ENABLE_TEXT_TO_SQL=true`)

---

## 3. 테스트 시나리오

### TC-012-1: 기본 수수료 계산

**Step 1 - 집계 조회:**
```
최근 3개월 mer_001 가맹점의 도서 관련 결제 합계
```

**기대 결과 1:**
- 집계 결과 표시 (예: 합계: ₩14,477,000)
- `renderSpec.type = "text"`
- `queryResult.isAggregation = true`

**Step 2 - 수수료 계산:**
```
0.6% 수수료는 얼마야?
```

**기대 결과 2:**
- **직접 계산** 실행 (새 SQL 없음)
- 결과: ₩86,862 (14,477,000 × 0.006)
- `renderSpec.metadata.mode = "text_to_sql_direct_answer"`
- 로그: `"Arithmetic request detected, invoking direct calculation"`

**검증 방법:**
1. Docker 로그에서 `"Phase 1: aggregation_result=True, is_arithmetic=True"` 확인
2. 응답의 `queryPlan.mode = "text_to_sql_direct_answer"` 확인
3. 계산 결과가 이전 집계 결과 기준인지 확인

---

### TC-012-2: VAT 포함 계산

**Step 1 - 집계 조회:**
```
이번 달 전체 매출 합계
```

**Step 2 - VAT 계산:**
```
VAT 10% 포함하면 얼마야?
```

**기대 결과:**

| 항목 | 기대값 |
|------|--------|
| 계산 방식 | 직접 계산 (DB 조회 X) |
| 수식 | 매출 합계 × 1.1 |
| mode | text_to_sql_direct_answer |

---

### TC-012-3: 연속 산술 연산 (직전 결과 스킵)

**Step 1 - 집계 조회:**
```
최근 1개월 결제 합계
```
결과: ₩10,000,000

**Step 2 - 첫 번째 수수료:**
```
3% 수수료는?
```
결과: ₩300,000

**Step 3 - 두 번째 수수료 (원본 기준):**
```
원래 금액에서 0.5% 수수료는?
```

**기대 결과:**
- Step 2 결과(300,000)를 스킵하고 Step 1 결과(10,000,000) 기준으로 계산
- 결과: ₩50,000 (10,000,000 × 0.005)
- 로그: `"Skipping direct_answer result at index X"`

---

### TC-012-4: 산술 요청이 아닌 경우 (Negative)

**Step 1 - 집계 조회:**
```
최근 3개월 결제 합계
```

**Step 2 - 새 조회 (산술 아님):**
```
상위 10건 보여줘
```

**기대 결과:**
- 직접 계산 실행 **안함**
- 새 SQL 생성하여 실행
- `is_arithmetic=False` 로그

---

### TC-012-5: 다양한 산술 패턴 인식

| 입력 메시지 | 기대 is_arithmetic |
|-------------|-------------------|
| "0.6% 수수료는 얼마야?" | True |
| "수수료 0.6%는?" | True |
| "VAT 10% 포함하면?" | True |
| "부가세 제외하면 얼마야?" | True |
| "2배 하면?" | True |
| "1000으로 나눠줘" | True |
| "계산해줘" | True |
| "새로 조회해줘" | False |
| "가맹점별로 보여줘" | False |

---

## 4. API 테스트

```bash
# Step 1: 집계 조회
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 3개월 전체 결제 합계"}' | jq '.renderSpec.type, .queryResult.isAggregation'

# Step 2: 수수료 계산 (conversationHistory 포함 필요)
# UI에서 테스트 권장
```

```bash
# 로그 확인
docker logs chatops-ai-orchestrator --tail 50 2>&1 | grep -E "(Phase 1|Arithmetic|direct_answer)"
```

---

## 5. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `chat.py` | `handle_text_to_sql()` L870-900 | Phase 1 산술 요청 감지 |
| `chat.py` | `_perform_direct_calculation()` | LLM 직접 계산 실행 |
| `conversation_context.py` | `extract_aggregation_value()` | 이전 집계 결과 추출 |
| `conversation_context.py` | `is_arithmetic_request()` | 산술 패턴 매칭 |
| `reference_patterns.py` | `ARITHMETIC_REQUEST_PATTERNS` | 산술 연산 패턴 정의 |

---

## 6. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-20 | Claude | ⏳ 대기 | 시나리오 작성 |

---

## 7. 관련 커밋

```
f2ed5c1 feat(ai): add direct calculation for arithmetic requests on aggregations
```
