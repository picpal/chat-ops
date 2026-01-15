# Check Point 013: TC-001/TC-004 수정 - 교훈 및 문제 해결 기록

**날짜**: 2026-01-16
**작업자**: Claude Opus 4.5
**관련 커밋**: `10cf5ff`

---

## 1. 문제 요약

| 이슈 | 증상 | 근본 원인 |
|------|------|----------|
| TC-001 | "그래프로 보여줘" → table 반환 | Text-to-SQL 모드에서 RenderComposer 미사용 |
| TC-004 | pagination이 null | 최상위 pagination 미포함, Core API 조건부 생성 |
| 4단계+ WHERE 체이닝 | 조건 유실 | is_refinement 조건, 암시적 패턴 미감지 |

---

## 2. 핵심 교훈

### 2.1 Text-to-SQL vs QueryPlan 모드의 코드 분리 문제

**발견**: Text-to-SQL 모드는 `handle_text_to_sql()` 함수에서 별도로 처리되며, `RenderComposer`를 사용하지 않음.

```
QueryPlan 모드: chat.py → RenderComposer.compose() → RenderSpec
Text-to-SQL 모드: chat.py → compose_sql_render_spec() → RenderSpec (별도 함수)
```

**교훈**:
- 동일 기능을 두 모드에 적용할 때 **두 경로 모두 수정해야 함**
- 코드 중복을 피하려면 공통 유틸리티 함수로 추출 권장

### 2.2 조건부 로직의 위험성

**TC-004 원인**:
```java
// Core API: 조건부 pagination 생성
if (rows.size() >= limit) {
    response.put("pagination", pagination);  // 조건 불만족 시 pagination 없음
}
```

```python
# RenderComposer: queryToken 있을 때만 pagination 추가
if pagination.get("queryToken"):
    render_spec["pagination"] = {...}
```

**교훈**:
- 조건부 로직은 **모든 경우를 커버하는지** 확인 필요
- "항상 포함 + 필드만 조건부"가 더 안전한 패턴

### 2.3 LLM 기반 시스템의 컨텍스트 전달

**4단계+ WHERE 체이닝 문제 원인**:
1. `is_refinement=True`일 때만 조건 누적 → 암시적 참조 표현 놓침
2. LLM 프롬프트에 누적 조건 강조 부족
3. 대화 히스토리에서 WHERE 조건 명시적 저장 안함

**해결 방법**:
```python
# 1. whereConditions 명시적 저장
entry["whereConditions"] = extract_where_conditions(sql)

# 2. 항상 조건 누적 (is_refinement 조건 제거)
accumulated_conditions = merge_where_conditions(...)

# 3. LLM 프롬프트에 강조
"=== [중요] 현재까지 누적된 모든 WHERE 조건 (필수 유지) ==="
```

**교훈**:
- LLM은 명시적으로 강조하지 않으면 맥락을 놓칠 수 있음
- 중요한 정보는 **별도 필드에 저장** + **프롬프트에 강조**

---

## 3. 수정된 파일 및 핵심 변경

| 파일 | 변경 내용 |
|------|----------|
| `chat.py` | `compose_sql_render_spec()`에 차트 감지 + 최상위 pagination 추가 |
| `text_to_sql.py` | WHERE 조건 누적 로직 개선, LLM 프롬프트 강화 |
| `render_composer.py` | pagination 조건 완화 (`if pagination:`) |
| `QueryExecutorService.java` | pagination 항상 생성, queryToken만 조건부 |
| `query-result.schema.json` | totalPages, pageSize 필드 추가 |

---

## 4. 디버깅 방법론

### 4.1 코드 경로 추적
```bash
# 어떤 함수가 RenderSpec을 생성하는지 확인
grep -n "render_composer\|compose_sql_render_spec" chat.py
```

### 4.2 로그 확인
```bash
docker logs chatops-ai-orchestrator --tail 100 | grep -i "render\|pagination"
```

### 4.3 직접 API 테스트
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -d '{"message": "테스트"}' | jq '.renderSpec.pagination'
```

---

## 5. 체크리스트 (향후 유사 작업 시)

### 새 기능 추가 시
- [ ] QueryPlan 모드와 Text-to-SQL 모드 **둘 다** 영향 확인
- [ ] Core API 응답 구조 변경 시 스키마 업데이트
- [ ] RenderComposer와 `compose_sql_render_spec()` 동기화 확인

### LLM 관련 수정 시
- [ ] 프롬프트에 중요 정보 **명시적 강조**
- [ ] 대화 히스토리에 필요한 메타데이터 저장
- [ ] 암시적 표현 패턴 커버리지 확인

### 테스트 시
- [ ] 단위 테스트 통과 확인
- [ ] Docker 재빌드 후 E2E 테스트
- [ ] 전체 시나리오 (TC-001~005) 회귀 테스트

---

## 6. 관련 링크

- **테스트 시나리오**: `test-scenarios/001~005-*.md`
- **커밋**: `10cf5ff fix(ai): resolve TC-001 chart rendering and TC-004 pagination issues`
- **이전 체크포인트**: `012-intent-classification-quality-improvement.md`
