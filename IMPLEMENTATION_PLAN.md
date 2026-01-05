# ChatOps (AI Backoffice) 구현 계획

## 프로젝트 개요

**목표**: 채팅 기반 전자상거래 백오피스 운영 시스템
- 1차: 전자상거래 데이터 조회/분석 (주문, 고객, 재고)
- 2차: 결제 서버 로그 분석 및 오류 진단

**현재 상태**: 빈 프로젝트 (아키텍처 설계 완료, UI 디자인 완료)

## 아키텍처

```
UI (React + Tailwind)
  ↓ POST /chat
AI Orchestrator (Python/FastAPI)
  - 자연어 → QueryPlan 변환
  - RAG 문서 검색
  - RenderSpec 생성
  ↓ POST /query/start, GET /query/page
Core API (Java/Spring Boot)
  - QueryPlan 검증
  - SQL 생성 및 실행
  - 서버사이드 페이징
  ↓
PostgreSQL + pgvector
```

**핵심 제약사항**:
- DB 접근: Core API만 가능
- AI 제약: Raw SQL 생성 금지
- QueryPlan: 물리 테이블명 금지 (논리 엔티티만)
- 페이징: queryToken 방식 사용

## 구현 단계

### Phase 1: 프로젝트 골격 및 환경 설정

**목표**: 3개 서비스 부트스트랩 + Docker 환경 구성

**생성할 디렉토리**:
```
chat-ops/
├── libs/contracts/
├── services/
│   ├── ui/
│   ├── ai-orchestrator/
│   └── core-api/
├── infra/docker/
└── scripts/
```

**주요 작업**:

1. **Core API 초기화**
   - `services/core-api/build.gradle` 생성
   - Spring Boot 3.2 + Java 21 설정
   - 의존성: Spring Web, Data JPA, Security, PostgreSQL, Flyway
   - 기본 Controller: `/api/v1/query/start`, `/api/v1/query/page`
   - Mock 응답으로 시작

2. **AI Orchestrator 초기화**
   - `services/ai-orchestrator/pyproject.toml` 생성
   - FastAPI + LangChain + pgvector 설정
   - 기본 Endpoint: `POST /api/v1/chat`
   - Mock RenderSpec 응답으로 시작

3. **UI 초기화**
   - `services/ui/package.json` 생성
   - Vite + React 18 + TypeScript + Tailwind
   - 의존성: React Query, Zustand, Recharts, React Markdown
   - ChatOps Web Design 프로토타입 기반 컴포넌트 구조

4. **Infrastructure 구성**
   - `infra/docker/docker-compose.yml`: PostgreSQL + 3개 서비스
   - `infra/docker/.env.example`: 환경변수 템플릿
   - `infra/docker/nginx/nginx.conf`: Reverse proxy (CORS)
   - `scripts/dev-up.sh`, `scripts/dev-down.sh`: 개발 환경 스크립트

**검증**: `./scripts/dev-up.sh` 실행 시 모든 서비스 기동 확인

---

### Phase 2: 계약 정의 및 타입 생성

**목표**: JSON Schema 작성 + 3개 언어 타입 자동 생성

**생성할 파일**:

1. **`libs/contracts/query-plan.schema.json`**
   - AI → Core API 쿼리 계획
   - 필수 필드: `requestId`, `entity`, `operation`
   - Entity 예시: Order, Customer, Product, Inventory
   - Operation: list, aggregate, search
   - Filters, aggregations, orderBy, limit, queryToken

2. **`libs/contracts/render-spec.schema.json`**
   - AI → UI 렌더링 명세
   - 타입: table, text, chart, log, composite
   - 각 타입별 설정 (columns, dataRef, pagination 등)

3. **`libs/contracts/query-result.schema.json`**
   - Core API → AI 쿼리 결과
   - 필수 필드: `requestId`, `status`, `data`
   - Pagination 정보 포함 (queryToken, hasMore)

4. **`scripts/generate-types.sh`**
   - TypeScript: json-schema-to-typescript
   - Python: datamodel-code-generator
   - Java: jsonschema2pojo Gradle 플러그인

**검증**: `./scripts/generate-types.sh` 실행 후 3개 언어 타입 생성 확인

---

### Phase 3: Core API 구현

**목표**: QueryPlan 실행 엔진 완성

**주요 구현 파일**:

1. **`services/core-api/src/main/java/com/chatops/core/service/QueryPlanValidatorService.java`**
   - Entity 화이트리스트 검증
   - Filter operator 검증
   - Limit 제한 (max 1000)
   - 시계열 데이터 시간 범위 필수 검증

2. **`services/core-api/src/main/java/com/chatops/core/service/SqlBuilderService.java`**
   - 논리 엔티티 → 물리 테이블 매핑 (application.yml 기반)
   - 논리 필드 → 물리 컬럼 매핑
   - Parameterized SQL 생성 (SQL Injection 방지)
   - WHERE, GROUP BY, ORDER BY, LIMIT 절 생성

3. **`services/core-api/src/main/java/com/chatops/core/service/QueryExecutorService.java`**
   - JdbcTemplate로 SQL 실행
   - QueryResult 객체 생성
   - 에러 핸들링 및 로깅

4. **`services/core-api/src/main/java/com/chatops/core/service/PaginationService.java`**
   - Cursor 기반 페이징 (마지막 row 값 저장)
   - QueryToken 생성 및 저장 (query_tokens 테이블)
   - 1시간 만료 설정

5. **Flyway Migrations**
   - `V1__create_orders.sql`: orders 테이블
   - `V2__create_customers.sql`: customers 테이블
   - `V3__create_products.sql`: products 테이블
   - `V4__create_inventory.sql`: inventory 테이블
   - `V5__create_query_tokens.sql`: query_tokens 테이블

**엔티티 매핑 설정** (`application.yml`):
```yaml
chatops:
  entity-mappings:
    Order:
      table: orders
      fields:
        orderId: order_id
        customerId: customer_id
        orderDate: order_date
        totalAmount: total_amount
        status: status
```

**검증**: Postman으로 `/api/v1/query/start` 호출하여 QueryPlan 실행 확인

---

### Phase 4: AI Orchestrator 구현

**목표**: 자연어 → QueryPlan 변환 + RenderSpec 생성

**주요 구현 파일**:

1. **`services/ai-orchestrator/app/services/query_planner.py`**
   - LangChain + GPT-4로 자연어 → QueryPlan 변환
   - Structured output (Pydantic)
   - 프롬프트: 사용 가능 엔티티, 필드 정보 제공
   - 예시: "최근 주문 보여줘" → QueryPlan(entity="Order", operation="list", ...)

2. **`services/ai-orchestrator/app/services/rag_service.py`**
   - pgvector 기반 문서 검색
   - OpenAI Embeddings (text-embedding-ada-002)
   - 초기 문서: 엔티티 설명, 에러 코드, 비즈니스 로직
   - `search_docs(query, k=3)` 메서드

3. **`services/ai-orchestrator/app/services/render_composer.py`**
   - QueryResult → RenderSpec 변환
   - 데이터 형태로 render type 결정:
     - rows 있으면 → table
     - aggregations 있으면 → chart
     - logs 있으면 → log
   - 컬럼 자동 추론 (타입, 포맷)

4. **`services/ai-orchestrator/app/api/v1/chat.py`**
   - 전체 플로우 통합:
     1. RAG 컨텍스트 검색
     2. QueryPlan 생성
     3. Core API 호출
     4. RenderSpec 생성
     5. 대화 저장
   - JWT 전달 (Core API 인증)

**검증**: curl로 `/api/v1/chat` 호출하여 E2E 플로우 확인

---

### Phase 5: UI 구현

**목표**: RenderSpec 렌더러 + 채팅 인터페이스

**주요 구현 파일**:

1. **RenderSpec Renderers**
   - `services/ui/src/components/renderers/TableRenderer.tsx`
     - ChatOps Web Design/Answer-Table 기반
     - 페이지네이션 (Load More 버튼)
     - Export CSV, Fullscreen 액션

   - `services/ui/src/components/renderers/TextRenderer.tsx`
     - ChatOps Web Design/Answer-Text 기반
     - React Markdown으로 content 렌더링
     - Sections (info, warning, error)

   - `services/ui/src/components/renderers/ChartRenderer.tsx`
     - Recharts (BarChart, LineChart)
     - RenderSpec.chart 설정 기반

   - `services/ui/src/components/renderers/LogRenderer.tsx`
     - ChatOps Web Design/Answer-Graph and Log Search Text 기반
     - 타임스탬프, 레벨, 메시지 표시
     - 검색어 하이라이트

2. **`services/ui/src/components/renderers/RenderSpecDispatcher.tsx`**
   - RenderSpec.type에 따라 적절한 렌더러 호출
   - Composite 타입 지원 (여러 컴포넌트 순차 렌더)

3. **`services/ui/src/components/chat/ChatInterface.tsx`**
   - 채팅 입력 + 메시지 히스토리
   - React Query로 API 호출
   - Zustand로 대화 상태 관리
   - Enter로 전송, Shift+Enter로 줄바꿈

4. **`services/ui/src/components/sidebar/Sidebar.tsx`**
   - ChatOps Web Design/Answer-Main Content 기반
   - Agent 프로필 (FinBot)
   - 분석 히스토리 (Today, Yesterday, Previous 7 Days)
   - New Analysis 버튼

5. **`services/ui/src/App.tsx`**
   - 전체 레이아웃 (사이드바 + 메인)
   - React Query Provider
   - 라우팅 (향후 확장)

**검증**: 브라우저에서 질문 입력 → 응답 렌더링 확인

---

### Phase 6: 통합 테스트 및 Docker 최적화

**목표**: E2E 테스트 + 프로덕션 준비

**주요 작업**:

1. **인증/인가**
   - Core API: Spring Security + JWT
   - AI Orchestrator: JWT 전달
   - UI: 로그인 화면 (향후)

2. **샘플 데이터 시딩**
   - `scripts/seed-data.sh`
   - 고객 100명, 상품 50개, 주문 500개
   - 다양한 status, payment_gateway

3. **테스트 작성**
   - Core API: JUnit 5 + TestContainers (PostgreSQL)
   - AI Orchestrator: pytest + httpx mock
   - UI: Vitest + React Testing Library

4. **Docker 최적화**
   - `infra/docker/docker-compose.prod.yml`
   - Health checks 추가
   - Resource limits 설정
   - Multi-stage builds (UI, Core API)

**검증**: 전체 시스템 E2E 테스트 통과

---

## MVP 기능 범위

**우선순위 1**: 기본 테이블 조회
- "최근 주문 보여줘" → Order 테이블 렌더링
- 페이지네이션 동작 확인

**우선순위 2**: 텍스트 분석
- "어제 정산 실패 분석해줘" → 텍스트 분석 결과

**우선순위 3**: 차트
- "에러 코드별 분포 보여줘" → 막대 그래프

**우선순위 4**: 로그 검색
- "'connection timeout' 검색해줘" → 로그 뷰어

## 기술 스택

**UI**: React 18 + Vite + TypeScript + Tailwind CSS
- 상태 관리: Zustand
- 데이터 페칭: TanStack Query
- 차트: Recharts
- 마크다운: React Markdown

**AI Orchestrator**: Python 3.11 + FastAPI
- LLM: LangChain + OpenAI (GPT-4)
- Vector DB: pgvector + OpenAI Embeddings
- HTTP Client: httpx

**Core API**: Java 21 + Spring Boot 3.2 + Gradle 8.5
- ORM: Spring Data JPA + Hibernate
- 마이그레이션: Flyway
- 보안: Spring Security + JWT

**인프라**: Docker Compose + PostgreSQL 16 + Nginx

## 주요 파일 경로 요약

```
libs/contracts/
├── query-plan.schema.json          # 계약: AI → Core API
├── render-spec.schema.json         # 계약: AI → UI
└── query-result.schema.json        # 계약: Core API → AI

services/core-api/src/main/
├── java/com/chatops/core/
│   ├── CoreApiApplication.java
│   ├── controller/QueryController.java
│   ├── service/
│   │   ├── QueryPlanValidatorService.java
│   │   ├── SqlBuilderService.java
│   │   ├── QueryExecutorService.java
│   │   └── PaginationService.java
│   └── domain/
│       ├── entity/                 # JPA 엔티티
│       └── model/                  # DTO (auto-generated)
└── resources/
    ├── application.yml
    └── db/migration/               # Flyway SQL

services/ai-orchestrator/app/
├── main.py
├── api/v1/chat.py
├── services/
│   ├── query_planner.py            # NL → QueryPlan
│   ├── render_composer.py          # QueryResult → RenderSpec
│   └── rag_service.py              # 문서 검색
└── models/                         # Pydantic (auto-generated)

services/ui/src/
├── App.tsx
├── components/
│   ├── chat/ChatInterface.tsx
│   ├── sidebar/Sidebar.tsx
│   └── renderers/
│       ├── RenderSpecDispatcher.tsx
│       ├── TableRenderer.tsx
│       ├── TextRenderer.tsx
│       ├── ChartRenderer.tsx
│       └── LogRenderer.tsx
└── types/                          # TypeScript (auto-generated)

infra/docker/
├── docker-compose.yml
├── .env.example
└── nginx/nginx.conf

scripts/
├── dev-up.sh
├── dev-down.sh
├── generate-types.sh
└── seed-data.sh
```

## 예상 일정

- Phase 1 (골격): 1주
- Phase 2 (계약): 1주
- Phase 3 (Core API): 2주
- Phase 4 (AI Orchestrator): 2주
- Phase 5 (UI): 2주
- Phase 6 (통합): 2주

**Total**: 약 10주

## 다음 단계

1. Phase 1 시작: 프로젝트 골격 생성
2. 각 서비스 기본 의존성 설정
3. Docker Compose 환경 구축
4. 개발 스크립트 작성

구현 준비 완료!
