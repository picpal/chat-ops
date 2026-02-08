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
- ✅ POST /api/v1/chat (자연어 → QueryPlan/Text-to-SQL → 응답)
- ✅ GET /api/v1/chat/test (연결 테스트)
- ✅ GET /health
- ✅ 자연어 → QueryPlan/Text-to-SQL 변환
- ✅ RenderSpec 생성
- ✅ RAG 문서 검색 (pgvector)
- ✅ 별점 평가 및 분석
- ✅ Quality Answer RAG

## API 엔드포인트

### Chat API
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/chat` | 자연어 채팅 (메인) |
| GET | `/api/v1/chat/test` | Core API 연결 테스트 |
| GET | `/api/v1/chat/config` | 현재 설정 확인 |
| GET | `/api/v1/chat/rag/status` | RAG 서비스 상태 |
| POST | `/api/v1/chat/rag/search` | RAG 문서 검색 테스트 |
| POST | `/api/v1/chat/download` | 대용량 결과 다운로드 |

### Documents API
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/documents` | 문서 목록 조회 |
| POST | `/api/v1/documents` | 문서 생성 |
| GET | `/api/v1/documents/{id}` | 문서 상세 조회 |
| PUT | `/api/v1/documents/{id}` | 문서 수정 |
| DELETE | `/api/v1/documents/{id}` | 문서 삭제 |
| POST | `/api/v1/documents/{id}/review` | 문서 승인/반려 |

### Ratings API
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/ratings` | 별점 저장 |
| GET | `/api/v1/ratings/{requestId}` | 별점 조회 |
| GET | `/api/v1/ratings/analytics/summary` | 별점 요약 통계 |
| GET | `/api/v1/ratings/analytics/distribution` | 별점 분포 |
| GET | `/api/v1/ratings/analytics/trend` | 별점 추이 |
| GET | `/api/v1/ratings/analytics/details` | 별점 상세 목록 |

### Settings API
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/settings/quality-answer-rag/status` | Quality Answer RAG 상태 |
| PUT | `/api/v1/settings/quality-answer-rag` | Quality Answer RAG 설정 업데이트 |
| GET | `/api/v1/settings/{key}` | 일반 설정 조회 |
| PUT | `/api/v1/settings/{key}` | 일반 설정 업데이트 |

## Quality Answer RAG

높은 별점(4~5점) 답변을 자동 저장하고 유사 질문 시 참고하여 답변 품질 향상.

### 데이터 흐름
```
[별점 4~5점] → rating_service → quality_answer_service → documents 테이블

[새 질문] → knowledge_answer intent → quality_answer_service.search() → LLM 프롬프트 보강
```

### 관련 서비스
- `app/services/settings_service.py` - 설정 CRUD
- `app/services/quality_answer_service.py` - 고품질 답변 저장/검색
- `app/api/v1/settings.py` - Settings REST API
