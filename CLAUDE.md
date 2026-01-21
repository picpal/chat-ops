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

## 8. Plan First 원칙 (필수)

**복잡한 작업은 반드시 계획을 먼저 수립하라**

### 언제 Plan Mode를 사용하는가?

| 조건 | Plan Mode 필요 |
|------|---------------|
| 여러 파일 수정이 필요한 기능 | ✅ 필수 |
| 기존 코드 수정/개선/리팩토링 | ✅ 필수 |
| 새로운 기능 추가 | ✅ 필수 |
| 버그 수정 (영향 범위 큼) | ✅ 필수 |
| 단순 오타/설정값 수정 | ❌ 불필요 |
| 파일 조회/질문 응답 | ❌ 불필요 |

### Plan Mode 워크플로우

```
1. 요청 접수
   ↓
2. 코드 분석 (code-analyzer 에이전트 활용)
   - 관련 파일 파악
   - 의존성 분석
   - 영향 범위 확인
   ↓
3. 계획 수립 (EnterPlanMode)
   - 변경 파일 목록
   - 구현 단계
   - 테스트 계획
   ↓
4. 사용자 승인 (ExitPlanMode)
   ↓
5. 구현 (개발 에이전트 활용)
   ↓
6. 테스트 (tester 에이전트)
```

### EnterPlanMode 사용 예시

```
사용자: "결제 API에 새로운 필드 추가해줘"

Claude:
1. code-analyzer로 관련 코드 분석
2. EnterPlanMode 진입
3. 계획서 작성:
   - 변경 파일: PaymentDTO.java, payments API, UI 컴포넌트
   - 단계: DTO 수정 → API 수정 → UI 반영 → 테스트
4. ExitPlanMode로 승인 요청
5. 승인 후 구현 진행
```

### Plan 작성 위치

계획서는 `.claude/plan.md` 파일에 작성됩니다.

---

## 9. Agent 사용 가이드

프로젝트에 설정된 에이전트를 **적극 활용**하세요.

### Agent First 원칙 (필수)

**"작업 전, 해당 에이전트가 있는지 먼저 확인하라"**

```
작업 요청 → 코드 분석 → 계획 수립 → 에이전트로 구현 → 테스트
```

#### 에이전트 사용 판단 기준

| 질문 | Yes → 에이전트 사용 |
|------|---------------------|
| 코드 구조/의존성 분석이 필요한가? | `code-analyzer` |
| 코드 수정 후 테스트가 필요한가? | `tester` |
| 특정 서비스(AI/Core API/UI) 코드를 수정하는가? | `ai-orchestrator-dev`, `core-api-dev`, `frontend-developer` |
| 서버 상태 확인/제어가 필요한가? | `server-ops-controller` |
| 오류 원인 파악이 필요한가? | `log-analyzer` |
| 문서 작성이 필요한가? | `project-doc-writer` |

#### 직접 작업해도 되는 경우
- 단일 파일의 1-2줄 단순 수정 (오타, 설정값 변경)
- 파일 내용 단순 조회
- 간단한 질문 응답

#### 에이전트 활용 이점
- **전문화된 컨텍스트**: 각 에이전트는 해당 도메인의 베스트 프랙티스 내장
- **일관된 워크플로우**: 수정 → 테스트 → 검증 자동화
- **품질 보장**: 테스트 누락 방지, 문서화 자동화

#### 병렬 에이전트 활용
독립적인 작업은 **병렬로 에이전트 실행**하여 효율성 극대화:
```
예: AI Orchestrator 수정 + Core API 수정이 동시에 필요한 경우
→ ai-orchestrator-dev와 core-api-dev를 병렬 실행
```

### 에이전트 목록 및 사용 시점

| 에이전트 | 용도 | 사용 시점 |
|---------|------|----------|
| **code-analyzer** | 코드 분석, 의존성 파악, 영향 범위 분석 | **구현 전 필수** - 수정/개선/신규 기능 작업 시 |
| server-ops-controller | 서버 시작/중지/재시작/상태확인 | 개발 시작/종료, 서비스 문제 발생 시 |
| ai-orchestrator-dev | AI Orchestrator (Python/FastAPI) 개발 | LLM 프롬프트, Text-to-SQL, RAG, SQL Validator 작업 |
| core-api-dev | Core API (Java/Spring Boot) 개발 | REST API, QueryPlan 검증, SQL Builder, DB 마이그레이션 |
| tester | 전체 테스트 관할 (Python/Java/React) | 코드 수정 후 테스트 실행, E2E 테스트 |
| log-analyzer | 로그 분석 및 디버깅 | 오류 발생 시, 동작 확인 필요 시 |
| frontend-developer | React UI 개발 | 프론트엔드 컴포넌트/페이지 작업 |
| project-doc-writer | 문서 작성 | 개발 계획서, ADR, 기술 문서 작성 |
| work-logger | 작업 기록 | 작업 완료 후 기록 필요 시 |
| file-explorer | 파일 탐색 | 파일 위치 찾기, 프로젝트 구조 파악 |

### 워크플로우 예시

**신규 기능 / 수정 / 개선 (공통):**
| 단계 | 에이전트/도구 | 필수 |
|------|--------------|------|
| 1. 코드 분석 | `code-analyzer` | ✅ |
| 2. 계획 수립 | `EnterPlanMode` | ✅ |
| 3. 사용자 승인 | `ExitPlanMode` | ✅ |
| 4. 구현 | 개발 에이전트 | ✅ |
| 5. 테스트 | `tester` | ✅ |
| 6. 문서화 | `project-doc-writer` | - |

**프론트엔드 개발:**
| 단계 | 에이전트 | 필수 |
|------|----------|------|
| 1. 코드 분석 | `code-analyzer` | ✅ |
| 2. 계획 수립/승인 | `EnterPlanMode` → `ExitPlanMode` | ✅ |
| 3. 서버 시작 | `server-ops-controller` | ✅ |
| 4. UI 컴포넌트 작업 | `frontend-developer` | ✅ |
| 5. 테스트 실행 | `tester` | ✅ |
| 6. 오류 분석 (필요시) | `log-analyzer` | - |

**백엔드 개발:**
| 단계 | 에이전트 | 필수 |
|------|----------|------|
| 1. 코드 분석 | `code-analyzer` | ✅ |
| 2. 계획 수립/승인 | `EnterPlanMode` → `ExitPlanMode` | ✅ |
| 3. 서버 시작 | `server-ops-controller` | ✅ |
| 4. AI/Core API 작업 | `ai-orchestrator-dev` / `core-api-dev` | ✅ |
| 5. 테스트 실행 | `tester` | ✅ |
| 6. 오류 분석 (필요시) | `log-analyzer` | - |

**중요: 구현 전 반드시 code-analyzer로 분석 + 계획 수립**

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

### RAG 문서 구성 (26개)

| 타입 | 개수 | 용도 |
|------|------|------|
| entity | 7 | 테이블/필드 정의 |
| business_logic | 6 | 비즈니스 규칙 |
| error_code | 4 | 에러 처리 |
| faq | 9 | 조회 패턴 예시 |

### 주요 조회 시나리오

- **결제**: 가맹점별 매출, 상태별 집계, 기간별 추이
- **환불**: 환불 현황, 사유 분석, 환불율
- **정산**: 정산 현황, 지급 상태, 금액 검증
- **가맹점**: 상태 현황, 수수료율