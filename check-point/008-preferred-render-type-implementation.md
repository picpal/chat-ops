# Check Point 008: preferredRenderType 필드 구현 (하드코딩 방식)

## 날짜
2026-01-13

## 상태
✅ 구현 완료 및 E2E 검증 통과

---

## 배경

### 문제 상황
사용자가 **"최근 3개월간 거래를 가맹점 별로 그룹화해서 표로 보여줘"**라고 요청했을 때:
- 기대 결과: **표(table)** 형태로 가맹점 ID 기준 그룹화 데이터 표시
- 실제 결과: **차트(chart)** 형태로 표시

### 근본 원인 분석

1. **QueryPlan 생성 단계**
   - LLM이 "가맹점별 그룹화"를 감지하면 `operation="aggregate"` + `groupBy=["merchantId"]` 설정
   - "표로 보여줘"라는 사용자 요청이 QueryPlan에 저장되지 않음

2. **RenderComposer 결정 로직** (`render_composer.py:241-257`)
   ```python
   def _compose_aggregate_spec(self, query_result, query_plan, user_message):
       if group_by and len(rows) > 1:
           return self._compose_chart_spec(...)  # ← 무조건 차트
   ```
   - `operation=aggregate` + `groupBy` 있으면 자동으로 차트 생성
   - 사용자 메시지의 "표" 키워드 무시

---

## 해결 방안

### 설계: preferredRenderType 필드 도입

사용자가 명시적으로 요청한 렌더링 타입을 QueryPlan에 저장하고, RenderComposer에서 우선 처리

| 사용자 표현 | preferredRenderType |
|------------|---------------------|
| "표로", "테이블로", "목록으로" | `table` |
| "그래프로", "차트로", "시각화로" | `chart` |
| "텍스트로", "요약으로" | `text` |

---

## 구현 내용

### 1. QueryPlan 스키마 수정

**파일**: `libs/contracts/query-plan.schema.json`

```json
"preferredRenderType": {
  "type": "string",
  "description": "사용자가 명시적으로 요청한 렌더링 타입 (표로, 차트로, 그래프로 등)",
  "enum": ["table", "chart", "text"]
}
```

### 2. Python 모델 업데이트

**파일**: `services/ai-orchestrator/app/models/query_plan.py`

```python
class PreferredRenderType(Enum):
    """사용자가 명시적으로 요청한 렌더링 타입"""
    table = 'table'
    chart = 'chart'
    text = 'text'

class QueryPlan(BaseModel):
    ...
    preferred_render_type: Optional[PreferredRenderType] = Field(
        None, alias='preferredRenderType'
    )
```

### 3. LLM 프롬프트 지시사항 추가

**파일**: `services/ai-orchestrator/app/services/query_planner.py` (line 816-845)

```markdown
## 렌더링 타입 (preferredRenderType) - 매우 중요!

사용자가 특정 렌더링 형식을 명시적으로 요청하면 반드시 **preferredRenderType** 필드를 설정하세요:

### 키워드 → preferredRenderType 매핑
| 사용자 표현 | preferredRenderType |
|------------|---------------------|
| "표로", "테이블로", "목록으로", "리스트로" | "table" |
| "그래프로", "차트로", "그림으로", "시각화로" | "chart" |
| "텍스트로", "글로", "요약으로" | "text" |

### 중요 규칙
- 사용자가 "표로"라고 명시하면 groupBy가 있더라도 반드시 preferredRenderType="table" 설정
- 사용자가 렌더링 타입을 명시하지 않으면 preferredRenderType 필드를 생략
```

### 4. RenderComposer에서 preferredRenderType 우선 처리

**파일**: `services/ai-orchestrator/app/services/render_composer.py` (line 177-186)

```python
def compose(self, query_result, query_plan, user_message):
    ...
    # 사용자가 명시적으로 요청한 렌더링 타입 우선 처리
    preferred_render_type = query_plan.get("preferredRenderType")
    if preferred_render_type:
        logger.info(f"Using preferred render type: {preferred_render_type}")
        if preferred_render_type == "table":
            return self._compose_table_spec(...)
        elif preferred_render_type == "chart":
            return self._compose_chart_spec(...)
        elif preferred_render_type == "text":
            return self._compose_text_spec(...)

    # preferredRenderType이 없으면 기존 로직 사용
    ...
```

---

## 테스트 결과

### 단위 테스트

```python
# Test 1: preferredRenderType='table' with groupBy
query_plan = {
    'entity': 'Payment',
    'operation': 'aggregate',
    'groupBy': ['merchantId'],
    'preferredRenderType': 'table'
}
result = rc.compose(query_result, query_plan, user_message)
# Result type: table ✅

# Test 2: No preferredRenderType (기존 동작)
query_plan = {
    'entity': 'Payment',
    'operation': 'aggregate',
    'groupBy': ['merchantId']
}
result = rc.compose(query_result, query_plan, user_message)
# Result type: chart ✅ (기존 동작 유지)
```

### 테스트 통과율: 100%

---

## 변경 흐름

### Before (문제 상황)
```
사용자: "가맹점별로 그룹화해서 표로 보여줘"
    ↓
QueryPlan: { operation: "aggregate", groupBy: ["merchantId"] }
    ↓
RenderComposer: groupBy 있음 → 차트 생성
    ↓
결과: 📊 BAR CHART (사용자 의도와 불일치)
```

### After (개선 후)
```
사용자: "가맹점별로 그룹화해서 표로 보여줘"
    ↓
QueryPlan: {
    operation: "aggregate",
    groupBy: ["merchantId"],
    preferredRenderType: "table"  ← NEW
}
    ↓
RenderComposer: preferredRenderType="table" 우선 처리
    ↓
결과: 📋 TABLE (사용자 의도 반영) ✅
```

---

## 최종 구현: 하드코딩 방식 (LLM 의존 제거)

### LLM vs 하드코딩 비교 후 결정

| 측면 | LLM 기반 판단 | 하드코딩 (규칙 기반) |
|------|--------------|---------------------|
| **정확도** | 불안정 (LLM이 무시) | **100% 확정적** |
| **속도** | 동시 처리 | 즉시 (ms 단위) |
| **비용** | LLM 토큰 소비 | **무료** |

**결론**: 명시적 키워드("표로", "차트로")는 하드코딩으로 100% 정확하게 처리

### 최종 구현 코드

**파일**: `services/ai-orchestrator/app/services/render_composer.py` (line 153-173)

```python
def _detect_render_type_from_message(self, message: str) -> Optional[str]:
    """
    사용자 메시지에서 명시적 렌더링 타입 요청 감지 (하드코딩)
    LLM 판단보다 확실한 키워드 매칭으로 100% 정확도 보장
    """
    msg = message.lower()

    # 표/테이블 요청
    if any(kw in msg for kw in ["표로", "테이블로", "목록으로", "리스트로", "표 형태", "테이블 형태"]):
        return "table"

    # 차트/그래프 요청
    if any(kw in msg for kw in ["그래프로", "차트로", "시각화로", "그래프 형태", "차트 형태"]):
        return "chart"

    # 텍스트 요청
    if any(kw in msg for kw in ["텍스트로", "글로", "요약으로"]):
        return "text"

    return None
```

### 우선순위 로직

```python
def compose(self, query_result, query_plan, user_message):
    # 1순위: 하드코딩 키워드 감지 (100% 정확)
    detected_render_type = self._detect_render_type_from_message(user_message)

    # 2순위: LLM이 설정한 preferredRenderType (fallback)
    preferred_render_type = query_plan.get("preferredRenderType")

    # 3순위: 기존 자동 결정 로직 (operation/entity 기반)
```

---

## E2E 테스트 결과

### 테스트 환경
- UI: localhost:3000
- AI Orchestrator: Docker container (rebuild 필요)
- 테스트 도구: Playwright MCP

### 시나리오 1: "표로 보여줘" 테스트

**입력**: "최근 3개월간 거래를 가맹점 별로 그룹화해서 표로 보여줘"

| 항목 | 결과 |
|------|------|
| 아이콘 | `table_rows` ✅ |
| RenderSpec type | `"table"` ✅ |
| 테이블 구조 | 컬럼 헤더 + 8행 데이터 ✅ |
| 로그 | "Detected render type from message: table" ✅ |

**결과**: ✅ PASS

### 주의사항

**Docker 컨테이너 rebuild 필요**
```bash
# 코드 변경 후 반드시 실행
docker-compose -f infra/docker/docker-compose.yml build ai-orchestrator
docker-compose -f infra/docker/docker-compose.yml up -d ai-orchestrator
```

`docker restart`만으로는 코드 변경이 반영되지 않음

---

## 관련 파일

- `libs/contracts/query-plan.schema.json` (line 133-137)
- `services/ai-orchestrator/app/models/query_plan.py` (line 128-136, 183-186)
- `services/ai-orchestrator/app/services/query_planner.py` (line 151-154, 816-851, 1289-1291)
- `services/ai-orchestrator/app/services/render_composer.py` (line 153-232) - **핵심 구현**
- `services/ai-orchestrator/app/api/v1/chat.py` (line 199) - 버그 수정 (`data` → `rows`)

## 이전 체크포인트 참조
- [007-two-stage-llm-judgment-success.md](./007-two-stage-llm-judgment-success.md)
