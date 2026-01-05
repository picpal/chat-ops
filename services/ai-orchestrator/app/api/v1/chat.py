"""
Chat API - Step 6: LangChain + Natural Language Processing
자연어 → QueryPlan → Core API → RenderSpec
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import logging
import os
import uuid
from datetime import datetime

from app.services.query_planner import get_query_planner
from app.services.render_composer import get_render_composer
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
CORE_API_URL = os.getenv("CORE_API_URL", "http://localhost:8080")


class ChatRequest(BaseModel):
    """채팅 요청"""
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """채팅 응답"""
    render_spec: Dict[str, Any]
    query_plan: Dict[str, Any]
    conversation_id: str
    original_message: str
    processing_info: Dict[str, Any]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Step 6: LangChain 기반 자연어 처리

    Flow:
    1. 사용자 메시지 수신
    2. QueryPlannerService로 자연어 → QueryPlan 변환
    3. Core API 호출
    4. RenderComposerService로 QueryResult → RenderSpec 변환
    5. RenderSpec 반환
    """
    start_time = datetime.utcnow()
    conversation_id = request.conversation_id or str(uuid.uuid4())
    request_id = f"req-{uuid.uuid4().hex[:8]}"

    logger.info(f"[{request_id}] Received message: {request.message}")

    processing_info = {
        "requestId": request_id,
        "stages": []
    }

    try:
        # Stage 1: Natural Language → QueryPlan
        stage_start = datetime.utcnow()
        query_planner = get_query_planner()
        query_plan = await query_planner.generate_query_plan(request.message)
        query_plan["requestId"] = request_id

        processing_info["stages"].append({
            "name": "query_plan_generation",
            "durationMs": int((datetime.utcnow() - stage_start).total_seconds() * 1000),
            "status": "success"
        })

        logger.info(f"[{request_id}] Generated QueryPlan: {query_plan}")

        # Stage 2: Call Core API
        stage_start = datetime.utcnow()
        query_result = await call_core_api(query_plan)

        processing_info["stages"].append({
            "name": "core_api_call",
            "durationMs": int((datetime.utcnow() - stage_start).total_seconds() * 1000),
            "status": "success" if query_result.get("status") == "success" else "error"
        })

        logger.info(f"[{request_id}] Core API response status: {query_result.get('status')}")

        # Stage 3: QueryResult → RenderSpec
        stage_start = datetime.utcnow()
        render_composer = get_render_composer()
        render_spec = render_composer.compose(query_result, query_plan, request.message)

        processing_info["stages"].append({
            "name": "render_spec_composition",
            "durationMs": int((datetime.utcnow() - stage_start).total_seconds() * 1000),
            "status": "success"
        })

        # Calculate total processing time
        total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        processing_info["totalDurationMs"] = total_time

        logger.info(f"[{request_id}] Completed in {total_time}ms")

        return ChatResponse(
            render_spec=render_spec,
            query_plan=query_plan,
            conversation_id=conversation_id,
            original_message=request.message,
            processing_info=processing_info
        )

    except Exception as e:
        logger.error(f"[{request_id}] Error: {e}", exc_info=True)

        total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        processing_info["totalDurationMs"] = total_time
        processing_info["error"] = str(e)

        # 에러 발생 시에도 RenderSpec 반환 (에러 메시지 표시용)
        error_render_spec = {
            "type": "text",
            "title": "처리 중 오류 발생",
            "text": {
                "content": f"## 요청 처리 중 오류가 발생했습니다\n\n"
                          f"**요청**: {request.message}\n\n"
                          f"**오류**: {str(e)}\n\n"
                          f"잠시 후 다시 시도해주세요.",
                "format": "markdown",
                "sections": [
                    {
                        "type": "error",
                        "title": "오류 정보",
                        "content": str(e)
                    }
                ]
            },
            "metadata": {
                "requestId": request_id,
                "generatedAt": datetime.utcnow().isoformat() + "Z"
            }
        }

        return ChatResponse(
            render_spec=error_render_spec,
            query_plan={"error": str(e)},
            conversation_id=conversation_id,
            original_message=request.message,
            processing_info=processing_info
        )


async def call_core_api(query_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Core API 호출"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CORE_API_URL}/api/v1/query/start",
                json=query_plan
            )

            # HTTP 에러가 아닌 비즈니스 에러도 처리
            if response.status_code >= 400:
                error_body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                logger.warning(f"Core API returned {response.status_code}: {error_body}")
                return error_body if error_body else {
                    "status": "error",
                    "error": {
                        "code": f"HTTP_{response.status_code}",
                        "message": response.text
                    }
                }

            return response.json()

    except httpx.TimeoutException:
        logger.error("Core API timeout")
        return {
            "status": "error",
            "error": {
                "code": "TIMEOUT",
                "message": "Core API 요청 시간이 초과되었습니다."
            }
        }
    except httpx.HTTPError as e:
        logger.error(f"Core API HTTP error: {e}")
        return {
            "status": "error",
            "error": {
                "code": "CONNECTION_ERROR",
                "message": f"Core API 연결 오류: {str(e)}"
            }
        }


@router.get("/chat/test")
async def test_core_api():
    """Core API 연결 테스트"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CORE_API_URL}/api/v1/query/health")
            response.raise_for_status()
            return {
                "core_api_status": "reachable",
                "core_api_response": response.json()
            }
    except httpx.HTTPError as e:
        return {
            "core_api_status": "unreachable",
            "error": str(e)
        }


@router.get("/chat/config")
async def get_config():
    """현재 설정 확인 (디버깅용)"""
    return {
        "core_api_url": CORE_API_URL,
        "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "rag_enabled": os.getenv("RAG_ENABLED", "true").lower() == "true",
        "database_url_set": bool(os.getenv("DATABASE_URL")),
        "step": "7-rag-document-search"
    }


@router.get("/chat/rag/status")
async def get_rag_status():
    """RAG 서비스 상태 확인"""
    try:
        rag_service = get_rag_service()
        doc_counts = await rag_service.get_document_count()

        return {
            "status": "available",
            "rag_enabled": os.getenv("RAG_ENABLED", "true").lower() == "true",
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
            "document_counts": doc_counts,
            "total_documents": sum(doc_counts.values()) if doc_counts else 0
        }
    except Exception as e:
        return {
            "status": "unavailable",
            "error": str(e)
        }


@router.post("/chat/rag/search")
async def search_documents(query: str, k: int = 3):
    """RAG 문서 검색 테스트"""
    try:
        rag_service = get_rag_service()
        documents = await rag_service.search_docs(query=query, k=k)

        return {
            "query": query,
            "count": len(documents),
            "documents": [
                {
                    "id": doc.id,
                    "doc_type": doc.doc_type,
                    "title": doc.title,
                    "content": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                    "similarity": doc.similarity
                }
                for doc in documents
            ]
        }
    except Exception as e:
        return {
            "query": query,
            "error": str(e)
        }
