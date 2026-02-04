"""
RAG Service: 문서 검색 및 컨텍스트 증강
pgvector를 사용한 벡터 유사도 검색
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

import psycopg
from pgvector.psycopg import register_vector

logger = logging.getLogger(__name__)


def calculate_dynamic_k(query: str) -> int:
    """
    쿼리 복잡도에 따른 동적 k값 계산

    - 단순 쿼리 (10단어 미만): k=2 (빠른 검색)
    - 중간 쿼리 (10-30단어): k=5 (표준)
    - 복잡 쿼리 (30+ 단어): k=8 (광범위 검색)

    Args:
        query: 사용자 쿼리 문자열

    Returns:
        적절한 k값 (2, 5, 또는 8)
    """
    # 한국어/영어 단어 수 계산 (공백 기준)
    word_count = len(query.split())

    if word_count < 10:
        return 2
    elif word_count < 30:
        return 5
    else:
        return 8


def get_domain_min_similarity(query: str) -> float:
    """
    쿼리의 도메인에 따른 최소 유사도 임계값 계산

    - 결제(Payment) 관련: 0.55 (금융 민감도 높음)
    - 환불(Refund) 관련: 0.55
    - 정산(Settlement) 관련: 0.53
    - 가맹점(Merchant) 관련: 0.50
    - 기타: 0.45

    Args:
        query: 사용자 쿼리 문자열

    Returns:
        최소 유사도 임계값
    """
    query_lower = query.lower()

    # 결제 관련 키워드
    payment_keywords = ["결제", "거래", "트랜잭션", "payment", "승인", "카드"]
    refund_keywords = ["환불", "취소", "반품", "refund", "cancel"]
    settlement_keywords = ["정산", "지급", "settlement", "payout"]
    merchant_keywords = ["가맹점", "merchant", "상점", "업체"]

    if any(kw in query_lower for kw in payment_keywords):
        return 0.55
    elif any(kw in query_lower for kw in refund_keywords):
        return 0.55
    elif any(kw in query_lower for kw in settlement_keywords):
        return 0.53
    elif any(kw in query_lower for kw in merchant_keywords):
        return 0.50
    else:
        return 0.45


@dataclass
class Document:
    """검색된 문서"""
    id: int
    doc_type: str
    title: str
    content: str
    metadata: Dict[str, Any]
    status: str = "active"
    similarity: float = 0.0
    has_embedding: bool = False
    submitted_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
        k: Optional[int] = None,
        doc_types: Optional[List[str]] = None,
        min_similarity: Optional[float] = None,
        use_dynamic_params: bool = True
    ) -> List[Document]:
        """
        쿼리와 유사한 문서 검색

        Args:
            query: 검색 쿼리
            k: 반환할 문서 개수 (None이면 동적 계산)
            doc_types: 필터링할 문서 타입 (None이면 전체)
            min_similarity: 최소 유사도 임계값 (None이면 도메인 기반 동적 계산)
            use_dynamic_params: True면 k와 min_similarity를 동적으로 계산

        Returns:
            유사도 순으로 정렬된 문서 리스트
        """
        # 동적 파라미터 계산
        if use_dynamic_params:
            if k is None:
                k = calculate_dynamic_k(query)
            if min_similarity is None:
                min_similarity = get_domain_min_similarity(query)
        else:
            # 기본값 사용
            k = k or 3
            min_similarity = min_similarity if min_similarity is not None else 0.5

        logger.info(f"Searching documents for query: {query[:50]}... (k={k}, min_sim={min_similarity})")

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
                    # 기본 쿼리 (active 상태만 검색)
                    sql = """
                        SELECT
                            id, doc_type, title, content, metadata,
                            1 - (embedding <=> %s::vector) as similarity
                        FROM documents
                        WHERE embedding IS NOT NULL
                          AND status = 'active'
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
                    # PostgreSQL 전문 검색 사용 (simple config for compatibility, active만)
                    sql = """
                        SELECT
                            id, doc_type, title, content, metadata,
                            ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', %s)) as rank
                        FROM documents
                        WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', %s)
                          AND status = 'active'
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
                        WHERE (content ILIKE %s OR title ILIKE %s)
                          AND status = 'active'
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

    async def add_document_without_embedding(
        self,
        doc_type: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "pending",
        submitted_by: Optional[str] = None
    ) -> int:
        """
        임베딩 없이 문서 추가 (skip_embedding=True용)

        Args:
            doc_type: 문서 타입 (entity, business_logic, error_code, faq)
            title: 문서 제목
            content: 문서 내용
            metadata: 추가 메타데이터
            status: 문서 상태 (기본: pending)
            submitted_by: 제출자 ID/이름

        Returns:
            생성된 문서 ID
        """
        logger.info(f"Adding document without embedding: {title} (status={status})")

        # metadata를 JSON 문자열로 변환
        metadata_json = json.dumps(metadata or {})

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (doc_type, title, content, metadata, status, submitted_by, submitted_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING id
                    """,
                    (doc_type, title, content, metadata_json, status, submitted_by)
                )
                doc_id = cur.fetchone()[0]
                conn.commit()

        logger.info(f"Document added without embedding with ID: {doc_id}")
        return doc_id

    async def add_document(
        self,
        doc_type: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "pending",
        submitted_by: Optional[str] = None
    ) -> int:
        """
        새 문서 추가

        Args:
            doc_type: 문서 타입 (entity, business_logic, error_code, faq)
            title: 문서 제목
            content: 문서 내용
            metadata: 추가 메타데이터
            status: 문서 상태 (기본: pending)
            submitted_by: 제출자 ID/이름

        Returns:
            생성된 문서 ID
        """
        logger.info(f"Adding document: {title} (status={status})")

        embedding = None
        if self.openai_api_key:
            try:
                embedding = await self._create_embedding(content)
            except Exception as e:
                logger.warning(f"Failed to create embedding: {e}")

        # metadata를 JSON 문자열로 변환
        metadata_json = json.dumps(metadata or {})

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                if embedding:
                    cur.execute(
                        """
                        INSERT INTO documents (doc_type, title, content, embedding, metadata, status, submitted_by, submitted_at)
                        VALUES (%s, %s, %s, %s::vector, %s::jsonb, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                        """,
                        (doc_type, title, content, embedding, metadata_json, status, submitted_by)
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO documents (doc_type, title, content, metadata, status, submitted_by, submitted_at)
                        VALUES (%s, %s, %s, %s::jsonb, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                        """,
                        (doc_type, title, content, metadata_json, status, submitted_by)
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

    # === CRUD 메서드 ===

    async def get_document(self, doc_id: int) -> Optional[Document]:
        """
        ID로 단일 문서 조회

        Args:
            doc_id: 문서 ID

        Returns:
            Document 또는 None (없는 경우)
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, doc_type, title, content, metadata, status,
                               embedding IS NOT NULL as has_embedding,
                               submitted_by, submitted_at, reviewed_by, reviewed_at, rejection_reason,
                               created_at, updated_at
                        FROM documents
                        WHERE id = %s
                        """,
                        (doc_id,)
                    )
                    row = cur.fetchone()

                    if row:
                        return Document(
                            id=row[0],
                            doc_type=row[1],
                            title=row[2],
                            content=row[3],
                            metadata=row[4] or {},
                            status=row[5],
                            has_embedding=row[6],
                            submitted_by=row[7],
                            submitted_at=row[8],
                            reviewed_by=row[9],
                            reviewed_at=row[10],
                            rejection_reason=row[11],
                            created_at=row[12],
                            updated_at=row[13]
                        )
                    return None

        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None

    async def list_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        doc_type: Optional[str] = None,
        status: Optional[str] = None,
        has_embedding: Optional[bool] = None,
        search_query: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Document], int]:
        """
        페이지네이션된 문서 목록 조회

        Args:
            page: 페이지 번호 (1부터 시작)
            page_size: 페이지 크기
            doc_type: 필터링할 문서 타입
            status: 필터링할 문서 상태 (pending, active, rejected)
            has_embedding: 임베딩 존재 여부 필터
            search_query: 제목/내용 검색어
            sort_by: 정렬 필드 (created_at, updated_at, title)
            sort_order: 정렬 방향 (asc, desc)

        Returns:
            (문서 리스트, 전체 개수) 튜플
        """
        documents = []
        total = 0
        offset = (page - 1) * page_size

        # SQL injection 방지를 위한 화이트리스트
        allowed_sort_fields = {"created_at", "updated_at", "title", "doc_type", "id", "status"}
        sort_column = sort_by if sort_by in allowed_sort_fields else "created_at"
        sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # 동적 WHERE 절 구성
                    conditions = []
                    params = []

                    if doc_type:
                        conditions.append("doc_type = %s")
                        params.append(doc_type)

                    if status:
                        conditions.append("status = %s")
                        params.append(status)

                    if has_embedding is not None:
                        if has_embedding:
                            conditions.append("embedding IS NOT NULL")
                        else:
                            conditions.append("embedding IS NULL")

                    if search_query:
                        conditions.append("(title ILIKE %s OR content ILIKE %s)")
                        params.extend([f"%{search_query}%", f"%{search_query}%"])

                    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

                    # 전체 개수 조회
                    count_sql = f"SELECT COUNT(*) FROM documents {where_clause}"
                    cur.execute(count_sql, params)
                    total = cur.fetchone()[0]

                    # 데이터 조회
                    data_sql = f"""
                        SELECT id, doc_type, title, content, metadata, status,
                               embedding IS NOT NULL as has_embedding,
                               submitted_by, submitted_at, reviewed_by, reviewed_at, rejection_reason,
                               created_at, updated_at
                        FROM documents
                        {where_clause}
                        ORDER BY {sort_column} {sort_dir}
                        LIMIT %s OFFSET %s
                    """
                    cur.execute(data_sql, params + [page_size, offset])
                    rows = cur.fetchall()

                    for row in rows:
                        documents.append(Document(
                            id=row[0],
                            doc_type=row[1],
                            title=row[2],
                            content=row[3],
                            metadata=row[4] or {},
                            status=row[5],
                            has_embedding=row[6],
                            submitted_by=row[7],
                            submitted_at=row[8],
                            reviewed_by=row[9],
                            reviewed_at=row[10],
                            rejection_reason=row[11],
                            created_at=row[12],
                            updated_at=row[13]
                        ))

            logger.info(f"Listed {len(documents)} documents (page {page}, total {total})")

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")

        return documents, total

    async def update_document(
        self,
        doc_id: int,
        doc_type: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        regenerate_embedding: bool = True
    ) -> Optional[Document]:
        """
        문서 수정

        Args:
            doc_id: 수정할 문서 ID
            doc_type: 새 문서 타입 (None이면 유지)
            title: 새 제목 (None이면 유지)
            content: 새 내용 (None이면 유지)
            metadata: 새 메타데이터 (None이면 유지)
            regenerate_embedding: content 변경 시 임베딩 재생성 여부

        Returns:
            수정된 Document 또는 None
        """
        logger.info(f"Updating document {doc_id}")

        # 기존 문서 확인
        existing = await self.get_document(doc_id)
        if not existing:
            logger.warning(f"Document {doc_id} not found")
            return None

        # 업데이트할 필드 구성
        updates = []
        params = []

        if doc_type is not None:
            updates.append("doc_type = %s")
            params.append(doc_type)

        if title is not None:
            updates.append("title = %s")
            params.append(title)

        if content is not None:
            updates.append("content = %s")
            params.append(content)

            # 내용 변경 시 임베딩 재생성
            if regenerate_embedding and self.openai_api_key:
                try:
                    embedding = await self._create_embedding(content)
                    updates.append("embedding = %s::vector")
                    params.append(embedding)
                except Exception as e:
                    logger.warning(f"Failed to regenerate embedding: {e}")

        if metadata is not None:
            import json
            updates.append("metadata = %s")
            params.append(json.dumps(metadata))

        if not updates:
            return existing

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(doc_id)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    sql = f"""
                        UPDATE documents
                        SET {', '.join(updates)}
                        WHERE id = %s
                    """
                    cur.execute(sql, params)
                    conn.commit()

            logger.info(f"Document {doc_id} updated successfully")
            return await self.get_document(doc_id)

        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return None

    async def delete_document(self, doc_id: int) -> bool:
        """
        문서 삭제

        Args:
            doc_id: 삭제할 문서 ID

        Returns:
            삭제 성공 여부
        """
        logger.info(f"Deleting document {doc_id}")

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
                    deleted = cur.rowcount > 0
                    conn.commit()

            if deleted:
                logger.info(f"Document {doc_id} deleted successfully")
            else:
                logger.warning(f"Document {doc_id} not found for deletion")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    async def bulk_add_documents(
        self,
        documents: List[Dict[str, Any]],
        skip_embedding: bool = False
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        대량 문서 추가

        Args:
            documents: 추가할 문서 목록 [{doc_type, title, content, metadata}, ...]
            skip_embedding: 임베딩 생성 건너뛰기

        Returns:
            (성공 개수, 실패 목록) 튜플
        """
        logger.info(f"Bulk adding {len(documents)} documents")

        success_count = 0
        failures = []

        for idx, doc in enumerate(documents):
            try:
                embedding = None
                if not skip_embedding and self.openai_api_key:
                    try:
                        embedding = await self._create_embedding(doc.get("content", ""))
                    except Exception as e:
                        logger.warning(f"Failed to create embedding for doc {idx}: {e}")

                with self._get_connection() as conn:
                    with conn.cursor() as cur:
                        if embedding:
                            cur.execute(
                                """
                                INSERT INTO documents (doc_type, title, content, embedding, metadata)
                                VALUES (%s, %s, %s, %s::vector, %s)
                                RETURNING id
                                """,
                                (
                                    doc.get("doc_type"),
                                    doc.get("title"),
                                    doc.get("content"),
                                    embedding,
                                    doc.get("metadata") or {}
                                )
                            )
                        else:
                            cur.execute(
                                """
                                INSERT INTO documents (doc_type, title, content, metadata)
                                VALUES (%s, %s, %s, %s)
                                RETURNING id
                                """,
                                (
                                    doc.get("doc_type"),
                                    doc.get("title"),
                                    doc.get("content"),
                                    doc.get("metadata") or {}
                                )
                            )
                        conn.commit()
                        success_count += 1

            except Exception as e:
                logger.error(f"Failed to add document at index {idx}: {e}")
                failures.append({
                    "index": idx,
                    "title": doc.get("title"),
                    "error": str(e)
                })

        logger.info(f"Bulk add completed: {success_count} success, {len(failures)} failed")
        return success_count, failures

    async def bulk_delete_documents(self, ids: List[int]) -> Tuple[int, List[int]]:
        """
        대량 문서 삭제

        Args:
            ids: 삭제할 문서 ID 목록

        Returns:
            (성공 개수, 실패 ID 목록) 튜플
        """
        logger.info(f"Bulk deleting {len(ids)} documents")

        success_count = 0
        failed_ids = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    for doc_id in ids:
                        try:
                            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
                            if cur.rowcount > 0:
                                success_count += 1
                            else:
                                failed_ids.append(doc_id)
                        except Exception as e:
                            logger.error(f"Failed to delete document {doc_id}: {e}")
                            failed_ids.append(doc_id)

                    conn.commit()

        except Exception as e:
            logger.error(f"Bulk delete transaction failed: {e}")
            failed_ids = ids

        logger.info(f"Bulk delete completed: {success_count} success, {len(failed_ids)} failed")
        return success_count, failed_ids

    async def get_document_stats(self) -> Dict[str, Any]:
        """
        문서 통계 조회 (확장)

        Returns:
            통계 정보 딕셔너리
        """
        stats = {
            "total_count": 0,
            "by_type": {},
            "by_status": {"pending": 0, "active": 0, "rejected": 0},
            "embedding_status": {"with_embedding": 0, "without_embedding": 0},
            "last_updated": None
        }

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # 전체 개수
                    cur.execute("SELECT COUNT(*) FROM documents")
                    stats["total_count"] = cur.fetchone()[0]

                    # 타입별 개수
                    cur.execute("""
                        SELECT doc_type, COUNT(*) as count
                        FROM documents
                        GROUP BY doc_type
                    """)
                    for row in cur.fetchall():
                        stats["by_type"][row[0]] = row[1]

                    # 상태별 개수
                    cur.execute("""
                        SELECT status, COUNT(*) as count
                        FROM documents
                        GROUP BY status
                    """)
                    for row in cur.fetchall():
                        stats["by_status"][row[0]] = row[1]

                    # 임베딩 상태
                    cur.execute("""
                        SELECT
                            COUNT(*) FILTER (WHERE embedding IS NOT NULL) as with_embedding,
                            COUNT(*) FILTER (WHERE embedding IS NULL) as without_embedding
                        FROM documents
                    """)
                    row = cur.fetchone()
                    stats["embedding_status"]["with_embedding"] = row[0]
                    stats["embedding_status"]["without_embedding"] = row[1]

                    # 최근 업데이트 시간
                    cur.execute("SELECT MAX(updated_at) FROM documents")
                    stats["last_updated"] = cur.fetchone()[0]

        except Exception as e:
            logger.error(f"Failed to get document stats: {e}")

        return stats

    async def refresh_embeddings(
        self,
        force_all: bool = False,
        doc_types: Optional[List[str]] = None,
        batch_size: int = 50
    ) -> Dict[str, int]:
        """
        임베딩 갱신

        Args:
            force_all: True면 전체 재생성, False면 없는 것만
            doc_types: 특정 타입만 갱신 (None이면 전체)
            batch_size: 배치 크기

        Returns:
            {"processed": n, "updated": n, "failed": n, "remaining": n}
        """
        result = {"processed": 0, "updated": 0, "failed": 0, "remaining": 0}

        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set, cannot refresh embeddings")
            return result

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # 대상 문서 조회
                    conditions = []
                    params = []

                    if not force_all:
                        conditions.append("embedding IS NULL")

                    if doc_types:
                        conditions.append("doc_type = ANY(%s)")
                        params.append(doc_types)

                    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

                    # 전체 대상 개수
                    cur.execute(f"SELECT COUNT(*) FROM documents {where_clause}", params)
                    total_target = cur.fetchone()[0]

                    # 배치 조회
                    cur.execute(
                        f"""
                        SELECT id, title, content FROM documents
                        {where_clause}
                        LIMIT %s
                        """,
                        params + [batch_size]
                    )
                    rows = cur.fetchall()

                    for row in rows:
                        doc_id, title, content = row
                        result["processed"] += 1

                        try:
                            text = f"{title}\n\n{content}"
                            embedding = await self._create_embedding(text)
                            cur.execute(
                                "UPDATE documents SET embedding = %s::vector, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                                (embedding, doc_id)
                            )
                            result["updated"] += 1
                        except Exception as e:
                            logger.error(f"Failed to update embedding for doc {doc_id}: {e}")
                            result["failed"] += 1

                    conn.commit()
                    result["remaining"] = total_target - result["processed"]

        except Exception as e:
            logger.error(f"Refresh embeddings failed: {e}")

        logger.info(f"Refresh embeddings completed: {result}")
        return result

    async def document_exists(self, doc_id: int) -> bool:
        """
        문서 존재 여부 확인

        Args:
            doc_id: 문서 ID

        Returns:
            존재 여부
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM documents WHERE id = %s", (doc_id,))
                    return cur.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check document existence: {e}")
            return False

    # === 승인/반려 메서드 ===

    async def approve_document(self, doc_id: int, reviewed_by: str) -> Optional[Document]:
        """
        문서 승인

        Args:
            doc_id: 문서 ID
            reviewed_by: 검토자 ID/이름

        Returns:
            승인된 Document 또는 None
        """
        logger.info(f"Approving document {doc_id} by {reviewed_by}")

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE documents
                        SET status = 'active',
                            reviewed_by = %s,
                            reviewed_at = CURRENT_TIMESTAMP,
                            rejection_reason = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND status = 'pending'
                        """,
                        (reviewed_by, doc_id)
                    )
                    updated = cur.rowcount > 0
                    conn.commit()

            if updated:
                logger.info(f"Document {doc_id} approved by {reviewed_by}")
                return await self.get_document(doc_id)
            else:
                logger.warning(f"Document {doc_id} not found or not pending")
                return None

        except Exception as e:
            logger.error(f"Failed to approve document {doc_id}: {e}")
            return None

    async def reject_document(
        self,
        doc_id: int,
        reviewed_by: str,
        reason: str
    ) -> Optional[Document]:
        """
        문서 반려

        Args:
            doc_id: 문서 ID
            reviewed_by: 검토자 ID/이름
            reason: 반려 사유

        Returns:
            반려된 Document 또는 None
        """
        logger.info(f"Rejecting document {doc_id} by {reviewed_by}")

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE documents
                        SET status = 'rejected',
                            reviewed_by = %s,
                            reviewed_at = CURRENT_TIMESTAMP,
                            rejection_reason = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND status = 'pending'
                        """,
                        (reviewed_by, reason, doc_id)
                    )
                    updated = cur.rowcount > 0
                    conn.commit()

            if updated:
                logger.info(f"Document {doc_id} rejected by {reviewed_by}")
                return await self.get_document(doc_id)
            else:
                logger.warning(f"Document {doc_id} not found or not pending")
                return None

        except Exception as e:
            logger.error(f"Failed to reject document {doc_id}: {e}")
            return None

    async def bulk_review_documents(
        self,
        ids: List[int],
        action: str,
        reviewed_by: str,
        reason: Optional[str] = None
    ) -> Tuple[int, List[int]]:
        """
        대량 문서 승인/반려

        Args:
            ids: 문서 ID 목록
            action: 'approve' 또는 'reject'
            reviewed_by: 검토자 ID/이름
            reason: 반려 사유 (reject 시)

        Returns:
            (성공 개수, 실패 ID 목록) 튜플
        """
        logger.info(f"Bulk {action} {len(ids)} documents by {reviewed_by}")

        success_count = 0
        failed_ids = []

        for doc_id in ids:
            if action == "approve":
                result = await self.approve_document(doc_id, reviewed_by)
            else:
                result = await self.reject_document(doc_id, reviewed_by, reason or "")

            if result:
                success_count += 1
            else:
                failed_ids.append(doc_id)

        logger.info(f"Bulk {action} completed: {success_count} success, {len(failed_ids)} failed")
        return success_count, failed_ids


# 싱글톤 인스턴스
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """RAGService 싱글톤 인스턴스 반환"""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
