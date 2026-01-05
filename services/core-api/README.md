# Core API - Step 1

> Mock 응답을 반환하는 기본 Spring Boot API

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
  "service": "core-api",
  "step": "1-mock"
}
```

### 3. Query 테스트

```bash
curl -X POST http://localhost:8080/api/v1/query/start \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "test-123",
    "entity": "Order",
    "operation": "list",
    "limit": 10
  }'
```

**예상 응답**:
```json
{
  "requestId": "test-123",
  "status": "success",
  "data": {
    "rows": [
      {
        "orderId": 1,
        "customerId": 101,
        "orderDate": "2024-01-05T10:30:00",
        "totalAmount": 2499.0,
        "status": "PAID",
        "paymentGateway": "Stripe"
      },
      {
        "orderId": 2,
        "customerId": 102,
        "orderDate": "2024-01-05T11:15:00",
        "totalAmount": 199.0,
        "status": "PENDING",
        "paymentGateway": "PayPal"
      },
      {
        "orderId": 3,
        "customerId": 103,
        "orderDate": "2024-01-04T16:45:00",
        "totalAmount": 1299.99,
        "status": "SHIPPED",
        "paymentGateway": "Stripe"
      }
    ]
  },
  "metadata": {
    "executionTimeMs": 45,
    "rowsReturned": 3
  }
}
```

## 현재 구현 상태

- ✅ Spring Boot 3.2 + Java 21
- ✅ Mock QueryController
- ✅ POST /api/v1/query/start (mock 데이터 반환)
- ✅ GET /api/v1/query/health
- ⬜ GET /api/v1/query/page/{token} (404 반환)

## 다음 단계

Step 2에서 AI Orchestrator를 추가하여 이 API를 호출합니다.
