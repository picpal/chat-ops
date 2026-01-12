# Check Point 004: operation vs query_intent 혼동 오류

## 발생일시
2026-01-12

## 증상
"이중 도서 관련 거래만" 질문 시 clarification 요청이 발생
- 이전에는 `filter_local`로 정상 처리되던 케이스
- "어떤 데이터를 조회하시겠습니까?" 메시지 표시

## 원인
LLM이 `operation` 필드와 `query_intent` 필드를 혼동

### 에러 로그
```
ERROR - Failed to generate QueryPlan: 1 validation error for QueryPlan
operation
  Input should be 'list', 'aggregate' or 'search' [type=enum, input_value='filter_local', input_type=str]
```

### 필드 구분
| 필드 | 용도 | 허용 값 |
|------|------|---------|
| `operation` | Core API 작업 유형 | `list`, `aggregate`, `search` |
| `query_intent` | 클라이언트 처리 방식 | `new_query`, `refine_previous`, `filter_local`, `aggregate_local`, `direct_answer` |

### 잘못된 예
```json
{
  "operation": "filter_local",  // ❌ 잘못됨
  "query_intent": "new_query"
}
```

### 올바른 예
```json
{
  "operation": "list",           // ✅ Core API용
  "query_intent": "filter_local" // ✅ 클라이언트 처리용
}
```

## 해결 방법
`query_planner.py` 프롬프트에 두 필드의 차이 명시:

```markdown
## 작업 유형 (operation 필드) - 중요!

**operation 필드는 Core API 작업 유형이며, 다음 3가지만 가능:**
1. **list**: 데이터 목록 조회 (기본값)
2. **aggregate**: 서버에서 집계/통계 (DB에서 집계)
3. **search**: 텍스트 검색 (LIKE 연산)

**주의: filter_local, aggregate_local, direct_answer는 operation이 아닌 query_intent 필드에 설정!**
- operation: "list" | "aggregate" | "search" (Core API용)
- query_intent: "new_query" | "refine_previous" | "filter_local" | "aggregate_local" | "direct_answer" (클라이언트 처리용)

**예시:**
- 클라이언트에서 필터링 → operation: "list", query_intent: "filter_local"
- 클라이언트에서 집계 → operation: "list", query_intent: "aggregate_local"
- LLM 직접 답변 → operation: "list", query_intent: "direct_answer"
```

## 수정 파일
- `services/ai-orchestrator/app/services/query_planner.py` (프롬프트 수정)

## 교훈
1. LLM에게 여러 유사한 개념의 필드가 있을 때 명확한 구분이 필요
2. validation error 발생 시 fallback 동작(clarification)이 발생하므로, 에러 로그 확인 필수
3. 새로운 의도(intent) 추가 시 기존 필드들과의 관계를 프롬프트에 명시해야 함

## 관련 이슈
- `direct_answer` 의도 추가 후 발생
- 프롬프트가 복잡해지면서 LLM의 필드 혼동 가능성 증가
