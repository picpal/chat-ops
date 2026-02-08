"""
Settings 관련 Pydantic 모델
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from pydantic import BaseModel, Field


# === Request Models ===

class QualityAnswerRagUpdate(BaseModel):
    """Quality Answer RAG 설정 업데이트 요청"""
    enabled: Optional[bool] = Field(None, description="기능 활성화 여부")
    minRating: Optional[int] = Field(None, ge=1, le=5, description="최소 별점 기준 (1-5)")


class SettingUpdate(BaseModel):
    """일반 설정 업데이트 요청"""
    value: Dict[str, Any] = Field(..., description="설정 값 (JSONB)")


# === Response Models ===

class QualityAnswerRagStatus(BaseModel):
    """Quality Answer RAG 상태 응답"""
    enabled: bool = Field(..., description="기능 활성화 여부")
    minRating: int = Field(..., description="최소 별점 기준")
    storedCount: int = Field(..., description="저장된 고품질 답변 수")
    lastUpdated: Optional[datetime] = Field(None, description="마지막 업데이트 시간")


class SettingResponse(BaseModel):
    """일반 설정 응답"""
    key: str = Field(..., description="설정 키")
    value: Dict[str, Any] = Field(..., description="설정 값")
    description: Optional[str] = Field(None, description="설정 설명")
    updatedAt: Optional[datetime] = Field(None, description="업데이트 시간")
