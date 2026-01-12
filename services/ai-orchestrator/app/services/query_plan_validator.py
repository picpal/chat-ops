"""
QueryPlanValidatorService: QueryPlan 품질 검증
2단계 LLM 검증 시스템의 Validator 역할
규칙 기반 사전 검증 + LLM 의미적 검증
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from app.models.validation import (
    ValidationIssueType,
    IssueSeverity,
    ValidationIssue,
    LLMValidationScore,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class QueryPlanValidatorService:
    """
    QueryPlan 품질 검증 서비스

    역할:
    1. 사용자 질문과 QueryPlan 일치 여부 검증
    2. 엔티티 선택 적절성 평가
    3. 필터 조건 누락/오류 검출
    4. quality_score 산출
    5. 자동 수정 가능한 minor 이슈 교정
    """

    # 도메인 용어 -> 엔티티 매핑 (명확한 매핑)
    DOMAIN_TERM_ENTITY_MAP = {
        "거래": "Payment",
        "결제": "Payment",
        "트랜잭션": "Payment",
        "내역": "Payment",
        "이력": "Payment",
        "transaction": "Payment",
        "payment": "Payment",
        "환불": "Refund",
        "취소환불": "Refund",
        "반품": "Refund",
        "refund": "Refund",
        "가맹점": "Merchant",
        "상점": "Merchant",
        "업체": "Merchant",
        "merchant": "Merchant",
        "정산": "Settlement",
        "settlement": "Settlement",
        "고객": "PgCustomer",
        "customer": "PgCustomer",
    }

    # 시계열 데이터 엔티티 (timeRange 권장)
    TIME_SERIES_ENTITIES = {"Payment", "PaymentHistory", "BalanceTransaction"}

    # 유효한 엔티티 목록
    VALID_ENTITIES = {
        "Order", "Merchant", "PgCustomer", "PaymentMethod",
        "Payment", "PaymentHistory", "Refund",
        "BalanceTransaction", "Settlement", "SettlementDetail"
    }

    # 유효한 연산자 목록
    VALID_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "like", "between"}

    # 엔티티별 유효 필드
    ENTITY_VALID_FIELDS = {
        "Payment": {
            "paymentKey", "orderId", "merchantId", "customerId", "orderName",
            "amount", "method", "status", "approvedAt", "failureCode",
            "failureMessage", "createdAt"
        },
        "Refund": {
            "refundKey", "paymentKey", "amount", "taxFreeAmount", "reason",
            "status", "approvedAt", "createdAt"
        },
        "Merchant": {
            "merchantId", "businessName", "businessNumber", "representativeName",
            "email", "phone", "status", "feeRate", "settlementCycle", "createdAt"
        },
        "Settlement": {
            "settlementId", "merchantId", "settlementDate", "periodStart",
            "periodEnd", "totalPaymentAmount", "totalRefundAmount", "totalFee",
            "netAmount", "paymentCount", "refundCount", "status"
        },
        "Order": {
            "orderId", "customerId", "orderDate", "totalAmount", "status", "paymentGateway"
        },
        "PgCustomer": {
            "customerId", "merchantId", "email", "name", "phone", "createdAt"
        },
        "PaymentMethod": {
            "paymentMethodId", "customerId", "type", "cardCompany",
            "cardNumberMasked", "bankCode", "status", "isDefault", "createdAt"
        },
        "PaymentHistory": {
            "historyId", "paymentKey", "previousStatus", "newStatus",
            "reason", "processedBy", "createdAt"
        },
        "BalanceTransaction": {
            "transactionId", "merchantId", "sourceType", "sourceId",
            "amount", "fee", "net", "balanceBefore", "balanceAfter", "status", "createdAt"
        },
        "SettlementDetail": {
            "detailId", "settlementId", "paymentKey", "amount", "fee", "netAmount", "type"
        }
    }

    # 심각도별 점수 감점
    SEVERITY_PENALTIES = {
        IssueSeverity.CRITICAL: 0.3,
        IssueSeverity.WARNING: 0.1,
        IssueSeverity.INFO: 0.02
    }

    def __init__(self, api_key: Optional[str] = None):
        self._llm_provider = os.getenv("VALIDATOR_LLM_PROVIDER", "openai").lower()

        if self._llm_provider == "anthropic":
            self._llm_model = os.getenv("VALIDATOR_LLM_MODEL", "claude-3-haiku-20241022")
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        else:
            self._llm_model = os.getenv("VALIDATOR_LLM_MODEL", "gpt-4o-mini")
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        self._llm = None
        self._quality_threshold = float(os.getenv("VALIDATOR_QUALITY_THRESHOLD", "0.8"))
        self._use_llm_validation = os.getenv("VALIDATOR_USE_LLM", "true").lower() == "true"

        logger.info(f"QueryPlanValidator initialized: provider={self._llm_provider}, model={self._llm_model}, threshold={self._quality_threshold}")

    def _get_llm(self):
        """LLM 인스턴스 지연 초기화"""
        if self._llm is None:
            if not self.api_key:
                logger.warning("Validator LLM API key not set, skipping LLM validation")
                return None

            try:
                if self._llm_provider == "anthropic":
                    from langchain_anthropic import ChatAnthropic
                    self._llm = ChatAnthropic(
                        model=self._llm_model,
                        temperature=0,
                        api_key=self.api_key
                    )
                else:
                    from langchain_openai import ChatOpenAI
                    self._llm = ChatOpenAI(
                        model=self._llm_model,
                        temperature=0,
                        api_key=self.api_key
                    )
                logger.info(f"Validator LLM initialized: {self._llm_model}")
            except Exception as e:
                logger.error(f"Failed to initialize validator LLM: {e}")
                return None

        return self._llm

    async def validate(
        self,
        user_message: str,
        query_plan: Dict[str, Any],
        conversation_context: Optional[str] = None
    ) -> ValidationResult:
        """
        QueryPlan 품질 검증

        검증 순서:
        1. 규칙 기반 사전 검증 (빠름, LLM 비용 절감)
        2. LLM 기반 의미적 검증 (정확함) - 선택적
        3. 종합 점수 계산 및 결과 반환

        Args:
            user_message: 원본 사용자 메시지
            query_plan: 검증할 QueryPlan
            conversation_context: 대화 컨텍스트 (선택)

        Returns:
            ValidationResult: 검증 결과
        """
        start_time = datetime.now()
        issues: List[ValidationIssue] = []
        llm_scores: Optional[LLMValidationScore] = None

        logger.info(f"Validating QueryPlan for: {user_message[:50]}...")

        # 1. 규칙 기반 사전 검증
        rule_issues = self._apply_rule_based_validation(user_message, query_plan)
        issues.extend(rule_issues)
        logger.info(f"Rule-based validation found {len(rule_issues)} issues")

        # Critical 이슈가 없고 LLM 검증이 활성화되면 LLM 검증 수행
        has_critical = any(i.severity == IssueSeverity.CRITICAL for i in issues)

        if not has_critical and self._use_llm_validation and self.api_key:
            try:
                llm_result = await self._llm_validate(
                    user_message, query_plan, conversation_context
                )
                if llm_result:
                    llm_scores = llm_result.get("scores")
                    llm_issues = llm_result.get("issues", [])
                    issues.extend(llm_issues)
                    logger.info(f"LLM validation found {len(llm_issues)} additional issues")
            except Exception as e:
                logger.warning(f"LLM validation failed: {e}")

        # 2. 품질 점수 계산
        quality_score = self._calculate_quality_score(issues, query_plan, llm_scores)

        # 3. 자동 수정 시도 (품질이 낮을 때)
        corrected_plan = None
        if issues and quality_score < self._quality_threshold:
            corrected_plan = self._try_auto_correct(query_plan, issues, user_message)
            if corrected_plan:
                # 수정 후 재평가
                new_issues = self._apply_rule_based_validation(user_message, corrected_plan)
                new_quality_score = self._calculate_quality_score(new_issues, corrected_plan, None)
                logger.info(f"Auto-correction applied: {quality_score:.2f} -> {new_quality_score:.2f}")

                if new_quality_score >= self._quality_threshold:
                    quality_score = new_quality_score
                    issues = new_issues

        # 4. clarification 필요 여부 판단
        clarification_needed = False
        clarification_question = None
        clarification_options = None

        if quality_score < self._quality_threshold and corrected_plan is None:
            clarification_needed, clarification_question, clarification_options = \
                self._determine_clarification(user_message, issues, query_plan)

        validation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        result = ValidationResult(
            quality_score=quality_score,
            is_valid=quality_score >= self._quality_threshold,
            issues=issues,
            corrected_plan=corrected_plan,
            clarification_needed=clarification_needed,
            clarification_question=clarification_question,
            clarification_options=clarification_options,
            validation_time_ms=validation_time_ms,
            llm_scores=llm_scores
        )

        logger.info(f"Validation complete: score={quality_score:.2f}, valid={result.is_valid}, time={validation_time_ms}ms")
        return result

    def _apply_rule_based_validation(
        self,
        user_message: str,
        query_plan: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """
        규칙 기반 사전 검증
        LLM 호출 전 빠르게 명확한 오류 감지
        """
        issues = []
        message_lower = user_message.lower()
        entity = query_plan.get("entity")
        query_intent = query_plan.get("query_intent", "new_query")
        is_local_operation = query_intent in ("filter_local", "aggregate_local")

        # 0. filter_local/aggregate_local일 때는 entity 없어도 OK
        # 이전 결과를 참조하는 연산이므로 entity는 시스템이 자동 상속함

        # 1. 불필요한 clarification 검사 (최우선)
        if query_plan.get("needs_clarification"):
            has_domain_term = any(term in message_lower for term in self.DOMAIN_TERM_ENTITY_MAP)
            # filter_local/aggregate_local 트리거 단어 확인
            has_local_trigger = any(trigger in message_lower for trigger in [
                "이중", "이중에", "여기서", "그중", "그중에", "위 결과", "이전 결과", "방금 결과"
            ])
            if has_domain_term or has_local_trigger:
                issues.append(ValidationIssue(
                    type=ValidationIssueType.UNNECESSARY_CLARIFICATION,
                    severity=IssueSeverity.CRITICAL,
                    message="도메인 용어 또는 이전 결과 참조 표현이 있어 clarification이 불필요함",
                    suggestion="needs_clarification을 false로 설정하고 filter_local 또는 적절한 엔티티 선택"
                ))

        # 2. 엔티티 유효성 검사 (filter_local/aggregate_local일 때는 entity 없어도 OK)
        if entity and entity not in self.VALID_ENTITIES:
            if not is_local_operation:  # local operation이면 entity 검증 skip
                issues.append(ValidationIssue(
                    type=ValidationIssueType.INVALID_ENTITY,
                    severity=IssueSeverity.CRITICAL,
                    field="entity",
                    message=f"'{entity}'는 유효하지 않은 엔티티",
                    suggestion=f"유효한 엔티티: {', '.join(list(self.VALID_ENTITIES)[:5])}"
                ))

        # 3. 도메인 용어-엔티티 일치 검사 (filter_local/aggregate_local일 때는 skip)
        if not is_local_operation:
            for term, expected_entity in self.DOMAIN_TERM_ENTITY_MAP.items():
                if term in message_lower:
                    if entity and entity != expected_entity:
                        # 같은 카테고리인지 확인 (예: Payment/PaymentHistory)
                        if not self._is_related_entity(entity, expected_entity):
                            issues.append(ValidationIssue(
                                type=ValidationIssueType.ENTITY_MISMATCH,
                                severity=IssueSeverity.CRITICAL,
                                field="entity",
                                message=f"'{term}' 키워드는 {expected_entity} 엔티티를 의미하지만, {entity}가 선택됨",
                                suggestion=f"entity를 {expected_entity}로 변경"
                            ))
                    break  # 첫 번째 매칭된 용어만 검사

        # 4. 시계열 데이터 timeRange 검사
        if entity in self.TIME_SERIES_ENTITIES:
            has_time_range = query_plan.get("timeRange") is not None
            has_limit = query_plan.get("limit") is not None
            if not has_time_range and not has_limit:
                issues.append(ValidationIssue(
                    type=ValidationIssueType.MISSING_TIME_RANGE,
                    severity=IssueSeverity.WARNING,
                    field="timeRange",
                    message=f"{entity}는 시계열 데이터로, timeRange 또는 limit 지정 권장",
                    suggestion="최근 7일 기본 timeRange 추가"
                ))

        # 5. 필터 검증
        filters = query_plan.get("filters", []) or []
        valid_fields = self.ENTITY_VALID_FIELDS.get(entity, set())

        for idx, f in enumerate(filters):
            field = f.get("field")
            operator = f.get("operator", "").lower()

            # 연산자 유효성 검사
            if operator and operator not in self.VALID_OPERATORS:
                issues.append(ValidationIssue(
                    type=ValidationIssueType.INVALID_OPERATOR,
                    severity=IssueSeverity.CRITICAL,
                    field=f"filters[{idx}].operator",
                    message=f"연산자 '{operator}'는 유효하지 않음",
                    suggestion=f"유효한 연산자: {', '.join(self.VALID_OPERATORS)}"
                ))

            # 필드 유효성 검사
            if valid_fields and field and field not in valid_fields:
                issues.append(ValidationIssue(
                    type=ValidationIssueType.FIELD_NOT_EXIST,
                    severity=IssueSeverity.WARNING,
                    field=f"filters[{idx}].field",
                    message=f"필드 '{field}'는 {entity}에 존재하지 않을 수 있음",
                    suggestion=f"유효한 필드: {', '.join(list(valid_fields)[:5])}"
                ))

        # 6. limit 범위 검사
        limit = query_plan.get("limit")
        if limit is not None:
            if limit < 1 or limit > 100:
                issues.append(ValidationIssue(
                    type=ValidationIssueType.LIMIT_OUT_OF_RANGE,
                    severity=IssueSeverity.WARNING,
                    field="limit",
                    message=f"limit {limit}은 권장 범위(1~100)를 벗어남",
                    suggestion="limit을 1~100 사이로 설정"
                ))

        return issues

    def _is_related_entity(self, entity1: str, entity2: str) -> bool:
        """두 엔티티가 관련되어 있는지 확인"""
        related_groups = [
            {"Payment", "PaymentHistory"},
            {"Settlement", "SettlementDetail"},
        ]
        for group in related_groups:
            if entity1 in group and entity2 in group:
                return True
        return False

    async def _llm_validate(
        self,
        user_message: str,
        query_plan: Dict[str, Any],
        conversation_context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """LLM 기반 의미적 검증"""
        llm = self._get_llm()
        if not llm:
            return None

        try:
            prompt = self._build_validator_prompt(user_message, query_plan, conversation_context)

            from langchain_core.messages import SystemMessage, HumanMessage

            messages = [
                SystemMessage(content=self._get_validator_system_prompt()),
                HumanMessage(content=prompt)
            ]

            response = await llm.ainvoke(messages)

            # JSON 파싱
            content = response.content
            # JSON 블록 추출
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())

            # ValidationIssue 객체로 변환
            issues = []
            for issue_data in result.get("issues", []):
                try:
                    issues.append(ValidationIssue(
                        type=ValidationIssueType(issue_data.get("type", "ambiguous_intent")),
                        severity=IssueSeverity(issue_data.get("severity", "warning")),
                        field=issue_data.get("field"),
                        message=issue_data.get("message", ""),
                        suggestion=issue_data.get("suggestion")
                    ))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse LLM issue: {e}")

            # LLMValidationScore 생성
            scores = LLMValidationScore(
                entity_match_score=result.get("entity_match_score", 1.0),
                filter_completeness_score=result.get("filter_completeness_score", 1.0),
                time_range_score=result.get("time_range_score", 1.0),
                clarification_appropriateness_score=result.get("clarification_appropriateness_score", 1.0),
                overall_score=result.get("overall_score", 1.0),
                reasoning=result.get("reasoning")
            )

            return {"scores": scores, "issues": issues}

        except Exception as e:
            logger.error(f"LLM validation error: {e}")
            return None

    def _get_validator_system_prompt(self) -> str:
        """Validator 시스템 프롬프트"""
        return """당신은 PG 결제 백오피스 QueryPlan 품질 검증 전문가입니다.

## 역할
사용자 질문과 생성된 QueryPlan이 일치하는지 검증하고, 품질 점수를 매깁니다.

## 검증 항목

### 1. 엔티티 선택 적절성 (entity_match_score)
- 도메인 용어 매핑:
  - "거래", "결제", "트랜잭션", "내역" → Payment
  - "환불", "취소환불" → Refund
  - "가맹점", "상점" → Merchant
  - "정산" → Settlement

### 2. 필터 조건 완성도 (filter_completeness_score)
- 사용자가 언급한 조건이 모두 filters에 반영되었는가?

### 3. 시간 범위 적절성 (time_range_score)
- Payment, PaymentHistory, BalanceTransaction은 timeRange 권장

### 4. clarification 적절성 (clarification_appropriateness_score)
- 도메인 용어가 명확하면 clarification 불필요!
- "거래 30건" → clarification 불필요

## 출력 형식 (JSON)
```json
{
  "entity_match_score": 0.0~1.0,
  "filter_completeness_score": 0.0~1.0,
  "time_range_score": 0.0~1.0,
  "clarification_appropriateness_score": 0.0~1.0,
  "overall_score": 0.0~1.0,
  "issues": [
    {
      "type": "entity_mismatch|missing_filter|unnecessary_clarification|...",
      "severity": "critical|warning|info",
      "field": "optional field name",
      "message": "이슈 설명",
      "suggestion": "해결 제안"
    }
  ],
  "reasoning": "평가 근거 (1-2문장)"
}
```"""

    def _build_validator_prompt(
        self,
        user_message: str,
        query_plan: Dict[str, Any],
        conversation_context: Optional[str] = None
    ) -> str:
        """Validator 프롬프트 생성"""
        context_section = ""
        if conversation_context:
            context_section = f"\n## 대화 컨텍스트\n{conversation_context}\n"

        return f"""## 사용자 질문
{user_message}
{context_section}
## 생성된 QueryPlan
```json
{json.dumps(query_plan, ensure_ascii=False, indent=2)}
```

위 QueryPlan을 검증하고 JSON 형식으로 결과를 반환하세요."""

    def _calculate_quality_score(
        self,
        issues: List[ValidationIssue],
        query_plan: Dict[str, Any],
        llm_scores: Optional[LLMValidationScore] = None
    ) -> float:
        """품질 점수 계산"""
        base_score = 1.0

        # 이슈별 감점
        for issue in issues:
            penalty = self.SEVERITY_PENALTIES.get(issue.severity, 0)
            base_score -= penalty

        # 보너스: QueryPlan 완성도
        if query_plan.get("entity"):
            base_score += 0.05
        if query_plan.get("filters"):
            base_score += 0.02
        if query_plan.get("orderBy"):
            base_score += 0.01
        if query_plan.get("timeRange") or query_plan.get("limit"):
            base_score += 0.02

        # LLM 점수가 있으면 가중 평균
        if llm_scores:
            llm_weight = 0.4
            rule_weight = 0.6
            combined_score = (base_score * rule_weight) + (llm_scores.overall_score * llm_weight)
            return max(0.0, min(1.0, combined_score))

        return max(0.0, min(1.0, base_score))

    def _try_auto_correct(
        self,
        query_plan: Dict[str, Any],
        issues: List[ValidationIssue],
        user_message: str
    ) -> Optional[Dict[str, Any]]:
        """자동 수정 가능한 이슈 교정"""
        corrected = dict(query_plan)
        corrected_any = False
        message_lower = user_message.lower()

        for issue in issues:
            # 불필요한 clarification 제거
            if issue.type == ValidationIssueType.UNNECESSARY_CLARIFICATION:
                corrected["needs_clarification"] = False
                corrected["clarification_question"] = None
                corrected["clarification_options"] = None
                corrected_any = True

                # 엔티티도 없으면 추론해서 설정
                if not corrected.get("entity"):
                    for term, entity in self.DOMAIN_TERM_ENTITY_MAP.items():
                        if term in message_lower:
                            corrected["entity"] = entity
                            break

                # 필수 필드 기본값 설정
                if not corrected.get("operation"):
                    corrected["operation"] = "list"
                if not corrected.get("limit"):
                    # 숫자 추출 시도 (예: "30건")
                    numbers = re.findall(r'\d+', user_message)
                    if numbers:
                        corrected["limit"] = min(int(numbers[0]), 100)
                    else:
                        corrected["limit"] = 10
                if not corrected.get("orderBy"):
                    corrected["orderBy"] = [{"field": "createdAt", "direction": "desc"}]

            # 엔티티 불일치 수정
            if issue.type == ValidationIssueType.ENTITY_MISMATCH:
                for term, entity in self.DOMAIN_TERM_ENTITY_MAP.items():
                    if term in message_lower:
                        corrected["entity"] = entity
                        corrected_any = True
                        break

            # timeRange 자동 추가
            if issue.type == ValidationIssueType.MISSING_TIME_RANGE:
                now = datetime.now()
                corrected["timeRange"] = {
                    "start": (now - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z"),
                    "end": now.strftime("%Y-%m-%dT23:59:59Z")
                }
                corrected_any = True

        return corrected if corrected_any else None

    def _determine_clarification(
        self,
        user_message: str,
        issues: List[ValidationIssue],
        query_plan: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        """clarification 필요 여부 및 질문 결정"""
        message_lower = user_message.lower()

        # filter_local/aggregate_local 의도면 clarification 불필요
        if query_plan:
            query_intent = query_plan.get("query_intent", "new_query")
            if query_intent in ("filter_local", "aggregate_local"):
                return False, None, None

        # 이전 결과 참조 트리거가 있으면 clarification 불필요
        has_local_trigger = any(trigger in message_lower for trigger in [
            "이중", "이중에", "여기서", "그중", "그중에", "위 결과", "이전 결과", "방금 결과"
        ])
        if has_local_trigger:
            return False, None, None

        # 도메인 용어가 있으면 clarification 불필요
        has_domain_term = any(term in message_lower for term in self.DOMAIN_TERM_ENTITY_MAP)
        if has_domain_term:
            return False, None, None

        # 엔티티 관련 이슈가 있으면 clarification 요청
        entity_issues = [i for i in issues if i.type in {
            ValidationIssueType.ENTITY_MISMATCH,
            ValidationIssueType.INVALID_ENTITY,
            ValidationIssueType.AMBIGUOUS_INTENT
        }]

        if entity_issues:
            return (
                True,
                f"'{user_message}'에 대해 어떤 데이터를 조회하시겠습니까?",
                ["결제 내역 (Payment)", "환불 내역 (Refund)", "가맹점 정보 (Merchant)", "정산 내역 (Settlement)"]
            )

        return False, None, None


# 싱글톤 인스턴스
_validator_instance: Optional[QueryPlanValidatorService] = None


def get_query_plan_validator() -> QueryPlanValidatorService:
    """QueryPlanValidatorService 싱글톤 인스턴스 반환"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = QueryPlanValidatorService()
    return _validator_instance
