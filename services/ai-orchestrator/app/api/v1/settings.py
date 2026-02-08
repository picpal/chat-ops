"""
Settings API - 애플리케이션 설정 관리
"""

from fastapi import APIRouter, HTTPException
import logging

from app.models.settings import (
    QualityAnswerRagUpdate,
    QualityAnswerRagStatus,
    SettingUpdate,
    SettingResponse
)
from app.services.settings_service import get_settings_service, SettingsService
from app.services.quality_answer_service import get_quality_answer_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/settings/quality-answer-rag/status",
    response_model=QualityAnswerRagStatus,
    summary="Quality Answer RAG 상태 조회",
    description="Quality Answer RAG 기능의 현재 상태를 조회합니다."
)
async def get_quality_answer_rag_status():
    """
    Quality Answer RAG 상태 조회

    Returns:
        - enabled: 기능 활성화 여부
        - minRating: 최소 별점 기준
        - storedCount: 저장된 고품질 답변 수
        - lastUpdated: 마지막 업데이트 시간
    """
    try:
        settings_service = get_settings_service()
        qa_service = get_quality_answer_service()

        # 저장된 고품질 답변 수 조회
        stored_count = qa_service.get_stored_count()

        # 상태 조회
        status = settings_service.get_quality_answer_rag_status(stored_count)

        return QualityAnswerRagStatus(
            enabled=status["enabled"],
            minRating=status["minRating"],
            storedCount=status["storedCount"],
            lastUpdated=status["lastUpdated"]
        )

    except Exception as e:
        logger.error(f"Failed to get quality answer RAG status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/settings/quality-answer-rag",
    response_model=SettingResponse,
    summary="Quality Answer RAG 설정 업데이트",
    description="Quality Answer RAG 기능의 설정을 업데이트합니다."
)
async def update_quality_answer_rag(request: QualityAnswerRagUpdate):
    """
    Quality Answer RAG 설정 업데이트

    Args:
        request: 업데이트할 설정 값
            - enabled: 기능 활성화 여부 (옵션)
            - minRating: 최소 별점 기준 (옵션)

    Returns:
        업데이트된 설정 정보
    """
    try:
        settings_service = get_settings_service()

        # 업데이트할 값 구성 (None이 아닌 값만)
        update_value = {}
        if request.enabled is not None:
            update_value["enabled"] = request.enabled
        if request.minRating is not None:
            update_value["minRating"] = request.minRating

        if not update_value:
            raise HTTPException(status_code=400, detail="No values to update")

        # 설정 업데이트
        result = settings_service.update_setting(
            SettingsService.QUALITY_ANSWER_RAG_KEY,
            update_value
        )

        logger.info(f"Quality Answer RAG settings updated: {update_value}")

        return SettingResponse(
            key=result["key"],
            value=result["value"],
            description=result.get("description"),
            updatedAt=result.get("updatedAt")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update quality answer RAG settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/settings/{key}",
    response_model=SettingResponse,
    summary="설정 조회",
    description="지정된 키의 설정을 조회합니다."
)
async def get_setting(key: str):
    """
    설정 조회

    Args:
        key: 설정 키

    Returns:
        설정 정보
    """
    try:
        settings_service = get_settings_service()
        result = settings_service.get_setting(key)

        if result is None:
            raise HTTPException(status_code=404, detail=f"Setting not found: {key}")

        return SettingResponse(
            key=result["key"],
            value=result["value"],
            description=result.get("description"),
            updatedAt=result.get("updatedAt")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get setting {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/settings/{key}",
    response_model=SettingResponse,
    summary="설정 업데이트",
    description="지정된 키의 설정을 업데이트합니다."
)
async def update_setting(key: str, request: SettingUpdate):
    """
    설정 업데이트

    Args:
        key: 설정 키
        request: 업데이트할 설정 값

    Returns:
        업데이트된 설정 정보
    """
    try:
        settings_service = get_settings_service()

        result = settings_service.update_setting(key, request.value)

        return SettingResponse(
            key=result["key"],
            value=result["value"],
            description=result.get("description"),
            updatedAt=result.get("updatedAt")
        )

    except Exception as e:
        logger.error(f"Failed to update setting {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
