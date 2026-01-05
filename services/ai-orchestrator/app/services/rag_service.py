"""
RAG Service: 문서 검색 및 컨텍스트 증강
pgvector를 사용한 벡터 유사도 검색
"""

import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import psycopg
from pgvector.psycopg import register_vector

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """검색된 문서"""
    id: int
    doc_type: str
    title: str
    content: str
    metadata: Dict[str, Any]
    similarity: float = 0.0


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) 서비스

    - pgvector를 사용한 벡터 유사도 검색
    - OpenAI Embeddings로 문서/쿼리 임베딩 생성
    - 컨텍스트 기반 응답 생성 지원
    """

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://chatops_user:chatops_pass@localhost:5432/chatops"
        )
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.embedding_model = "text-embedding-ada-002"
        self.embedding_dimension = 1536
        self._openai_client = None
        self._initialized = False

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

    async def search_docs(
        self,
        query: str,
        k: int = 3,
        doc_types: Optional[List[str]] = None,
        min_similarity: float = 0.5
    ) -> List[Document]:
        """
        쿼리와 유사한 문서 검색

        Args:
            query: 검색 쿼리
            k: 반환할 문서 개수
            doc_types: 필터링할 문서 타입 (None이면 전체)
            min_similarity: 최소 유사도 임계값

        Returns:
            유사도 순으로 정렬된 문서 리스트
        """
        logger.info(f"Searching documents for query: {query[:50]}...")

        # OpenAI API가 없으면 키워드 기반 검색 fallback
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set, using keyword fallback")
            return await self._keyword_search(query, k, doc_types)

        try:
            # 쿼리 임베딩 생성
            query_embedding = await self._create_embedding(query)

            # 벡터 유사도 검색
            return await self._vector_search(
                query_embedding, k, doc_types, min_similarity
            )

        except Exception as e:
            logger.error(f"Vector search failed: {e}, falling back to keyword search")
            return await self._keyword_search(query, k, doc_types)

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

    async def _vector_search(
        self,
        query_embedding: List[float],
        k: int,
        doc_types: Optional[List[str]],
        min_similarity: float
    ) -> List[Document]:
        """pgvector를 사용한 벡터 유사도 검색"""
        documents = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # 기본 쿼리
                    sql = """
                        SELECT
                            id, doc_type, title, content, metadata,
                            1 - (embedding <=> %s::vector) as similarity
                        FROM documents
                        WHERE embedding IS NOT NULL
                    """
                    params = [query_embedding]

                    # doc_type 필터 추가
                    if doc_types:
                        sql += " AND doc_type = ANY(%s)"
                        params.append(doc_types)

                    # 유사도 임계값 필터
                    sql += " AND 1 - (embedding <=> %s::vector) >= %s"
                    params.extend([query_embedding, min_similarity])

                    # 정렬 및 제한
                    sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
                    params.extend([query_embedding, k])

                    cur.execute(sql, params)
                    rows = cur.fetchall()

                    for row in rows:
                        doc = Document(
                            id=row[0],
                            doc_type=row[1],
                            title=row[2],
                            content=row[3],
                            metadata=row[4] or {},
                            similarity=float(row[5])
                        )
                        documents.append(doc)

            logger.info(f"Found {len(documents)} documents via vector search")

        except Exception as e:
            logger.error(f"Vector search error: {e}")

        return documents

    async def _keyword_search(
        self,
        query: str,
        k: int,
        doc_types: Optional[List[str]]
    ) -> List[Document]:
        """키워드 기반 전문 검색 (fallback)"""
        documents = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # PostgreSQL 전문 검색 사용 (simple config for compatibility)
                    sql = """
                        SELECT
                            id, doc_type, title, content, metadata,
                            ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', %s)) as rank
                        FROM documents
                        WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', %s)
                    """
                    params = [query, query]

                    if doc_types:
                        sql += " AND doc_type = ANY(%s)"
                        params.append(doc_types)

                    sql += " ORDER BY rank DESC LIMIT %s"
                    params.append(k)

                    cur.execute(sql, params)
                    rows = cur.fetchall()

                    for row in rows:
                        doc = Document(
                            id=row[0],
                            doc_type=row[1],
                            title=row[2],
                            content=row[3],
                            metadata=row[4] or {},
                            similarity=float(row[5]) if row[5] else 0.0
                        )
                        documents.append(doc)

            # 전문 검색 결과가 없으면 LIKE 검색
            if not documents:
                documents = await self._like_search(query, k, doc_types)

            logger.info(f"Found {len(documents)} documents via keyword search")

        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            # 최후의 수단: LIKE 검색
            documents = await self._like_search(query, k, doc_types)

        return documents

    async def _like_search(
        self,
        query: str,
        k: int,
        doc_types: Optional[List[str]]
    ) -> List[Document]:
        """단순 LIKE 검색 (최후의 fallback)"""
        documents = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                        SELECT id, doc_type, title, content, metadata
                        FROM documents
                        WHERE content ILIKE %s OR title ILIKE %s
                    """
                    pattern = f"%{query}%"
                    params = [pattern, pattern]

                    if doc_types:
                        sql += " AND doc_type = ANY(%s)"
                        params.append(doc_types)

                    sql += " LIMIT %s"
                    params.append(k)

                    cur.execute(sql, params)
                    rows = cur.fetchall()

                    for row in rows:
                        doc = Document(
                            id=row[0],
                            doc_type=row[1],
                            title=row[2],
                            content=row[3],
                            metadata=row[4] or {},
                            similarity=0.5  # LIKE는 정확도를 알 수 없음
                        )
                        documents.append(doc)

            logger.info(f"Found {len(documents)} documents via LIKE search")

        except Exception as e:
            logger.error(f"LIKE search error: {e}")

        return documents

    async def add_document(
        self,
        doc_type: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        새 문서 추가

        Args:
            doc_type: 문서 타입 (entity, business_logic, error_code, faq)
            title: 문서 제목
            content: 문서 내용
            metadata: 추가 메타데이터

        Returns:
            생성된 문서 ID
        """
        logger.info(f"Adding document: {title}")

        embedding = None
        if self.openai_api_key:
            try:
                embedding = await self._create_embedding(content)
            except Exception as e:
                logger.warning(f"Failed to create embedding: {e}")

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                if embedding:
                    cur.execute(
                        """
                        INSERT INTO documents (doc_type, title, content, embedding, metadata)
                        VALUES (%s, %s, %s, %s::vector, %s)
                        RETURNING id
                        """,
                        (doc_type, title, content, embedding, metadata or {})
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO documents (doc_type, title, content, metadata)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (doc_type, title, content, metadata or {})
                    )
                doc_id = cur.fetchone()[0]
                conn.commit()

        logger.info(f"Document added with ID: {doc_id}")
        return doc_id

    async def update_embeddings(self, batch_size: int = 100) -> int:
        """
        임베딩이 없는 문서들의 임베딩을 일괄 생성

        Returns:
            업데이트된 문서 수
        """
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set, cannot update embeddings")
            return 0

        updated_count = 0

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # 임베딩이 없는 문서 조회
                cur.execute(
                    "SELECT id, content FROM documents WHERE embedding IS NULL LIMIT %s",
                    (batch_size,)
                )
                rows = cur.fetchall()

                for row in rows:
                    doc_id, content = row
                    try:
                        embedding = await self._create_embedding(content)
                        cur.execute(
                            "UPDATE documents SET embedding = %s::vector WHERE id = %s",
                            (embedding, doc_id)
                        )
                        updated_count += 1
                    except Exception as e:
                        logger.error(f"Failed to update embedding for doc {doc_id}: {e}")

                conn.commit()

        logger.info(f"Updated embeddings for {updated_count} documents")
        return updated_count

    def format_context(self, documents: List[Document]) -> str:
        """
        검색된 문서들을 LLM 컨텍스트 문자열로 변환

        Args:
            documents: 검색된 문서 리스트

        Returns:
            포맷팅된 컨텍스트 문자열
        """
        if not documents:
            return ""

        context_parts = ["## 참고 문서\n"]

        for i, doc in enumerate(documents, 1):
            context_parts.append(f"### {i}. {doc.title} ({doc.doc_type})")
            context_parts.append(f"{doc.content}")
            if doc.metadata:
                context_parts.append(f"메타데이터: {doc.metadata}")
            context_parts.append("")

        return "\n".join(context_parts)

    async def get_document_count(self) -> Dict[str, int]:
        """문서 타입별 개수 조회"""
        counts = {}

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT doc_type, COUNT(*) as count
                        FROM documents
                        GROUP BY doc_type
                        """
                    )
                    rows = cur.fetchall()
                    for row in rows:
                        counts[row[0]] = row[1]

        except Exception as e:
            logger.error(f"Failed to get document count: {e}")

        return counts


# 싱글톤 인스턴스
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """RAGService 싱글톤 인스턴스 반환"""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
