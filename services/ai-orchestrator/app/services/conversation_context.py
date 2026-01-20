"""
ConversationContextService: 대화 컨텍스트 관리

연속 대화에서 이전 결과 참조, 필터 병합, 컨텍스트 빌드 등을 담당
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING

from app.constants.reference_patterns import (
    ReferenceType,
    REFERENCE_PATTERNS,
    NEW_QUERY_PATTERNS,
    AGGREGATION_KEYWORDS,
)

if TYPE_CHECKING:
    from app.api.v1.chat import ChatMessageItem

logger = logging.getLogger(__name__)


# ============================================
# 유틸리티 함수
# ============================================

def to_camel(string: str) -> str:
    """snake_case를 camelCase로 변환"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


# ============================================
# 참조 표현 감지
# ============================================

def detect_reference_expression(message: str) -> Tuple[bool, str]:
    """
    사용자 메시지에서 참조 표현 감지

    참조 표현이 있으면 이전 WHERE 조건을 유지해야 함을 의미

    Args:
        message: 사용자 메시지

    Returns:
        (is_refinement, ref_type) 튜플
        - is_refinement: True면 이전 조건 유지 필요
        - ref_type: 'filter' (필터 추가), 'aggregation' (집계 요청), 'new' (새 쿼리), 'none' (해당없음)
    """
    # 새 쿼리 패턴 먼저 체크 (우선순위 높음)
    for pattern in NEW_QUERY_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            return (False, 'new')

    # 참조 패턴 체크 (유형별)
    for ref_type, patterns in REFERENCE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return (True, 'filter')

    # 집계 키워드 체크 (이전 결과에 대한 집계로 처리)
    # 집계 요청은 이전 대화에서 조회한 결과에 대해 수행하는 것으로 간주
    for pattern in AGGREGATION_KEYWORDS:
        if re.search(pattern, message, re.IGNORECASE):
            return (True, 'aggregation')

    return (False, 'none')


def detect_reference_type(message: str) -> ReferenceType:
    """
    참조 표현의 세부 유형 감지

    Args:
        message: 사용자 메시지

    Returns:
        ReferenceType: 참조 유형 (LATEST, SPECIFIC, PARTIAL, NONE)
    """
    # 우선순위: SPECIFIC > PARTIAL > LATEST
    for ref_type in [ReferenceType.SPECIFIC, ReferenceType.PARTIAL, ReferenceType.LATEST]:
        if ref_type in REFERENCE_PATTERNS:
            for pattern in REFERENCE_PATTERNS[ref_type]:
                if re.search(pattern, message, re.IGNORECASE):
                    return ref_type

    return ReferenceType.NONE


# ============================================
# QueryPlan 관련
# ============================================

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


def get_previous_query_plan(history: List["ChatMessageItem"]) -> Optional[Dict[str, Any]]:
    """이전 대화에서 마지막 queryPlan 추출"""
    if not history:
        return None

    # 역순으로 탐색하여 가장 최근 assistant의 queryPlan 찾기
    for msg in reversed(history):
        if msg.role == 'assistant' and msg.queryPlan:
            return msg.queryPlan
    return None


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


# ============================================
# 대화 컨텍스트 빌드
# ============================================

def build_conversation_context(history: List["ChatMessageItem"]) -> str:
    """이전 대화를 프롬프트용 텍스트로 변환 (구조화된 결과 현황 포함)"""
    if not history:
        return ""

    context = "## 이전 대화 컨텍스트\n\n"

    # ============================================
    # 조회 결과 현황 (구조화된 테이블 형식)
    # ============================================
    result_messages = []
    for i, msg in enumerate(history):
        if msg.role == "assistant" and msg.queryResult:
            entity = msg.queryPlan.get("entity", "unknown") if msg.queryPlan else "unknown"
            count = msg.queryResult.get("totalCount", 0)

            # 필터 정보 추출
            filters = msg.queryPlan.get("filters", []) if msg.queryPlan else []
            filter_desc = "-"
            if filters:
                filter_strs = [f"{f.get('field')}={f.get('value')}" for f in filters[:2]]
                filter_desc = ", ".join(filter_strs)

            # 금액 정보 추출
            total_amount = None
            data_obj = msg.queryResult.get("data", {})
            rows = data_obj.get("rows", []) if isinstance(data_obj, dict) else []
            if rows:
                amounts = []
                for row in rows:
                    if isinstance(row, dict):
                        for field in ["amount", "totalAmount", "total_amount", "price"]:
                            if field in row and row[field] is not None:
                                try:
                                    amounts.append(float(row[field]))
                                except (ValueError, TypeError):
                                    pass
                                break
                if amounts:
                    total_amount = sum(amounts)

            # 결과 타입 판단 (테이블 vs 집계)
            result_type = "table"  # 기본값
            if msg.renderSpec and msg.renderSpec.get("type") == "text":
                result_type = "aggregation"

            # 관계 정보 추정
            relation = "최초 조회"
            if len(result_messages) > 0:
                prev = result_messages[-1]
                if prev["entity"] == entity and filters:
                    relation = f"#{prev['index']}에서 필터링"
                elif prev["entity"] != entity:
                    relation = "새로운 엔티티"
                else:
                    relation = "조건 변경"

            result_messages.append({
                "index": i,
                "entity": entity,
                "count": count,
                "filter_desc": filter_desc,
                "total_amount": total_amount,
                "result_type": result_type,
                "relation": relation,
                "is_latest": False
            })

    if result_messages:
        result_messages[-1]["is_latest"] = True  # 마지막이 직전 결과

        # 구조화된 테이블 형식
        context += "### 조회 결과 현황\n"
        context += "| # | 엔티티 | 건수 | 조건 | 금액 | 타입 | 관계 |\n"
        context += "|---|--------|------|------|------|------|------|\n"

        for r in result_messages:
            marker = ">" if r["is_latest"] else ""
            amount_str = f"${r['total_amount']:,.0f}" if r['total_amount'] else "-"
            context += f"| {marker}{r['index']} | {r['entity']} | {r['count']} | {r['filter_desc']} | {amount_str} | {r['result_type']} | {r['relation']} |\n"

        context += "\n"

        # ============================================
        # 결과 관계 분석 (LLM이 이해하기 쉽게)
        # ============================================
        context += "### 결과 관계 분석\n"
        entities = {}
        for r in result_messages:
            if r["entity"] not in entities:
                entities[r["entity"]] = []
            entities[r["entity"]].append(r)

        for entity, results in entities.items():
            if len(results) > 1:
                context += f"- **{entity}**: {len(results)}개 결과 (조건이 다름)\n"
                for r in results[1:]:
                    context += f"  - 결과 #{r['index']}은 #{result_messages[0]['index']}에서 파생됨\n"
            else:
                context += f"- **{entity}**: 1개 결과\n"

        context += "\n"

        # ============================================
        # 계산에 사용할 데이터 (명시적)
        # ============================================
        latest = result_messages[-1]
        context += "### 현재 작업 대상 (직전 결과)\n"
        context += f"- **엔티티**: {latest['entity']}\n"
        context += f"- **건수**: {latest['count']}건\n"
        context += f"- **타입**: {latest['result_type']} ({'목록 데이터' if latest['result_type'] == 'table' else '집계 결과'})\n"
        if latest['total_amount']:
            context += f"- **금액 합계**: ${latest['total_amount']:,.0f}\n"
        if latest['filter_desc'] != "-":
            context += f"- **적용된 필터**: {latest['filter_desc']}\n"

        context += "\n"

        # 다중 결과 경고
        if len(result_messages) > 1:
            entity_set = set(r["entity"] for r in result_messages)
            if len(entity_set) > 1:
                context += f"**주의**: 다른 종류의 결과가 {len(result_messages)}개 있습니다 ({', '.join(entity_set)})\n"
                context += "- 참조 표현 없으면 어떤 결과를 대상으로 하는지 불명확할 수 있음\n\n"

    # ============================================
    # 대화 히스토리 (최근 5개)
    # ============================================
    context += "### 대화 히스토리\n"
    for msg in history[-5:]:
        if msg.role == 'user':
            context += f"**사용자**: {msg.content}\n"
        else:
            # queryPlan 요약 포함
            if msg.queryPlan:
                plan_summary = summarize_query_plan(msg.queryPlan)
                context += f"**어시스턴트**: [쿼리: {plan_summary}]\n"
            else:
                context += f"**어시스턴트**: [결과 표시됨]\n"

            # 집계 결과값 포함 (중요: 후속 계산용)
            if msg.renderSpec and msg.renderSpec.get("type") == "text":
                text_content = msg.renderSpec.get("text", {}).get("content", "")
                if text_content and ("합계" in text_content or "$" in text_content or "원" in text_content):
                    context += f"  -> **집계 결과**: {text_content}\n"

    # ============================================
    # 후속 질문 처리 규칙 (강화)
    # ============================================
    context += "\n### 후속 질문 처리 규칙\n"
    context += "1. **참조 표현 있음** ('이중에', '여기서', '직전', '방금', '아까 그거') -> 직전 결과 사용\n"
    context += "2. **참조 표현 없음** + 다중 결과 -> 문맥상 명확하지 않으면 clarification 고려\n"
    context += "3. **직전 결과 타입 확인**:\n"
    context += "   - 테이블(목록) + '합산' -> aggregate_local\n"
    context += "   - 집계결과 + '수수료 적용' -> direct_answer\n"
    context += "   - 집계결과 + '필터링' -> query_needed (집계 결과는 필터 불가)\n"
    context += "4. **엔티티 유지**: 후속 질문에서 다른 엔티티로 변경하려면 명시적 표현 필요\n"

    return context


# ============================================
# 이전 결과 추출 (Intent Classification용)
# ============================================

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
                        # 1순위: 괄호 안의 전체 금액 (예: "$2.88M ($2,878,000)" -> 2878000)
                        full_amount_match = re.search(r'\(\$?([\d,]+)\)', text_content)
                        if full_amount_match:
                            try:
                                result_info["total_amount"] = float(full_amount_match.group(1).replace(',', ''))
                                logger.info(f"[extract_previous_results] Extracted full amount from parens: ${result_info['total_amount']:,.0f}")
                            except ValueError:
                                pass

                        # 2순위: M/K 접미사 처리 (예: "$2.88M" -> 2880000)
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
