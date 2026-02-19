"""
로그 분석 설정 관련 Pydantic 모델
"""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


# === Config Models ===

class LogPath(BaseModel):
    """로그 경로 설정"""
    id: str = Field(description="경로 ID")
    name: str = Field(description="표시 이름")
    path: str = Field(description="로그 파일 경로")
    enabled: bool = Field(default=True, description="활성화 여부")


class MaskingPattern(BaseModel):
    """마스킹 패턴"""
    name: str = Field(description="패턴 이름")
    regex: str = Field(description="정규식 패턴")
    replacement: str = Field(description="대체 문자열")


class MaskingConfig(BaseModel):
    """마스킹 설정"""
    enabled: bool = Field(default=True, description="마스킹 활성화")
    patterns: List[MaskingPattern] = Field(default_factory=list, description="마스킹 패턴 목록")


class LogAnalysisDefaults(BaseModel):
    """기본 분석 설정"""
    maxLines: int = Field(default=500, description="최대 읽기 줄 수")
    timeRangeMinutes: int = Field(default=60, description="기본 시간 범위 (분)")


class LogAnalysisSettings(BaseModel):
    """로그 분석 설정"""
    enabled: bool = Field(default=False, description="로그 분석 기능 활성화")
    paths: List[LogPath] = Field(default_factory=list, description="로그 경로 목록")
    masking: MaskingConfig = Field(default_factory=MaskingConfig, description="마스킹 설정")
    defaults: LogAnalysisDefaults = Field(default_factory=LogAnalysisDefaults, description="기본 설정")


# === Request Models ===

class LogAnalysisSettingsUpdate(BaseModel):
    """로그 분석 설정 업데이트 요청"""
    enabled: Optional[bool] = Field(None, description="기능 활성화 여부")
    paths: Optional[List[LogPath]] = Field(None, description="로그 경로 목록")
    masking: Optional[MaskingConfig] = Field(None, description="마스킹 설정")
    defaults: Optional[LogAnalysisDefaults] = Field(None, description="기본 설정")


# === Result Models ===

class LogEntry(BaseModel):
    """파싱된 로그 엔트리"""
    timestamp: Optional[datetime] = Field(None, description="로그 타임스탬프")
    level: Optional[str] = Field(None, description="로그 레벨 (ERROR, WARN, INFO 등)")
    message: str = Field(description="로그 메시지")
    raw: str = Field(description="원본 로그 라인")


class LogAnalysisResult(BaseModel):
    """로그 분석 결과"""
    entries: List[LogEntry] = Field(default_factory=list, description="파싱된 로그 엔트리 목록")
    summary: Optional[str] = Field(None, description="분석 요약")
    error_count: int = Field(default=0, description="에러 로그 개수")
    warn_count: int = Field(default=0, description="경고 로그 개수")
    time_range: Optional[str] = Field(None, description="분석 시간 범위")


# === Response Models ===

class LogAnalysisStatusResponse(BaseModel):
    """로그 분석 상태 응답"""
    enabled: bool = Field(..., description="기능 활성화 여부")
    pathCount: int = Field(..., description="설정된 로그 경로 수")
    enabledPathCount: int = Field(..., description="활성화된 로그 경로 수")
    maskingEnabled: bool = Field(..., description="마스킹 활성화 여부")
    lastUpdated: Optional[datetime] = Field(None, description="마지막 업데이트 시간")
