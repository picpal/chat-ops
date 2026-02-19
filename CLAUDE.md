<!-- ORCHESTRA-START -->
# Claude Orchestra

> **이 프로젝트는 Claude Orchestra 멀티 에이전트 시스템을 사용합니다.**

## Preflight Check (Edit/Write 호출 전 확인)

**매번 Edit/Write 호출 전:**
1. 이 파일이 코드 파일인가? (`.orchestra/`, `.claude/`, `*.md` 제외)
2. **YES** → STOP. `Task(High-Player/Low-Player)`로 위임
3. **NO** → 진행 가능

## 필수 규칙 (모든 요청에 적용)

### 1. 매 응답 첫 줄: Intent 선언
```
[Maestro] Intent: {TYPE} | Reason: {근거}
```

### 2. Intent 분류
| Intent | 조건 | 행동 |
|--------|------|------|
| **TRIVIAL** | 코드와 완전히 무관 | 직접 응답 |
| **EXPLORATORY** | 코드 탐색/검색 | Task(Explorer) 호출 |
| **AMBIGUOUS** | 불명확한 요청 | AskUserQuestion으로 명확화 |
| **OPEN-ENDED** | **모든 코드 수정** | 전체 Phase 흐름 실행 |

**"간단한 수정"도 OPEN-ENDED** — 코드 변경 크기 무관!

### 3. OPEN-ENDED 필수 체크리스트
Executor 호출 전 반드시 완료:
- [ ] Task(Interviewer) 완료?
- [ ] Task(Plan-Checker) 완료?
- [ ] Task(Plan-Reviewer) "Approved"?
- [ ] Task(Planner) 6-Section 프롬프트?

### 4. 금지 행위
- **직접 Edit/Write (코드)** → Task(High-Player/Low-Player)로 위임
- **직접 코드 탐색** → Task(Explorer)로 위임
- **Planning 없이 코드 수정** → Interviewer → Planner → Executor 순서 필수

### 5. 상세 규칙
`.claude/rules/maestro-protocol.md` 참조

<!-- ORCHESTRA-END -->

# ChatOps (AI Backoffice)

## 1. Architecture (A-Plan)
- UI: React (RenderSpec renderer, pagination UI)
- AI Orchestrator: Python/FastAPI
  - NL -> QueryPlan
  - RAG (documents -> pgvector)
  - Compose RenderSpec + datasets/dataRef
- Core API: Java 21 / Spring Boot / Gradle
  - Auth/RBAC, audit logs
  - QueryPlan validation
  - SQL Builder + DB execution
  - QueryToken + pagination (server-side)
- DB: PostgreSQL (+ pgvector optional)

Data flow:
UI -> AI(/chat) -> Core API(/query/start, /query/page) -> PostgreSQL

## 2. Non-negotiable rules
- DB access: ONLY Core API can query business DB.
- AI service must NOT build raw SQL strings for execution.
- QueryPlan must NOT contain physical table/column names.
- Pagination for large datasets must be server-side using queryToken.

## 3. Contracts (Single Source of Truth)
Location: /libs/contracts
- query-plan.schema.json
- render-spec.schema.json
- query-result.schema.json

Change process:
1) Update schema in libs/contracts
2) Update types in Java/Python/UI accordingly
3) Run unit + integration tests

## 4. Local development
### Start all services
- ./scripts/dev-up.sh

### Stop all services
- ./scripts/dev-down.sh

### Ports (example)
- UI: http://localhost:3000
- AI: http://localhost:8000
- Core API: http://localhost:8080
- PostgreSQL: localhost:5432

## 5. Service commands
### core-api (Java)
- Build: ./gradlew build
- Run: ./gradlew bootRun
- Test: ./gradlew test

### ai-orchestrator (Python)
- Install: uv sync (or pip install -r requirements.txt)
- Run: uvicorn app.main:app --reload --port 8000
- Test: pytest

### ui (React)
- Install: npm ci
- Run: npm run dev
- Build: npm run build

## 6. Environment variables
See: infra/docker/.env.example
- DATABASE_URL=
- CORE_API_URL=
- LLM_PROVIDER=
- LLM_API_KEY=
- VECTOR_DB_MODE= (postgres_pgvector / external)

## 7. Troubleshooting
- CORS: use infra/docker/nginx as reverse proxy (preferred)
- Migration errors: check Flyway logs and db/migration order
- Slow queries: ensure time range filter + limit are enforced

## 8. Development Workflow (7-Phase Process)

**복잡한 작업은 7단계 워크플로우를 따른다**

### 워크플로우 다이어그램

```
┌──────────────────────────────────────────────────────────────┐
│  1. ANALYZE     → code-analyzer로 영향 범위 분석            │
│  2. PLAN        → EnterPlanMode로 계획 수립                 │
│  3. APPROVE     → 사용자 승인 + Feature 브랜치 생성         │
│  4. IMPLEMENT   → 개발 에이전트로 구현 (병렬 가능)          │
│  5. TEST        → tester로 테스트 (실패시 4로 회귀)         │
│  6. PR REVIEW   → PR 생성 + pr-reviewer (수정시 4로 회귀)   │
│  7. MERGE       → PR 머지 + 브랜치/Worktree 정리            │
└──────────────────────────────────────────────────────────────┘
```

### 언제 7-Phase 워크플로우를 사용하는가?

| 조건 | 7-Phase 필요 |
|------|--------------|
| 여러 파일 수정이 필요한 기능 | 필수 |
| 기존 코드 수정/개선/리팩토링 | 필수 |
| 새로운 기능 추가 | 필수 |
| 버그 수정 (영향 범위 큼) | 필수 |
| 단순 오타/설정값 수정 | 불필요 |
| 파일 조회/질문 응답 | 불필요 |

### 각 Phase 상세

#### Phase 1: ANALYZE
- `code-analyzer` 에이전트로 영향 범위 분석
- 관련 파일, 의존성, 아키텍처 영향 파악

#### Phase 2: PLAN
- `EnterPlanMode`로 계획 수립
- 변경 파일 목록, 구현 단계, 테스트 계획 작성
- 계획서는 `.claude/plan.md`에 작성

#### Phase 3: APPROVE
- `ExitPlanMode`로 사용자 승인 요청
- 승인 후 `git-workflow-manager`로 Feature 브랜치 생성
- 브랜치 네이밍: `<type>/<issue-number>-<description>`

#### Phase 4: IMPLEMENT
- 개발 에이전트로 구현 (`ai-orchestrator-dev`, `core-api-dev`, `frontend-developer`)
- 서비스 간 의존성 없으면 병렬 실행 가능

#### Phase 5: TEST (반복 단계)
- `tester` 에이전트로 테스트 실행
- 실패 시 → 코드 수정 → 재테스트 (Phase 4로 회귀)
- **통과 기준:**
  - [ ] 단위 테스트 100% 통과
  - [ ] 빌드 성공
  - [ ] 린트 에러 없음

#### Phase 6: PR REVIEW (반복 단계)
- `git-workflow-manager`로 PR 생성 (`/cp --pr` 또는 `/pr`)
- `pr-reviewer` 에이전트로 리뷰 수행
- CHANGES_REQUESTED → 코드 수정 → 재커밋 → 재리뷰 (Phase 4로 회귀)
- **승인 기준:**
  - [ ] CRITICAL 이슈 0개
  - [ ] WARNING 이슈 3개 이하

#### Phase 7: MERGE
- PR 머지 (squash merge 권장)
- 브랜치/Worktree 정리

### Git Worktree 사용 시점

| 시나리오 | Worktree 사용 |
|----------|---------------|
| 단일 기능 개발 | 불필요 |
| 복수 기능 병렬 개발 | 권장 |
| 긴급 핫픽스 (작업 중 다른 기능 진행) | 필수 |

### 브랜치 네이밍 컨벤션

```
<type>/<issue-number>-<description>

예시:
- feat/123-payment-api
- fix/456-pagination-bug
- refactor/789-query-service
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

---

## 9. Agent 사용 가이드

프로젝트에 설정된 에이전트를 **적극 활용**하세요.

### Phase-Agent 매핑

| Phase | 담당 에이전트 |
|-------|--------------|
| 1. ANALYZE | `code-analyzer` |
| 2. PLAN | Main Agent (`EnterPlanMode`) |
| 3. APPROVE | 사용자 + `git-workflow-manager` |
| 4. IMPLEMENT | `ai-orchestrator-dev`, `core-api-dev`, `frontend-developer` |
| 5. TEST | `tester` |
| 6. PR REVIEW | `git-workflow-manager` + `pr-reviewer` |
| 7. MERGE | `git-workflow-manager` |

### Agent First 원칙 (필수)

**"작업 전, 해당 에이전트가 있는지 먼저 확인하라"**

#### 에이전트 사용 판단 기준

| 질문 | Yes → 에이전트 사용 |
|------|---------------------|
| 코드 구조/의존성 분석이 필요한가? | `code-analyzer` |
| Git 브랜치/PR/Worktree 관리가 필요한가? | `git-workflow-manager` |
| 코드 수정 후 테스트가 필요한가? | `tester` |
| 특정 서비스(AI/Core API/UI) 코드를 수정하는가? | `ai-orchestrator-dev`, `core-api-dev`, `frontend-developer` |
| 서버 상태 확인/제어가 필요한가? | `server-ops-controller` |
| 오류 원인 파악이 필요한가? | `log-analyzer` |
| PR 리뷰가 필요한가? | `pr-reviewer` |
| 문서 작성이 필요한가? | `project-doc-writer` |

#### 직접 작업해도 되는 경우
- 단일 파일의 1-2줄 단순 수정 (오타, 설정값 변경)
- 파일 내용 단순 조회
- 간단한 질문 응답

### 병렬 실행 조건

서비스 간 의존성 없을 때 병렬 실행 가능:
- `ai-orchestrator-dev` ∥ `core-api-dev`
- `core-api-dev` ∥ `frontend-developer`
- `ai-orchestrator-dev` ∥ `frontend-developer`

```
예: AI Orchestrator 수정 + Core API 수정이 동시에 필요한 경우
→ ai-orchestrator-dev와 core-api-dev를 병렬 실행
```

### 반복 프로세스

#### TEST 실패 시 (Phase 5)
```
개발 에이전트로 수정 → tester로 재테스트 → 통과까지 반복
```

#### PR CHANGES_REQUESTED 시 (Phase 6)
```
개발 에이전트로 수정 → 커밋 → pr-reviewer로 재리뷰 → APPROVED까지 반복
```

### 에이전트 목록 및 사용 시점

| 에이전트 | 용도 | Phase |
|---------|------|-------|
| **code-analyzer** | 코드 분석, 의존성 파악, 영향 범위 분석 | 1. ANALYZE |
| **git-workflow-manager** | Git 브랜치, Worktree, PR 관리 | 3, 6, 7 |
| server-ops-controller | 서버 시작/중지/재시작/상태확인 | 4. IMPLEMENT |
| ai-orchestrator-dev | AI Orchestrator (Python/FastAPI) 개발 | 4. IMPLEMENT |
| core-api-dev | Core API (Java/Spring Boot) 개발 | 4. IMPLEMENT |
| frontend-developer | React UI 개발 | 4. IMPLEMENT |
| **tester** | 전체 테스트 관할 (Python/Java/React) | 5. TEST |
| **pr-reviewer** | PR 코드 리뷰 | 6. PR REVIEW |
| log-analyzer | 로그 분석 및 디버깅 | 디버깅 시 |
| project-doc-writer | 문서 작성 | 문서화 시 |
| work-logger | 작업 기록 | 작업 완료 후 |
| file-explorer | 파일 탐색 | 파일 위치 찾기 |

### 주의사항

- **AI Orchestrator 코드 수정 후**: `docker restart`가 아닌 Docker rebuild 필요
  ```bash
  docker-compose -f infra/docker/docker-compose.yml build ai-orchestrator
  docker-compose -f infra/docker/docker-compose.yml up -d ai-orchestrator
  ```
- **E2E 테스트 전**: 모든 서비스(UI, AI, Core API, DB) 실행 확인
- **check-point 기록**: 주요 구현 완료 시 check-point/ 폴더에 문서화
- **test-scenarios 기록**: 테스트 시나리오는 test-scenarios/ 폴더에 저장

## 10. Business Domain (PG 결제 백오피스)

이 서비스는 **PG(결제 게이트웨이) 백오피스**로, 자연어로 결제/정산 데이터를 조회합니다.

### 핵심 엔티티 (10개)

| 엔티티 | 테이블 | 역할 |
|--------|--------|------|
| **Merchant** | merchants | 가맹점 정보, 수수료율, 정산 계좌 |
| **PgCustomer** | pg_customers | 가맹점별 고객 정보 |
| **PaymentMethod** | payment_methods | 저장된 결제수단 (카드, 간편결제 등) |
| **Payment** | payments | 결제 트랜잭션 (핵심 테이블) |
| **PaymentHistory** | payment_history | 결제 상태 변경 이력 |
| **Refund** | refunds | 환불/취소 트랜잭션 |
| **BalanceTransaction** | balance_transactions | 가맹점 잔액 변동 내역 |
| **Settlement** | settlements | 일일 정산 |
| **SettlementDetail** | settlement_details | 정산 상세 내역 |
| **Order** | orders | 주문 (샘플 데이터) |

### 엔티티 관계도

```
Merchant (가맹점)
├─ PgCustomer (고객) 1:N
│  └─ PaymentMethod (결제수단) 1:N
├─ Payment (결제) 1:N
│  ├─ PaymentHistory (이력) 1:N
│  └─ Refund (환불) 1:N
├─ BalanceTransaction (잔액거래) 1:N
└─ Settlement (정산) 1:N
   └─ SettlementDetail (정산상세) 1:N
```

### 주요 비즈니스 규칙

**결제 상태 흐름:**
- READY → IN_PROGRESS → DONE (정상)
- DONE → CANCELED (전액취소) / PARTIAL_CANCELED (부분취소)
- WAITING_FOR_DEPOSIT (가상계좌) → DONE / EXPIRED

**정산 주기:** D+0, D+1, D+2, WEEKLY, MONTHLY

**수수료율:**
- 신용카드: 3.3%
- 체크카드: 2.5%
- 가상계좌: 300원/건
- 간편결제: 3.3%

### 시계열 데이터 (timeRange 필수)

- Payment, PaymentHistory, BalanceTransaction

### RAG 문서 구성 (26개+)

| 타입 | 개수 | 용도 |
|------|------|------|
| entity | 7 | 테이블/필드 정의 |
| business_logic | 6 | 비즈니스 규칙 |
| error_code | 4 | 에러 처리 |
| faq | 9 | 조회 패턴 예시 |
| quality_answer | 동적 | 고품질 답변 자동 저장 (4점 이상) |

### 주요 조회 시나리오

- **결제**: 가맹점별 매출, 상태별 집계, 기간별 추이
- **환불**: 환불 현황, 사유 분석, 환불율
- **정산**: 정산 현황, 지급 상태, 금액 검증
- **가맹점**: 상태 현황, 수수료율

## 11. Quality Answer RAG

높은 별점(4~5점) 답변을 자동 저장하고, 새 질문 시 유사 고품질 답변을 참고하여 답변 품질을 향상시키는 기능.

### 기능 개요

```
[별점 4~5점 저장] → rating_service.save_rating()
                         ↓
              quality_answer_service.save_quality_answer()
                         ↓
              documents 테이블에 저장 (doc_type='quality_answer')

[새 질문] → _generate_knowledge_answer()
                  ↓
         quality_answer_service.search_similar_answers()
                  ↓
         "## 참고 답변 예시" 섹션으로 LLM 프롬프트에 추가
```

### 설정

| 설정 키 | 기본값 | 설명 |
|---------|--------|------|
| `quality_answer_rag.enabled` | true | 기능 활성화 여부 |
| `quality_answer_rag.minRating` | 4 | 저장 최소 별점 (4 또는 5) |

### API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/settings/quality-answer-rag/status` | 상태 조회 (활성화 여부, 저장된 답변 수) |
| PUT | `/api/v1/settings/quality-answer-rag` | 설정 업데이트 |

### UI 토글 위치

시나리오 관리 페이지 (`/scenarios`) 헤더에서 ON/OFF 토글로 제어 가능.

### 관련 파일

```
services/core-api/src/main/resources/db/migration/
  └── V22__create_settings_table.sql

services/ai-orchestrator/app/
  ├── models/settings.py
  ├── services/
  │   ├── settings_service.py
  │   ├── quality_answer_service.py
  │   └── rating_service.py (수정)
  ├── api/v1/
  │   ├── settings.py
  │   └── chat.py (수정)
  └── main.py (수정)

services/ui/src/
  ├── types/settings.ts
  ├── api/settings.ts
  ├── hooks/useSettings.ts
  └── components/scenarios/
      ├── QualityAnswerToggle.tsx
      └── ScenariosPage.tsx (수정)
```
