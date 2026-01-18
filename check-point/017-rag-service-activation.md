# Check-point 017: RAG 서비스 활성화

**작성일:** 2026-01-18
**상태:** 완료

---

## 1. 문제 상황

### 증상
모든 API 요청에서 다음 경고가 발생:
```
RAG context retrieval failed: 'RAGService' object has no attribute 'search'
```

### 원인
`text_to_sql.py:734`에서 존재하지 않는 `search()` 메서드 호출

```python
# 기존 코드 (에러)
results = await rag_service.search(question, top_k=self._rag_top_k)
```

실제 RAGService에는 `search_docs()` 메서드만 구현되어 있음

---

## 2. 해결 방법

### 수정 파일
`services/ai-orchestrator/app/services/text_to_sql.py`

### 변경 내용 (Line 727-749)

```python
async def _get_rag_context(self, question: str) -> str:
    """RAG 컨텍스트 조회"""
    if not self._rag_enabled:
        return ""

    try:
        rag_service = get_rag_service()
        # search_docs() 메서드 사용 (search()는 존재하지 않음)
        results = await rag_service.search_docs(query=question, k=self._rag_top_k)

        if not results:
            return ""

        context_parts = []
        for doc in results:
            # Document 객체의 속성 접근
            context_parts.append(f"[{doc.doc_type}] {doc.title}: {doc.content[:500]}")

        logger.info(f"RAG context retrieved: {len(results)} documents")
        return "\n\n".join(context_parts)
    except Exception as e:
        logger.warning(f"RAG context retrieval failed: {e}")
        return ""
```

### 주요 변경점
1. `search()` → `search_docs(query=..., k=...)` 메서드 호출
2. `doc['type']` → `doc.doc_type` (딕셔너리 → 객체 속성)
3. RAG 성공 로그 추가

---

## 3. RAG 구현 현황

### 구성요소 상태

| 구성요소 | 상태 | 비고 |
|---------|------|------|
| RAGService 클래스 | ✅ 완전 | 20+ 메서드 구현 |
| pgvector 설정 | ✅ 완전 | HNSW 인덱스, 1536차원 |
| RAG 문서 | ✅ 24개 | entity 7, business_logic 6, error_code 3, faq 8 |
| 임베딩 | ✅ 완료 | OpenAI text-embedding-ada-002 |
| text_to_sql 연동 | ✅ 수정됨 | 메서드명 불일치 해결 |

### 검색 전략 (3단계 폴백)
1. **Vector Search** (HNSW + pgvector) - 기본
2. **Keyword Search** (PostgreSQL tsvector) - 폴백 1
3. **LIKE Search** - 폴백 2

---

## 4. 테스트 결과

### RAG 통합 테스트
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 1개월 결제건 조회"}'
```

### 로그 확인
```
Searching documents for query: 최근 1개월 결제건 조회... (k=3, min_sim=0.55)
Found 3 documents via vector search
RAG context retrieved: 3 documents
```

✅ 에러 없이 정상 동작

---

## 5. 향상 효과

| 영역 | 이전 (LLM-only) | 이후 (RAG 적용) |
|------|----------------|-----------------|
| 테이블/컬럼 정확도 | LLM 추론 의존 | Entity 문서로 정확한 스키마 제공 |
| 비즈니스 규칙 | 없음 | 정산 주기, 수수료율 등 도메인 지식 |
| 조회 패턴 | 없음 | FAQ 문서로 자주 쓰는 쿼리 참조 |
| 에러 처리 | 기본 응답 | 에러 코드별 안내 메시지 |

---

## 6. 관련 파일

| 파일 | 역할 |
|------|------|
| `app/services/text_to_sql.py` | RAG 컨텍스트 조회 (수정됨) |
| `app/services/rag_service.py` | RAG 서비스 구현 |
| `scripts/seed-rag-documents.py` | RAG 문서 시드 스크립트 |

---

## 7. 롤백 방법

문제 발생 시:
```bash
# RAG 비활성화
# .env에서 RAG_ENABLED=false 설정 후
docker-compose -f infra/docker/docker-compose.yml restart ai-orchestrator
```
