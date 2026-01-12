"""
RAG 문서 관리 API용 Pydantic 모델
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from typing import Literal


class DocType(str, Enum):
    """문서 타입"""
    ENTITY = "entity"
    BUSINESS_LOGIC = "business_logic"
    ERROR_CODE = "error_code"
    FAQ = "faq"


class DocumentStatus(str, Enum):
    """문서 상태"""
    PENDING = "pending"      # 승인 대기
    ACTIVE = "active"        # 승인됨 (RAG 검색에 사용)
    REJECTED = "rejected"    # 반려됨


# === Request Models ===

class DocumentCreate(BaseModel):
    """문서 생성 요청"""
    doc_type: DocType = Field(..., description="문서 타입")
    title: str = Field(..., min_length=1, max_length=255, description="문서 제목")
    content: str = Field(..., min_length=1, description="문서 내용")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 메타데이터")
    skip_embedding: bool = Field(default=False, description="임베딩 생성 건너뛰기")
    # 관리자용 옵션: 일반 사용자는 pending, 관리자는 active 직접 지정 가능
    status: Optional[DocumentStatus] = Field(default=None, description="문서 상태 (기본: pending)")
    submitted_by: Optional[str] = Field(default=None, description="제출자 ID/이름")


class DocumentUpdate(BaseModel):
    """문서 수정 요청"""
    doc_type: Optional[DocType] = Field(None, description="문서 타입")
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="문서 제목")
    content: Optional[str] = Field(None, min_length=1, description="문서 내용")
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")
    regenerate_embedding: bool = Field(default=True, description="내용 변경 시 임베딩 재생성")


class DocumentBulkCreate(BaseModel):
    """대량 문서 생성 요청"""
    documents: List[DocumentCreate] = Field(..., min_length=1, max_length=100, description="문서 목록")
    skip_embedding: bool = Field(default=False, description="전체 임베딩 생성 건너뛰기")


class DocumentBulkDelete(BaseModel):
    """대량 문서 삭제 요청"""
    ids: List[int] = Field(..., min_length=1, max_length=100, description="삭제할 문서 ID 목록")


class EmbeddingRefreshRequest(BaseModel):
    """임베딩 갱신 요청"""
    force_all: bool = Field(default=False, description="True면 전체, False면 없는 것만")
    doc_types: Optional[List[DocType]] = Field(None, description="특정 타입만 갱신")
    batch_size: int = Field(default=50, ge=1, le=200, description="배치 크기")


class DocumentReviewRequest(BaseModel):
    """문서 승인/반려 요청"""
    action: Literal["approve", "reject"] = Field(..., description="승인(approve) 또는 반려(reject)")
    reviewed_by: str = Field(..., min_length=1, description="검토자 ID/이름")
    rejection_reason: Optional[str] = Field(None, description="반려 사유 (reject 시 필수)")


class BulkReviewRequest(BaseModel):
    """대량 문서 승인/반려 요청"""
    ids: List[int] = Field(..., min_length=1, max_length=50, description="문서 ID 목록")
    action: Literal["approve", "reject"] = Field(..., description="승인(approve) 또는 반려(reject)")
    reviewed_by: str = Field(..., min_length=1, description="검토자 ID/이름")
    rejection_reason: Optional[str] = Field(None, description="반려 사유 (reject 시)")


# === Response Models ===

class DocumentResponse(BaseModel):
    """단일 문서 응답"""
    id: int
    doc_type: str
    title: str
    content: str
    metadata: Dict[str, Any]
    status: str
    has_embedding: bool
    submitted_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentListItem(BaseModel):
    """문서 목록 아이템 (content 축약)"""
    id: int
    doc_type: str
    title: str
    content_preview: str = Field(..., description="최대 200자")
    status: str
    has_embedding: bool
    submitted_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PaginatedDocuments(BaseModel):
    """페이지네이션된 문서 목록 응답"""
    items: List[DocumentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class DocumentStats(BaseModel):
    """문서 통계 응답"""
    total_count: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]  # {"pending": n, "active": m, "rejected": k}
    embedding_status: Dict[str, int]  # {"with_embedding": n, "without_embedding": m}
    last_updated: Optional[datetime] = None


class BulkOperationResult(BaseModel):
    """대량 작업 결과"""
    success_count: int
    failed_count: int
    failed_ids: List[int] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class EmbeddingRefreshResult(BaseModel):
    """임베딩 갱신 결과"""
    processed: int
    updated: int
    failed: int
    remaining: int
