"""
Log Analysis Settings API - 로그 분석 설정 관리
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import os
import uuid
from datetime import datetime

from app.services.settings_service import get_settings_service
from app.models.log_settings import (
    LogPath,
    LogAnalysisSettings,
    LogAnalysisSettingsUpdate,
    LogAnalysisStatusResponse,
    MaskingConfig,
    LogAnalysisDefaults
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings/log-analysis", tags=["log-settings"])

SETTINGS_KEY = "log_analysis"


class LogPathCreate(BaseModel):
    """로그 경로 생성 요청"""
    name: str = Field(description="표시 이름")
    path: str = Field(description="로그 파일 경로")
    enabled: bool = Field(default=True, description="활성화 여부")


class LogPathUpdate(BaseModel):
    """로그 경로 수정 요청"""
    name: Optional[str] = None
    path: Optional[str] = None
    enabled: Optional[bool] = None


class PathTestResult(BaseModel):
    """경로 테스트 결과"""
    success: bool
    message: str
    fileSize: Optional[int] = None
    lastModified: Optional[str] = None


def _get_current_settings() -> LogAnalysisSettings:
    """현재 설정 조회"""
    settings_service = get_settings_service()
    setting = settings_service.get_setting(SETTINGS_KEY)
    if setting is None:
        return LogAnalysisSettings()

    # value에서 설정 복원
    value = setting.get("value", {})

    # paths 복원
    paths = []
    for p in value.get("paths", []):
        paths.append(LogPath(**p))

    # masking 복원
    masking_data = value.get("masking", {})
    masking = MaskingConfig(**masking_data) if masking_data else MaskingConfig()

    # defaults 복원
    defaults_data = value.get("defaults", {})
    defaults = LogAnalysisDefaults(**defaults_data) if defaults_data else LogAnalysisDefaults()

    return LogAnalysisSettings(
        enabled=value.get("enabled", False),
        paths=paths,
        masking=masking,
        defaults=defaults
    )


def _save_settings(settings: LogAnalysisSettings) -> dict:
    """설정 저장"""
    settings_service = get_settings_service()
    return settings_service.update_setting(
        key=SETTINGS_KEY,
        value=settings.model_dump(),
        description="서버 로그 분석 설정"
    )


@router.get("/status", response_model=LogAnalysisStatusResponse)
async def get_status():
    """
    로그 분석 설정 상태 조회

    Returns:
        - enabled: 기능 활성화 여부
        - pathCount: 설정된 로그 경로 수
        - enabledPathCount: 활성화된 로그 경로 수
        - maskingEnabled: 마스킹 활성화 여부
    """
    try:
        settings = _get_current_settings()
        enabled_paths = [p for p in settings.paths if p.enabled]

        return LogAnalysisStatusResponse(
            enabled=settings.enabled,
            pathCount=len(settings.paths),
            enabledPathCount=len(enabled_paths),
            maskingEnabled=settings.masking.enabled
        )
    except Exception as e:
        logger.error(f"Failed to get log analysis status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=LogAnalysisSettings)
async def get_settings():
    """
    전체 로그 분석 설정 조회

    Returns:
        로그 분석 설정 전체
    """
    try:
        return _get_current_settings()
    except Exception as e:
        logger.error(f"Failed to get log analysis settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("")
async def update_settings(update: LogAnalysisSettingsUpdate):
    """
    로그 분석 설정 업데이트

    Args:
        update: 업데이트할 설정 값 (부분 업데이트 지원)

    Returns:
        업데이트된 설정 정보
    """
    try:
        current = _get_current_settings()

        # 부분 업데이트
        if update.enabled is not None:
            current.enabled = update.enabled
        if update.masking is not None:
            current.masking = update.masking
        if update.defaults is not None:
            current.defaults = update.defaults
        if update.paths is not None:
            current.paths = update.paths

        result = _save_settings(current)
        logger.info(f"Log analysis settings updated: enabled={current.enabled}")
        return result
    except Exception as e:
        logger.error(f"Failed to update log analysis settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paths", response_model=List[LogPath])
async def get_paths():
    """
    로그 경로 목록 조회

    Returns:
        설정된 로그 경로 목록
    """
    try:
        settings = _get_current_settings()
        return settings.paths
    except Exception as e:
        logger.error(f"Failed to get log paths: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/paths", response_model=LogPath)
async def add_path(path_data: LogPathCreate):
    """
    로그 경로 추가

    Args:
        path_data: 추가할 로그 경로 정보

    Returns:
        생성된 로그 경로
    """
    try:
        settings = _get_current_settings()

        # 중복 경로 체크
        if any(p.path == path_data.path for p in settings.paths):
            raise HTTPException(
                status_code=400,
                detail=f"Path already exists: {path_data.path}"
            )

        # 새 경로 생성
        new_path = LogPath(
            id=str(uuid.uuid4())[:8],
            name=path_data.name,
            path=path_data.path,
            enabled=path_data.enabled
        )

        settings.paths.append(new_path)
        _save_settings(settings)

        logger.info(f"Log path added: {new_path.id} -> {new_path.path}")
        return new_path
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add log path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/paths/{path_id}", response_model=LogPath)
async def update_path(path_id: str, path_data: LogPathUpdate):
    """
    로그 경로 수정

    Args:
        path_id: 수정할 경로 ID
        path_data: 수정할 필드

    Returns:
        수정된 로그 경로
    """
    try:
        settings = _get_current_settings()

        # 경로 찾기
        path_index = next(
            (i for i, p in enumerate(settings.paths) if p.id == path_id),
            None
        )
        if path_index is None:
            raise HTTPException(
                status_code=404,
                detail=f"Path not found: {path_id}"
            )

        # 업데이트
        current_path = settings.paths[path_index]
        if path_data.name is not None:
            current_path.name = path_data.name
        if path_data.path is not None:
            # 중복 경로 체크 (자기 자신 제외)
            if any(p.path == path_data.path and p.id != path_id for p in settings.paths):
                raise HTTPException(
                    status_code=400,
                    detail=f"Path already exists: {path_data.path}"
                )
            current_path.path = path_data.path
        if path_data.enabled is not None:
            current_path.enabled = path_data.enabled

        settings.paths[path_index] = current_path
        _save_settings(settings)

        logger.info(f"Log path updated: {path_id}")
        return current_path
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update log path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/paths/{path_id}")
async def delete_path(path_id: str):
    """
    로그 경로 삭제

    Args:
        path_id: 삭제할 경로 ID

    Returns:
        삭제 확인 메시지
    """
    try:
        settings = _get_current_settings()

        # 경로 찾기
        path_index = next(
            (i for i, p in enumerate(settings.paths) if p.id == path_id),
            None
        )
        if path_index is None:
            raise HTTPException(
                status_code=404,
                detail=f"Path not found: {path_id}"
            )

        # 삭제
        deleted_path = settings.paths.pop(path_index)
        _save_settings(settings)

        logger.info(f"Log path deleted: {path_id} -> {deleted_path.path}")
        return {"message": f"Path '{deleted_path.name}' deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete log path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/paths/{path_id}/test", response_model=PathTestResult)
async def test_path(path_id: str):
    """
    로그 경로 테스트

    Args:
        path_id: 테스트할 경로 ID

    Returns:
        테스트 결과 (성공 여부, 파일 정보)
    """
    try:
        settings = _get_current_settings()

        # 경로 찾기
        log_path = next(
            (p for p in settings.paths if p.id == path_id),
            None
        )
        if log_path is None:
            raise HTTPException(
                status_code=404,
                detail=f"Path not found: {path_id}"
            )

        path = log_path.path

        # 파일 존재 확인
        if not os.path.exists(path):
            return PathTestResult(
                success=False,
                message=f"파일을 찾을 수 없습니다: {path}"
            )

        # 파일 정보 조회
        try:
            stat = os.stat(path)
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # 읽기 권한 확인
            if not os.access(path, os.R_OK):
                return PathTestResult(
                    success=False,
                    message=f"파일 읽기 권한이 없습니다: {path}"
                )

            return PathTestResult(
                success=True,
                message="연결 성공",
                fileSize=stat.st_size,
                lastModified=last_modified
            )
        except PermissionError:
            return PathTestResult(
                success=False,
                message=f"파일 접근 권한이 없습니다: {path}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Path test error: {e}")
        return PathTestResult(
            success=False,
            message=f"테스트 실패: {str(e)}"
        )
