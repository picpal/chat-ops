# Check-Point 015: 페이지네이션 Entity 복원 버그 수정

**날짜:** 2026-01-18
**작업 유형:** Bug Fix
**상태:** ✅ 완료

---

## 문제 상황

### 증상
페이지네이션 토큰으로 페이지 이동 시 "entity is required" 검증 오류 발생

```bash
# 오류 발생
GET /api/v1/query/page/{token}
→ {"error": {"code": "VALIDATION_ERROR", "message": "entity is required"}}
```

### 근본 원인
`QueryController.getPage()`와 `goToPage()` 메서드에서 `queryPlanWithToken` 생성 시:
- `PaginationContext.originalQueryPlan`에 모든 필드가 저장되어 있음
- 하지만 새 Map 생성 시 queryToken과 requestId만 포함
- entity, operation, timeRange 등 필수 필드가 누락됨

### 데이터 흐름

```
[문제 있는 흐름]
GET /api/v1/query/page/{token}
  → getContext(token) ✅ originalQueryPlan에 모든 필드 있음
  → new HashMap<>() + queryToken + requestId ❌ entity 누락!
  → validate() ❌ "entity is required" 실패
```

---

## 해결 방안

### 수정 내용
`originalQueryPlan` 전체를 복원한 후 queryToken과 requestId를 덮어씀

### 수정 파일
**파일:** `services/core-api/src/main/java/com/chatops/core/controller/QueryController.java`

#### getPage() 메서드 (line 76-88)

```java
// 변경 전
Map<String, Object> queryPlanWithToken = new HashMap<>();
queryPlanWithToken.put("queryToken", token);
queryPlanWithToken.put("requestId", "page-" + token.substring(0, 8));

// 변경 후
Map<String, Object> queryPlanWithToken = new HashMap<>();
Map<String, Object> originalPlan = context.getOriginalQueryPlan();
if (originalPlan != null) {
    queryPlanWithToken.putAll(originalPlan);  // 모든 필드 복원
}
queryPlanWithToken.put("queryToken", token);
queryPlanWithToken.put("requestId", "page-" + token.substring(0, 8));
```

#### goToPage() 메서드 (line 140-150)

동일한 패턴으로 수정

---

## 테스트 결과

### Core API 직접 테스트

| 테스트 | 수정 전 | 수정 후 |
|--------|---------|---------|
| getPage() | ❌ entity is required | ✅ success |
| goToPage(5) | ❌ entity is required | ✅ success |
| goToPage(마지막) | ❌ entity is required | ✅ success |

### Docker 환경 테스트

```bash
# 초기 쿼리
POST /api/v1/query/start → Token 생성 ✅

# 페이지 이동
GET /api/v1/query/page/{token} → Status: success ✅

# 특정 페이지 이동
GET /api/v1/query/page/{token}/goto/5 → Page: 5 ✅
```

---

## 영향 범위

| 파일 | 변경 내용 |
|------|----------|
| `QueryController.java` | `getPage()`, `goToPage()` 메서드 |

기존 기능 영향 없음 (필드 복원만 추가)

---

## 관련 시나리오

- `test-scenarios/004-server-side-pagination.md`

---

## 추가 수정 (2026-01-18 후속)

### 문제: 페이지 이동 시 pagination 필드 불완전

**파일:** `QueryExecutorService.java` - `executePaginatedQuery()` 메서드

**수정 전:**
```java
response.put("pagination", Map.of(
    "queryToken", nextToken,
    "hasMore", true,
    "currentPage", context.getCurrentPage() + 1
    // ❌ totalRows, totalPages, pageSize 누락
));
```

**수정 후:**
```java
Map<String, Object> pagination = new HashMap<>();
pagination.put("currentPage", context.getCurrentPage() + 1);
pagination.put("totalRows", context.getTotalRows());
pagination.put("totalPages", context.getTotalPages());
pagination.put("pageSize", context.getPageSize());
// ... queryToken, hasMore 조건부 추가
```

**테스트 결과:**
```json
// Page 2 Pagination (수정 후)
{
  "totalPages": 100,
  "hasMore": true,
  "pageSize": 10,
  "totalRows": 1000,
  "currentPage": 2,
  "queryToken": "qt_..."
}
```

✅ 모든 필드 포함 확인

---

## 다음 단계

- [x] Core API 페이지 이동 시 pagination 필드 완전성 확인
- [ ] AI Orchestrator → UI 간 pagination 전달 E2E 테스트

---

## 학습 포인트

1. **컨텍스트 보존의 중요성**
   - 페이지네이션 토큰만으로는 쿼리 재실행 불가
   - originalQueryPlan 전체를 활용해야 함

2. **점진적 필드 복원 vs 전체 복원**
   - 처음: entity, operation만 복원 → timeRange 누락 오류
   - 최종: `putAll()`로 전체 복원 → 모든 필드 유지

3. **Docker 환경 테스트 필수**
   - 로컬 jar와 Docker 컨테이너 코드 동기화 확인
