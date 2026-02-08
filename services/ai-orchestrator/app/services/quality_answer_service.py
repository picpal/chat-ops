"""
Quality Answer 서비스 - 고품질 답변 RAG 저장/검색
"""

import json
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

import psycopg
from pgvector.psycopg import register_vector

logger = logging.getLogger(__name__)


@dataclass
class QualityAnswer:
    """고품질 답변 문서"""
    id: int
    title: str
    content: str
    metadata: Dict[str, Any]
    similarity: float = 0.0
    created_at: Optional[datetime] = None


class QualityAnswerService:
    """
    고품질 답변 RAG 서비스

    높은 별점(4~5점) 답변을 documents 테이블에 저장하고,
    새 질문 시 유사 고품질 답변을 검색하여 답변 품질 향상
    """

    DOC_TYPE = "quality_answer"

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://chatops_user:chatops_pass@localhost:5432/chatops"
        )
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.embedding_model = "text-embedding-ada-002"
        self._openai_client = None

    def _get_openai_client(self):
        """OpenAI 클라이언트 lazy initialization"""
        if self._openai_client is None and self.openai_api_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_api_key)
            except ImportError:
                logger.warning("openai package not installed")
        return self._openai_client

    def _get_connection(self):
        """PostgreSQL 연결 생성"""
        conn = psycopg.connect(self.database_url)
        register_vector(conn)
        return conn

    async def _create_embedding(self, text: str) -> List[float]:
        """OpenAI로 텍스트 임베딩 생성"""
        client = self._get_openai_client()
        if not client:
            raise ValueError("OpenAI client not available")

        response = client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    async def save_quality_answer(
        self,
        request_id: str,
        user_question: str,
        ai_response: str,
        rating: int,
        session_id: str
    ) -> Optional[int]:
        """
        고품질 답변 저장

        Args:
            request_id: 요청 ID
            user_question: 사용자 질문
            ai_response: AI 응답
            rating: 별점
            session_id: 세션 ID

        Returns:
            생성된 문서 ID 또는 None (실패 시)
        """
        logger.info(f"Saving quality answer: request_id={request_id}, rating={rating}")

        try:
            # 제목: 질문의 앞 50자
            title = f"[{rating}점] {user_question[:50]}..." if len(user_question) > 50 else f"[{rating}점] {user_question}"

            # 컨텐츠: Q&A 형식
            content = f"""## 질문
{user_question}

## 답변
{ai_response}"""

            # 메타데이터
            metadata = {
                "request_id": request_id,
                "session_id": session_id,
                "rating": rating,
                "question_length": len(user_question),
                "answer_length": len(ai_response),
                "saved_at": datetime.utcnow().isoformat()
            }

            # 임베딩 생성 (질문 + 답변 요약)
            embedding = None
            if self.openai_api_key:
                try:
                    # 임베딩은 질문을 기반으로 생성 (유사 질문 검색용)
                    embedding = await self._create_embedding(user_question)
                except Exception as e:
                    logger.warning(f"Failed to create embedding for quality answer: {e}")

            # documents 테이블에 저장
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    if embedding:
                        cur.execute(
                            """
                            INSERT INTO documents (doc_type, title, content, embedding, metadata, status)
                            VALUES (%s, %s, %s, %s::vector, %s::jsonb, 'active')
                            RETURNING id
                            """,
                            (self.DOC_TYPE, title, content, embedding, json.dumps(metadata))
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO documents (doc_type, title, content, metadata, status)
                            VALUES (%s, %s, %s, %s::jsonb, 'active')
                            RETURNING id
                            """,
                            (self.DOC_TYPE, title, content, json.dumps(metadata))
                        )

                    doc_id = cur.fetchone()[0]
                    conn.commit()

            logger.info(f"Quality answer saved with ID: {doc_id}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to save quality answer: {e}", exc_info=True)
            return None

    async def search_similar_answers(
        self,
        query: str,
        k: int = 2,
        min_similarity: float = 0.6
    ) -> List[QualityAnswer]:
        """
        유사 고품질 답변 검색

        Args:
            query: 검색 쿼리 (사용자 질문)
            k: 반환할 문서 개수
            min_similarity: 최소 유사도 임계값

        Returns:
            유사도 순으로 정렬된 고품질 답변 리스트
        """
        logger.info(f"Searching similar quality answers for: {query[:50]}...")

        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set, cannot search quality answers")
            return []

        try:
            # 쿼리 임베딩 생성
            query_embedding = await self._create_embedding(query)

            documents = []
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            id, title, content, metadata,
                            1 - (embedding <=> %s::vector) as similarity,
                            created_at
                        FROM documents
                        WHERE doc_type = %s
                          AND embedding IS NOT NULL
                          AND status = 'active'
                          AND 1 - (embedding <=> %s::vector) >= %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (query_embedding, self.DOC_TYPE, query_embedding, min_similarity, query_embedding, k)
                    )
                    rows = cur.fetchall()

                    for row in rows:
                        doc = QualityAnswer(
                            id=row[0],
                            title=row[1],
                            content=row[2],
                            metadata=row[3] or {},
                            similarity=float(row[4]),
                            created_at=row[5]
                        )
                        documents.append(doc)

            logger.info(f"Found {len(documents)} similar quality answers")
            return documents

        except Exception as e:
            logger.error(f"Failed to search quality answers: {e}", exc_info=True)
            return []

    def format_quality_context(self, documents: List[QualityAnswer]) -> str:
        """
        검색된 고품질 답변을 LLM 컨텍스트 문자열로 변환

        Args:
            documents: 검색된 고품질 답변 리스트

        Returns:
            포맷팅된 컨텍스트 문자열
        """
        if not documents:
            return ""

        context_parts = ["## 참고 답변 예시\n"]
        context_parts.append("아래는 유사한 질문에 대한 고품질 답변 예시입니다. 참고하여 일관되고 품질 높은 답변을 작성하세요.\n")

        for i, doc in enumerate(documents, 1):
            rating = doc.metadata.get("rating", "?")
            context_parts.append(f"### 예시 {i} (별점 {rating}점, 유사도 {doc.similarity:.2f})")
            context_parts.append(doc.content)
            context_parts.append("")

        return "\n".join(context_parts)

    def get_stored_count(self) -> int:
        """
        저장된 고품질 답변 수 조회

        Returns:
            문서 수
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM documents
                        WHERE doc_type = %s AND status = 'active'
                        """,
                        (self.DOC_TYPE,)
                    )
                    return cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get stored count: {e}")
            return 0

    async def is_duplicate_question(self, user_question: str, threshold: float = 0.95) -> bool:
        """
        중복 질문 여부 확인 (매우 유사한 질문이 이미 저장되어 있는지)

        Args:
            user_question: 사용자 질문
            threshold: 중복 판단 임계값

        Returns:
            중복 여부
        """
        try:
            similar = await self.search_similar_answers(user_question, k=1, min_similarity=threshold)
            return len(similar) > 0
        except Exception as e:
            logger.warning(f"Failed to check duplicate: {e}")
            return False


# 싱글톤 인스턴스
_quality_answer_service: Optional[QualityAnswerService] = None


def get_quality_answer_service() -> QualityAnswerService:
    """QualityAnswerService 싱글톤 반환"""
    global _quality_answer_service
    if _quality_answer_service is None:
        _quality_answer_service = QualityAnswerService()
    return _quality_answer_service
