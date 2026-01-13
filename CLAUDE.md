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

## 8. Agent 사용 가이드

프로젝트에 설정된 에이전트를 적극 활용하세요.

### 에이전트 목록 및 사용 시점

| 에이전트 | 용도 | 사용 시점 |
|---------|------|----------|
| server-ops-controller | 서버 시작/중지/재시작/상태확인 | 개발 시작/종료, 서비스 문제 발생 시 |
| ui-e2e-tester | UI 기능 테스트 (Playwright) | UI 기능 구현 완료 후 검증 |
| log-analyzer | 로그 분석 및 디버깅 | 오류 발생 시, 동작 확인 필요 시 |
| frontend-developer | React UI 개발 | 프론트엔드 컴포넌트/페이지 작업 |
| project-doc-writer | 문서 작성 | 개발 계획서, ADR, 기술 문서 작성 |
| work-logger | 작업 기록 | 작업 완료 후 기록 필요 시 |
| file-explorer | 파일 탐색 | 코드베이스 구조 파악, 파일 찾기 |

### 워크플로우 예시

1. **개발 시작**: server-ops-controller로 서버 시작
2. **기능 개발**: frontend-developer (UI) 또는 직접 수정 (백엔드)
3. **테스트**: ui-e2e-tester로 E2E 테스트
4. **오류 발생**: log-analyzer로 로그 분석
5. **문서화**: project-doc-writer로 문서 작성
6. **개발 종료**: server-ops-controller로 서버 중지

### 주의사항

- **AI Orchestrator 코드 수정 후**: `docker restart`가 아닌 Docker rebuild 필요
  ```bash
  docker-compose -f infra/docker/docker-compose.yml build ai-orchestrator
  docker-compose -f infra/docker/docker-compose.yml up -d ai-orchestrator
  ```
- **E2E 테스트 전**: 모든 서비스(UI, AI, Core API, DB) 실행 확인
- **check-point 기록**: 주요 구현 완료 시 check-point/ 폴더에 문서화
- **test-scenarios 기록**: 테스트 시나리오는 test-scenarios/ 폴더에 저장