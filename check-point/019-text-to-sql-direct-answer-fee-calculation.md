# Check-point 019: Text-to-SQL 모드 수수료 계산 버그 수정

## 작업 일자
2026-01-20

## 작업 목표
Text-to-SQL 모드에서 이전 집계 결과 기반 산술 연산(수수료, VAT, 비율 계산 등) 요청 시 잘못된 SQL 재실행 버그 수정

---

## 1. 문제 상황

### 증상
**시나리오:**
1. Q1: "최근 3개월 mer_001 가맹점의 도서 관련 결제 합계" → 결과: ₩14,563,862
2. Q2: "결제 합산 금액에서 0.6% 수수료는 얼마죠?"

**예상 동작:**
- DB 조회 없이 직접 계산: 14,563,862 × 0.6% = ₩87,383

**실제 동작 (버그):**
- 새 SQL 실행 → ₩86,862 반환
- **문제**: "상품명: 도서 포함" 필터 조건이 누락된 SQL 생성

### 근본 원인
Text-to-SQL 모드에서 `direct_answer` intent 처리 로직이 없음
- QueryPlan 모드에는 산술 연산 감지 기능 존재
- Text-to-SQL 모드에서는 모든 요청을 SQL 생성으로 처리

### 영향 범위
- 수수료 계산 요청
- VAT/부가세 계산 요청
- 비율/증감률 계산 요청
- 기타 산술 연산(나누기, 곱하기, 더하기 등)

---

## 2. 해결 방법

### 접근 방식
이전 대화에서 집계 결과를 추출하고, 산술 연산 요청을 감지하여 DB 조회 없이 LLM을 통해 직접 계산

### 변경 흐름

#### Before (버그)
```
사용자 메시지 수신
    ↓
Text-to-SQL 프롬프트 생성
    ↓
LLM이 SQL 생성
    ↓
SQL 실행 (컨텍스트 누락으로 잘못된 결과)
```

#### After (수정)
```
사용자 메시지 수신
    ↓
이전 대화에서 집계 결과 추출
    ↓
산술 연산 요청 감지
    ↓
[감지됨] → LLM 직접 계산 → 결과 반환
[감지 안됨] → 기존 SQL 생성 로직 실행
```

---

## 3. 구현 상세

### 3.1 산술 연산 패턴 정의
**파일**: `app/constants/reference_patterns.py`

```python
ARITHMETIC_REQUEST_PATTERNS = [
    # 수수료/비율
    r'\d+\.?\d*%\s*(수수료|fee)',
    r'(수수료|fee)\s*\d+\.?\d*%',
    r'수수료.*얼마',
    r'fee.*how much',

    # VAT/세금
    r'vat\s*\d+\.?\d*%',
    r'부가세\s*\d+\.?\d*%',
    r'세금.*적용',

    # 기본 산술
    r'(\d+\.?\d*)\s*(으로|로)\s*나눠',
    r'(\d+\.?\d*)배',
    r'(\d+\.?\d*)를?\s*더해',

    # ... 총 19개 패턴
]
```

### 3.2 금액 추출 로직
**파일**: `app/services/conversation_context.py`

```python
def extract_aggregation_value(history: list[dict]) -> Optional[float]:
    """이전 대화에서 집계 결과 금액 추출"""

    # 우선순위 1: 괄호 안 전체 금액
    # 예: "(14,563,862원)" → 14563862
    pattern1 = r'\(([₩$€£¥]?\s*[\d,]+(?:\.\d+)?)\s*[원달러유로파운드엔]?\)'

    # 우선순위 2: 억/만 접미사
    # 예: "1,456만원" → 14560000
    pattern2 = r'([₩$€£¥]?\s*[\d,]+(?:\.\d+)?)\s*(억|만)\s*[원달러유로파운드엔]?'

    # 우선순위 3: M/K 접미사
    # 예: "$2.88M" → 2880000
    pattern3 = r'([₩$€£¥]?\s*[\d,]+(?:\.\d+)?)\s*([MK])'

    # 우선순위 4: 일반 금액
    # 예: "₩14,563,862" → 14563862
    pattern4 = r'([₩$€£¥]\s*[\d,]+(?:\.\d+)?|\d[\d,]*(?:\.\d+)?)\s*[원달러유로파운드엔]?'
```

### 3.3 산술 연산 감지
**파일**: `app/services/conversation_context.py`

```python
def is_arithmetic_request(message: str) -> bool:
    """산술 연산 요청인지 감지"""
    message_lower = message.lower()

    for pattern in ARITHMETIC_REQUEST_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return True

    return False
```

### 3.4 직접 계산 로직
**파일**: `app/api/v1/chat.py`

```python
async def _perform_direct_calculation(
    user_message: str,
    aggregation_value: float,
    history: list[dict]
) -> str:
    """LLM을 통해 산술 연산 직접 수행"""

    prompt = f"""
이전 대화에서 집계된 금액: {aggregation_value:,.0f}원

사용자 요청: "{user_message}"

위 집계 금액을 기반으로 사용자의 요청을 처리하세요.
- 계산 과정을 명확하게 설명
- 최종 결과를 숫자와 함께 제시
"""

    response = await llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o",
        temperature=0
    )

    return response
```

### 3.5 메인 로직 통합
**파일**: `app/api/v1/chat.py` - `handle_text_to_sql()` 함수

```python
async def handle_text_to_sql(
    user_message: str,
    conversation_history: list[dict],
    # ...
) -> ChatResponse:
    """Text-to-SQL 모드 핸들러"""

    # 1. 이전 대화에서 집계 결과 추출
    aggregation_value = extract_aggregation_value(conversation_history)

    # 2. 산술 연산 요청 감지
    if aggregation_value and is_arithmetic_request(user_message):
        # 3. 직접 계산
        answer = await _perform_direct_calculation(
            user_message,
            aggregation_value,
            conversation_history
        )

        return ChatResponse(
            answer=answer,
            renderSpec=None,
            queryToken=None,
            intent="direct_answer"
        )

    # 기존 SQL 생성 로직...
```

---

## 4. 테스트 결과

### 새 테스트 케이스
**파일**: `tests/test_text_to_sql_direct_answer.py`

```python
class TestDirectAnswerIntegration:
    """산술 연산 직접 계산 통합 테스트"""

    def test_fee_calculation_after_aggregate(self):
        """시나리오: 집계 → 수수료 계산"""
        # Q1: 결제 합계 조회
        # Q2: 수수료 계산 요청
        # 검증: SQL 재실행 없이 직접 계산
```

**테스트 항목 (20개):**
- 기본 수수료 계산: 6개
- VAT/부가세 계산: 4개
- 기타 산술 연산: 4개
- 금액 추출 우선순위: 4개
- 엣지 케이스: 2개

**결과:**
- 새 테스트: 20/20 통과 ✅
- 관련 기존 테스트: 91/91 통과 ✅

---

## 5. 주요 패턴 정리

### 산술 연산 요청 패턴

| 카테고리 | 예시 |
|---------|------|
| 수수료/비율 | "0.6% 수수료", "수수료 0.6%", "수수료 얼마야?" |
| VAT/세금 | "VAT 10%", "부가세 포함", "세금 적용" |
| 기본 산술 | "1000으로 나눠", "2배", "100을 더해" |
| 증감/비율 | "20% 증가", "50% 감소", "비율 계산" |

### 금액 추출 우선순위

| 우선순위 | 패턴 | 예시 | 결과 |
|---------|------|------|------|
| 1 | 괄호 안 전체 금액 | `(14,563,862원)` | 14563862 |
| 2 | 억/만 접미사 | `1,456만원` | 14560000 |
| 3 | M/K 접미사 | `$2.88M` | 2880000 |
| 4 | 일반 금액 | `₩14,563,862` | 14563862 |

---

## 6. 성능 영향

| 항목 | Before (버그) | After (수정) |
|------|--------------|--------------|
| DB 쿼리 | 불필요한 SQL 실행 | 쿼리 없음 |
| 응답 시간 | ~3초 (SQL 실행) | ~1초 (LLM 계산) |
| 결과 정확도 | 낮음 (컨텍스트 누락) | 높음 (정확한 계산) |
| 사용자 경험 | 혼란 | 명확 |

---

## 7. 교훈

### 대화형 AI의 컨텍스트 관리
1. **이전 결과 재사용**: 모든 요청을 새 쿼리로 처리하지 말 것
2. **Intent 분류 중요성**: SQL 생성 vs 직접 계산 vs 단순 질의 구분 필수
3. **패턴 매칭 + LLM 조합**: 규칙 기반 감지 → LLM 계산으로 정확도와 유연성 확보

### 버그 예방 체크리스트
- [ ] QueryPlan 모드와 Text-to-SQL 모드의 기능 패리티 확인
- [ ] 이전 대화 컨텍스트 활용 여부 검증
- [ ] 불필요한 DB 쿼리 실행 여부 모니터링

---

## 8. 관련 파일

### 신규 파일
- `app/constants/reference_patterns.py`
  - `ARITHMETIC_REQUEST_PATTERNS` 상수 정의

### 수정 파일
- `app/services/conversation_context.py`
  - `extract_aggregation_value()` 함수
  - `is_arithmetic_request()` 함수
  - `_extract_amount_from_text()` 함수

- `app/api/v1/chat.py`
  - `handle_text_to_sql()` 함수 시작 부분에 감지 로직 추가
  - `_perform_direct_calculation()` 함수 추가

### 테스트 파일
- `tests/test_text_to_sql_direct_answer.py` (신규)
  - 20개 단위 테스트

---

## 9. 향후 개선 가능 사항

1. **패턴 확장**:
   - 다국어 산술 표현 지원 (영어, 한국어 외)
   - 복잡한 복합 연산 (예: "10% 할인 후 VAT 10% 적용")

2. **정확도 향상**:
   - 금액 추출 시 통화 단위 자동 감지
   - 소수점 자릿수 자동 조정

3. **사용자 피드백**:
   - "계산 과정을 보여주세요" 요청 시 상세 단계 출력
   - 잘못된 계산 시 사용자가 직접 수정 가능하도록

4. **모니터링**:
   - 산술 연산 요청 빈도 추적
   - 감지 실패 케이스 로깅 및 패턴 개선
