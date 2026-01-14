"""
Chat API - Step 6: LangChain + Natural Language Processing
자연어 → QueryPlan → Core API → RenderSpec

Text-to-SQL 모드 추가:
SQL_ENABLE_TEXT_TO_SQL=true 설정 시 AI가 직접 SQL을 생성하여 읽기 전용 DB에서 실행
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Generator
import httpx
import logging
import os
import re
import uuid
import csv
import io
from datetime import datetime

# Text-to-SQL 모드 플래그
ENABLE_TEXT_TO_SQL = os.getenv("SQL_ENABLE_TEXT_TO_SQL", "false").lower() == "true"


def to_camel(string: str) -> str:
    """snake_case를 camelCase로 변환"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def summarize_query_plan(query_plan: Dict[str, Any]) -> str:
    """QueryPlan을 간단한 요약 문자열로 변환"""
    parts = []

    entity = query_plan.get("entity", "")
    if entity:
        parts.append(entity)

    # 필터 요약
    filters = query_plan.get("filters", [])
    if filters:
        filter_strs = [f"{f.get('field')} {f.get('operator')} {f.get('value')}" for f in filters]
        parts.append(f"filters:[{', '.join(filter_strs)}]")

    # limit
    if query_plan.get("limit"):
        parts.append(f"limit:{query_plan['limit']}")

    # orderBy
    order_by = query_plan.get("orderBy", [])
    if order_by:
        order_strs = [f"{o.get('field')} {o.get('direction', 'asc')}" for o in order_by]
        parts.append(f"orderBy:[{', '.join(order_strs)}]")

    return ", ".join(parts) if parts else "[쿼리 없음]"


def build_conversation_context(history: List["ChatMessageItem"]) -> str:
    """이전 대화를 프롬프트용 텍스트로 변환 (다중 결과 상황 명시 포함)"""
    if not history:
        return ""

    context = "## 이전 대화 컨텍스트\n\n"

    # ============================================
    # [NEW] 다중 결과 상황 명시 섹션
    # ============================================
    result_messages = []
    for i, msg in enumerate(history):
        if msg.role == "assistant" and msg.queryResult:
            entity = msg.queryPlan.get("entity", "unknown") if msg.queryPlan else "unknown"
            count = msg.queryResult.get("totalCount", 0)
            # 필터 정보도 추가 (같은 entity라도 조건이 다를 수 있음)
            filters = msg.queryPlan.get("filters", []) if msg.queryPlan else []
            filter_desc = ""
            if filters:
                filter_strs = [f"{f.get('field')}={f.get('value')}" for f in filters[:2]]
                filter_desc = f" ({', '.join(filter_strs)})"
            result_messages.append({
                "index": i,
                "entity": entity,
                "count": count,
                "filter_desc": filter_desc,
                "is_latest": False
            })

    if result_messages:
        result_messages[-1]["is_latest"] = True  # 마지막이 직전 결과

        context += "### 📊 현재 세션의 조회 결과 현황\n"
        for r in result_messages:
            marker = "👉 (직전)" if r["is_latest"] else ""
            context += f"- 결과 #{r['index']}: {r['entity']} {r['count']}건{r['filter_desc']} {marker}\n"

        if len(result_messages) > 1:
            # 다중 결과 경고 - LLM이 주목하도록
            entities = set(r["entity"] for r in result_messages)
            if len(entities) > 1:
                context += f"\n⚠️ **다른 종류의 결과가 {len(result_messages)}개 있습니다** ({', '.join(entities)})\n"
                context += "→ 사용자가 특정 결과를 지정하지 않으면 needs_result_clarification=true 권장\n"
            else:
                context += f"\n📌 동일 엔티티({list(entities)[0]}) 결과가 {len(result_messages)}개 있습니다 (조건이 다름).\n"
                context += "→ 참조 표현 없이 집계/필터 요청 시 needs_result_clarification=true 고려\n"
        context += "\n"

    # ============================================
    # 대화 히스토리 (기존 유지)
    # ============================================
    context += "### 대화 히스토리\n"
    for msg in history[-5:]:
        if msg.role == 'user':
            context += f"사용자: {msg.content}\n"
        else:
            # queryPlan 요약 포함
            if msg.queryPlan:
                plan_summary = summarize_query_plan(msg.queryPlan)
                context += f"어시스턴트: [쿼리: {plan_summary}]\n"
            else:
                context += f"어시스턴트: [결과 표시됨]\n"

            # 집계 결과값 포함 (중요: 후속 계산용)
            if msg.renderSpec and msg.renderSpec.get("type") == "text":
                text_content = msg.renderSpec.get("text", {}).get("content", "")
                if text_content and ("합계" in text_content or "$" in text_content or "원" in text_content):
                    context += f"  → 집계 결과: {text_content}\n"

    # ============================================
    # 후속 질문 처리 규칙 (개선)
    # ============================================
    context += "\n### 후속 질문 처리 규칙\n"
    context += "1. '이중에', '여기서', '직전', '방금' 등 참조 표현 → **직전 결과 사용**, needs_result_clarification=false\n"
    context += "2. 참조 표현 없이 집계/필터 요청 + 다중 결과 → needs_result_clarification=true 고려\n"
    context += "3. 후속 질문에서는 **이전 엔티티 유지** (다른 엔티티로 변경 금지)\n"
    context += "4. 이전 집계 결과에 대한 산술 연산 → query_intent=direct_answer\n"
    return context


def get_previous_query_plan(history: List["ChatMessageItem"]) -> Optional[Dict[str, Any]]:
    """이전 대화에서 마지막 queryPlan 추출"""
    if not history:
        return None

    # 역순으로 탐색하여 가장 최근 assistant의 queryPlan 찾기
    for msg in reversed(history):
        if msg.role == 'assistant' and msg.queryPlan:
            return msg.queryPlan
    return None


def extract_previous_results(history: List["ChatMessageItem"]) -> List[Dict[str, Any]]:
    """이전 대화에서 조회/집계 결과 요약 추출 (Intent Classification용)

    실제 데이터 값도 추출하여 LLM이 계산할 수 있도록 함
    """
    results = []
    if not history:
        return results

    for i, msg in enumerate(history):
        if msg.role == "assistant":
            result_info = {
                "index": i,
                "entity": None,
                "count": 0,
                "aggregation": None,
                "data_summary": None,  # 실제 데이터 요약
                "total_amount": None   # 금액 합계 (있는 경우)
            }

            # QueryResult가 있으면 조회 결과
            if msg.queryResult:
                logger.info(f"[extract_previous_results] msg #{i} has queryResult with keys: {list(msg.queryResult.keys())}")
                result_info["count"] = msg.queryResult.get("totalCount", 0)
                if msg.queryPlan:
                    result_info["entity"] = msg.queryPlan.get("entity", "unknown")

                # 실제 데이터에서 금액 합계 추출
                data_obj = msg.queryResult.get("data", {})
                # data is an object with 'rows' property according to query-result.schema.json
                rows = data_obj.get("rows", []) if isinstance(data_obj, dict) else []
                logger.info(f"[extract_previous_results] msg #{i} rows length: {len(rows) if rows else 0}")

                if rows:
                    # amount 필드가 있으면 합계 계산
                    amounts = []
                    for row_idx, row in enumerate(rows):
                        if isinstance(row, dict):
                            logger.info(f"[extract_previous_results] msg #{i} row #{row_idx} keys: {list(row.keys())}")
                            # amount, totalAmount, 금액 등 다양한 필드명 체크
                            for field in ["amount", "totalAmount", "total_amount", "price", "금액"]:
                                if field in row and row[field] is not None:
                                    try:
                                        amounts.append(float(row[field]))
                                        logger.info(f"[extract_previous_results] msg #{i} row #{row_idx} found {field}={row[field]}")
                                    except (ValueError, TypeError) as e:
                                        logger.info(f"[extract_previous_results] msg #{i} row #{row_idx} error converting {field}: {e}")
                                        pass
                                    break
                        else:
                            logger.info(f"[extract_previous_results] msg #{i} row #{row_idx} is not a dict: {type(row)}")

                    if amounts:
                        result_info["total_amount"] = sum(amounts)
                        result_info["data_summary"] = f"금액 합계: ${result_info['total_amount']:,.0f} ({len(amounts)}건)"
                        logger.info(f"[extract_previous_results] msg #{i} extracted total_amount: ${result_info['total_amount']:,.0f} from {len(amounts)} amounts")
                    else:
                        logger.info(f"[extract_previous_results] msg #{i} no amounts found in {len(rows)} rows")

            # RenderSpec이 text 타입이면 집계 결과일 수 있음
            if msg.renderSpec and msg.renderSpec.get("type") == "text":
                text_content = msg.renderSpec.get("text", {}).get("content", "")
                if text_content:
                    result_info["aggregation"] = text_content

                    # 텍스트에서 금액 추출 (우선순위: 괄호 안 전체 금액 > 축약 금액)
                    if result_info["total_amount"] is None:
                        # 1순위: 괄호 안의 전체 금액 (예: "$2.88M ($2,878,000)" → 2878000)
                        full_amount_match = re.search(r'\(\$?([\d,]+)\)', text_content)
                        if full_amount_match:
                            try:
                                result_info["total_amount"] = float(full_amount_match.group(1).replace(',', ''))
                                logger.info(f"[extract_previous_results] Extracted full amount from parens: ${result_info['total_amount']:,.0f}")
                            except ValueError:
                                pass

                        # 2순위: M/K 접미사 처리 (예: "$2.88M" → 2880000)
                        if result_info["total_amount"] is None:
                            abbrev_match = re.search(r'\$?([\d,]+(?:\.\d+)?)\s*([MK])', text_content)
                            if abbrev_match:
                                try:
                                    value = float(abbrev_match.group(1).replace(',', ''))
                                    suffix = abbrev_match.group(2)
                                    if suffix == 'M':
                                        value *= 1_000_000
                                    elif suffix == 'K':
                                        value *= 1_000
                                    result_info["total_amount"] = value
                                    logger.info(f"[extract_previous_results] Extracted abbreviated amount: ${result_info['total_amount']:,.0f}")
                                except ValueError:
                                    pass

                        # 3순위: 일반 금액 (예: "$1,234,567")
                        if result_info["total_amount"] is None:
                            simple_match = re.search(r'\$?([\d,]+(?:\.\d+)?)', text_content)
                            if simple_match:
                                try:
                                    result_info["total_amount"] = float(simple_match.group(1).replace(',', ''))
                                    logger.info(f"[extract_previous_results] Extracted simple amount: ${result_info['total_amount']:,.0f}")
                                except ValueError:
                                    pass

            # 조회 결과나 집계 결과가 있으면 추가
            if result_info["count"] > 0 or result_info["aggregation"]:
                results.append(result_info)
                logger.info(f"[extract_previous_results] Added result #{len(results)}: entity={result_info['entity']}, count={result_info['count']}, total_amount={result_info['total_amount']}")

    logger.info(f"[extract_previous_results] Total results extracted: {len(results)}")
    return results


def merge_filters(previous_plan: Dict[str, Any], new_plan: Dict[str, Any]) -> Dict[str, Any]:
    """이전 필터와 새 필터를 병합"""
    if not previous_plan:
        return new_plan

    # clarification 요청이면 병합하지 않음
    if new_plan.get("needs_clarification"):
        return new_plan

    # 이전 필터 가져오기
    prev_filters = previous_plan.get("filters", [])
    new_filters = new_plan.get("filters", [])

    # 새 필터의 필드명 목록
    new_filter_fields = {f.get("field") for f in new_filters}

    # 이전 필터 중 새 필터에 없는 것만 병합 (중복 필드 방지)
    merged_filters = list(new_filters)  # 새 필터 우선
    for prev_filter in prev_filters:
        if prev_filter.get("field") not in new_filter_fields:
            merged_filters.append(prev_filter)

    # 병합된 결과
    merged_plan = dict(new_plan)
    if merged_filters:
        merged_plan["filters"] = merged_filters

    # 이전 entity 유지 (새 plan에 entity가 없으면)
    if not merged_plan.get("entity") and previous_plan.get("entity"):
        merged_plan["entity"] = previous_plan["entity"]

    # 이전 limit 유지 (새 plan이 기본값 10이면)
    if merged_plan.get("limit") == 10 and previous_plan.get("limit"):
        merged_plan["limit"] = previous_plan["limit"]

    return merged_plan

from app.services.query_planner import get_query_planner, IntentType
from app.services.render_composer import get_render_composer
from app.services.rag_service import get_rag_service

# Text-to-SQL 모드용 import (조건부)
if ENABLE_TEXT_TO_SQL:
    from app.services.text_to_sql import get_text_to_sql_service

logger = logging.getLogger(__name__)
logger.info(f"Text-to-SQL mode: {'ENABLED' if ENABLE_TEXT_TO_SQL else 'DISABLED'}")

router = APIRouter()

# Configuration
CORE_API_URL = os.getenv("CORE_API_URL", "http://localhost:8080")
ENABLE_QUERY_PLAN_VALIDATION = os.getenv("ENABLE_QUERY_PLAN_VALIDATION", "true").lower() == "true"


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


@router.post("/chat", response_model=ChatResponse, response_model_by_alias=True)
async def chat(request: ChatRequest):
    """
    Step 6: LangChain 기반 자연어 처리

    Flow (기존 QueryPlan 모드):
    1. 사용자 메시지 수신
    2. QueryPlannerService로 자연어 → QueryPlan 변환
    3. Core API 호출
    4. RenderComposerService로 QueryResult → RenderSpec 변환
    5. RenderSpec 반환

    Flow (Text-to-SQL 모드, SQL_ENABLE_TEXT_TO_SQL=true):
    1. 사용자 메시지 수신
    2. TextToSqlService로 자연어 → SQL 변환
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
    # Text-to-SQL 모드 분기
    # ========================================
    if ENABLE_TEXT_TO_SQL:
        return await handle_text_to_sql(request, request_id, start_time)

    try:
        # Stage 0: Intent Classification (2단계 분류)
        stage_start = datetime.utcnow()
        query_planner = get_query_planner()

        # 대화 컨텍스트 빌드
        conversation_context = None
        previous_results = []
        if request.conversation_history:
            conversation_context = build_conversation_context(request.conversation_history)
            previous_results = extract_previous_results(request.conversation_history)
            logger.info(f"[{request_id}] Using conversation context with {len(request.conversation_history)} messages")
            logger.info(f"[{request_id}] Found {len(previous_results)} previous results for intent classification")

        # 1단계: Intent 분류 (가벼운 모델로 빠르게)
        intent_result = await query_planner.classify_intent(
            request.message,
            conversation_context or "",
            previous_results
        )
        logger.info(f"[{request_id}] Intent classification: {intent_result.intent.value}, confidence={intent_result.confidence:.2f}")

        # direct_answer면 바로 응답 반환 (QueryPlan 생성 스킵)
        if intent_result.intent == IntentType.DIRECT_ANSWER and intent_result.direct_answer_text:
            logger.info(f"[{request_id}] Direct answer detected, skipping QueryPlan generation")
            logger.info(f"[{request_id}] Direct answer text: {intent_result.direct_answer_text}")

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

        processing_info["stages"].append({
            "name": "Intent Classification",
            "duration": (datetime.utcnow() - stage_start).total_seconds() * 1000,
            "result": intent_result.intent.value
        })

        # Stage 1: Natural Language → QueryPlan
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
            logger.info(f"[{request_id}] Intent: filter_local, client-side filtering")

            # entity가 없으면 이전 queryPlan에서 상속
            if not query_plan.get("entity") and request.conversation_history:
                previous_plan = get_previous_query_plan(request.conversation_history)
                if previous_plan and previous_plan.get("entity"):
                    query_plan["entity"] = previous_plan["entity"]
                    logger.info(f"[{request_id}] Inherited entity from previous plan: {query_plan['entity']}")

            # 이전 결과가 있는 메시지들 찾기
            result_messages = []
            if request.conversation_history:
                logger.info(f"[{request_id}] Checking {len(request.conversation_history)} messages in history")
                for i, msg in enumerate(request.conversation_history):
                    has_query_result = msg.queryResult is not None
                    logger.info(f"[{request_id}] Message {i}: role={msg.role}, hasQueryResult={has_query_result}")
                    if msg.role == "assistant" and msg.queryResult:
                        result_messages.append((i, msg))

            logger.info(f"[{request_id}] Found {len(result_messages)} result messages")

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
                    # 결과 요약 라벨 생성
                    entity = msg.queryPlan.get("entity", "데이터") if msg.queryPlan else "데이터"
                    count = "?"
                    if msg.queryResult:
                        if isinstance(msg.queryResult, dict):
                            count = msg.queryResult.get("totalCount", msg.queryResult.get("metadata", {}).get("rowsReturned", "?"))
                        elif hasattr(msg.queryResult, "totalCount"):
                            count = msg.queryResult.totalCount
                    time_str = msg.timestamp[-8:-3] if msg.timestamp and len(msg.timestamp) >= 8 else ""

                    label = f"직전: {entity} {count}건 ({time_str})" if idx == 0 else f"{entity} {count}건 ({time_str})"
                    options.append(label)
                    indices.append(msg_idx)

                logger.info(f"[{request_id}] Multiple results found, requesting clarification")

                clarification_render_spec = {
                    "type": "clarification",
                    "clarification": {
                        "question": "어떤 조회 결과를 필터링할까요?",
                        "options": options
                    },
                    "metadata": {
                        "requestId": request_id,
                        "targetResultIndices": indices,
                        "pendingFilters": query_plan.get("filters", []),
                        "generatedAt": datetime.utcnow().isoformat() + "Z"
                    }
                }

                return ChatResponse(
                    request_id=request_id,
                    render_spec=clarification_render_spec,
                    query_result=None,
                    query_plan={**query_plan, "needs_clarification": True, "requestId": request_id},
                    ai_message="어떤 조회 결과를 필터링할까요?",
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )

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
        elif query_intent == "aggregate_local":
            # 클라이언트 사이드 집계: 이전 결과에서 집계
            logger.info(f"[{request_id}] Intent: aggregate_local, client-side aggregation")

            # entity가 없으면 이전 queryPlan에서 상속
            if not query_plan.get("entity") and request.conversation_history:
                previous_plan = get_previous_query_plan(request.conversation_history)
                if previous_plan and previous_plan.get("entity"):
                    query_plan["entity"] = previous_plan["entity"]
                    logger.info(f"[{request_id}] Inherited entity from previous plan: {query_plan['entity']}")

            # 이전 결과가 있는 메시지들 찾기
            result_messages = []
            if request.conversation_history:
                logger.info(f"[{request_id}] Checking {len(request.conversation_history)} messages in history")
                for i, msg in enumerate(request.conversation_history):
                    has_query_result = msg.queryResult is not None
                    if msg.role == "assistant" and msg.queryResult:
                        result_messages.append((i, msg))

            logger.info(f"[{request_id}] Found {len(result_messages)} result messages for aggregation")

            # 집계 정보 추출
            aggregations = query_plan.get("aggregations", [])
            if not aggregations:
                # 기본 집계: sum(amount)
                aggregations = [{"function": "sum", "field": "amount", "alias": "totalAmount", "displayLabel": "결제 금액 합계", "currency": "USD"}]

            # 1단계: LLM이 모호하다고 판단했는지 확인
            needs_result_clarification = query_plan.get("needs_result_clarification", False)
            logger.info(f"[{request_id}] 1st stage LLM decision (aggregate): needs_result_clarification={needs_result_clarification}")

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
                logger.info(f"[{request_id}] 2nd stage LLM decision (aggregate): needs_result_clarification={needs_result_clarification}")

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

                logger.info(f"[{request_id}] Multiple results found, requesting clarification for aggregation")

                clarification_render_spec = {
                    "type": "clarification",
                    "clarification": {
                        "question": "어떤 데이터를 기준으로 집계할까요?",
                        "options": options
                    },
                    "metadata": {
                        "requestId": request_id,
                        "targetResultIndices": indices,
                        "pendingAggregations": aggregations,
                        "aggregationType": "aggregate_local",
                        "generatedAt": datetime.utcnow().isoformat() + "Z"
                    }
                }

                return ChatResponse(
                    request_id=request_id,
                    render_spec=clarification_render_spec,
                    query_result=None,
                    query_plan={**query_plan, "needs_clarification": True, "requestId": request_id},
                    ai_message="어떤 데이터를 기준으로 집계할까요?",
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )

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
        elif query_intent == "direct_answer":
            # LLM이 직접 답변: DB 조회 없이 텍스트 응답
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
            request_id=request_id,
            render_spec=render_spec,
            query_result=query_result,
            query_plan=query_plan,  # 후속 질문에서 이전 쿼리 조건 참조용
            ai_message=f"'{request.message}'에 대한 결과입니다.",
            timestamp=datetime.utcnow().isoformat() + "Z"
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

        # 에러 시 빈 QueryResult 반환
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
                "message": str(e)
            }
        }

        # 에러 시 빈 QueryPlan 반환
        error_query_plan = {
            "entity": "",
            "operation": "list"
        }

        return ChatResponse(
            request_id=request_id,
            render_spec=error_render_spec,
            query_result=error_query_result,
            query_plan=error_query_plan,
            ai_message=f"요청 처리 중 오류가 발생했습니다: {str(e)}",
            timestamp=datetime.utcnow().isoformat() + "Z"
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

class DownloadRequest(BaseModel):
    """다운로드 요청"""
    sql: str
    format: str = "csv"  # csv 또는 excel


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
    from app.services.text_to_sql import get_text_to_sql_service

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

    def generate_csv() -> Generator[str, None, None]:
        """CSV 스트리밍 생성기"""
        import psycopg
        from psycopg.rows import dict_row

        try:
            with text_to_sql._get_readonly_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(unlimited_sql)

                    # 헤더 출력
                    columns = [desc[0] for desc in cur.description]
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow(columns)
                    yield output.getvalue()

                    # 데이터 배치 처리 (1000건씩)
                    batch_size = 1000
                    row_count = 0
                    while True:
                        rows = cur.fetchmany(batch_size)
                        if not rows:
                            break

                        output = io.StringIO()
                        writer = csv.writer(output)
                        for row in rows:
                            # datetime 변환
                            processed_row = []
                            for value in row.values() if hasattr(row, 'values') else row:
                                if hasattr(value, 'isoformat'):
                                    processed_row.append(value.isoformat())
                                else:
                                    processed_row.append(value)
                            writer.writerow(processed_row)
                            row_count += 1

                        yield output.getvalue()

                    logger.info(f"Download completed: {row_count} rows")

        except psycopg.Error as e:
            logger.error(f"Download SQL execution failed: {e}")
            yield f"Error: {str(e)}"

    # 파일명 생성
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"query_result_{timestamp}.csv"

    return StreamingResponse(
        generate_csv(),
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
    """
    logger.info(f"[{request_id}] Text-to-SQL mode: processing")

    try:
        text_to_sql = get_text_to_sql_service()

        # 대화 이력 변환 (Text-to-SQL 형식)
        sql_history = build_sql_history(request.conversation_history)

        # SQL 생성 및 실행
        result = await text_to_sql.query(
            question=request.message,
            conversation_history=sql_history,
            retry_on_error=True
        )

        # 실행 시간 계산
        total_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        if result["success"]:
            # 성공: 데이터를 RenderSpec으로 변환
            render_spec = compose_sql_render_spec(result, request.message)
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
                }
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


def build_sql_history(conversation_history: Optional[List[ChatMessageItem]]) -> List[Dict[str, str]]:
    """대화 이력을 Text-to-SQL 형식으로 변환"""
    if not conversation_history:
        return []

    sql_history = []
    for msg in conversation_history[-10:]:  # 최근 10개만
        entry = {
            "role": msg.role,
            "content": msg.content
        }
        # assistant 메시지에 SQL 정보가 있으면 포함
        if msg.role == "assistant" and msg.queryPlan:
            if msg.queryPlan.get("mode") == "text_to_sql" and msg.queryPlan.get("sql"):
                entry["sql"] = msg.queryPlan.get("sql")
        sql_history.append(entry)

    return sql_history


def compose_sql_render_spec(result: Dict[str, Any], question: str) -> Dict[str, Any]:
    """SQL 실행 결과를 RenderSpec으로 변환

    - 1000건 초과: 다운로드 RenderSpec (테이블 표시 안함)
    - 1000건 이하: 미리보기 10건 + 전체보기 모달
    """
    data = result.get("data", [])
    row_count = result.get("rowCount", 0)
    total_count = result.get("totalCount") or row_count
    is_truncated = result.get("isTruncated", False)
    PREVIEW_LIMIT = 10  # 미리보기 행 수
    MAX_DISPLAY_ROWS = 1000  # 화면 표시 최대 건수

    # 1000건 초과: 다운로드 RenderSpec 반환
    if is_truncated:
        return {
            "type": "download",
            "title": "대용량 데이터 조회",
            "download": {
                "totalRows": total_count,
                "maxDisplayRows": MAX_DISPLAY_ROWS,
                "message": f"조회 결과가 {total_count:,}건으로 화면 표시 제한({MAX_DISPLAY_ROWS:,}건)을 초과합니다.",
                "sql": result.get("sql"),
                "formats": ["csv"]
            },
            "metadata": {
                "sql": result.get("sql"),
                "executionTimeMs": result.get("executionTimeMs"),
                "mode": "text_to_sql"
            }
        }

    if not data:
        return {
            "type": "text",
            "title": "조회 결과",
            "text": {
                "content": "조회 결과가 없습니다.",
                "format": "plain"
            },
            "metadata": {
                "sql": result.get("sql"),
                "executionTimeMs": result.get("executionTimeMs")
            }
        }

    # 단일 행 + 집계 결과처럼 보이면 텍스트로 표시
    if row_count == 1 and len(data[0]) <= 3:
        row = data[0]
        # 키-값 쌍으로 표시
        content_parts = []
        for key, value in row.items():
            # 금액 포맷팅
            if isinstance(value, (int, float)) and any(kw in key.lower() for kw in ["amount", "sum", "total", "count", "avg"]):
                if value >= 1000000:
                    formatted = f"₩{value:,.0f} ({value/1000000:.2f}M)"
                elif value >= 1000:
                    formatted = f"₩{value:,.0f}"
                else:
                    formatted = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
                content_parts.append(f"**{key}**: {formatted}")
            else:
                content_parts.append(f"**{key}**: {value}")

        return {
            "type": "text",
            "title": "집계 결과",
            "text": {
                "content": "\n".join(content_parts),
                "format": "markdown"
            },
            "metadata": {
                "sql": result.get("sql"),
                "executionTimeMs": result.get("executionTimeMs"),
                "mode": "text_to_sql"
            }
        }

    # 다중 행: 테이블로 표시 (미리보기 모드)
    if data:
        columns = list(data[0].keys())
        column_defs = []
        for col in columns:
            col_def = {
                "key": col,  # UI TableRenderer 호환
                "label": col.replace("_", " ").title(),  # TableRenderer expects 'label'
                "field": col,
                "headerName": col.replace("_", " ").title()
            }
            # 금액 필드 감지
            if any(kw in col.lower() for kw in ["amount", "fee", "net", "total", "price"]):
                col_def["type"] = "currency"
                col_def["currencyCode"] = "KRW"
            # 날짜 필드 감지
            elif any(kw in col.lower() for kw in ["date", "time", "at", "created", "updated"]):
                col_def["type"] = "datetime"
            column_defs.append(col_def)

        # 미리보기용 데이터 (최대 PREVIEW_LIMIT건)
        preview_data = data[:PREVIEW_LIMIT]
        has_more = row_count > PREVIEW_LIMIT

        # 타이틀: 미리보기인 경우 표시
        if has_more:
            title = f"조회 결과 ({row_count}건 중 {PREVIEW_LIMIT}건 미리보기)"
        else:
            title = f"조회 결과 ({row_count}건)"

        return {
            "type": "table",
            "title": title,
            "table": {
                "columns": column_defs,
                "data": preview_data,  # 미리보기만 전송
                "dataRef": "data.rows",
                "actions": [
                    {"action": "fullscreen", "label": "전체보기"},
                    {"action": "export-csv", "label": "CSV 다운로드"}
                ],
                "pagination": {
                    "enabled": False,  # 미리보기에서는 페이지네이션 비활성화
                    "pageSize": PREVIEW_LIMIT,
                    "totalRows": row_count
                }
            },
            # 전체 데이터는 별도로 저장 (모달에서 사용)
            "fullData": data if has_more else None,
            "preview": {
                "enabled": has_more,
                "previewRows": PREVIEW_LIMIT,
                "totalRows": row_count,
                "message": f"전체 {row_count}건 중 {PREVIEW_LIMIT}건만 표시됩니다. 전체보기 버튼을 클릭하세요."
            },
            "metadata": {
                "sql": result.get("sql"),
                "executionTimeMs": result.get("executionTimeMs"),
                "mode": "text_to_sql"
            }
        }

    return {
        "type": "text",
        "title": "결과",
        "text": {
            "content": f"조회 완료: {row_count}건",
            "format": "plain"
        }
    }
