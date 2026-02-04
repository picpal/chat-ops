"""
RAG 문서 관리 API 엔드포인트
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, UploadFile, File, Form

from app.services.rag_service import get_rag_service
from app.services.file_parser import FileParser
from app.models.document import (
    DocType,
    DocumentStatus,
    DocumentCreate,
    DocumentUpdate,
    DocumentBulkCreate,
    DocumentBulkDelete,
    EmbeddingRefreshRequest,
    DocumentReviewRequest,
    BulkReviewRequest,
    DocumentResponse,
    DocumentListItem,
    PaginatedDocuments,
    DocumentStats,
    BulkOperationResult,
    EmbeddingRefreshResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# === 기본 CRUD ===

@router.get("", response_model=PaginatedDocuments)
async def list_documents(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    doc_type: Optional[DocType] = Query(None, description="문서 타입 필터"),
    status: Optional[DocumentStatus] = Query(None, description="문서 상태 필터"),
    has_embedding: Optional[bool] = Query(None, description="임베딩 존재 여부 필터"),
    search: Optional[str] = Query(None, description="제목/내용 검색어"),
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|title|doc_type|id|status)$", description="정렬 필드"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="정렬 방향")
):
    """
    문서 목록 조회 (페이지네이션, 필터링, 정렬)
    """
    logger.info(f"List documents: page={page}, page_size={page_size}, doc_type={doc_type}, status={status}")

    rag_service = get_rag_service()

    documents, total = await rag_service.list_documents(
        page=page,
        page_size=page_size,
        doc_type=doc_type.value if doc_type else None,
        status=status.value if status else None,
        has_embedding=has_embedding,
        search_query=search,
        sort_by=sort_by,
        sort_order=sort_order
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return PaginatedDocuments(
        items=[
            DocumentListItem(
                id=doc.id,
                doc_type=doc.doc_type,
                title=doc.title,
                content_preview=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                status=doc.status,
                has_embedding=doc.has_embedding,
                submitted_by=doc.submitted_by,
                submitted_at=doc.submitted_at,
                reviewed_by=doc.reviewed_by,
                reviewed_at=doc.reviewed_at,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
            for doc in documents
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.get("/stats", response_model=DocumentStats)
async def get_stats():
    """
    문서 통계 조회
    """
    logger.info("Get document stats")

    rag_service = get_rag_service()
    stats = await rag_service.get_document_stats()

    return DocumentStats(
        total_count=stats["total_count"],
        by_type=stats["by_type"],
        by_status=stats["by_status"],
        embedding_status=stats["embedding_status"],
        last_updated=stats["last_updated"]
    )


@router.get("/pending", response_model=PaginatedDocuments)
async def list_pending_documents(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    doc_type: Optional[DocType] = Query(None, description="문서 타입 필터"),
    search: Optional[str] = Query(None, description="제목/내용 검색어"),
    sort_by: str = Query("submitted_at", pattern="^(created_at|updated_at|title|doc_type|id|submitted_at)$", description="정렬 필드"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="정렬 방향")
):
    """
    승인 대기 문서 목록 조회 (관리자용)
    """
    logger.info(f"List pending documents: page={page}, page_size={page_size}")

    rag_service = get_rag_service()

    documents, total = await rag_service.list_documents(
        page=page,
        page_size=page_size,
        doc_type=doc_type.value if doc_type else None,
        status="pending",
        search_query=search,
        sort_by=sort_by if sort_by != "submitted_at" else "created_at",
        sort_order=sort_order
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return PaginatedDocuments(
        items=[
            DocumentListItem(
                id=doc.id,
                doc_type=doc.doc_type,
                title=doc.title,
                content_preview=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                status=doc.status,
                has_embedding=doc.has_embedding,
                submitted_by=doc.submitted_by,
                submitted_at=doc.submitted_at,
                reviewed_by=doc.reviewed_by,
                reviewed_at=doc.reviewed_at,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
            for doc in documents
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: int):
    """
    단일 문서 조회
    """
    logger.info(f"Get document: {doc_id}")

    rag_service = get_rag_service()
    doc = await rag_service.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    return DocumentResponse(
        id=doc.id,
        doc_type=doc.doc_type,
        title=doc.title,
        content=doc.content,
        metadata=doc.metadata,
        status=doc.status,
        has_embedding=doc.has_embedding,
        submitted_by=doc.submitted_by,
        submitted_at=doc.submitted_at,
        reviewed_by=doc.reviewed_by,
        reviewed_at=doc.reviewed_at,
        rejection_reason=doc.rejection_reason,
        created_at=doc.created_at,
        updated_at=doc.updated_at
    )


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(request: DocumentCreate):
    """
    문서 생성

    - 일반 사용자: status 미지정 시 pending 상태로 생성
    - 관리자: status=active 지정 시 바로 활성화
    """
    # status 기본값: pending (일반 사용자), 요청에서 지정하면 해당 값 사용
    status = request.status.value if request.status else "pending"
    logger.info(f"Create document: {request.title} (status={status})")

    rag_service = get_rag_service()

    # add_document는 status, submitted_by 파라미터 지원
    if request.skip_embedding:
        # 임베딩 없이 추가
        import psycopg
        from pgvector.psycopg import register_vector

        conn = psycopg.connect(rag_service.database_url)
        register_vector(conn)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (doc_type, title, content, metadata, status, submitted_by, submitted_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                (request.doc_type.value, request.title, request.content, request.metadata or {}, status, request.submitted_by)
            )
            doc_id = cur.fetchone()[0]
            conn.commit()
        conn.close()
    else:
        doc_id = await rag_service.add_document(
            doc_type=request.doc_type.value,
            title=request.title,
            content=request.content,
            metadata=request.metadata,
            status=status,
            submitted_by=request.submitted_by
        )

    # 생성된 문서 조회하여 반환
    doc = await rag_service.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=500, detail="Failed to retrieve created document")

    return DocumentResponse(
        id=doc.id,
        doc_type=doc.doc_type,
        title=doc.title,
        content=doc.content,
        metadata=doc.metadata,
        status=doc.status,
        has_embedding=doc.has_embedding,
        submitted_by=doc.submitted_by,
        submitted_at=doc.submitted_at,
        reviewed_by=doc.reviewed_by,
        reviewed_at=doc.reviewed_at,
        rejection_reason=doc.rejection_reason,
        created_at=doc.created_at,
        updated_at=doc.updated_at
    )


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(..., description="업로드할 문서 파일 (.md, .txt, .pdf)"),
    doc_type: DocType = Form(..., description="문서 타입"),
    title: Optional[str] = Form(None, description="문서 제목 (미입력시 파일명 사용)"),
    skip_embedding: bool = Form(False, description="임베딩 생성 건너뛰기"),
    status: Optional[DocumentStatus] = Form(None, description="문서 상태"),
    submitted_by: Optional[str] = Form(None, description="제출자")
):
    """
    파일을 업로드하여 RAG 문서 생성

    지원 형식: .md, .txt, .pdf
    최대 크기: 10MB
    """
    logger.info(f"Upload document: {file.filename}, doc_type={doc_type}")

    # 1. 파일 파싱
    parsed_title, content = await FileParser.parse(file)

    # 2. 제목 결정 (입력값 우선, 없으면 파일명)
    final_title = title or parsed_title

    # 3. 상태 결정
    final_status = status.value if status else "pending"

    # 4. 문서 저장
    rag_service = get_rag_service()

    if skip_embedding:
        # 임베딩 없이 추가
        import psycopg
        from pgvector.psycopg import register_vector

        conn = psycopg.connect(rag_service.database_url)
        register_vector(conn)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (doc_type, title, content, metadata, status, submitted_by, submitted_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                (doc_type.value, final_title, content, {"original_filename": file.filename}, final_status, submitted_by)
            )
            doc_id = cur.fetchone()[0]
            conn.commit()
        conn.close()
    else:
        doc_id = await rag_service.add_document(
            doc_type=doc_type.value,
            title=final_title,
            content=content,
            metadata={"original_filename": file.filename},
            status=final_status,
            submitted_by=submitted_by
        )

    # 생성된 문서 조회하여 반환
    doc = await rag_service.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=500, detail="Failed to retrieve created document")

    return DocumentResponse(
        id=doc.id,
        doc_type=doc.doc_type,
        title=doc.title,
        content=doc.content,
        metadata=doc.metadata,
        status=doc.status,
        has_embedding=doc.has_embedding,
        submitted_by=doc.submitted_by,
        submitted_at=doc.submitted_at,
        reviewed_by=doc.reviewed_by,
        reviewed_at=doc.reviewed_at,
        rejection_reason=doc.rejection_reason,
        created_at=doc.created_at,
        updated_at=doc.updated_at
    )


@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(doc_id: int, request: DocumentUpdate):
    """
    문서 수정
    """
    logger.info(f"Update document: {doc_id}")

    rag_service = get_rag_service()

    # 존재 확인
    if not await rag_service.document_exists(doc_id):
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    doc = await rag_service.update_document(
        doc_id=doc_id,
        doc_type=request.doc_type.value if request.doc_type else None,
        title=request.title,
        content=request.content,
        metadata=request.metadata,
        regenerate_embedding=request.regenerate_embedding
    )

    if not doc:
        raise HTTPException(status_code=500, detail="Failed to update document")

    return DocumentResponse(
        id=doc.id,
        doc_type=doc.doc_type,
        title=doc.title,
        content=doc.content,
        metadata=doc.metadata,
        status=doc.status,
        has_embedding=doc.has_embedding,
        submitted_by=doc.submitted_by,
        submitted_at=doc.submitted_at,
        reviewed_by=doc.reviewed_by,
        reviewed_at=doc.reviewed_at,
        rejection_reason=doc.rejection_reason,
        created_at=doc.created_at,
        updated_at=doc.updated_at
    )


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: int):
    """
    문서 삭제
    """
    logger.info(f"Delete document: {doc_id}")

    rag_service = get_rag_service()

    deleted = await rag_service.delete_document(doc_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    return Response(status_code=204)


# === 대량 작업 ===

@router.post("/bulk", response_model=BulkOperationResult, status_code=201)
async def bulk_create_documents(request: DocumentBulkCreate):
    """
    대량 문서 생성 (최대 100개)
    """
    logger.info(f"Bulk create documents: {len(request.documents)} items")

    rag_service = get_rag_service()

    # DocumentCreate를 dict로 변환
    docs_data = [
        {
            "doc_type": doc.doc_type.value,
            "title": doc.title,
            "content": doc.content,
            "metadata": doc.metadata
        }
        for doc in request.documents
    ]

    success_count, failures = await rag_service.bulk_add_documents(
        documents=docs_data,
        skip_embedding=request.skip_embedding
    )

    return BulkOperationResult(
        success_count=success_count,
        failed_count=len(failures),
        failed_ids=[],  # bulk add에서는 ID가 없음
        errors=failures
    )


@router.post("/bulk/delete", response_model=BulkOperationResult)
async def bulk_delete_documents(request: DocumentBulkDelete):
    """
    대량 문서 삭제 (최대 100개)

    Note: DELETE 메서드는 body를 지원하지 않으므로 POST 사용
    """
    logger.info(f"Bulk delete documents: {len(request.ids)} items")

    rag_service = get_rag_service()

    success_count, failed_ids = await rag_service.bulk_delete_documents(request.ids)

    return BulkOperationResult(
        success_count=success_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids,
        errors=[{"id": fid, "error": "Not found or delete failed"} for fid in failed_ids]
    )


# === 임베딩 관리 ===

@router.post("/embeddings/refresh", response_model=EmbeddingRefreshResult)
async def refresh_embeddings(request: EmbeddingRefreshRequest):
    """
    임베딩 갱신

    - force_all=False (기본): 임베딩이 없는 문서만 처리
    - force_all=True: 모든 문서 임베딩 재생성
    """
    logger.info(f"Refresh embeddings: force_all={request.force_all}, doc_types={request.doc_types}")

    rag_service = get_rag_service()

    result = await rag_service.refresh_embeddings(
        force_all=request.force_all,
        doc_types=[dt.value for dt in request.doc_types] if request.doc_types else None,
        batch_size=request.batch_size
    )

    return EmbeddingRefreshResult(
        processed=result["processed"],
        updated=result["updated"],
        failed=result["failed"],
        remaining=result["remaining"]
    )


# === 승인/반려 ===

@router.post("/bulk/review", response_model=BulkOperationResult)
async def bulk_review_documents(request: BulkReviewRequest):
    """
    대량 문서 승인/반려 (최대 50개)

    - approve: 선택된 문서들을 active 상태로 변경
    - reject: 선택된 문서들을 rejected 상태로 변경

    Note: /{doc_id}/review 보다 먼저 정의하여 라우트 충돌 방지
    """
    logger.info(f"Bulk review documents: {len(request.ids)} items, action={request.action}")

    if request.action == "reject" and not request.rejection_reason:
        raise HTTPException(status_code=400, detail="rejection_reason is required for reject action")

    rag_service = get_rag_service()

    success_count, failed_ids = await rag_service.bulk_review_documents(
        ids=request.ids,
        action=request.action,
        reviewed_by=request.reviewed_by,
        reason=request.rejection_reason
    )

    return BulkOperationResult(
        success_count=success_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids,
        errors=[{"id": fid, "error": "Not found or review failed"} for fid in failed_ids]
    )


@router.post("/{doc_id}/review", response_model=DocumentResponse)
async def review_document(doc_id: int, request: DocumentReviewRequest):
    """
    문서 승인/반려

    - approve: 문서를 active 상태로 변경 (RAG 검색에 사용 가능)
    - reject: 문서를 rejected 상태로 변경 (rejection_reason 필수)
    """
    logger.info(f"Review document {doc_id}: action={request.action}, reviewed_by={request.reviewed_by}")

    rag_service = get_rag_service()

    # 존재 확인
    if not await rag_service.document_exists(doc_id):
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    if request.action == "approve":
        doc = await rag_service.approve_document(doc_id, request.reviewed_by)
    else:  # reject
        if not request.rejection_reason:
            raise HTTPException(status_code=400, detail="rejection_reason is required for reject action")
        doc = await rag_service.reject_document(doc_id, request.reviewed_by, request.rejection_reason)

    if not doc:
        raise HTTPException(status_code=500, detail="Failed to review document")

    return DocumentResponse(
        id=doc.id,
        doc_type=doc.doc_type,
        title=doc.title,
        content=doc.content,
        metadata=doc.metadata,
        status=doc.status,
        has_embedding=doc.has_embedding,
        submitted_by=doc.submitted_by,
        submitted_at=doc.submitted_at,
        reviewed_by=doc.reviewed_by,
        reviewed_at=doc.reviewed_at,
        rejection_reason=doc.rejection_reason,
        created_at=doc.created_at,
        updated_at=doc.updated_at
    )
