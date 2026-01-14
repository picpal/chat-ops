# 테스트 시나리오: 집계 쿼리 테이블 렌더링 버그 수정

**작성일:** 2026-01-13
**이슈:** 집계(aggregate) 쿼리 결과가 테이블에서 모두 "-"로 표시됨
**상태:** ✅ 해결 완료

---

## 1. 문제 현상

### 재현 시나리오
1. UI에서 다음 쿼리 입력: "최근 3개월 결제건에 대해서 가맹점 별로 건수 및 금액 합계를 보여줘"
2. 결과: 테이블에 8건의 데이터가 있다고 표시되지만 모든 셀이 "-"로 표시됨

### 스크린샷
- 수정 전: `.playwright-mcp/test-results/03-scenario1-result-with-dashes.png`

---

## 2. 원인 분석

### 데이터 흐름 추적

```
1. QueryPlan 생성 (AI Orchestrator)
   - operation: "aggregate"
   - groupBy: ["merchantId"]
   - aggregations: [{function: "sum", field: "amount", alias: "totalAmount"}]

2. SQL 생성 (Core API - SqlBuilderService.java)
   SELECT merchant_id AS merchantId, SUM(amount) AS totalAmount
   → PostgreSQL은 따옴표 없는 식별자를 소문자로 변환
   → 실제 결과 키: {merchantid, totalamount} (소문자)

3. RenderSpec 생성 (AI Orchestrator - render_composer.py)
   - 기존: ENTITY_COLUMNS["Payment"] 사용 → snake_case 컬럼
   - 문제: 집계 결과 필드와 컬럼 정의 불일치

4. UI 렌더링 (TableRenderer.tsx)
   - row[col.key] 접근 시 undefined 반환
   - formatCellValue(undefined) → "-" 표시
```

### 근본 원인 (2가지)

| 문제 | 설명 |
|------|------|
| **A. 컬럼 정의 불일치** | 집계 결과는 `{merchantId, count, totalAmount}`, ENTITY_COLUMNS는 원본 엔티티 컬럼 `{payment_key, order_id, ...}` |
| **B. PostgreSQL 대소문자 변환** | SQL alias `AS merchantId` → 소문자 `merchantid`로 변환되어 키 불일치 |

---

## 3. 해결 방안

### 수정 파일 및 내용

#### 3.1 AI Orchestrator - render_composer.py

**변경 1: `_build_aggregate_columns` 메서드 추가 (635행)**

```python
def _build_aggregate_columns(
    self,
    query_plan: Dict[str, Any],
    rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """집계 쿼리 결과용 동적 컬럼 생성"""
    columns = []
    group_by = query_plan.get("groupBy", [])
    aggregations = query_plan.get("aggregations", [])

    # 1. groupBy 필드를 컬럼으로 추가
    for field in group_by:
        columns.append({
            "key": field,  # camelCase (SQL alias와 동일)
            "label": self._get_axis_label(field),
            "type": "string",
            "align": "left"
        })

    # 2. 집계 필드를 컬럼으로 추가
    for agg in aggregations:
        alias = agg.get("alias") or f"{agg['function']}_{agg['field']}"
        # ... 컬럼 정의 생성

    return columns
```

**변경 2: `_compose_table_spec` 메서드 수정 (248행)**

```python
# 집계 쿼리를 테이블로 표시할 때는 동적 컬럼 생성
if operation == "aggregate":
    columns = self._build_aggregate_columns(query_plan, rows)
else:
    columns = ENTITY_COLUMNS.get(entity, self._infer_columns(rows))
```

#### 3.2 Core API - SqlBuilderService.java

**변경: SQL alias에 따옴표 추가 (100-124행)**

```java
// 변경 전
selectJoiner.add(column + " AS " + field);
selectJoiner.add(aggExpression + " AS " + alias);

// 변경 후 - PostgreSQL camelCase 보존을 위해 따옴표 사용
selectJoiner.add(column + " AS \"" + field + "\"");
selectJoiner.add(aggExpression + " AS \"" + alias + "\"");
```

---

## 4. 테스트 시나리오

### 시나리오 1: 가맹점별 결제 집계

| 항목 | 내용 |
|------|------|
| **쿼리** | "최근 3개월 결제건에 대해서 가맹점 별로 건수 및 금액 합계를 보여줘" |
| **기대 결과** | 테이블에 가맹점ID, 건수, 금액이 실제 값으로 표시 |
| **실제 결과** | ✅ 8개 가맹점의 집계 데이터가 정상 표시 |

**검증 데이터:**
| 가맹점 | 건수 | 총금액 |
|--------|------|--------|
| mer_001 | 125 | ₩66,313,000 |
| mer_002 | 125 | ₩60,713,000 |
| ... | ... | ... |

### 시나리오 2: 상태별 결제 현황 (표로)

| 항목 | 내용 |
|------|------|
| **쿼리** | "결제 상태별 현황 표로 보여줘" |
| **기대 결과** | 테이블 형태로 상태별 집계 표시 (차트 아님) |
| **실제 결과** | ✅ 5개 상태의 집계 데이터가 테이블로 표시 |

**검증 데이터:**
| 상태 | 건수 | 총금액 |
|------|------|--------|
| DONE | 714 | ₩371,078,000 |
| CANCELED | 95 | ₩44,787,000 |
| ... | ... | ... |

---

## 5. 회귀 테스트

| 기능 | 테스트 결과 |
|------|-------------|
| list 쿼리 + 테이블 | ✅ 영향 없음 |
| aggregate 쿼리 + 차트 | ✅ 영향 없음 |
| aggregate 쿼리 + 텍스트 | ✅ 영향 없음 |
| log 쿼리 | ✅ 영향 없음 |

---

## 6. 결론

### 수정 요약

1. **AI Orchestrator**: 집계 쿼리용 동적 컬럼 생성 로직 추가
2. **Core API**: PostgreSQL 대소문자 보존을 위한 SQL alias 따옴표 처리

### 테스트 결과

- ✅ 모든 테스트 시나리오 통과
- ✅ 기존 기능 회귀 없음
- ✅ 배포 준비 완료

### 스크린샷
- 수정 후 시나리오 1: `.playwright-mcp/test-output-scenario1.png`
- 수정 후 시나리오 2: `.playwright-mcp/test-output-scenario2.png`
