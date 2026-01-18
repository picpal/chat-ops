# Test Scenario 004: Server-Side Pagination

**작성일:** 2025-01-13
**기능:** 대용량 데이터 서버 사이드 페이지네이션
**상태:** ⚠️ 부분 수정 (Core API 페이지 이동 수정, AI→UI 전달 미완)

---

## 1. 테스트 목적

Core API의 서버 사이드 페이지네이션이 UI까지 올바르게 전달되는지 검증

### 배경
- Core API: queryToken 기반 페이지네이션 구현 완료
- 문제: AI Orchestrator → UI 간 pagination 데이터 전달 실패
- 증상: totalRows=178인데 UI에서 10으로 표시

---

## 2. 사전 조건

- [ ] UI: http://localhost:3000 실행 중
- [ ] AI Orchestrator: Docker container 실행 중
- [ ] Core API: http://localhost:8080 실행 중
- [ ] PostgreSQL: 10건 이상의 테스트 데이터 존재

---

## 3. 테스트 시나리오

### TC-004-1: 초기 페이지 로드

**입력:**
```
최근 1개월 결제 내역 조회
```

**기대 결과:**
| 항목 | 기대값 |
|------|--------|
| Core API totalRows | 178 |
| UI 표시 totalRows | 178 |
| 페이지네이션 버튼 | 표시됨 (1, 2, 3...) |
| "(Server-side)" 표시 | 있음 |

**실제 결과 (2025-01-13):**
| 항목 | 실제값 | 결과 |
|------|--------|------|
| Core API totalRows | 178 | ✅ |
| UI 표시 totalRows | **10** | ❌ |
| 페이지네이션 버튼 | **없음** | ❌ |

---

### TC-004-2: 페이지 이동

**입력:**
- TC-004-1 완료 후 "페이지 2" 클릭

**기대 결과:**
- `/query/page` API 호출
- 11~20번째 데이터 표시
- "Showing 11 to 20 of 178 results"

**실제 결과:** 테스트 불가 (페이지네이션 버튼 미표시)

---

### TC-004-3: 마지막 페이지

**입력:**
- 마지막 페이지(18) 클릭

**기대 결과:**
- 171~178번째 데이터 표시 (8건)
- "다음" 버튼 비활성화

**실제 결과:** 테스트 불가

---

## 4. 근본 원인 분석

### 데이터 흐름

```
Core API Response (✅ 정상)
└─ totalRows: 178
└─ queryToken: "qt_ec395f40..."
    ↓
AI Orchestrator RenderComposer (⚠️ 이슈)
└─ pagination 추출 실패 또는 누락
    ↓
UI receives (❌ 오류)
└─ totalRows: 10 (data.length로 표시)
```

### Core API 로그 (정상)
```log
13:52:58.918 [http-nio-8080-exec-4] INFO QueryExecutorService
- Query executed successfully. requestId=req-60087c9f, rows=10, totalRows=178
- Created pagination token: qt_ec395f40caa641b1967d32a8ac8fe232
```

### 문제 위치
| 레이어 | 상태 | 설명 |
|--------|------|------|
| Core API | ✅ | totalRows=178, queryToken 정상 생성 |
| AI Orchestrator | ⚠️ | RenderSpec에 pagination 미포함 의심 |
| UI | ❌ | pagination 정보 없어서 rows.length 사용 |

---

## 5. 필요한 수정사항

### Priority 1: AI Orchestrator - RenderComposer
```python
# render_composer.py
# Core API response에서 pagination 추출하여 RenderSpec에 포함
{
  "pagination": {
    "queryToken": "qt_...",
    "totalRows": 178,
    "totalPages": 18,
    "pageSize": 10
  }
}
```

### Priority 2: Core API 응답 구조 확인
```json
{
  "pagination": {
    "queryToken": "qt_ec395f40...",
    "hasMore": true,
    "totalRows": 178,
    "totalPages": 18
  }
}
```

---

## 6. 관련 코드

| 파일 | 함수/위치 | 역할 |
|------|----------|------|
| `render_composer.py` | `_compose_table_spec()` | RenderSpec 생성 (pagination 포함 필요) |
| `QueryController.java` | `startQuery()` | pagination 객체 반환 |
| `TableRenderer.tsx` | `paginationInfo` | spec.pagination 또는 data.pagination 사용 |

---

## 7. 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-18 | Claude | ⚠️ PARTIAL | Core API getPage/goToPage entity 복원 수정 |
| 2025-01-13 | Claude | ❌ FAIL | pagination 데이터 전달 실패 |

### 2026-01-18 수정 내용
**문제:** `/api/v1/query/page/{token}` 호출 시 "entity is required" 오류
**원인:** `QueryController`에서 `originalQueryPlan` 필드 복원 누락
**수정:** `getPage()`, `goToPage()` 메서드에서 `putAll(originalPlan)` 적용
**결과:** Core API 페이지 이동 API 정상 동작 ✅

**남은 이슈:** AI Orchestrator → UI 간 pagination 전달 (별도 작업 필요)

### 2026-01-18 추가 수정
**문제:** 페이지 이동 시 pagination 필드 불완전 (totalRows, totalPages, pageSize 누락)
**원인:** `QueryExecutorService.executePaginatedQuery()`에서 일부 필드만 반환
**수정:** HashMap 사용하여 모든 필드 포함
**결과:** 페이지 이동 API에서 모든 pagination 필드 정상 반환 ✅

---

## 8. 수정 후 검증 체크리스트

- [ ] Core API `/query/start` pagination 객체 반환 확인
- [ ] AI Orchestrator 로그에서 pagination 추출 확인
- [ ] UI RenderSpec에 pagination 포함 확인
- [ ] Modal에서 정확한 totalRows 표시 (178)
- [ ] 페이지네이션 버튼 표시
- [ ] "(Server-side)" 표시
- [ ] 페이지 2 클릭 시 `/query/page` 호출

---

## 9. 스크린샷

| 파일명 | 설명 |
|--------|------|
| `step1-initial-page.png` | 초기 페이지 로드 |
| `step3-response-received.png` | 첫 번째 쿼리 응답 (10건) |
| `step5-second-query-modal.png` | **문제 화면** - "10 of 10" 표시 |
