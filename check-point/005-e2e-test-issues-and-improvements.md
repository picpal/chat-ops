# E2E 테스트 이슈 및 개선 포인트

**작성일**: 2026-01-12
**관련 작업**: Playwright MCP 기반 E2E 테스트 실행

---

## 1. 발생한 오류

### 1.1 LLM API 401 Unauthorized 오류 (Critical - 해결됨)

**현상**
- 모든 LLM 호출이 401 Unauthorized 오류로 실패
- Auto-correction fallback이 실행되어 잘못된 QueryPlan 생성

**원인**
```bash
# Docker 컨테이너 환경 변수
OPENAI_API_KEY=sk-your-openai-api-key-here  # 플레이스홀더!
```

- `infra/docker/.env` 파일에 실제 API 키가 설정되지 않음
- `services/ai-orchestrator/.env`에는 실제 키가 있었으나, Docker는 별도 .env 참조

**해결**
```bash
# infra/docker/.env 수정
OPENAI_API_KEY=sk-proj-실제키값...

# 컨테이너 재생성 (restart가 아닌 down → up 필요)
docker-compose down ai-orchestrator && docker-compose up -d ai-orchestrator
```

**교훈**
- `docker-compose restart`는 환경 변수를 다시 로드하지 않음
- Docker 환경과 로컬 개발 환경의 .env 파일이 분리되어 있어 혼란 발생

---

### 1.2 Clarification 미작동 (Medium - 미해결)

**현상**
- "결제 금액 합산" 입력 시 명확화 옵션 미제공
- AI가 자동으로 가장 최근 컨텍스트(3건 데이터)를 선택하여 즉시 계산

**기대 동작**
```
ClarificationRenderer: "어떤 결과를 합산할까요?"
├─ 전체 30건 거래
├─ 도서 7건 거래
└─ mer_001 3건 거래
```

**실제 동작**
```
TextRenderer: "totalamount: 510,911,000"
→ 명확화 없이 즉시 결과 반환
```

**원인 분석**
- `needs_result_clarification` 값이 AI 판단에 의존
- AI가 "컨텍스트가 충분히 명확하다"고 판단하면 clarification 스킵
- query_planner.py의 프롬프트에 명확화 트리거 조건이 있으나, LLM이 이를 판단

**관련 코드** (`chat.py:255-302`)
```python
if len(result_messages) > 1 and needs_result_clarification:
    # 다중 결과 + LLM이 모호하다고 판단한 경우에만 clarification
```

---

### 1.3 통화 단위 불일치 (Low - 미확인)

**현상**
- 테이블 데이터: $113,000, $787,000, $551,000 (USD 표기)
- 합산 결과: 510,911,000 (원화로 추정)

**가능한 원인**
- 데이터베이스에는 원화 저장, UI에서 $ 표기만 추가
- 또는 aggregate 쿼리가 다른 데이터셋을 참조

---

## 2. 개선 포인트

### 2.1 Docker 환경 변수 관리

**현재 문제**
- 2개의 .env 파일이 존재하여 혼란
  - `services/ai-orchestrator/.env` (로컬 개발용)
  - `infra/docker/.env` (Docker 실행용)

**개선 방안**
1. **단일 소스**: `.env.example` + 실제 `.env`는 프로젝트 루트에만 배치
2. **Docker 설정**: `docker-compose.yml`에서 루트 .env 참조
3. **문서화**: 환경 변수 설정 가이드 작성

```yaml
# docker-compose.yml 개선안
services:
  ai-orchestrator:
    env_file:
      - ../../.env  # 프로젝트 루트 참조
```

---

### 2.2 Clarification 트리거 조건 명확화

**현재 로직**
```
LLM 판단 (needs_result_clarification) + 다중 결과 존재 → Clarification
```

**개선 방안 A: 규칙 기반 강제 트리거**
```python
# 집계 연산 + 다중 결과 → 항상 clarification
if query_intent == "aggregate_local" and len(result_messages) > 1:
    return clarification_response  # LLM 판단 무시
```

**개선 방안 B: 프롬프트 강화**
```
## Clarification 필수 조건 (매우 중요!)
다음 경우 needs_result_clarification=true로 설정:
- aggregate_local + 이전 결과 2개 이상 존재
- "합산", "평균", "총합" 등 집계 표현 + 다중 컨텍스트
```

---

### 2.3 E2E 테스트 자동화

**현재 상태**
- 수동 테스트 (Playwright MCP로 에이전트가 실행)
- 테스트 결과가 일회성

**개선 방안**
1. **테스트 스크립트 작성**: `services/ui/e2e/` 디렉토리에 Playwright 테스트 파일
2. **CI 통합**: GitHub Actions에서 E2E 테스트 자동 실행
3. **테스트 데이터 시딩**: 일관된 테스트를 위한 fixtures 구성

---

## 3. 고민거리

### 3.1 Clarification: 강제 vs AI 판단

**Option A: 규칙 기반 강제**
- 장점: 예측 가능한 UX, 사용자에게 항상 선택권 부여
- 단점: 불필요한 clarification으로 UX 저하 가능

**Option B: AI 판단에 위임**
- 장점: 유연한 대화, 맥락상 명확하면 빠른 응답
- 단점: 예측 불가, 사용자 의도와 다른 결과 가능

**현재 선택**: Option B (AI 판단)
**고민**: 집계 연산처럼 비가역적 결과에는 Option A가 나을 수 있음

---

### 3.2 컨텍스트 "명확성"의 기준

**시나리오**
```
[30건 조회] → [도서 7건 필터] → [mer_001 3건 필터] → "합산해줘"
```

**질문**: "합산해줘"의 대상이 명확한가?

- **명확하다고 볼 수 있는 근거**: 가장 최근 결과(3건)가 현재 컨텍스트
- **모호하다고 볼 수 있는 근거**: 이전 결과들도 유효한 선택지

**제안**: aggregate 연산에는 항상 대상을 명시하도록 UI 가이드 제공
- "3건 결과 합산해줘" (명확)
- "도서 거래 합산해줘" (명확)
- "합산해줘" (모호 → clarification)

---

### 3.3 filter_local vs refine_previous 구분

**현재 동작**
- "이중 도서만" → `filter_local` (클라이언트 필터링)
- "도서만 다시 조회" → `refine_previous` (서버 재조회)

**고민**: 사용자가 이 차이를 인지하지 못할 수 있음

- `filter_local`: 빠르지만 기존 데이터 범위 내에서만 필터링
- `refine_previous`: 느리지만 DB에서 새로 조회 (더 정확할 수 있음)

**질문**: 사용자에게 이 선택을 노출해야 하는가?

---

## 4. 다음 단계

1. [ ] Clarification 트리거 조건 개선 (aggregate_local + 다중 결과)
2. [ ] Docker 환경 변수 관리 체계 정비
3. [ ] E2E 테스트 자동화 스크립트 작성
4. [ ] 통화 단위 일관성 검증 및 수정
5. [ ] 테스트 시나리오 추가 (엣지 케이스)

---

## 5. 참고 파일

| 파일 | 용도 |
|------|------|
| `services/ai-orchestrator/app/api/v1/chat.py` | Clarification 처리 로직 |
| `services/ai-orchestrator/app/services/query_planner.py` | LLM 프롬프트 및 QueryPlan 생성 |
| `infra/docker/.env` | Docker 환경 변수 |
| `.claude/agents/ui-e2e-tester.md` | E2E 테스트 에이전트 설정 |
