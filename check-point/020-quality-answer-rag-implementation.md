# Check Point 020: Quality Answer RAG 구현

## 개요

높은 별점(4~5점) 답변을 RAG에 저장하고, 새 질문 시 유사 고품질 답변을 참고하여 답변 품질을 향상시키는 기능 구현.

## 배경

- 사용자가 높은 별점을 부여한 답변은 품질이 검증된 것으로 간주
- 유사한 질문이 반복될 때 일관된 품질의 답변 제공 필요
- 기존 RAG 인프라(pgvector) 재활용으로 최소 비용 구현

## 설계 결정

| 항목 | 선택 | 이유 |
|------|------|------|
| 저장소 | 기존 `documents` 테이블 재사용 | pgvector 인프라 재활용, 마이그레이션 최소화 |
| doc_type | `quality_answer` | 기존 RAG 문서와 구분 |
| 토글 상태 | DB `settings` 테이블 | 서버 재시작 후에도 유지, UI에서 관리 가능 |
| 검색 시점 | `knowledge_answer` intent 시 | 가장 관련성 높은 시점, 불필요한 오버헤드 방지 |

## 구현 내용

### 1. DB 마이그레이션
- `V22__create_settings_table.sql` 생성
- `settings` 테이블: key-value(JSONB) 기반 설정 저장
- 기본값: `{"enabled": true, "minRating": 4}`

### 2. AI Orchestrator (Python)

**신규 파일:**
- `app/models/settings.py` - Pydantic 모델
- `app/services/settings_service.py` - 설정 CRUD
- `app/services/quality_answer_service.py` - 고품질 답변 저장/검색
- `app/api/v1/settings.py` - REST API 엔드포인트

**수정 파일:**
- `app/main.py` - settings router 등록
- `app/services/rating_service.py` - 별점 저장 시 quality answer 자동 저장
- `app/api/v1/chat.py` - knowledge_answer 생성 시 quality context 추가

### 3. UI (React)

**신규 파일:**
- `src/types/settings.ts` - TypeScript 타입
- `src/api/settings.ts` - API 클라이언트
- `src/hooks/useSettings.ts` - React Query 훅
- `src/components/scenarios/QualityAnswerToggle.tsx` - 토글 컴포넌트

**수정 파일:**
- `src/components/scenarios/ScenariosPage.tsx` - 헤더에 토글 배치

### 4. 테스트
- `tests/test_settings_service.py` - Settings 서비스 테스트
- `tests/test_quality_answer_service.py` - Quality Answer 서비스 테스트

## 데이터 흐름

### 저장 흐름
```
사용자 별점 저장 (rating >= 4)
        │
        ▼
rating_service.save_rating()
        │
        ├─ 기존: message_ratings 테이블에 저장
        │
        └─ 신규: quality_answer_service.save_quality_answer()
                        │
                        ▼
                documents 테이블 (doc_type='quality_answer')
                - title: "[{rating}점] {질문 앞 50자}..."
                - content: "## 질문\n{질문}\n\n## 답변\n{답변}"
                - metadata: {request_id, session_id, rating, ...}
                - embedding: 질문 기반 벡터 (유사 질문 검색용)
```

### 검색 흐름
```
사용자 질문 (knowledge_answer intent)
        │
        ▼
_generate_knowledge_answer()
        │
        ├─ 기존: rag_service.search_docs() → 참고 문서
        │
        └─ 신규: quality_answer_service.search_similar_answers()
                        │
                        ▼
                유사 고품질 답변 (k=2, min_similarity=0.6)
                        │
                        ▼
                format_quality_context()
                "## 참고 답변 예시\n..."
                        │
                        ▼
                LLM 프롬프트에 컨텍스트 추가
```

## API 설계

### GET `/api/v1/settings/quality-answer-rag/status`
```json
{
  "enabled": true,
  "minRating": 4,
  "storedCount": 42,
  "lastUpdated": "2026-02-06T10:30:00Z"
}
```

### PUT `/api/v1/settings/quality-answer-rag`
```json
// Request
{ "enabled": false }

// Response
{
  "key": "quality_answer_rag",
  "value": { "enabled": false, "minRating": 4 },
  "updatedAt": "2026-02-06T10:35:00Z"
}
```

## UI 배치

```
┌─────────────────────────────────────────────────────────┐
│ 시나리오 관리                                            │
│                                                         │
│ [토글 ON/OFF] Quality Answer RAG  고품질 답변 참고 활성화  │
│                                                         │
│ ┌─────────────┐  [오늘] [7일] [30일] [전체]              │
│ │ 요약 카드들  │                                         │
│ └─────────────┘                                         │
└─────────────────────────────────────────────────────────┘
```

## 검증 방법

### 단위 테스트
- `test_settings_service.py` - 설정 CRUD
- `test_quality_answer_service.py` - 저장/검색 로직

### 통합 테스트
1. 별점 5점 저장 → documents 테이블에 quality_answer 생성 확인
2. 유사 질문 입력 → 고품질 답변 검색 확인
3. 토글 OFF → 기능 비활성화 확인

### E2E 테스트
1. 채팅에서 별점 5점 평가
2. 시나리오 관리 페이지에서 토글 확인
3. 유사 질문 입력 시 답변 품질 확인

## 향후 개선 사항

1. **중복 방지**: 매우 유사한 질문(similarity > 0.95) 저장 스킵
2. **만료 정책**: 오래된 quality_answer 자동 정리
3. **가중치 조정**: 별점 5점 답변에 더 높은 가중치
4. **분석 대시보드**: quality_answer 활용 통계 시각화

## 관련 문서

- CLAUDE.md § 11. Quality Answer RAG
- README.md § Features
- services/ai-orchestrator/README.md § API 엔드포인트
