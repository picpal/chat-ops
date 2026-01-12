"""
QueryPlanValidatorService 테스트
규칙 기반 검증 + 자동 수정 테스트
"""

import pytest
from app.services.query_plan_validator import QueryPlanValidatorService
from app.models.validation import ValidationIssueType, IssueSeverity


class TestRuleBasedValidation:
    """규칙 기반 검증 테스트"""

    def setup_method(self):
        self.validator = QueryPlanValidatorService()

    def test_domain_term_entity_match_correct(self):
        """도메인 용어-엔티티 일치 (정상)"""
        issues = self.validator._apply_rule_based_validation(
            "최근 결제 30건",
            {"entity": "Payment", "limit": 30}
        )
        entity_mismatch = [i for i in issues if i.type == ValidationIssueType.ENTITY_MISMATCH]
        assert len(entity_mismatch) == 0

    def test_domain_term_entity_mismatch(self):
        """도메인 용어-엔티티 불일치 감지"""
        issues = self.validator._apply_rule_based_validation(
            "최근 결제 30건",
            {"entity": "Order", "limit": 30}  # 잘못된 엔티티
        )
        entity_mismatch = [i for i in issues if i.type == ValidationIssueType.ENTITY_MISMATCH]
        assert len(entity_mismatch) > 0
        assert entity_mismatch[0].severity == IssueSeverity.CRITICAL

    def test_unnecessary_clarification_detection(self):
        """불필요한 clarification 감지"""
        issues = self.validator._apply_rule_based_validation(
            "거래 내역 조회해줘",
            {"needs_clarification": True, "clarification_question": "어떤 데이터?"}
        )
        unnecessary = [i for i in issues if i.type == ValidationIssueType.UNNECESSARY_CLARIFICATION]
        assert len(unnecessary) > 0
        assert unnecessary[0].severity == IssueSeverity.CRITICAL

    def test_clarification_needed_for_ambiguous(self):
        """모호한 요청에는 clarification 필요 없음 (검출 안함)"""
        issues = self.validator._apply_rule_based_validation(
            "정보 보여줘",  # 도메인 용어 없음
            {"needs_clarification": True, "clarification_question": "어떤 데이터?"}
        )
        unnecessary = [i for i in issues if i.type == ValidationIssueType.UNNECESSARY_CLARIFICATION]
        assert len(unnecessary) == 0  # 모호한 요청이므로 clarification 허용

    def test_missing_time_range_warning(self):
        """시계열 데이터에 timeRange 누락 경고"""
        issues = self.validator._apply_rule_based_validation(
            "결제 조회",
            {"entity": "Payment"}  # timeRange, limit 모두 없음
        )
        missing_time = [i for i in issues if i.type == ValidationIssueType.MISSING_TIME_RANGE]
        assert len(missing_time) > 0
        assert missing_time[0].severity == IssueSeverity.WARNING

    def test_no_time_range_warning_with_limit(self):
        """limit이 있으면 timeRange 경고 없음"""
        issues = self.validator._apply_rule_based_validation(
            "결제 30건",
            {"entity": "Payment", "limit": 30}
        )
        missing_time = [i for i in issues if i.type == ValidationIssueType.MISSING_TIME_RANGE]
        assert len(missing_time) == 0

    def test_invalid_operator_detection(self):
        """잘못된 연산자 감지"""
        issues = self.validator._apply_rule_based_validation(
            "결제 조회",
            {
                "entity": "Payment",
                "filters": [{"field": "amount", "operator": ">=", "value": 1000}]  # 잘못된 연산자
            }
        )
        invalid_op = [i for i in issues if i.type == ValidationIssueType.INVALID_OPERATOR]
        assert len(invalid_op) > 0

    def test_valid_operator_passes(self):
        """올바른 연산자 통과"""
        issues = self.validator._apply_rule_based_validation(
            "결제 조회",
            {
                "entity": "Payment",
                "limit": 10,
                "filters": [{"field": "amount", "operator": "gte", "value": 1000}]
            }
        )
        invalid_op = [i for i in issues if i.type == ValidationIssueType.INVALID_OPERATOR]
        assert len(invalid_op) == 0


class TestQualityScoreCalculation:
    """품질 점수 계산 테스트"""

    def setup_method(self):
        self.validator = QueryPlanValidatorService()

    def test_perfect_score(self):
        """이슈 없으면 높은 점수"""
        score = self.validator._calculate_quality_score(
            issues=[],
            query_plan={"entity": "Payment", "filters": [], "orderBy": [{"field": "createdAt", "direction": "desc"}]}
        )
        assert score >= 0.9

    def test_critical_issue_penalty(self):
        """Critical 이슈는 큰 감점"""
        from app.models.validation import ValidationIssue
        issues = [ValidationIssue(
            type=ValidationIssueType.ENTITY_MISMATCH,
            severity=IssueSeverity.CRITICAL,
            message="test"
        )]
        score = self.validator._calculate_quality_score(issues, {"entity": "Payment"})
        assert score < 0.8  # threshold 미만

    def test_warning_issue_small_penalty(self):
        """Warning 이슈는 작은 감점"""
        from app.models.validation import ValidationIssue
        issues = [ValidationIssue(
            type=ValidationIssueType.MISSING_TIME_RANGE,
            severity=IssueSeverity.WARNING,
            message="test"
        )]
        score = self.validator._calculate_quality_score(issues, {"entity": "Payment"})
        assert score >= 0.8  # threshold 이상 (warning만으로는 실패 안 함)


class TestAutoCorrection:
    """자동 수정 테스트"""

    def setup_method(self):
        self.validator = QueryPlanValidatorService()

    def test_auto_correct_unnecessary_clarification(self):
        """불필요한 clarification 자동 수정"""
        from app.models.validation import ValidationIssue
        issues = [ValidationIssue(
            type=ValidationIssueType.UNNECESSARY_CLARIFICATION,
            severity=IssueSeverity.CRITICAL,
            message="도메인 용어가 명확함"
        )]
        corrected = self.validator._try_auto_correct(
            {"needs_clarification": True, "clarification_question": "어떤 데이터?"},
            issues,
            "결제 30건 조회"
        )
        assert corrected is not None
        assert corrected["needs_clarification"] == False
        assert corrected["entity"] == "Payment"  # 자동 추론

    def test_auto_correct_entity_mismatch(self):
        """엔티티 불일치 자동 수정"""
        from app.models.validation import ValidationIssue
        issues = [ValidationIssue(
            type=ValidationIssueType.ENTITY_MISMATCH,
            severity=IssueSeverity.CRITICAL,
            message="잘못된 엔티티"
        )]
        corrected = self.validator._try_auto_correct(
            {"entity": "Order", "limit": 30},
            issues,
            "거래 30건 조회"
        )
        assert corrected is not None
        assert corrected["entity"] == "Payment"

    def test_auto_add_time_range(self):
        """timeRange 자동 추가"""
        from app.models.validation import ValidationIssue
        issues = [ValidationIssue(
            type=ValidationIssueType.MISSING_TIME_RANGE,
            severity=IssueSeverity.WARNING,
            message="timeRange 권장"
        )]
        corrected = self.validator._try_auto_correct(
            {"entity": "Payment"},
            issues,
            "결제 조회"
        )
        assert corrected is not None
        assert "timeRange" in corrected
        assert "start" in corrected["timeRange"]
        assert "end" in corrected["timeRange"]


class TestClarificationDecision:
    """clarification 결정 테스트"""

    def setup_method(self):
        self.validator = QueryPlanValidatorService()

    def test_no_clarification_with_domain_term(self):
        """도메인 용어 있으면 clarification 불필요"""
        from app.models.validation import ValidationIssue
        issues = [ValidationIssue(
            type=ValidationIssueType.AMBIGUOUS_INTENT,
            severity=IssueSeverity.CRITICAL,
            message="의도 불명확"
        )]
        needed, question, options = self.validator._determine_clarification(
            "결제 내역 보여줘",  # 도메인 용어 있음
            issues
        )
        assert needed == False

    def test_clarification_needed_without_domain_term(self):
        """도메인 용어 없으면 clarification 필요"""
        from app.models.validation import ValidationIssue
        issues = [ValidationIssue(
            type=ValidationIssueType.AMBIGUOUS_INTENT,
            severity=IssueSeverity.CRITICAL,
            message="의도 불명확"
        )]
        needed, question, options = self.validator._determine_clarification(
            "정보 보여줘",  # 도메인 용어 없음
            issues
        )
        assert needed == True
        assert question is not None
        assert options is not None


@pytest.mark.asyncio
class TestValidatorIntegration:
    """통합 테스트"""

    async def test_validate_correct_plan(self):
        """올바른 QueryPlan 검증 통과"""
        validator = QueryPlanValidatorService()
        result = await validator.validate(
            "최근 결제 30건",
            {"entity": "Payment", "limit": 30, "orderBy": [{"field": "createdAt", "direction": "desc"}]}
        )
        assert result.is_valid == True
        assert result.quality_score >= 0.8

    async def test_validate_and_auto_correct(self):
        """잘못된 QueryPlan 자동 수정"""
        validator = QueryPlanValidatorService()
        result = await validator.validate(
            "결제 내역 30건 보여줘",
            {"entity": "Order", "needs_clarification": True, "limit": 30}  # 잘못된 상태
        )
        # 자동 수정되어야 함
        assert result.corrected_plan is not None
        assert result.corrected_plan["entity"] == "Payment"
        assert result.corrected_plan["needs_clarification"] == False

    async def test_validate_ambiguous_request(self):
        """모호한 요청에 clarification"""
        validator = QueryPlanValidatorService()
        result = await validator.validate(
            "데이터 조회해줘",  # 모호한 요청
            {"needs_clarification": True, "clarification_question": "어떤 데이터?"}
        )
        # 모호한 요청이므로 clarification 유지
        assert result.clarification_needed == True or result.quality_score >= 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
