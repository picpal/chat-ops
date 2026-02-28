# ChatOps (PG 결제 백오피스)

자연어로 결제/정산 데이터를 조회하는 AI 백오피스 시스템.

## Non-negotiable Rules

- DB access: ONLY Core API can query business DB.
- AI service must NOT build raw SQL strings for execution.
- QueryPlan must NOT contain physical table/column names.
- Pagination for large datasets must be server-side using queryToken.
- AI Orchestrator 코드 수정 후: docker restart가 아닌 **Docker rebuild** 필요

## Architecture

```
UI (React:3000) → AI Orchestrator (Python/FastAPI:8000) → Core API (Java/Spring:8080) → PostgreSQL(:5432)
```

| Layer | Tech | Role |
|-------|------|------|
| UI | React | RenderSpec renderer, pagination UI |
| AI | Python/FastAPI | NL→QueryPlan, RAG(pgvector), RenderSpec 생성 |
| Core API | Java 21/Spring Boot/Gradle | Auth/RBAC, QueryPlan validation, SQL Builder, DB execution |
| DB | PostgreSQL (+pgvector) | Business data + vector store |

## Contracts (Single Source of Truth)

Location: `/libs/contracts` — query-plan.schema.json, render-spec.schema.json, query-result.schema.json
변경 시: schema 수정 → Java/Python/UI 타입 반영 → 테스트

## Service Commands

| Service | Build/Install | Run | Test |
|---------|--------------|-----|------|
| core-api | `./gradlew build` | `./gradlew bootRun` | `./gradlew test` |
| ai-orchestrator | `uv sync` | `uvicorn app.main:app --reload --port 8000` | `pytest` |
| ui | `npm ci` | `npm run dev` | `npm run build` |

Start all: `./scripts/dev-up.sh` / Stop all: `./scripts/dev-down.sh`
Env: `infra/docker/.env.example` (DATABASE_URL, CORE_API_URL, LLM_PROVIDER, LLM_API_KEY, VECTOR_DB_MODE)

## Business Domain

### 엔티티 관계도

```
Merchant (가맹점)
├─ PgCustomer (고객) → PaymentMethod (결제수단)
├─ Payment (결제) → PaymentHistory (이력), Refund (환불)
├─ BalanceTransaction (잔액거래)
└─ Settlement (정산) → SettlementDetail (정산상세)
```

### 핵심 테이블

| 엔티티 | 테이블 | 비고 |
|--------|--------|------|
| Merchant | merchants | 수수료율, 정산 계좌 |
| Payment | payments | **핵심**, 시계열(timeRange 필수) |
| Refund | refunds | 환불/취소 |
| Settlement | settlements | 일일 정산 |
| BalanceTransaction | balance_transactions | 시계열(timeRange 필수) |
| PaymentHistory | payment_history | 시계열(timeRange 필수) |

### 비즈니스 규칙

- **결제 상태**: READY → IN_PROGRESS → DONE → CANCELED / PARTIAL_CANCELED
- **가상계좌**: WAITING_FOR_DEPOSIT → DONE / EXPIRED
- **정산 주기**: D+0, D+1, D+2, WEEKLY, MONTHLY
- **수수료**: 신용카드 3.3%, 체크카드 2.5%, 가상계좌 300원/건, 간편결제 3.3%

### RAG 문서: entity(7), business_logic(6), error_code(4), faq(9), quality_answer(동적, 4점+)

## Quality Answer RAG

별점 4~5점 답변을 자동 저장 → 유사 질문 시 참고 답변으로 LLM 프롬프트에 추가.

- 설정: `quality_answer_rag.enabled`(true), `quality_answer_rag.minRating`(4)
- API: `GET /api/v1/settings/quality-answer-rag/status`, `PUT /api/v1/settings/quality-answer-rag`
- UI: `/scenarios` 페이지 헤더 토글

## Troubleshooting

- CORS → infra/docker/nginx 리버스 프록시 사용
- Migration 에러 → Flyway 로그 및 db/migration 순서 확인
- 느린 쿼리 → timeRange 필터 + limit 확인
