"""
별점 평가 Pydantic 모델
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RatingCreateRequest(BaseModel):
    """별점 생성/수정 요청"""
    requestId: str = Field(..., description="메시지 request ID")
    rating: int = Field(..., ge=1, le=5, description="별점 (1-5)")
    feedback: Optional[str] = Field(None, description="추가 피드백")
    sessionId: str = Field(..., description="세션 ID (필수)")


class RatingResponse(BaseModel):
    """별점 응답"""
    requestId: str
    rating: int
    feedback: Optional[str] = None
    savedAt: str


class RatingDetailResponse(BaseModel):
    """별점 상세 조회 응답"""
    requestId: str
    rating: int
    feedback: Optional[str] = None
    createdAt: str


class RatingListResponse(BaseModel):
    """세션별 별점 목록 응답"""
    ratings: list[RatingDetailResponse]


# === Analytics Models ===

class RatingSummaryResponse(BaseModel):
    """별점 요약 통계"""
    totalCount: int
    averageRating: float
    distribution: dict[str, int]
    withFeedbackCount: int
    period: str


class DistributionItem(BaseModel):
    """별점 분포 항목"""
    rating: int
    count: int
    percentage: float


class RatingDistributionResponse(BaseModel):
    """별점 분포 응답"""
    distribution: list[DistributionItem]
    period: str


class TrendItem(BaseModel):
    """일별 추이 항목"""
    date: str
    averageRating: float
    count: int


class RatingTrendResponse(BaseModel):
    """별점 추이 응답"""
    trend: list[TrendItem]
    period: str


class RatingDetailItem(BaseModel):
    """별점 상세 항목 (분석용)"""
    requestId: str
    sessionId: Optional[str] = None
    sessionTitle: Optional[str] = None
    userQuestion: Optional[str] = None
    aiResponseSummary: Optional[str] = None
    rating: int
    feedback: Optional[str] = None
    createdAt: str


class RatingDetailsPageResponse(BaseModel):
    """별점 상세 페이지 응답"""
    items: list[RatingDetailItem]
    total: int
    page: int
    pageSize: int
    totalPages: int


class ConversationPair(BaseModel):
    """대화 쌍 (질문 + 응답)"""
    userQuestion: str
    aiResponse: str
    createdAt: Optional[str] = None


class RatingContextResponse(BaseModel):
    """평가 컨텍스트 응답 (대화 이력 + 평가 정보)"""
    requestId: str
    sessionId: Optional[str] = None
    sessionTitle: Optional[str] = None
    rating: int
    feedback: Optional[str] = None
    createdAt: str
    conversations: list[ConversationPair]
