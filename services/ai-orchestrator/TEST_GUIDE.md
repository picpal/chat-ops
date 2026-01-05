# ChatOps 테스트 가이드

이 문서는 ChatOps 프로젝트의 테스트 실행 방법과 테스트 구조를 설명합니다.

---

## 테스트 현황 요약

| 서비스 | 테스트 수 | 프레임워크 | 상태 |
|--------|----------|------------|------|
| **Core API** | 81개 | JUnit 5 | ✅ 통과 |
| **AI Orchestrator** | 45개 | pytest | ✅ 통과 |
| **총합** | **126개** | - | ✅ |

---

## 1. AI Orchestrator 테스트

### 1.1 테스트 실행

```bash
cd services/ai-orchestrator

# 모든 테스트 실행
python3 -m pytest tests/ -v

# 특정 파일 테스트
python3 -m pytest tests/test_query_planner.py -v

# 특정 클래스 테스트
python3 -m pytest tests/test_query_planner.py::TestQueryPlannerService -v

# 특정 메서드 테스트
python3 -m pytest tests/test_query_planner.py::TestQueryPlannerService::TestFallbackPlan::test_fallback_default_entity_is_order -v

# 커버리지 포함 (pytest-cov 설치 필요)
python3 -m pytest tests/ --cov=app --cov-report=html
```

### 1.2 테스트 파일 구조

```
tests/
├── __init__.py
├── conftest.py              # 공통 fixtures (TestClient, Mock 설정)
├── test_main.py             # Health, Config 엔드포인트 (3개)
├── test_query_planner.py    # QueryPlannerService (26개)
├── test_rag_service.py      # RAGService (14개)
└── test_render_composer.py  # RenderComposerService (5개)
```

### 1.3 테스트 카테고리

#### test_query_planner.py

| 클래스 | 설명 | 테스트 수 |
|--------|------|----------|
| `TestFallbackPlan` | 키워드 기반 fallback 로직 | 5 |
| `TestConvertToDict` | QueryPlan → Dict 변환 | 5 |
| `TestSystemPrompt` | 시스템 프롬프트 생성 | 3 |
| `TestEntitySchemas` | 엔티티 스키마 상수 | 3 |
| `TestPydanticModels` | Pydantic 모델 검증 | 4 |
| `TestQueryPlannerSingleton` | 싱글톤 패턴 | 1 |
| `TestGenerateQueryPlanWithMock` | Mock 기반 통합 테스트 | 2 |

#### test_rag_service.py

| 클래스 | 설명 | 테스트 수 |
|--------|------|----------|
| `TestDocument` | Document 데이터클래스 | 3 |
| `TestRAGServiceFormatContext` | 컨텍스트 포맷팅 | 4 |
| `TestRAGServiceInit` | 서비스 초기화 | 2 |
| `TestRAGServiceSingleton` | 싱글톤 패턴 | 1 |
| `TestRAGServiceSearchWithMock` | Mock 기반 검색 | 2 |
| `TestRAGServiceAddDocument` | 문서 추가 | 1 |

### 1.4 Mock 사용 가이드

```python
# conftest.py에 정의된 fixtures 사용
@pytest.fixture
def mock_core_api():
    """Core API 응답 Mock"""
    with patch("app.api.v1.chat.call_core_api") as mock:
        mock.return_value = {"status": "success", "data": {...}}
        yield mock

@pytest.fixture
def mock_rag_service():
    """RAG 서비스 Mock"""
    with patch("app.services.query_planner.get_rag_service") as mock:
        mock_instance = MagicMock()
        mock_instance.search_docs.return_value = []
        mock.return_value = mock_instance
        yield mock_instance
```

### 1.5 비동기 테스트

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """비동기 함수 테스트"""
    result = await some_async_function()
    assert result is not None
```

---

## 2. Core API 테스트

### 2.1 테스트 실행

```bash
cd services/core-api

# 모든 테스트 실행
./gradlew test

# 테스트 리포트 확인
open build/reports/tests/test/index.html

# 특정 테스트 클래스 실행
./gradlew test --tests "SqlBuilderServiceUnitTest"

# 특정 테스트 메서드 실행
./gradlew test --tests "SqlBuilderServiceUnitTest.BasicSelectQuery.shouldBuildBasicOrderQuery"

# 커버리지 포함 (JaCoCo 설정 필요)
./gradlew test jacocoTestReport
```

### 2.2 테스트 파일 구조

```
src/test/java/com/chatops/core/
├── controller/
│   └── QueryControllerTest.java        # API 엔드포인트 테스트
├── domain/repository/
│   └── OrderRepositoryTest.java        # JPA 레포지토리 테스트
└── service/
    ├── SqlBuilderServiceUnitTest.java          # SQL 빌더 (순수 단위)
    ├── SqlBuilderServiceTest.java              # SQL 빌더 (통합)
    ├── QueryPlanValidatorServiceUnitTest.java  # 검증 서비스 (순수 단위)
    └── PaginationServiceUnitTest.java          # 페이징 서비스 (Mock 사용)

src/test/resources/
└── application-test.yml     # 테스트 환경 설정
```

### 2.3 테스트 카테고리

#### SqlBuilderServiceUnitTest.java (순수 단위 테스트)

| 중첩 클래스 | 설명 | 테스트 수 |
|-------------|------|----------|
| `BasicSelectQuery` | 기본 SELECT 쿼리 생성 | 4 |
| `FilterConditions` | 필터 조건 처리 (eq, in, like 등) | 7 |
| `OrderByConditions` | 정렬 조건 처리 | 2 |
| `AggregateQuery` | 집계 쿼리 (GROUP BY) | 4 |
| `FieldMapping` | 논리→물리 필드 매핑 | 1 |
| `ExceptionHandling` | 예외 처리 | 3 |

#### QueryPlanValidatorServiceUnitTest.java

| 중첩 클래스 | 설명 | 테스트 수 |
|-------------|------|----------|
| `RequiredFieldValidation` | 필수 필드 검증 | 3 |
| `EntityValidation` | 엔티티 검증 | 2 |
| `OperationValidation` | Operation 검증 | 4 |
| `LimitValidation` | Limit 범위 검증 | 3 |
| `FilterValidation` | 필터 조건 검증 | 5 |
| `AggregationValidation` | 집계 함수 검증 | 2 |
| `OrderByValidation` | 정렬 조건 검증 | 2 |
| `TimeRangeValidation` | 시간 범위 검증 | 3 |
| `ComplexQueryPlanValidation` | 복합 검증 | 2 |

#### PaginationServiceUnitTest.java

| 중첩 클래스 | 설명 | 테스트 수 |
|-------------|------|----------|
| `TokenCreation` | 토큰 생성 | 2 |
| `NextPageTokenCreation` | 다음 페이지 토큰 | 2 |
| `TokenRetrieval` | 토큰 조회 | 1 |
| `TokenInvalidation` | 토큰 무효화 | 1 |
| `PaginationContext` | 컨텍스트 검증 | 4 |
| `ExpiredTokenCleanup` | 만료 토큰 정리 | 1 |

### 2.4 순수 단위 테스트 vs 통합 테스트

#### 순수 단위 테스트 (권장)

```java
// Spring Context 없이 직접 의존성 주입
class SqlBuilderServiceUnitTest {
    private SqlBuilderService service;
    private ChatOpsProperties properties;

    @BeforeEach
    void setUp() {
        properties = createTestProperties();  // 직접 생성
        service = new SqlBuilderService(properties);
    }
}
```

**장점**:
- 빠른 실행 속도 (Spring Context 로드 불필요)
- 격리된 테스트 (외부 의존성 없음)
- 명확한 테스트 범위

#### 통합 테스트

```java
// Spring Context 사용
@SpringBootTest
@ActiveProfiles("test")
class SqlBuilderServiceTest {
    @Autowired
    private SqlBuilderService service;
}
```

**장점**:
- 실제 환경과 유사
- DI, 설정 파일 연동 테스트
- 컴포넌트 간 상호작용 테스트

### 2.5 Mockito 사용 가이드

```java
@ExtendWith(MockitoExtension.class)
class PaginationServiceUnitTest {

    @Mock
    private SqlBuilderService sqlBuilderService;

    @BeforeEach
    void setUp() {
        service = new PaginationService(properties, sqlBuilderService);
    }

    @Test
    void shouldCreateToken() {
        // Mock 설정
        when(sqlBuilderService.buildQuery(any()))
            .thenReturn(new SqlQuery("SELECT ...", List.of()));

        // 테스트 실행
        String token = service.createToken(...);

        // 검증
        assertThat(token).startsWith("qt_");
    }
}
```

---

## 3. 테스트 작성 가이드라인

### 3.1 테스트 네이밍

```java
// Java - BDD 스타일
@Test
@DisplayName("Order 엔티티 기본 조회")
void shouldBuildBasicOrderQuery() { }

// Python - 명확한 설명
def test_fallback_default_entity_is_order(self):
    """기본 엔티티는 Order"""
```

### 3.2 Arrange-Act-Assert 패턴

```java
@Test
void shouldFilterByStatus() {
    // Arrange (준비)
    Map<String, Object> queryPlan = Map.of(
        "entity", "Order",
        "filters", List.of(Map.of("field", "status", "operator", "eq", "value", "PAID"))
    );

    // Act (실행)
    SqlQuery result = service.buildQuery(queryPlan);

    // Assert (검증)
    assertThat(result.getSql()).contains("status = ?");
    assertThat(result.getParams()).contains("PAID");
}
```

### 3.3 테스트 데이터 팩토리

```java
// 테스트용 설정 생성 메서드
private ChatOpsProperties createTestProperties() {
    ChatOpsProperties props = new ChatOpsProperties();
    // ... 설정
    return props;
}
```

### 3.4 예외 테스트

```java
// Java
@Test
void shouldThrowForUnknownEntity() {
    assertThatThrownBy(() -> service.buildQuery(invalidPlan))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Unknown entity");
}
```

```python
# Python
def test_raises_on_invalid_input():
    with pytest.raises(ValueError) as exc_info:
        service.process(invalid_input)
    assert "Invalid" in str(exc_info.value)
```

---

## 4. CI/CD 통합

### 4.1 GitHub Actions 예시

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test-core-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
      - name: Run tests
        run: |
          cd services/core-api
          ./gradlew test

  test-ai-orchestrator:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd services/ai-orchestrator
          pip install -e ".[test]"
      - name: Run tests
        run: |
          cd services/ai-orchestrator
          pytest tests/ -v
```

### 4.2 커버리지 임계값

| 서비스 | 목표 커버리지 |
|--------|---------------|
| Core API | 80% |
| AI Orchestrator | 75% |

---

## 5. 트러블슈팅

### 5.1 테스트 실패 시

1. **로그 확인**: `--info` 또는 `-v` 옵션 사용
2. **단일 테스트 실행**: 실패한 테스트만 격리 실행
3. **캐시 정리**: `./gradlew clean` 또는 `pytest --cache-clear`

### 5.2 일반적인 문제

| 문제 | 해결책 |
|------|--------|
| Spring Context 로드 실패 | `application-test.yml` 확인 |
| Mock 설정 오류 | `@ExtendWith(MockitoExtension.class)` 확인 |
| 비동기 테스트 실패 | `@pytest.mark.asyncio` 확인 |
| DB 연결 오류 | H2 in-memory DB 설정 확인 |

### 5.3 테스트 환경 설정

```yaml
# Core API: application-test.yml
spring:
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
  jpa:
    hibernate:
      ddl-auto: create-drop
```

```python
# AI Orchestrator: conftest.py
@pytest.fixture
def client():
    return TestClient(app)
```

---

## 6. 참고 자료

- [JUnit 5 User Guide](https://junit.org/junit5/docs/current/user-guide/)
- [pytest Documentation](https://docs.pytest.org/)
- [Mockito Documentation](https://site.mockito.org/)
- [AssertJ Documentation](https://assertj.github.io/doc/)
