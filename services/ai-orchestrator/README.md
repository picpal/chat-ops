# AI Orchestrator - Step 2

> FastAPI 서비스가 Core API와 통신하여 쿼리 결과를 반환

## 실행 방법

### 1. 의존성 설치

```bash
cd services/ai-orchestrator
pip install -e .
```

또는 uv 사용 시:
```bash
uv pip install -e .
```

### 2. 서버 시작

```bash
uvicorn app.main:app --reload --port 8000
```

서버가 http://localhost:8000 에서 시작됩니다.

### 3. Core API 연결 테스트

```bash
curl http://localhost:8000/api/v1/chat/test
```

**예상 응답**:
```json
{
  "core_api_status": "reachable",
  "core_api_response": {
    "status": "UP",
    "service": "core-api",
    "step": "1-mock"
  }
}
```

### 4. 채팅 테스트

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "최근 주문 보여줘"
  }'
```

**예상 응답**:
```json
{
  "query_result": {
    "requestId": "req-...",
    "status": "success",
    "data": {
      "rows": [...]
    }
  },
  "conversation_id": "new-conversation",
  "original_message": "최근 주문 보여줘"
}
```

## 현재 구현 상태

- ✅ FastAPI 기본 설정
- ✅ POST /api/v1/chat (Core API 호출)
- ✅ GET /api/v1/chat/test (연결 테스트)
- ✅ GET /health
- ⬜ 자연어 → QueryPlan 변환 (Step 6에서 구현)
- ⬜ RenderSpec 생성 (Step 6에서 구현)

## 다음 단계

Step 3에서 PostgreSQL을 추가하고 실제 DB 데이터를 조회합니다.
