# Test Scenario 001: preferredRenderType 기능 테스트

## 테스트 목적
사용자가 "표로", "그래프로" 등 렌더링 타입을 명시적으로 요청했을 때 올바르게 처리되는지 검증

## 사전 조건
- UI: http://localhost:3000 실행 중
- AI Orchestrator: Docker container 실행 중 (최신 코드 반영)
- Core API: http://localhost:8080 실행 중
- PostgreSQL: 테스트 데이터 존재

## 테스트 시나리오

### TC-001-1: "표로 보여줘" 테스트

**입력**:
```
최근 3개월간 거래를 가맹점 별로 그룹화해서 표로 보여줘
```

**기대 결과**:
- RenderSpec type: `"table"`
- 아이콘: `table_rows` (차트 아이콘 아님)
- 테이블 구조: 컬럼 헤더 + 데이터 행
- 로그: `"Detected render type from message: table"`

**검증 방법**:
1. 새 채팅 세션 시작
2. 위 메시지 전송
3. 결과 화면에서 테이블 형태 확인
4. AI Orchestrator 로그에서 "Detected render type from message: table" 확인

---

### TC-001-2: "그래프로 보여줘" 테스트

**입력**:
```
최근 1개월 결제 현황을 그래프로 보여줘
```

**기대 결과**:
- RenderSpec type: `"chart"`
- 아이콘: `bar_chart` 또는 차트 이미지
- 로그: `"Detected render type from message: chart"`

---

### TC-001-3: 렌더링 타입 명시 없음 (기본 동작)

**입력**:
```
최근 거래 30건 조회해줘
```

**기대 결과**:
- operation=list → 테이블로 표시
- operation=aggregate + groupBy → 차트로 표시 (기존 동작)

---

### TC-001-4: 키워드 변형 테스트

| 입력 키워드 | 기대 렌더링 타입 |
|------------|-----------------|
| "테이블로" | table |
| "목록으로" | table |
| "리스트로" | table |
| "차트로" | chart |
| "시각화로" | chart |
| "텍스트로" | text |

---

## 관련 코드

- `render_composer.py:153-173` - `_detect_render_type_from_message()`
- `render_composer.py:199-208` - 우선순위 1 처리

## 테스트 이력

| 날짜 | 테스터 | 결과 | 비고 |
|------|--------|------|------|
| 2026-01-13 | Claude | PASS | E2E 테스트 (Playwright) |
