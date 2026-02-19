"""
Chat API - Step 6: LangChain + Natural Language Processing
자연어 -> QueryPlan -> Core API -> RenderSpec

Text-to-SQL 모드 추가:
SQL_ENABLE_TEXT_TO_SQL=true 설정 시 AI가 직접 SQL을 생성하여 읽기 전용 DB에서 실행
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import httpx
import logging
import os
import re
import uuid
from datetime import datetime

# ============================================
# 분리된 모듈에서 import
# ============================================

# 상수/패턴
from app.constants.reference_patterns import ReferenceType

# 대화 컨텍스트 서비스
from app.services.conversation_context import (
    detect_reference_expression,
    build_conversation_context,
    get_previous_query_plan,
    extract_previous_results,
    merge_filters,
    extract_aggregation_value,
    is_arithmetic_request,
)

# SQL RenderSpec 작성기
from app.services.sql_render_composer import compose_sql_render_spec

# 서비스
from app.services.query_planner import get_query_planner, IntentType
from app.services.render_composer import get_render_composer
from app.services.rag_service import get_rag_service
from app.services.log_analysis_service import get_log_analysis_service

# 템플릿
from app.templates.daily_check import (
    get_daily_check_queries,
    compose_daily_check_render_spec,
    get_daily_check_context,
    _calculate_metrics,
    _safe_get_first_row,
    _safe_get_rows
)

# Text-to-SQL 모드 플래그
ENABLE_TEXT_TO_SQL = os.getenv("SQL_ENABLE_TEXT_TO_SQL", "false").lower() == "true"

# Text-to-SQL 모드용 import (조건부)
if ENABLE_TEXT_TO_SQL:
    from app.services.text_to_sql import get_text_to_sql_service, extract_where_conditions
    from app.services.download_service import generate_csv, generate_excel

logger = logging.getLogger(__name__)
logger.info(f"Text-to-SQL mode: {'ENABLED' if ENABLE_TEXT_TO_SQL else 'DISABLED'}")

router = APIRouter()

# Configuration
CORE_API_URL = os.getenv("CORE_API_URL", "http://localhost:8080")
ENABLE_QUERY_PLAN_VALIDATION = os.getenv("ENABLE_QUERY_PLAN_VALIDATION", "true").lower() == "true"


# ============================================
# 모델 정의
# ============================================

class ChatMessageItem(BaseModel):
    """대화 메시지 아이템"""
    id: str
    role: str  # 'user' | 'assistant'
    content: str
    timestamp: str
    status: Optional[str] = None
    renderSpec: Optional[Dict[str, Any]] = None
    queryResult: Optional[Dict[str, Any]] = None
    queryPlan: Optional[Dict[str, Any]] = None  # 이전 쿼리 조건 저장용


class ChatRequest(BaseModel):
    """채팅 요청"""
    message: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    conversation_history: Optional[List[ChatMessageItem]] = Field(default=None, alias="conversationHistory")

    class Config:
        populate_by_name = True


class ChatResponse(BaseModel):
    """채팅 응답 - UI 타입과 일치"""
    request_id: str = Field(alias="requestId")
    render_spec: Dict[str, Any] = Field(alias="renderSpec")
    query_result: Optional[Dict[str, Any]] = Field(default=None, alias="queryResult")  # filter_local 시 None 가능
    query_plan: Dict[str, Any] = Field(alias="queryPlan")  # 이번 쿼리 조건 (후속 질문용)
    ai_message: Optional[str] = Field(default=None, alias="aiMessage")
    timestamp: str

    class Config:
        populate_by_name = True


class DownloadRequest(BaseModel):
    """다운로드 요청"""
    sql: str
    format: str = "csv"  # csv 또는 excel


# ============================================
# 메인 채팅 엔드포인트
# ============================================

@router.post("/chat", response_model=ChatResponse, response_model_by_alias=True)
async def chat(request: ChatRequest):
    """
    Step 6: LangChain 기반 자연어 처리

    Flow (기존 QueryPlan 모드):
    1. 사용자 메시지 수신
    2. QueryPlannerService로 자연어 -> QueryPlan 변환
    3. Core API 호출
    4. RenderComposerService로 QueryResult -> RenderSpec 변환
    5. RenderSpec 반환

    Flow (Text-to-SQL 모드, SQL_ENABLE_TEXT_TO_SQL=true):
    1. 사용자 메시지 수신
    2. TextToSqlService로 자연어 -> SQL 변환
    3. SQL 검증 (SqlValidator)
    4. 읽기 전용 DB에서 직접 실행
    5. 결과를 RenderSpec으로 변환
    """
    start_time = datetime.utcnow()
    conversation_id = request.conversation_id or str(uuid.uuid4())
    request_id = f"req-{uuid.uuid4().hex[:8]}"

    logger.info(f"[{request_id}] Received message: {request.message}")

    processing_info = {
        "requestId": request_id,
        "stages": []
    }

    # ========================================
    # 템플릿 기반 Intent 분류 (Text-to-SQL 분기 전)
    # ========================================
    try:
        query_planner = get_query_planner()

        # 대화 컨텍스트 빌드
        conversation_context = None
        previous_results = []
        if request.conversation_history:
            conversation_context = build_conversation_context(request.conversation_history)
            previous_results = extract_previous_results(request.conversation_history)

        # Intent 분류 (템플릿 기반 요청 감지)
        intent_result = await query_planner.classify_intent(
            request.message,
            conversation_context or "",
            previous_results
        )
        logger.info(f"[{request_id}] Intent classification: {intent_result.intent.value}, confidence={intent_result.confidence:.2f}")

        # daily_check면 템플릿 기반 처리 (Text-to-SQL/QueryPlan 우회)
        if intent_result.intent == IntentType.DAILY_CHECK:
            logger.info(f"[{request_id}] Daily check template triggered")
            return await _handle_daily_check_template(
                request,
                request_id,
                intent_result
            )

        # knowledge_answer면 RAG 문서 기반 응답 반환
        if intent_result.intent == IntentType.KNOWLEDGE_ANSWER:
            logger.info(f"[{request_id}] Knowledge answer detected")
            return await _handle_knowledge_answer(request, request_id, intent_result)

        # log_analysis면 서버 로그 분석
        if intent_result.intent == IntentType.LOG_ANALYSIS:
            logger.info(f"[{request_id}] Log analysis detected")
            return await _handle_log_analysis(request, request_id, intent_result)

        # direct_answer면 바로 응답 반환
        if intent_result.intent == IntentType.DIRECT_ANSWER and intent_result.direct_answer_text:
            logger.info(f"[{request_id}] Direct answer detected")
            return ChatResponse(
                request_id=request_id,
                query_plan={
                    "query_intent": "direct_answer",
                    "requestId": request_id
                },
                query_result=None,
                render_spec={
                    "type": "text",
                    "text": {
                        "content": intent_result.direct_answer_text,
                        "format": "markdown"
                    },
                    "metadata": {
                        "intent": "direct_answer",
                        "confidence": intent_result.confidence,
                        "reasoning": intent_result.reasoning
                    }
                },
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
    except Exception as e:
        logger.warning(f"[{request_id}] Intent classification failed, proceeding to default mode: {e}")
        # 예외 발생 시 변수 초기화
        query_planner = None
        conversation_context = None

    # ========================================
    # Text-to-SQL 모드 분기
    # ========================================
    if ENABLE_TEXT_TO_SQL:
        return await handle_text_to_sql(request, request_id, start_time)

    # ========================================
    # QueryPlan 모드 (Text-to-SQL 비활성화 시)
    # ========================================
    try:
        # QueryPlanner 초기화 (Intent 분류 실패 시 재초기화)
        if query_planner is None:
            query_planner = get_query_planner()
        if conversation_context is None and request.conversation_history:
            conversation_context = build_conversation_context(request.conversation_history)

        # Stage 1: Natural Language -> QueryPlan
        stage_start = datetime.utcnow()

        query_plan = await query_planner.generate_query_plan(
            request.message,
            conversation_context=conversation_context,
            enable_validation=ENABLE_QUERY_PLAN_VALIDATION
        )

        # LLM이 판단한 의도에 따라 필터 병합 결정
        query_intent = query_plan.get("query_intent", "new_query")
        logger.info(f"[{request_id}] Query intent: {query_intent}")

        if query_intent == "refine_previous":
            if request.conversation_history:
                previous_plan = get_previous_query_plan(request.conversation_history)
                if previous_plan:
                    logger.info(f"[{request_id}] Intent: refine_previous, merging with previous filters")
                    logger.info(f"[{request_id}] Previous plan: {previous_plan}")
                    query_plan = merge_filters(previous_plan, query_plan)
                    logger.info(f"[{request_id}] Merged plan: {query_plan}")
        elif query_intent == "filter_local":
            # 클라이언트 사이드 필터링: Core API 호출 없이 필터 조건만 반환
            return await _handle_filter_local(request, request_id, query_plan, query_planner)
        elif query_intent == "aggregate_local":
            # 클라이언트 사이드 집계: 이전 결과에서 집계
            return await _handle_aggregate_local(request, request_id, query_plan, query_planner)
        elif query_intent == "direct_answer":
            # LLM이 직접 답변: DB 조회 없이 텍스트 응답
            return _handle_direct_answer(request_id, query_plan)
        else:
            logger.info(f"[{request_id}] Intent: new_query, no filter merge")

        query_plan["requestId"] = request_id

        processing_info["stages"].append({
            "name": "query_plan_generation",
            "durationMs": int((datetime.utcnow() - stage_start).total_seconds() * 1000),
            "status": "success"
        })

        logger.info(f"[{request_id}] Final QueryPlan: {query_plan}")

        # Clarification 필요 시 쿼리 실행 없이 대화형 질문 반환
        if query_plan.get("needs_clarification"):
            return _handle_clarification(request_id, query_plan, start_time)

        # Stage 2: Call Core API
        stage_start = datetime.utcnow()
        query_result = await call_core_api(query_plan)

        processing_info["stages"].append({
            "name": "core_api_call",
            "durationMs": int((datetime.utcnow() - stage_start).total_seconds() * 1000),
            "status": "success" if query_result.get("status") == "success" else "error"
        })

        logger.info(f"[{request_id}] Core API response status: {query_result.get('status')}")

        # Stage 3: QueryResult -> RenderSpec
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
            request_id=request_id,
            render_spec=render_spec,
            query_result=query_result,
            query_plan=query_plan,  # 후속 질문에서 이전 쿼리 조건 참조용
            ai_message=f"'{request.message}'에 대한 결과입니다.",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        logger.error(f"[{request_id}] Error: {e}", exc_info=True)
        return _handle_error(request_id, request.message, e, start_time)


# ============================================
# Intent 별 핸들러
# ============================================

async def _handle_daily_check_template(
    request: ChatRequest,
    request_id: str,
    intent_result
) -> ChatResponse:
    """템플릿 기반 일일점검 처리"""
    # 대상 날짜 결정
    target_date = intent_result.check_date or datetime.now().strftime("%Y-%m-%d")

    logger.info(f"[{request_id}] Processing daily check for date: {target_date}")

    # 템플릿에서 쿼리 목록 가져오기
    queries = get_daily_check_queries(target_date)

    # Core API 순차 호출
    results = []
    for i, query_plan in enumerate(queries):
        logger.info(f"[{request_id}] Executing daily check query {i+1}/4: {query_plan.get('entity')}")
        try:
            result = await call_core_api(query_plan)
            results.append(result)
        except Exception as e:
            logger.error(f"[{request_id}] Failed to execute query {i+1}: {e}")
            results.append({"data": {"rows": []}})

    # 템플릿으로 RenderSpec 생성
    render_spec = compose_daily_check_render_spec(
        results,
        target_date,
        request.message
    )

    # 꼬리질문 지원을 위한 컨텍스트 생성
    today_summary = _safe_get_first_row(results[0])
    status_dist = _safe_get_rows(results[1])
    refund_summary = _safe_get_first_row(results[2])
    yesterday_summary = _safe_get_first_row(results[3])
    metrics = _calculate_metrics(today_summary, yesterday_summary, refund_summary)
    context = get_daily_check_context(metrics, status_dist, target_date)

    return ChatResponse(
        request_id=request_id,
        render_spec=render_spec,
        query_plan={
            "mode": "daily_check_template",
            "targetDate": target_date,
            "requestId": request_id
        },
        query_result={
            "requestId": request_id,
            "status": "success",
            "data": {"rows": [], "aggregations": {}},
            "metadata": {
                "dataSource": "daily_check_template",
                "targetDate": target_date,
                "queryCount": len(queries)
            },
            "context_for_followup": context
        },
        ai_message=f"'{request.message}'에 대한 일일점검 결과입니다.",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


async def _handle_filter_local(
    request: ChatRequest,
    request_id: str,
    query_plan: Dict[str, Any],
    query_planner
) -> ChatResponse:
    """filter_local intent 처리"""
    logger.info(f"[{request_id}] Intent: filter_local, client-side filtering")

    # entity가 없으면 이전 queryPlan에서 상속
    if not query_plan.get("entity") and request.conversation_history:
        previous_plan = get_previous_query_plan(request.conversation_history)
        if previous_plan and previous_plan.get("entity"):
            query_plan["entity"] = previous_plan["entity"]
            logger.info(f"[{request_id}] Inherited entity from previous plan: {query_plan['entity']}")

    # 이전 결과가 있는 메시지들 찾기
    result_messages = _find_result_messages(request.conversation_history, request_id)
    logger.info(f"[{request_id}] Found {len(result_messages)} result messages")

    # 다중 결과 clarification 체크
    needs_clarification = await _check_multi_result_clarification(
        request, request_id, query_plan, result_messages, query_planner, "filter_local"
    )

    if needs_clarification:
        return needs_clarification

    # 결과가 1개 이하: 클라이언트에서 필터링하도록 응답
    target_index = result_messages[-1][0] if result_messages else -1
    logger.info(f"[{request_id}] Single result, returning filter_local response (target: {target_index})")

    filter_local_render_spec = {
        "type": "filter_local",
        "filter": query_plan.get("filters", []),
        "targetResultIndex": target_index,
        "metadata": {
            "requestId": request_id,
            "generatedAt": datetime.utcnow().isoformat() + "Z"
        }
    }

    return ChatResponse(
        request_id=request_id,
        render_spec=filter_local_render_spec,
        query_result=None,
        query_plan={**query_plan, "requestId": request_id},
        ai_message="이전 결과에서 필터링합니다.",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


async def _handle_aggregate_local(
    request: ChatRequest,
    request_id: str,
    query_plan: Dict[str, Any],
    query_planner
) -> ChatResponse:
    """aggregate_local intent 처리"""
    logger.info(f"[{request_id}] Intent: aggregate_local, client-side aggregation")

    # entity가 없으면 이전 queryPlan에서 상속
    if not query_plan.get("entity") and request.conversation_history:
        previous_plan = get_previous_query_plan(request.conversation_history)
        if previous_plan and previous_plan.get("entity"):
            query_plan["entity"] = previous_plan["entity"]
            logger.info(f"[{request_id}] Inherited entity from previous plan: {query_plan['entity']}")

    # 이전 결과가 있는 메시지들 찾기
    result_messages = _find_result_messages(request.conversation_history, request_id)
    logger.info(f"[{request_id}] Found {len(result_messages)} result messages for aggregation")

    # 집계 정보 추출
    aggregations = query_plan.get("aggregations", [])
    if not aggregations:
        # 기본 집계: sum(amount)
        aggregations = [{"function": "sum", "field": "amount", "alias": "totalAmount", "displayLabel": "결제 금액 합계", "currency": "USD"}]

    # 다중 결과 clarification 체크
    needs_clarification = await _check_multi_result_clarification(
        request, request_id, query_plan, result_messages, query_planner, "aggregate_local", aggregations
    )

    if needs_clarification:
        return needs_clarification

    # 결과가 1개 이하: 클라이언트에서 집계하도록 응답
    target_index = result_messages[-1][0] if result_messages else -1
    logger.info(f"[{request_id}] Single result, returning aggregate_local response (target: {target_index})")

    aggregate_local_render_spec = {
        "type": "aggregate_local",
        "aggregations": aggregations,
        "targetResultIndex": target_index,
        "metadata": {
            "requestId": request_id,
            "generatedAt": datetime.utcnow().isoformat() + "Z"
        }
    }

    return ChatResponse(
        request_id=request_id,
        render_spec=aggregate_local_render_spec,
        query_result=None,
        query_plan={**query_plan, "requestId": request_id},
        ai_message="이전 결과에서 집계합니다.",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


def _handle_direct_answer(request_id: str, query_plan: Dict[str, Any]) -> ChatResponse:
    """direct_answer intent 처리"""
    direct_answer = query_plan.get("direct_answer", "")
    logger.info(f"[{request_id}] Intent: direct_answer, returning LLM response")

    if not direct_answer:
        direct_answer = "죄송합니다. 답변을 생성하지 못했습니다."

    direct_answer_render_spec = {
        "type": "text",
        "title": "분석 결과",
        "text": {
            "content": direct_answer,
            "format": "markdown"
        },
        "metadata": {
            "requestId": request_id,
            "generatedAt": datetime.utcnow().isoformat() + "Z"
        }
    }

    return ChatResponse(
        request_id=request_id,
        render_spec=direct_answer_render_spec,
        query_result=None,
        query_plan={**query_plan, "requestId": request_id},
        ai_message=direct_answer,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


async def _handle_knowledge_answer(
    request: ChatRequest,
    request_id: str,
    intent_result
) -> ChatResponse:
    """RAG 문서 기반 지식 응답 처리"""
    try:
        rag_service = get_rag_service()

        # RAG 문서 검색 (k=5, 낮은 유사도 임계값으로 폭넓게 검색)
        documents = await rag_service.search_docs(
            query=request.message,
            k=5,
            min_similarity=0.4,
            use_dynamic_params=False
        )

        if not documents:
            logger.info(f"[{request_id}] No RAG documents found for knowledge answer")
            return ChatResponse(
                request_id=request_id,
                query_plan={
                    "query_intent": "knowledge_answer",
                    "requestId": request_id
                },
                query_result=None,
                render_spec={
                    "type": "text",
                    "title": "문서 검색 결과 없음",
                    "text": {
                        "content": "관련 문서를 찾지 못했습니다. 질문을 다시 표현해 주시거나, 데이터 조회가 필요하시면 구체적인 조회 조건을 말씀해 주세요.",
                        "format": "markdown"
                    },
                    "metadata": {
                        "intent": "knowledge_answer",
                        "confidence": intent_result.confidence,
                        "reasoning": intent_result.reasoning
                    }
                },
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

        # LLM을 통한 RAG 기반 답변 생성
        logger.info(f"[{request_id}] Found {len(documents)} RAG documents, generating knowledge answer")
        answer_text = await _generate_knowledge_answer(request.message, documents, rag_service)

        # 참조 문서 정보 구성
        references = [
            {
                "title": doc.title,
                "doc_type": doc.doc_type,
                "similarity": round(doc.similarity, 3)
            }
            for doc in documents
        ]

        return ChatResponse(
            request_id=request_id,
            query_plan={
                "query_intent": "knowledge_answer",
                "requestId": request_id
            },
            query_result=None,
            render_spec={
                "type": "text",
                "title": "업무 지식 답변",
                "text": {
                    "content": answer_text,
                    "format": "markdown"
                },
                "metadata": {
                    "intent": "knowledge_answer",
                    "confidence": intent_result.confidence,
                    "reasoning": intent_result.reasoning,
                    "references": references
                }
            },
            ai_message="질문에 대한 답변입니다.",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        logger.error(f"[{request_id}] Knowledge answer error: {e}", exc_info=True)
        return ChatResponse(
            request_id=request_id,
            query_plan={
                "query_intent": "knowledge_answer",
                "requestId": request_id
            },
            query_result=None,
            render_spec={
                "type": "text",
                "title": "처리 오류",
                "text": {
                    "content": f"지식 기반 답변 생성 중 오류가 발생했습니다: {str(e)}",
                    "format": "markdown"
                },
                "metadata": {
                    "intent": "knowledge_answer",
                    "error": str(e)
                }
            },
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


async def _handle_log_analysis(
    request: ChatRequest,
    request_id: str,
    intent_result
) -> ChatResponse:
    """서버 로그 분석 처리"""
    try:
        log_service = get_log_analysis_service()

        # 로그 분석 수행
        result = await log_service.analyze(
            user_question=request.message,
            time_range_minutes=60,
            max_lines=500,
            level_filter=["ERROR", "WARN"]  # 에러/경고 우선
        )

        # 로그 엔트리를 표시용 데이터로 변환
        log_entries_display = []
        for entry in result.entries[-100:]:  # 최근 100건만 표시
            log_entries_display.append({
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "level": entry.level,
                "message": entry.message
            })

        # RenderSpec 구성
        render_spec = {
            "type": "log_analysis",
            "title": "서버 로그 분석 결과",
            "log_analysis": {
                "summary": result.summary,
                "statistics": {
                    "totalEntries": len(result.entries),
                    "errorCount": result.error_count,
                    "warnCount": result.warn_count,
                    "timeRange": result.time_range
                },
                "entries": log_entries_display
            },
            "metadata": {
                "requestId": request_id,
                "generatedAt": datetime.utcnow().isoformat() + "Z",
                "intent": "log_analysis",
                "confidence": intent_result.confidence
            }
        }

        return ChatResponse(
            request_id=request_id,
            query_plan={
                "query_intent": "log_analysis",
                "requestId": request_id
            },
            query_result=None,
            render_spec=render_spec,
            ai_message=result.summary or "로그 분석이 완료되었습니다.",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        logger.error(f"[{request_id}] Log analysis error: {e}", exc_info=True)
        return ChatResponse(
            request_id=request_id,
            query_plan={
                "query_intent": "log_analysis",
                "requestId": request_id
            },
            query_result=None,
            render_spec={
                "type": "text",
                "title": "로그 분석 오류",
                "text": {
                    "content": f"로그 분석 중 오류가 발생했습니다: {str(e)}",
                    "format": "markdown"
                },
                "metadata": {
                    "intent": "log_analysis",
                    "error": str(e)
                }
            },
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


async def _generate_knowledge_answer(
    user_message: str,
    documents: list,
    rag_service
) -> str:
    """RAG 컨텍스트 + 사용자 질문으로 LLM 답변 생성"""
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage
    from app.services.settings_service import get_settings_service
    from app.services.quality_answer_service import get_quality_answer_service

    # RAG 컨텍스트 구성
    context = rag_service.format_context(documents)

    # Quality Answer RAG: 유사 고품질 답변 검색 및 컨텍스트 추가
    quality_context = ""
    try:
        settings_service = get_settings_service()
        if settings_service.is_quality_answer_rag_enabled():
            qa_service = get_quality_answer_service()
            quality_answers = await qa_service.search_similar_answers(user_message, k=2, min_similarity=0.6)
            if quality_answers:
                quality_context = qa_service.format_quality_context(quality_answers)
                logger.info(f"Found {len(quality_answers)} quality answers for context enhancement")
    except Exception as e:
        logger.warning(f"Failed to search quality answers (non-blocking): {e}")

    # LLM 설정
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    if llm_provider == "anthropic":
        llm = ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            temperature=0
        )
    else:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0
        )

    # 프롬프트 구성 (quality_context가 있으면 추가)
    full_context = context
    if quality_context:
        full_context = f"{context}\n\n{quality_context}"

    prompt = f"""당신은 PG(결제 게이트웨이) 백오피스 업무 지식 전문가입니다.
아래 제공된 참고 문서만을 기반으로 사용자 질문에 답변하세요.

{full_context}

## 사용자 질문
{user_message}

## 답변 규칙
1. **제공된 문서 내용만** 기반으로 답변하세요. 문서에 없는 내용은 추측하지 마세요.
2. 문서에 해당 내용이 부족하면 "제공된 문서에서 해당 내용을 충분히 확인하지 못했습니다"라고 안내하세요.
3. **마크다운 형식**으로 가독성 있게 작성하세요 (제목, 목록, 굵은 글씨 활용).
4. 프로세스/절차 설명 시 **단계별 번호**를 사용하세요.
5. 관련 에러코드, 주의사항 등 부가 정보가 문서에 있으면 함께 안내하세요.
6. "참고 답변 예시"가 있다면 해당 답변의 톤과 구조를 참고하되, 반드시 현재 질문에 맞게 답변하세요.
"""

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return response.content.strip()


def _handle_clarification(request_id: str, query_plan: Dict[str, Any], start_time: datetime) -> ChatResponse:
    """clarification 필요 시 처리"""
    question = query_plan.get("clarification_question", "어떤 데이터를 조회하시겠습니까?")
    logger.info(f"[{request_id}] Clarification needed: {question}")

    # 대화형 텍스트로 응답 (버튼 없이)
    clarification_render_spec = {
        "type": "text",
        "title": "추가 정보 필요",
        "text": {
            "content": question,
            "format": "plain"
        },
        "metadata": {
            "requestId": request_id,
            "generatedAt": datetime.utcnow().isoformat() + "Z"
        }
    }

    clarification_query_result = {
        "requestId": request_id,
        "status": "pending",
        "data": {"rows": [], "aggregations": {}},
        "metadata": {
            "executionTimeMs": int((datetime.utcnow() - start_time).total_seconds() * 1000),
            "rowsReturned": 0,
            "dataSource": "clarification_required"
        }
    }

    return ChatResponse(
        request_id=request_id,
        render_spec=clarification_render_spec,
        query_result=clarification_query_result,
        query_plan=query_plan,
        ai_message=question,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


def _handle_error(request_id: str, message: str, error: Exception, start_time: datetime) -> ChatResponse:
    """에러 처리"""
    total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    error_render_spec = {
        "type": "text",
        "title": "처리 중 오류 발생",
        "text": {
            "content": f"## 요청 처리 중 오류가 발생했습니다\n\n"
                      f"**요청**: {message}\n\n"
                      f"**오류**: {str(error)}\n\n"
                      f"잠시 후 다시 시도해주세요.",
            "format": "markdown",
            "sections": [
                {
                    "type": "error",
                    "title": "오류 정보",
                    "content": str(error)
                }
            ]
        },
        "metadata": {
            "requestId": request_id,
            "generatedAt": datetime.utcnow().isoformat() + "Z"
        }
    }

    error_query_result = {
        "requestId": request_id,
        "status": "error",
        "data": {"rows": [], "aggregations": {}},
        "metadata": {
            "executionTimeMs": total_time,
            "rowsReturned": 0,
            "totalRows": 0,
            "dataSource": "error"
        },
        "error": {
            "code": "PROCESSING_ERROR",
            "message": str(error)
        }
    }

    error_query_plan = {
        "entity": "",
        "operation": "list"
    }

    return ChatResponse(
        request_id=request_id,
        render_spec=error_render_spec,
        query_result=error_query_result,
        query_plan=error_query_plan,
        ai_message=f"요청 처리 중 오류가 발생했습니다: {str(error)}",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


# ============================================
# 유틸리티 함수
# ============================================

def _find_daily_check_context(conversation_history: List[ChatMessageItem]) -> Optional[Dict[str, Any]]:
    """
    대화 이력에서 일일점검 컨텍스트 찾기

    Returns:
        daily_check_result 컨텍스트 또는 None
    """
    for msg in reversed(conversation_history):
        if msg.role == "assistant" and msg.queryResult:
            context = msg.queryResult.get("context_for_followup") or msg.queryResult.get("metadata", {})
            if context.get("type") == "daily_check_result" or context.get("dataSource") == "daily_check_template":
                return {
                    "targetDate": context.get("targetDate") or msg.queryResult.get("metadata", {}).get("targetDate"),
                    "metrics": context.get("metrics", {})
                }
            # queryPlan에서 daily_check_template 확인
            if msg.queryPlan and msg.queryPlan.get("mode") == "daily_check_template":
                return {
                    "targetDate": msg.queryPlan.get("targetDate"),
                    "metrics": {}
                }
    return None


def _is_error_related_query(message: str) -> bool:
    """
    오류/실패 관련 질문인지 확인
    """
    error_keywords = [
        "오류", "실패", "에러", "error", "fail", "aborted",
        "중단", "취소", "문제", "장애", "이슈",
        "failure_code", "failure_message"
    ]
    message_lower = message.lower()
    return any(keyword.lower() in message_lower for keyword in error_keywords)


def _has_date_in_message(message: str) -> bool:
    """
    메시지에 날짜가 이미 포함되어 있는지 확인
    """
    import re
    # 날짜 패턴: YYYY-MM-DD, YYYY년 M월 D일, M월 D일 등
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',  # 2026-01-24
        r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',  # 2026년 1월 24일
        r'\d{1,2}월\s*\d{1,2}일',  # 1월 24일
        r'오늘', r'어제', r'금일', r'당일', r'전일'
    ]
    for pattern in date_patterns:
        if re.search(pattern, message):
            return True
    return False


def _find_result_messages(conversation_history: Optional[List[ChatMessageItem]], request_id: str) -> List[tuple]:
    """대화 이력에서 결과가 있는 메시지들 찾기"""
    result_messages = []
    if conversation_history:
        logger.info(f"[{request_id}] Checking {len(conversation_history)} messages in history")
        for i, msg in enumerate(conversation_history):
            has_query_result = msg.queryResult is not None
            logger.info(f"[{request_id}] Message {i}: role={msg.role}, hasQueryResult={has_query_result}")
            if msg.role == "assistant" and msg.queryResult:
                result_messages.append((i, msg))
    return result_messages


async def _check_multi_result_clarification(
    request: ChatRequest,
    request_id: str,
    query_plan: Dict[str, Any],
    result_messages: List[tuple],
    query_planner,
    query_intent: str,
    aggregations: Optional[List[Dict]] = None
) -> Optional[ChatResponse]:
    """다중 결과에 대한 clarification 체크"""
    # 1단계: LLM이 모호하다고 판단했는지 확인
    needs_result_clarification = query_plan.get("needs_result_clarification", False)
    logger.info(f"[{request_id}] 1st stage LLM decision: needs_result_clarification={needs_result_clarification}")

    # 2단계: 다중 결과 + 1단계가 False면 상위 모델로 재판단
    if len(result_messages) > 1 and not needs_result_clarification:
        logger.info(f"[{request_id}] Multiple results but 1st stage said no clarification, invoking 2nd stage check...")

        # 결과 요약 생성
        result_summaries = []
        for msg_idx, msg in result_messages:
            entity = msg.queryPlan.get("entity", "unknown") if msg.queryPlan else "unknown"
            count = 0
            if msg.queryResult:
                if isinstance(msg.queryResult, dict):
                    count = msg.queryResult.get("totalCount", msg.queryResult.get("metadata", {}).get("rowsReturned", 0))
            filters_str = ""
            if msg.queryPlan and msg.queryPlan.get("filters"):
                filters_str = ", ".join([f"{f.get('field')}={f.get('value')}" for f in msg.queryPlan.get("filters", [])[:2]])
            result_summaries.append({"entity": entity, "count": count, "filters": filters_str})

        # 2단계 LLM 판단 호출
        needs_result_clarification = await query_planner.check_clarification_needed(
            user_message=request.message,
            result_summaries=result_summaries,
            query_intent=query_intent
        )
        logger.info(f"[{request_id}] 2nd stage LLM decision: needs_result_clarification={needs_result_clarification}")

    if len(result_messages) > 1 and needs_result_clarification:
        # 다중 결과 + LLM이 모호하다고 판단: clarification 요청
        recent_results = result_messages[-5:]  # 최근 5개만
        options = []
        indices = []

        for idx, (msg_idx, msg) in enumerate(reversed(recent_results)):
            entity = msg.queryPlan.get("entity", "데이터") if msg.queryPlan else "데이터"
            count = "?"
            if msg.queryResult:
                if isinstance(msg.queryResult, dict):
                    count = msg.queryResult.get("totalCount", msg.queryResult.get("metadata", {}).get("rowsReturned", "?"))
            time_str = msg.timestamp[-8:-3] if msg.timestamp and len(msg.timestamp) >= 8 else ""

            label = f"직전: {entity} {count}건 ({time_str})" if idx == 0 else f"{entity} {count}건 ({time_str})"
            options.append(label)
            indices.append(msg_idx)

        is_aggregation = query_intent == "aggregate_local"
        question = "어떤 데이터를 기준으로 집계할까요?" if is_aggregation else "어떤 조회 결과를 필터링할까요?"
        logger.info(f"[{request_id}] Multiple results found, requesting clarification")

        clarification_render_spec = {
            "type": "clarification",
            "clarification": {
                "question": question,
                "options": options
            },
            "metadata": {
                "requestId": request_id,
                "targetResultIndices": indices,
                "pendingFilters": query_plan.get("filters", []) if not is_aggregation else None,
                "pendingAggregations": aggregations if is_aggregation else None,
                "aggregationType": query_intent if is_aggregation else None,
                "generatedAt": datetime.utcnow().isoformat() + "Z"
            }
        }

        return ChatResponse(
            request_id=request_id,
            render_spec=clarification_render_spec,
            query_result=None,
            query_plan={**query_plan, "needs_clarification": True, "requestId": request_id},
            ai_message=question,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    return None


# ============================================
# Core API 호출
# ============================================

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


# ============================================
# 디버깅/유틸리티 엔드포인트
# ============================================

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
        "anthropic_api_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
        "rag_enabled": os.getenv("RAG_ENABLED", "true").lower() == "true",
        "database_url_set": bool(os.getenv("DATABASE_URL")),
        "query_plan_validation": {
            "enabled": ENABLE_QUERY_PLAN_VALIDATION,
            "validator_provider": os.getenv("VALIDATOR_LLM_PROVIDER", "openai"),
            "validator_model": os.getenv("VALIDATOR_LLM_MODEL", "gpt-4o-mini"),
            "quality_threshold": float(os.getenv("VALIDATOR_QUALITY_THRESHOLD", "0.8")),
            "use_llm_validation": os.getenv("VALIDATOR_USE_LLM", "true").lower() == "true"
        },
        "step": "8-query-plan-validation"
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


# ============================================
# 대용량 데이터 다운로드 엔드포인트
# ============================================

@router.post("/chat/download")
async def download_query_result(request: DownloadRequest):
    """
    대용량 쿼리 결과 다운로드

    - SQL 재검증 후 실행 (LIMIT 없이)
    - Streaming 응답으로 메모리 효율화
    """
    if not ENABLE_TEXT_TO_SQL:
        raise HTTPException(400, "Text-to-SQL mode is not enabled")

    from app.services.sql_validator import get_sql_validator

    # SQL 검증 (보안)
    validator = get_sql_validator()
    validation = validator.validate(request.sql)

    if not validation.is_valid:
        raise HTTPException(400, f"Invalid SQL: {', '.join(validation.issues)}")

    # LIMIT 제거 (전체 데이터 다운로드)
    unlimited_sql = re.sub(r'\bLIMIT\s+\d+', '', validation.sanitized_sql, flags=re.IGNORECASE)
    unlimited_sql = re.sub(r'\bOFFSET\s+\d+', '', unlimited_sql, flags=re.IGNORECASE)

    logger.info(f"Download request - Original SQL: {request.sql[:100]}...")
    logger.info(f"Download request - Unlimited SQL: {unlimited_sql[:100]}...")

    text_to_sql = get_text_to_sql_service()

    # 파일명 생성
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # format에 따라 분기 처리
    if request.format == "excel":
        try:
            excel_data = generate_excel(text_to_sql, unlimited_sql)
            filename = f"query_result_{timestamp}.xlsx"

            from fastapi.responses import Response
            return Response(
                content=excel_data,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "X-Content-Type-Options": "nosniff"
                }
            )
        except Exception as e:
            logger.error(f"Excel download failed: {e}")
            raise HTTPException(500, f"Excel generation failed: {str(e)}")

    # CSV 응답 (기본)
    filename = f"query_result_{timestamp}.csv"
    return StreamingResponse(
        generate_csv(text_to_sql, unlimited_sql),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Content-Type-Options": "nosniff"
        }
    )


# ============================================
# Text-to-SQL 모드 핸들러
# ============================================

async def handle_text_to_sql(
    request: ChatRequest,
    request_id: str,
    start_time: datetime
) -> ChatResponse:
    """
    Text-to-SQL 모드 처리

    AI가 직접 SQL을 생성하고 읽기 전용 DB에서 실행합니다.

    Phase 0 추가: 일일점검 꼬리 질문 처리
    - 일일점검 컨텍스트가 있고 오류/실패 관련 질문인 경우
    - targetDate를 메시지에 자동 주입

    Phase 1 추가: 산술 연산 요청 감지
    - 이전 집계 결과가 있고 + 산술 연산 요청인 경우
    - DB 조회 없이 직접 계산하여 응답
    """
    logger.info(f"[{request_id}] Text-to-SQL mode: processing")

    # 메시지 변환용 (일일점검 꼬리 질문 처리 결과)
    enhanced_message = request.message

    try:
        # ========================================
        # Phase 0: 일일점검 꼬리 질문 처리
        # ========================================
        if request.conversation_history:
            daily_check_context = _find_daily_check_context(request.conversation_history)
            if daily_check_context:
                target_date = daily_check_context.get("targetDate")
                if target_date and _is_error_related_query(request.message):
                    # 메시지에 날짜가 없으면 자동 주입
                    if not _has_date_in_message(request.message):
                        enhanced_message = f"{target_date} 날짜 기준으로 {request.message}"
                        logger.info(f"[{request_id}] Daily check followup: injected targetDate={target_date}")
                        logger.info(f"[{request_id}] Enhanced message: {enhanced_message}")

        # ========================================
        # Phase 1: 산술 연산 요청 감지 (수수료, VAT 등)
        # ========================================
        if request.conversation_history:
            logger.info(f"[{request_id}] Phase 1: Checking arithmetic request, history size={len(request.conversation_history)}")

            # 디버그: conversation_history 구조 확인
            for i, msg in enumerate(request.conversation_history[-3:]):  # 최근 3개만
                logger.info(f"[{request_id}] Phase 1 Debug: msg[{i}] role={msg.role}, has_renderSpec={msg.renderSpec is not None}, has_queryResult={msg.queryResult is not None}")
                if msg.renderSpec:
                    logger.info(f"[{request_id}] Phase 1 Debug: msg[{i}] renderSpec.type={msg.renderSpec.get('type')}")
                if msg.queryResult:
                    logger.info(f"[{request_id}] Phase 1 Debug: msg[{i}] queryResult.isAggregation={msg.queryResult.get('isAggregation')}")

            aggregation_result = extract_aggregation_value(request.conversation_history)
            is_arithmetic = is_arithmetic_request(request.message)
            logger.info(f"[{request_id}] Phase 1: aggregation_result={aggregation_result is not None}, is_arithmetic={is_arithmetic}")

            if aggregation_result and is_arithmetic:
                logger.info(f"[{request_id}] Arithmetic request detected, invoking direct calculation")
                logger.info(f"[{request_id}] Previous aggregation: {aggregation_result['formatted']}, context: {aggregation_result['context']}")

                direct_result = await _perform_direct_calculation(
                    request_id, request.message, aggregation_result, start_time
                )
                if direct_result:
                    return direct_result
                # 직접 계산 실패 시 기존 SQL 생성 로직으로 fallback
                logger.info(f"[{request_id}] Direct calculation failed, falling back to SQL generation")

        # ========================================
        # Phase 1.5: 집계 요청 + 기간 없음 clarification
        # ========================================
        # 참조 표현 먼저 감지 (새 대화인지 확인용)
        is_refinement, ref_type = detect_reference_expression(request.message)

        # 집계 요청인데 기간이 없으면 clarification 반환
        clarification_response = _check_aggregate_without_timerange_for_text_to_sql(
            enhanced_message, is_refinement, request_id
        )
        if clarification_response:
            return clarification_response

        text_to_sql = get_text_to_sql_service()

        # 참조 표현 감지 (연속 대화 WHERE 조건 병합용) - 위에서 이미 감지함
        if is_refinement:
            logger.info(f"[{request_id}] Reference expression detected (type: {ref_type}), will preserve previous WHERE conditions")

        # 대화 이력 변환 (Text-to-SQL 형식)
        sql_history = build_sql_history(request.conversation_history)

        # SQL 생성 및 실행 (is_refinement 전달, enhanced_message 사용)
        result = await text_to_sql.query(
            question=enhanced_message,
            conversation_history=sql_history,
            retry_on_error=True,
            is_refinement=is_refinement
        )

        # 실행 시간 계산
        total_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        if result["success"]:
            # 성공: 데이터를 RenderSpec으로 변환
            # LLM 추천 차트 타입, 인사이트 템플릿, summaryStats 템플릿 추출
            llm_chart_type = result.get("llmChartType")
            insight_template = result.get("insightTemplate")
            summary_stats_template = result.get("summaryStatsTemplate")
            if llm_chart_type:
                logger.info(f"[{request_id}] LLM chart type: {llm_chart_type}")
            if insight_template:
                logger.info(f"[{request_id}] LLM insight template: {insight_template[:50]}...")
            if summary_stats_template:
                logger.info(f"[{request_id}] LLM summaryStats template: {len(summary_stats_template)} items")

            # QueryPlan 추출 (metricType 기반 포맷팅용)
            query_plan = result.get("queryPlan")
            render_spec = compose_sql_render_spec(result, request.message, llm_chart_type, insight_template, summary_stats_template, query_plan)

            # 집계 쿼리 메타데이터 추가
            is_aggregation = result.get("isAggregation", False)
            aggregation_context = result.get("aggregationContext")

            query_result = {
                "requestId": request_id,
                "status": "success",
                "data": {
                    "rows": result["data"],
                    "aggregations": {}
                },
                "metadata": {
                    "executionTimeMs": int(result.get("executionTimeMs") or 0),
                    "rowsReturned": result["rowCount"],
                    "totalRows": result["rowCount"],
                    "dataSource": "text_to_sql"
                },
                # 집계 쿼리 정보 추가
                "isAggregation": is_aggregation,
                "aggregationContext": aggregation_context
            }
        else:
            # 실패: 에러 RenderSpec
            render_spec = {
                "type": "text",
                "title": "쿼리 실행 오류",
                "text": {
                    "content": f"## 쿼리 실행 중 오류가 발생했습니다\n\n"
                              f"**질문**: {request.message}\n\n"
                              f"**오류**: {result.get('error', '알 수 없는 오류')}\n\n"
                              f"**생성된 SQL**:\n```sql\n{result.get('sql', 'N/A')}\n```",
                    "format": "markdown"
                },
                "metadata": {
                    "requestId": request_id,
                    "generatedAt": datetime.utcnow().isoformat() + "Z",
                    "mode": "text_to_sql"
                }
            }
            query_result = {
                "requestId": request_id,
                "status": "error",
                "data": {"rows": [], "aggregations": {}},
                "metadata": {
                    "executionTimeMs": total_time_ms,
                    "rowsReturned": 0,
                    "dataSource": "text_to_sql"
                },
                "error": {
                    "code": "SQL_EXECUTION_ERROR",
                    "message": result.get("error", "Unknown error")
                }
            }

        logger.info(f"[{request_id}] Text-to-SQL completed: success={result['success']}, rows={result['rowCount']}")

        return ChatResponse(
            request_id=request_id,
            render_spec=render_spec,
            query_result=query_result,
            query_plan={
                "mode": "text_to_sql",
                "sql": result.get("sql"),
                "requestId": request_id
            },
            ai_message=f"'{request.message}'에 대한 결과입니다." if result["success"] else "쿼리 실행 중 오류가 발생했습니다.",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        logger.error(f"[{request_id}] Text-to-SQL error: {e}", exc_info=True)
        total_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        error_render_spec = {
            "type": "text",
            "title": "처리 중 오류 발생",
            "text": {
                "content": f"## Text-to-SQL 처리 중 오류가 발생했습니다\n\n"
                          f"**요청**: {request.message}\n\n"
                          f"**오류**: {str(e)}\n\n"
                          f"잠시 후 다시 시도해주세요.",
                "format": "markdown"
            },
            "metadata": {
                "requestId": request_id,
                "generatedAt": datetime.utcnow().isoformat() + "Z",
                "mode": "text_to_sql"
            }
        }

        return ChatResponse(
            request_id=request_id,
            render_spec=error_render_spec,
            query_result={
                "requestId": request_id,
                "status": "error",
                "data": {"rows": [], "aggregations": {}},
                "metadata": {"executionTimeMs": total_time_ms, "rowsReturned": 0}
            },
            query_plan={"mode": "text_to_sql", "error": str(e)},
            ai_message=f"처리 중 오류가 발생했습니다: {str(e)}",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


def build_sql_history(conversation_history: Optional[List[ChatMessageItem]]) -> List[Dict[str, Any]]:
    """
    대화 이력을 Text-to-SQL 형식으로 변환

    대화 기반 맥락 처리를 위해 다음 정보를 포함:
    - role: 메시지 역할 (user/assistant)
    - content: 메시지 내용
    - sql: 생성된 SQL (assistant 메시지)
    - rowCount: 쿼리 결과 건수 (assistant 메시지)
    - whereConditions: WHERE 조건 목록 (assistant 메시지) - Phase 1: 명시적 저장
    """
    if not conversation_history:
        return []

    sql_history = []
    for msg in conversation_history[-10:]:  # 최근 10개만
        entry: Dict[str, Any] = {
            "role": msg.role,
            "content": msg.content
        }

        # assistant 메시지에 SQL 정보가 있으면 포함
        if msg.role == "assistant" and msg.queryPlan:
            if msg.queryPlan.get("mode") == "text_to_sql" and msg.queryPlan.get("sql"):
                sql = msg.queryPlan.get("sql")
                entry["sql"] = sql

                # Phase 1: WHERE 조건을 명시적으로 추출하여 저장
                # 이를 통해 4단계+ 체이닝에서도 조건이 유실되지 않음
                if ENABLE_TEXT_TO_SQL:
                    where_conditions = extract_where_conditions(sql)
                    if where_conditions:
                        entry["whereConditions"] = where_conditions

        # 결과 건수 추출 (queryResult의 metadata에서)
        if msg.role == "assistant" and msg.queryResult:
            metadata = msg.queryResult.get("metadata", {})
            # totalRows 또는 rowsReturned 우선순위로 확인
            row_count = (
                msg.queryResult.get("totalCount") or
                metadata.get("totalRows") or
                metadata.get("rowsReturned")
            )
            if row_count is not None:
                entry["rowCount"] = row_count

        sql_history.append(entry)

    return sql_history


# ============================================
# 직접 계산 핸들러 (산술 연산 요청용)
# ============================================

async def _perform_direct_calculation(
    request_id: str,
    message: str,
    aggregation_result: Dict[str, Any],
    start_time: datetime
) -> Optional[ChatResponse]:
    """
    이전 집계 결과에 대한 산술 연산 수행 (DB 조회 없이)

    수수료, VAT, 비율 계산 등을 LLM을 통해 직접 계산합니다.

    Args:
        request_id: 요청 ID
        message: 사용자 메시지
        aggregation_result: 이전 집계 결과 정보
        start_time: 처리 시작 시간

    Returns:
        ChatResponse 또는 None (계산 실패 시)
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_anthropic import ChatAnthropic
        import os

        # LLM 설정 (빠른 응답을 위해 가벼운 모델 사용)
        llm_provider = os.getenv("LLM_PROVIDER", "openai")

        if llm_provider == "anthropic":
            llm = ChatAnthropic(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
                temperature=0
            )
        else:
            llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0
            )

        # 계산 프롬프트 구성
        base_amount = aggregation_result["amount"]
        context = aggregation_result.get("context", "이전 조회 결과")

        calculation_prompt = f"""당신은 숫자 계산 전문가입니다. 사용자의 요청에 따라 정확한 계산을 수행하세요.

## 기준 금액
- 금액: {base_amount:,.0f}원
- 컨텍스트: {context}

## 사용자 요청
{message}

## 응답 형식
다음 형식으로 응답해주세요:
1. 첫 줄: 계산 결과 금액만 (예: "87,383원")
2. 빈 줄
3. 계산 과정 설명 (간단히)

## 주의사항
- 퍼센트 계산: X%는 기준 금액의 X/100을 곱함
- 수수료: 기준 금액 × 수수료율
- VAT 포함: 기준 금액 × 1.1 (10% VAT인 경우)
- VAT 제외: 기준 금액 ÷ 1.1 (10% VAT인 경우)
- 소수점 이하는 반올림하여 정수로 표시
"""

        # LLM 호출
        response = await llm.ainvoke(calculation_prompt)
        result_text = response.content.strip()

        if not result_text:
            logger.warning(f"[{request_id}] Direct calculation returned empty result")
            return None

        total_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        logger.info(f"[{request_id}] Direct calculation completed: {result_text[:100]}...")

        # RenderSpec 구성
        render_spec = {
            "type": "text",
            "title": "계산 결과",
            "text": {
                "content": f"**{aggregation_result['formatted']}** 기준\n\n{result_text}",
                "format": "markdown"
            },
            "metadata": {
                "requestId": request_id,
                "generatedAt": datetime.utcnow().isoformat() + "Z",
                "mode": "text_to_sql_direct_answer",
                "baseAmount": base_amount,
                "context": context
            }
        }

        return ChatResponse(
            request_id=request_id,
            render_spec=render_spec,
            query_result={
                "requestId": request_id,
                "status": "success",
                "data": {"rows": [], "aggregations": {}},
                "metadata": {
                    "executionTimeMs": total_time_ms,
                    "rowsReturned": 0,
                    "dataSource": "direct_calculation"
                }
            },
            query_plan={
                "mode": "text_to_sql_direct_answer",
                "calculation_type": "arithmetic",
                "base_amount": base_amount,
                "requestId": request_id
            },
            ai_message=result_text.split('\n')[0] if result_text else "계산이 완료되었습니다.",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        logger.error(f"[{request_id}] Direct calculation error: {e}", exc_info=True)
        return None


# ============================================
# 집계 요청 + 기간 없음 clarification 체크
# ============================================

# 집계성 키워드 (clarification 필요 판단용)
AGGREGATE_KEYWORDS = ["추이", "추세", "합계", "평균", "통계", "현황", "분석", "트렌드", "변화"]

# 명시적 기간 표현 패턴
EXPLICIT_TIME_PATTERNS = [
    r"최근\s*\d+\s*[일주월년개]",      # 최근 3개월, 최근 2주
    r"지난\s*\d+\s*[일주월년개]",      # 지난 1달
    r"\d{4}년",                        # 2024년
    r"\d{1,2}월",                      # 3월, 12월
    r"오늘|어제|그제",
    r"이번\s*주|지난\s*주|이번\s*달|지난\s*달",
    r"올해|작년|내년",
]


def _check_aggregate_without_timerange_for_text_to_sql(
    message: str,
    is_refinement: bool,
    request_id: str
) -> Optional[ChatResponse]:
    """
    Text-to-SQL 모드에서 집계 요청 + 기간 없음 체크

    세 가지 조건 모두 충족 시 clarification 응답 반환:
    1. 새 대화 (참조 표현 없음)
    2. 집계성 키워드 포함 (추이, 추세, 합계, 평균, 통계 등)
    3. 명시적 기간 표현 없음

    Returns:
        ChatResponse with clarification if needed, None otherwise
    """
    # 조건 1: 새 대화인지 확인 (참조 표현이 있으면 기존 대화 이어가기)
    if is_refinement:
        return None

    # 조건 2: 집계 요청인지 확인
    message_lower = message.lower()
    is_aggregate_request = any(kw in message_lower for kw in AGGREGATE_KEYWORDS)
    if not is_aggregate_request:
        return None

    # 조건 3: 명시적 기간 표현이 있는지 확인
    has_explicit_time = any(
        re.search(pattern, message) for pattern in EXPLICIT_TIME_PATTERNS
    )
    if has_explicit_time:
        return None

    # 세 조건 모두 충족: clarification 응답 반환
    logger.info(f"[{request_id}] Aggregate request without timerange detected - returning clarification")

    # UI ClarificationRenderSpec 구조에 맞춤:
    # { type: "clarification", clarification: { question: string, options: string[] }, metadata: { originalQuestion: string } }
    # metadata.originalQuestion: 옵션 선택 시 원래 질문과 합쳐서 조회하기 위함
    return ChatResponse(
        request_id=request_id,
        render_spec={
            "type": "clarification",
            "clarification": {
                "question": "조회 기간을 선택해주세요",
                "options": ["최근 1개월", "최근 3개월", "최근 6개월", "최근 1년"]
            },
            "metadata": {
                "originalQuestion": message,
                "clarificationType": "timerange_selection"
            }
        },
        query_result=None,
        query_plan={
            "needs_clarification": True,
            "clarification_question": "조회 기간을 선택해주세요",
            "clarification_options": ["최근 1개월", "최근 3개월", "최근 6개월", "최근 1년"],
            "original_question": message,
            "mode": "text_to_sql"
        },
        ai_message="집계/추이 데이터를 조회하려면 기간 범위가 필요합니다. 원하시는 기간을 선택해주세요.",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
