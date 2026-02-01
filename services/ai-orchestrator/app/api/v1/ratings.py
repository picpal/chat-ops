"""
별점 평가 API 라우터
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from pydantic import BaseModel

from app.models.rating import (
    RatingCreateRequest, RatingResponse, RatingDetailResponse, RatingListResponse,
    RatingSummaryResponse, RatingDistributionResponse, RatingTrendResponse, RatingDetailsPageResponse,
    RatingContextResponse,
)
from app.services.rating_service import get_rating_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ratings", response_model=RatingResponse)
async def create_rating(request: RatingCreateRequest):
    """별점 저장 (생성 또는 수정)"""
    try:
        service = get_rating_service()
        result = service.save_rating(
            request_id=request.requestId,
            rating=request.rating,
            feedback=request.feedback,
            session_id=request.sessionId,
        )
        return RatingResponse(**result)
    except Exception as e:
        logger.error(f"Failed to save rating: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ratings/session/{session_id}", response_model=RatingListResponse)
async def get_ratings_by_session(session_id: str):
    """세션별 별점 일괄 조회"""
    try:
        service = get_rating_service()
        results = service.get_ratings_by_session(session_id)
        return RatingListResponse(
            ratings=[RatingDetailResponse(**r) for r in results]
        )
    except Exception as e:
        logger.error(f"Failed to get ratings by session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ratings/analytics/summary", response_model=RatingSummaryResponse)
async def get_ratings_summary(period: str = Query("all", regex="^(today|7d|30d|all)$")):
    """별점 요약 통계"""
    try:
        service = get_rating_service()
        result = service.get_summary(period)
        return RatingSummaryResponse(**result)
    except Exception as e:
        logger.error(f"Failed to get ratings summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ratings/analytics/distribution", response_model=RatingDistributionResponse)
async def get_ratings_distribution(period: str = Query("30d", regex="^(today|7d|30d|all)$")):
    """별점 분포"""
    try:
        service = get_rating_service()
        result = service.get_distribution(period)
        return RatingDistributionResponse(**result)
    except Exception as e:
        logger.error(f"Failed to get ratings distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ratings/analytics/trend", response_model=RatingTrendResponse)
async def get_ratings_trend(
    period: str = Query("30d", regex="^(today|7d|30d|all)$"),
    granularity: str = Query("day", regex="^(day|week)$"),
):
    """별점 추이"""
    try:
        service = get_rating_service()
        result = service.get_trend(period, granularity)
        return RatingTrendResponse(**result)
    except Exception as e:
        logger.error(f"Failed to get ratings trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ratings/analytics/details", response_model=RatingDetailsPageResponse)
async def get_ratings_details(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    has_feedback: Optional[bool] = Query(None),
):
    """별점 상세 목록"""
    try:
        service = get_rating_service()
        result = service.get_details(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            min_rating=min_rating,
            max_rating=max_rating,
            has_feedback=has_feedback,
        )
        return RatingDetailsPageResponse(**result)
    except Exception as e:
        logger.error(f"Failed to get ratings details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class FeedbackUpdateRequest(BaseModel):
    """피드백 수정 요청"""
    feedback: str


@router.get("/ratings/{request_id}/context", response_model=RatingContextResponse)
async def get_rating_context(request_id: str):
    """평가 컨텍스트 조회 (이전 대화 3쌍 + 평가 정보)"""
    try:
        service = get_rating_service()
        result = service.get_rating_context(request_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Rating not found")
        return RatingContextResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rating context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/ratings/{request_id}/feedback", response_model=RatingResponse)
async def update_feedback(request_id: str, request: FeedbackUpdateRequest):
    """피드백 수정"""
    try:
        service = get_rating_service()
        result = service.update_feedback(request_id, request.feedback)
        if result is None:
            raise HTTPException(status_code=404, detail="Rating not found")
        return RatingResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ratings/{request_id}", response_model=RatingDetailResponse)
async def get_rating(request_id: str):
    """별점 조회"""
    try:
        service = get_rating_service()
        result = service.get_rating(request_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Rating not found")
        return RatingDetailResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rating: {e}")
        raise HTTPException(status_code=500, detail=str(e))
