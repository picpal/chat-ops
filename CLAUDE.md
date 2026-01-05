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