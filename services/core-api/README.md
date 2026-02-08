# Core API

> Spring Boot 기반 QueryPlan 검증, SQL 빌드 및 실행 서비스

## Tech Stack

- **Java 21** + Spring Boot 3.2
- **Gradle** 빌드 시스템
- **PostgreSQL** (pgvector 확장)
- **Flyway** DB 마이그레이션
- **Docker** 컨테이너화

## 실행 방법

### 1. 서버 시작

```bash
cd services/core-api
./gradlew bootRun
```

서버가 http://localhost:8080 에서 시작됩니다.

### 2. Health Check

```bash
curl http://localhost:8080/api/v1/query/health
```

**예상 응답**:
```json
{
  "status": "UP",
  "service": "core-api"
}
```

### 3. 테스트

```bash
./gradlew test
```

## 현재 구현 상태

- ✅ Spring Boot 3.2 + Java 21
- ✅ QueryPlan 검증 (Validator)
- ✅ SQL Builder (QueryPlan → SQL)
- ✅ Flyway DB 마이그레이션
- ✅ pgvector 확장 (RAG용)
- ✅ 페이지네이션 (QueryToken)
- ✅ 집계 쿼리 지원

## API 엔드포인트

### Query API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/query/start` | QueryPlan 실행 (첫 페이지) |
| GET | `/api/v1/query/page/{token}` | 다음 페이지 조회 |
| GET | `/api/v1/query/health` | 헬스 체크 |

### 요청 예시

```bash
curl -X POST http://localhost:8080/api/v1/query/start \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "test-123",
    "entity": "Payment",
    "operation": "list",
    "filters": [
      {"field": "status", "operator": "eq", "value": "DONE"}
    ],
    "timeRange": {
      "field": "requestedAt",
      "start": "2026-02-01T00:00:00Z",
      "end": "2026-02-07T23:59:59Z"
    },
    "limit": 50
  }'
```

## DB 마이그레이션

마이그레이션 파일 위치: `src/main/resources/db/migration/`

| 버전 | 설명 |
|------|------|
| V1 | 초기 스키마 (orders) |
| V2-V14 | PG 결제 도메인 테이블 |
| V15 | pgvector 확장 |
| V16-V21 | RAG 문서, 별점 테이블 |
| V22 | settings 테이블 (Quality Answer RAG) |

### 마이그레이션 실행

```bash
# Docker 환경에서 자동 실행
docker-compose up -d

# 로컬 환경
./gradlew flywayMigrate
```

## 프로젝트 구조

```
src/main/java/com/chatops/core/
├── config/           # 설정 클래스
├── controller/       # REST 컨트롤러
├── dto/              # 요청/응답 DTO
├── entity/           # JPA 엔티티
├── exception/        # 예외 처리
├── repository/       # JPA 리포지토리
├── service/          # 비즈니스 로직
│   ├── QueryService.java
│   ├── QueryPlanValidator.java
│   └── SqlBuilder.java
└── util/             # 유틸리티
```

## 핵심 서비스

### QueryPlanValidator

QueryPlan JSON을 검증:
- 필수 필드 검증 (entity, operation)
- 논리명 → 물리명 변환 (payments → tbl_payments)
- 시계열 테이블 timeRange 필수 검증

### SqlBuilder

QueryPlan을 SQL로 변환:
- SELECT/WHERE/ORDER BY/LIMIT 생성
- 집계 쿼리 지원 (COUNT, SUM, AVG)
- 페이지네이션 처리

## 환경 변수

```properties
# application.properties
spring.datasource.url=jdbc:postgresql://localhost:5432/chatops
spring.datasource.username=postgres
spring.datasource.password=postgres
spring.flyway.enabled=true
```

## 트러블슈팅

### Flyway 마이그레이션 오류

```bash
# 마이그레이션 상태 확인
./gradlew flywayInfo

# 마이그레이션 수리 (체크섬 불일치 시)
./gradlew flywayRepair
```

### 연결 오류

1. PostgreSQL 실행 확인: `docker ps`
2. 포트 확인: `lsof -i :5432`
3. 환경 변수 확인: `application.properties`
