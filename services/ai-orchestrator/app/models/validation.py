"""
Validation Models for QueryPlan Quality Assessment
2단계 LLM 검증 시스템의 Pydantic 모델 정의
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class ValidationIssueType(str, Enum):
    """검증 이슈 유형"""
    ENTITY_MISMATCH = "entity_mismatch"           # 질문과 엔티티 불일치
    MISSING_FILTER = "missing_filter"              # 필수 필터 누락
    INVALID_FILTER = "invalid_filter"              # 잘못된 필터 조건
    MISSING_TIME_RANGE = "missing_time_range"      # 시계열 데이터에 timeRange 누락
    AMBIGUOUS_INTENT = "ambiguous_intent"          # 의도 불명확
    UNNECESSARY_CLARIFICATION = "unnecessary_clarification"  # 불필요한 clarification
    MISSING_CLARIFICATION = "missing_clarification"  # 필요한 clarification 누락 (집계+기간없음)
    INVALID_OPERATOR = "invalid_operator"          # 잘못된 연산자
    FIELD_NOT_EXIST = "field_not_exist"            # 존재하지 않는 필드
    INVALID_ENTITY = "invalid_entity"              # 유효하지 않은 엔티티
    LIMIT_OUT_OF_RANGE = "limit_out_of_range"      # limit 범위 초과


class IssueSeverity(str, Enum):
    """이슈 심각도"""
    CRITICAL = "critical"  # 실행 불가, 반드시 수정 필요
    WARNING = "warning"    # 실행 가능하나 결과 부정확 가능
    INFO = "info"          # 개선 권장


class ValidationIssue(BaseModel):
    """개별 검증 이슈"""
    type: ValidationIssueType = Field(description="이슈 유형")
    severity: IssueSeverity = Field(description="심각도")
    field: Optional[str] = Field(default=None, description="문제가 있는 필드")
    message: str = Field(description="이슈 설명")
    suggestion: Optional[str] = Field(default=None, description="해결 제안")


class LLMValidationScore(BaseModel):
    """LLM 검증 점수 (상세)"""
    entity_match_score: float = Field(ge=0.0, le=1.0, description="엔티티 일치 점수")
    filter_completeness_score: float = Field(ge=0.0, le=1.0, description="필터 완성도 점수")
    time_range_score: float = Field(ge=0.0, le=1.0, description="시간 범위 적절성 점수")
    clarification_appropriateness_score: float = Field(ge=0.0, le=1.0, description="clarification 적절성 점수")
    overall_score: float = Field(ge=0.0, le=1.0, description="종합 점수")
    reasoning: Optional[str] = Field(default=None, description="평가 근거")


class ValidationResult(BaseModel):
    """검증 결과"""
    quality_score: float = Field(ge=0.0, le=1.0, description="품질 점수 (0.0~1.0)")
    is_valid: bool = Field(description="유효 여부 (quality_score >= threshold)")
    issues: List[ValidationIssue] = Field(default_factory=list, description="발견된 이슈 목록")
    corrected_plan: Optional[Dict[str, Any]] = Field(
        default=None,
        description="수정된 QueryPlan (자동 수정 적용 시)"
    )
    clarification_needed: bool = Field(default=False, description="clarification 필요 여부")
    clarification_question: Optional[str] = Field(default=None, description="clarification 질문")
    clarification_options: Optional[List[str]] = Field(default=None, description="clarification 선택지")
    validation_time_ms: int = Field(default=0, description="검증 소요 시간 (ms)")
    llm_scores: Optional[LLMValidationScore] = Field(default=None, description="LLM 검증 상세 점수")

    class Config:
        json_schema_extra = {
            "example": {
                "quality_score": 0.95,
                "is_valid": True,
                "issues": [],
                "corrected_plan": None,
                "clarification_needed": False,
                "validation_time_ms": 150
            }
        }
