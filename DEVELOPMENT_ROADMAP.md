# ChatOps 개발 로드맵 (단계별 진행)

> **접근법**: 전체 골격을 한번에 만들지 않고, 각 단계마다 동작을 확인하면서 점진적으로 구축

## 진행 원칙

- ✅ 각 Step마다 실제 동작 확인
- ✅ 문제 발생 시 즉시 피드백
- ✅ 불필요한 복잡성 방지
- ✅ UI는 별도 세션에서 병렬 진행

---

## Step 1: Core API 단독 실행 ⬅️ **현재 단계**

**목표**: Core API만 띄워서 mock 응답 확인

**생성할 구조**:
```
services/core-api/
├── build.gradle
├── settings.gradle
├── src/main/
│   ├── java/com/chatops/core/
│   │   ├── CoreApiApplication.java
│   │   └── controller/
│   │       └── QueryController.java (mock 응답)
│   └── resources/
│       └── application.yml
└── src/test/
```

**주요 작업**:
1. Gradle 프로젝트 초기화
2. Spring Boot 3.2 + Java 21 설정
3. 최소 의존성:
   - spring-boot-starter-web
   - lombok
4. Mock QueryController 작성
   - `POST /api/v1/query/start` → mock QueryResult
   - `GET /api/v1/query/page/{token}` → 404

**검증**:
```bash
cd services/core-api
./gradlew bootRun

# 다른 터미널에서
curl -X POST http://localhost:8080/api/v1/query/start \
  -H "Content-Type: application/json" \
  -d '{"requestId":"test-1","entity":"Order","operation":"list"}'
```

**예상 응답**:
```json
{
  "requestId": "test-1",
  "status": "success",
  "data": {
    "rows": [
      {"orderId": 1, "totalAmount": 100.00, "status": "PAID"}
    ]
  }
}
```

---

## Step 2: AI Orchestrator 추가 + 통신 테스트

**목표**: AI Orchestrator → Core API 호출 동작 확인

**생성할 구조**:
```
services/ai-orchestrator/
├── pyproject.toml
├── app/
│   ├── main.py
│   └── api/v1/
│       └── chat.py
└── tests/
```

**주요 작업**:
1. FastAPI 프로젝트 초기화
2. 최소 의존성:
   - fastapi
   - uvicorn
   - httpx (Core API 호출용)
3. Mock chat endpoint
   - `POST /api/v1/chat`
   - Core API 호출 → 응답 그대로 반환

**검증**:
```bash
cd services/ai-orchestrator
uvicorn app.main:app --reload --port 8000

# 다른 터미널에서
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"최근 주문 보여줘"}'
```

---

## Step 3: PostgreSQL + 실제 데이터

**목표**: Mock 대신 실제 DB 쿼리

**생성할 구조**:
```
services/core-api/src/main/resources/
└── db/migration/
    └── V1__create_orders.sql

infra/docker/
├── docker-compose.yml (PostgreSQL만)
└── .env.example
```

**주요 작업**:
1. Docker Compose로 PostgreSQL 16 시작
2. Core API에 의존성 추가:
   - spring-boot-starter-data-jpa
   - postgresql
   - flyway-core
3. Flyway 마이그레이션: orders 테이블
4. 샘플 데이터 5개 row 삽입
5. JPA Entity: Order.java
6. Repository: OrderRepository
7. QueryController에서 실제 DB 조회

**검증**:
```bash
docker-compose up -d postgres
./gradlew bootRun

curl http://localhost:8080/api/v1/query/start
# → 실제 DB 데이터 5개 반환
```

---

## Step 4: JSON Schema 계약 + 타입 생성

**목표**: 서비스 간 계약 정의 및 타입 안정성 확보

**생성할 구조**:
```
libs/contracts/
├── query-plan.schema.json
├── render-spec.schema.json
└── query-result.schema.json

scripts/
└── generate-types.sh
```

**주요 작업**:
1. 3개 JSON Schema 작성
2. 타입 생성 스크립트:
   - Python: datamodel-code-generator
   - Java: jsonschema2pojo Gradle plugin
3. 기존 코드를 생성된 타입으로 리팩토링

**검증**:
```bash
./scripts/generate-types.sh
# → services/core-api/src/main/java/com/chatops/core/domain/model/
# → services/ai-orchestrator/app/models/
```

---

## Step 5: QueryPlan 실행 엔진

**목표**: QueryPlan을 받아서 실제 SQL로 변환 및 실행

**주요 작업**:
1. QueryPlanValidatorService
2. SqlBuilderService (논리 엔티티 → SQL)
3. EntityMappingConfig (application.yml)
4. QueryExecutorService
5. PaginationService (queryToken)

**검증**:
```bash
curl -X POST http://localhost:8080/api/v1/query/start \
  -d '{
    "requestId": "req-1",
    "entity": "Order",
    "operation": "list",
    "filters": [{"field":"status","operator":"eq","value":"PAID"}],
    "limit": 10
  }'
```

---

## Step 6: AI 자연어 처리 (LangChain)

**목표**: 자연어 → QueryPlan 변환

**주요 작업**:
1. AI Orchestrator에 의존성 추가:
   - langchain
   - langchain-openai
2. QueryPlannerService 구현
3. LLM 프롬프트 작성
4. RenderComposerService (QueryResult → RenderSpec)

**검증**:
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -d '{"message":"어제 결제 성공한 주문 10개 보여줘"}'

# AI가 자동으로 QueryPlan 생성 → Core API 호출 → RenderSpec 반환
```

---

## Step 7: RAG 문서 검색 (pgvector)

**목표**: 컨텍스트 기반 쿼리 개선

**주요 작업**:
1. PostgreSQL에 pgvector 확장 설치
2. 문서 임베딩 테이블 생성
3. RAGService 구현
4. 초기 문서 시딩:
   - 엔티티 설명
   - 비즈니스 로직
   - 에러 코드

**검증**:
```python
# AI Orchestrator에서
docs = await rag_service.search_docs("결제 실패 원인")
# → 관련 문서 3개 반환
```

---

## Step 8: 통합 테스트 & 최적화

**목표**: E2E 플로우 안정화

**주요 작업**:
1. 단위 테스트 작성
2. 통합 테스트 (TestContainers)
3. Docker Compose 최적화
4. Nginx reverse proxy 추가
5. 환경변수 관리 개선
6. 에러 핸들링 강화
7. 로깅 및 모니터링

---

## UI 개발 (별도 세션 병렬 진행)

UI는 별도로 진행하며, Step 2 완료 후 언제든 연동 가능:

**최소 요구사항**:
- `POST /api/v1/chat` 호출
- RenderSpec 기반 렌더링:
  - TableRenderer
  - TextRenderer
  - ChartRenderer
  - LogRenderer

---

## 현재 진행 상황

- [ ] Step 1: Core API 단독 실행
- [ ] Step 2: AI Orchestrator 추가
- [ ] Step 3: PostgreSQL + 실제 데이터
- [ ] Step 4: JSON Schema 계약
- [ ] Step 5: QueryPlan 실행 엔진
- [ ] Step 6: AI 자연어 처리
- [ ] Step 7: RAG 문서 검색
- [ ] Step 8: 통합 테스트

---

## 다음 액션

**Step 1 시작**: Core API 프로젝트 생성 및 Mock 응답 구현
