# 집계 쿼리 테이블 렌더링 테스트 보고서

**테스트 일자**: 2026-01-13
**테스터**: UI/UX and E2E Testing Specialist
**테스트 목적**: 집계(aggregate) 쿼리를 테이블로 렌더링할 때 데이터가 "-"가 아닌 실제 값으로 표시되는지 확인

---

## 테스트 환경

- **UI**: http://localhost:3000 (Docker: chatops-ui)
- **AI Orchestrator**: http://localhost:8000 (Docker: chatops-ai-orchestrator)
- **Core API**: http://localhost:8080 (Docker: chatops-core-api)
- **Database**: PostgreSQL 16 with pgvector (Docker: chatops-postgres)

---

## 테스트 시나리오 및 결과

### 시나리오 1: 가맹점별 결제 집계

**테스트 쿼리**: "최근 3개월 결제건에 대해서 가맹점 별로 건수 및 금액 합계를 보여줘"

**결과**: ❌ **실패**

**관찰 사항**:
- 테이블이 정상적으로 렌더링됨
- 컬럼 헤더: "가맹점", "결제건수", "총금액"
- **모든 데이터 셀이 "-"로 표시됨** (8 rows)
- 데이터는 실제로 존재함을 확인

**스크린샷**: `/Users/picpal/Desktop/workspace/chat-ops/.playwright-mcp/test-results/03-scenario1-result-with-dashes.png`

---

### 시나리오 2: 상태별 결제 현황

**테스트 쿼리**: "결제 상태별 현황 표로 보여줘"

**결과**: ⚠️ **부분 성공**

**관찰 사항**:
- 테이블이 정상적으로 렌더링됨
- 컬럼 헤더: "상태", "건수", "총금액"
- **일부 컬럼만 정상 표시**:
  - "상태" 컬럼: ✅ 정상 (DONE, CANCELED, ABORTED, PARTIAL_CANCELED, WAITING_FOR_DEPOSIT)
  - "건수" 컬럼: ✅ 정상 (714, 95, 46, 91, 54)
  - "총금액" 컬럼: ❌ 모두 "-"로 표시 (5 rows)

**스크린샷**: `/Users/picpal/Desktop/workspace/chat-ops/.playwright-mcp/test-results/04-scenario2-result-partial-data.png`

---

## 근본 원인 분석

### 문제 흐름도

```
[Core API] SQL with camelCase aliases
    ↓
    SELECT merchant_id AS merchantId,
           COUNT(*) AS paymentCount,
           SUM(amount) AS totalAmount
    ↓
[PostgreSQL] 따옴표 없는 식별자를 소문자로 변환
    ↓
    실제 반환 키: merchantid, paymentcount, totalamount
    ↓
[AI Orchestrator] RenderComposer - camelCase 컬럼 정의 생성
    ↓
    columns: [{key: "merchantId"}, {key: "paymentCount"}, {key: "totalAmount"}]
    ↓
[UI] TableRenderer - row[col.key]로 데이터 접근
    ↓
    row["merchantId"] → undefined (실제 키는 "merchantid")
    ↓
[UI] formatCellValue(undefined, ...) → "-"
```

### 상세 분석

#### 1. Core API (Java/Spring Boot)

**파일**: `/Users/picpal/Desktop/workspace/chat-ops/services/core-api/src/main/java/com/chatops/core/service/SqlBuilderService.java`

```java
// SQL alias를 camelCase로 생성
SELECT merchant_id AS merchantId,
       COUNT(*) AS paymentCount,
       SUM(amount) AS totalAmount
```

**문제**: PostgreSQL은 따옴표로 감싸지 않은 식별자를 자동으로 소문자로 변환합니다.

#### 2. PostgreSQL 동작

```sql
-- Core API가 생성한 SQL
SELECT merchant_id AS merchantId, COUNT(*) AS paymentCount

-- PostgreSQL이 실제로 처리하는 것
SELECT merchant_id AS merchantid, COUNT(*) AS paymentcount

-- 따옴표를 사용하면 대소문자 유지
SELECT merchant_id AS "merchantId", COUNT(*) AS "paymentCount"  ✅
```

**확인**:
```bash
$ docker exec chatops-postgres psql -U chatops_user -d chatops \
  -c "SELECT merchant_id, COUNT(*) as payment_count, SUM(amount) as total_amount
      FROM payments WHERE created_at >= '2025-10-13'
      GROUP BY merchant_id LIMIT 3;"

 merchant_id | payment_count | total_amount
-------------+---------------+--------------
 mer_001     |           125 |     66313000  ✅ 실제 데이터 존재
 mer_002     |           125 |     60713000
 mer_003     |           125 |     60570000
```

#### 3. AI Orchestrator (Python)

**파일**: `/Users/picpal/Desktop/workspace/chat-ops/services/ai-orchestrator/app/services/render_composer.py`

**라인 639-690**: `_build_aggregate_columns()` 함수

```python
# QueryPlan의 alias를 그대로 컬럼 키로 사용
columns.append({
    "key": alias,  # camelCase (예: "merchantId", "totalAmount")
    "label": display_label,
    "type": col_type,
    "align": "right"
})
```

**로그**:
```
[extract_previous_results] msg #1 row #0 keys: ['merchantid', 'paymentcount', 'totalamount']
[extract_previous_results] msg #1 no amounts found in 8 rows
```

실제 데이터는 소문자 키(`merchantid`, `totalamount`)를 가지고 있지만, RenderSpec은 camelCase 키를 정의합니다.

#### 4. UI (React/TypeScript)

**파일**: `/Users/picpal/Desktop/workspace/chat-ops/services/ui/src/components/renderers/TableRenderer.tsx`

**라인 198**: 데이터 렌더링

```typescript
{formatCellValue(row[col.key], col.type, col.format)}
```

**라인 65**: formatCellValue 함수

```typescript
const formatCellValue = (value: any, type: string, _format?: string): React.ReactNode => {
    if (value == null) return '-'  // ← 여기서 "-" 반환
    // ...
}
```

**실행 흐름**:
```typescript
row = { merchantid: "mer_001", paymentcount: 125, totalamount: 66313000 }
col.key = "merchantId"  // camelCase

row[col.key] = row["merchantId"] = undefined  ❌

formatCellValue(undefined, "currency")
    → value == null
    → return "-"
```

#### 5. 시나리오 2에서 일부 데이터가 표시되는 이유

**QueryPlan 비교**:

시나리오 1:
```json
{
  "aggregations": [
    {"alias": "paymentCount"},
    {"alias": "totalAmount"}
  ]
}
```

시나리오 2:
```json
{
  "aggregations": [
    {"alias": "count"},        ← 소문자 그대로
    {"alias": "totalAmount"}
  ]
}
```

Core API SQL:
```sql
-- 시나리오 2
SELECT status AS status,        ← 원래 소문자
       COUNT(*) AS count,        ← 소문자 alias → 소문자로 반환 ✅
       SUM(amount) AS totalAmount  ← camelCase alias → 소문자로 변환 ❌
```

**결론**: `alias`가 원래 소문자면 PostgreSQL 변환 후에도 일치하므로 데이터가 표시됩니다.

---

## 해결 방안

### Option 1: Core API에서 SQL alias에 따옴표 추가 (권장)

**수정 파일**: `services/core-api/src/main/java/com/chatops/core/service/SqlBuilderService.java`

```java
// 변경 전
SELECT merchant_id AS merchantId

// 변경 후
SELECT merchant_id AS "merchantId"
```

**장점**:
- PostgreSQL이 대소문자를 보존
- 다른 서비스에 영향 없음
- 표준 SQL 문법 준수

**단점**:
- SQL 문자열에 따옴표 추가 필요

---

### Option 2: AI Orchestrator에서 키를 소문자로 변환

**수정 파일**: `services/ai-orchestrator/app/services/render_composer.py`

```python
# 변경 전
columns.append({
    "key": alias,  # camelCase
    ...
})

# 변경 후
columns.append({
    "key": alias.lower(),  # 소문자로 변환
    ...
})
```

**장점**:
- 간단한 수정

**단점**:
- UI에서 컬럼 키가 소문자로 표시됨 (일관성 저하)
- 다른 컴포넌트에도 영향 가능

---

### Option 3: UI에서 대소문자 구분 없이 매칭

**수정 파일**: `services/ui/src/components/renderers/TableRenderer.tsx`

```typescript
// 변경 전
{formatCellValue(row[col.key], col.type, col.format)}

// 변경 후
{formatCellValue(
  row[col.key] ?? row[col.key.toLowerCase()],
  col.type,
  col.format
)}
```

**장점**:
- 빠른 임시 해결

**단점**:
- 근본 원인 해결이 아님
- 성능 오버헤드
- 유지보수성 저하

---

## 권장 해결책

**Option 1을 권장합니다**: Core API의 `SqlBuilderService`에서 SQL alias에 따옴표를 추가하여 PostgreSQL이 대소문자를 보존하도록 합니다.

### 구현 가이드

1. `SqlBuilderService.java`의 alias 생성 부분을 수정:
   ```java
   private String buildAggregateClause(Map<String, Object> aggregation) {
       String function = (String) aggregation.get("function");
       String field = (String) aggregation.get("field");
       String alias = (String) aggregation.get("alias");

       // 따옴표로 alias를 감싸서 대소문자 보존
       return String.format("%s(%s) AS \"%s\"",
           function.toUpperCase(),
           translateField(field),
           alias);  // ← 따옴표 추가
   }
   ```

2. groupBy 필드도 동일하게 처리:
   ```java
   private String buildGroupByClause(List<String> groupBy) {
       return groupBy.stream()
           .map(field -> String.format("%s AS \"%s\"",
               translateFieldToColumn(field),
               field))  // ← 따옴표 추가
           .collect(Collectors.joining(", "));
   }
   ```

3. 테스트:
   ```bash
   # Core API 재시작
   docker-compose -f infra/docker/docker-compose.yml restart core-api

   # UI에서 동일한 쿼리 재실행
   # "최근 3개월 결제건에 대해서 가맹점 별로 건수 및 금액 합계를 보여줘"
   ```

---

## 추가 발견 사항

### 1. 네트워크 로그 분석

```
[POST] http://localhost:8000/api/v1/chat => [200] OK
```

API 호출은 성공했으나 데이터 매핑 문제로 UI에서 "-"로 표시됨.

### 2. AI Orchestrator 로그

```
[extract_previous_results] msg #1 no amounts found in 8 rows
```

AI Orchestrator가 이전 결과를 추출할 때도 camelCase 키로 접근하여 금액 데이터를 찾지 못함.

### 3. 데이터베이스 실제 데이터 확인

모든 집계 결과는 데이터베이스에 정상적으로 존재합니다. 단순히 키 매핑 문제입니다.

---

## 테스트 통과 기준

수정 후 다음 조건을 모두 만족해야 합니다:

1. ✅ 시나리오 1: 모든 컬럼(가맹점, 결제건수, 총금액)에 실제 데이터 표시
2. ✅ 시나리오 2: 모든 컬럼(상태, 건수, 총금액)에 실제 데이터 표시
3. ✅ 금액 필드는 currency 포맷으로 표시 (예: ₩66,313,000)
4. ✅ 페이지네이션 정상 동작
5. ✅ CSV 내보내기 정상 동작

---

## 파일 경로 요약

### 수정 필요 파일
- `/Users/picpal/Desktop/workspace/chat-ops/services/core-api/src/main/java/com/chatops/core/service/SqlBuilderService.java`

### 관련 파일
- `/Users/picpal/Desktop/workspace/chat-ops/services/ai-orchestrator/app/services/render_composer.py`
- `/Users/picpal/Desktop/workspace/chat-ops/services/ui/src/components/renderers/TableRenderer.tsx`
- `/Users/picpal/Desktop/workspace/chat-ops/services/core-api/src/main/java/com/chatops/core/service/QueryExecutorService.java`

### 테스트 결과 파일
- `/Users/picpal/Desktop/workspace/chat-ops/.playwright-mcp/test-results/01-initial-page.png`
- `/Users/picpal/Desktop/workspace/chat-ops/.playwright-mcp/test-results/02-chat-session-started.png`
- `/Users/picpal/Desktop/workspace/chat-ops/.playwright-mcp/test-results/03-scenario1-result-with-dashes.png`
- `/Users/picpal/Desktop/workspace/chat-ops/.playwright-mcp/test-results/04-scenario2-result-partial-data.png`

---

## 결론

집계 쿼리를 테이블로 렌더링할 때 데이터가 "-"로 표시되는 문제는 **PostgreSQL의 식별자 대소문자 변환** 때문입니다. Core API에서 생성하는 SQL alias를 따옴표로 감싸면 문제가 해결됩니다.

이 이슈는 데이터 자체의 문제가 아니라 **키 매핑 불일치**로 인한 것이며, Core API 한 곳만 수정하면 전체 시스템이 정상 작동할 것으로 예상됩니다.
