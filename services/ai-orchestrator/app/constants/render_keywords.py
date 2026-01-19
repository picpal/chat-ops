"""
Render Keywords Constants

차트/테이블/텍스트 렌더링 타입 감지를 위한 키워드 상수 정의
RenderComposerService와 chat.py에서 공통으로 사용
"""

from typing import Dict, List

# ============================================
# 차트 관련 키워드
# ============================================

# 차트 렌더링 요청 키워드 (단독 키워드 포함)
CHART_KEYWORDS: List[str] = [
    # 단독 키워드 (문장에 포함되면 차트 요청으로 간주)
    "그래프",
    "차트",
    "시각화",
    # 조사 포함 키워드
    "그래프로",
    "차트로",
    "시각화로",
    "그래프 형태",
    "차트 형태",
    "그래프로 보여",
    "차트로 보여",
    "그래프로 보고",
    "차트로 보고",
    "그래프 만들어",
    "차트 만들어",
]

# 차트 타입별 키워드 (자동 차트 타입 결정에 사용)
CHART_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "pie": [
        "비율",
        "점유율",
        "분포",
        "비중",
        "퍼센트",
        "%",
        "파이",
        "원형",
        "pie",
    ],
    "line": [
        "추이",
        "추세",
        "변화",
        "트렌드",
        "trend",
        "일별",
        "월별",
        "주별",
        "연별",
        "시계열",
        "라인",
        "line",
    ],
    "bar": [
        "막대",
        "막대 그래프",
        "막대 차트",
        "바 차트",
        "bar chart",
        "bar",
        "비교",
    ],
    "area": [
        "영역",
        "면적",
        "area",
        "누적",
        "stacked",
    ],
}

# ============================================
# 테이블 관련 키워드
# ============================================

# 테이블 렌더링 요청 키워드
# NOTE: 단독 "표"는 "표현", "표시" 등과 혼동될 수 있으므로 조사 포함 형태 사용
TABLE_KEYWORDS: List[str] = [
    # 조사 포함 키워드 (단독 "표"는 "표현" 등과 혼동 방지)
    "표로",
    "표 보여",
    "표 만들어",
    "테이블로",
    "테이블 보여",
    "테이블 만들어",
    "목록으로",
    "목록 보여",
    "리스트로",
    "리스트 보여",
    "표 형태",
    "테이블 형태",
    "표로 보여",
    "테이블로 보여",
    # 부정 표현 (차트 대신 표) - 최우선 순위
    "그래프 말고",
    "차트 말고",
    "그래프 대신",
    "차트 대신",
]

# ============================================
# 텍스트 관련 키워드
# ============================================

# 텍스트 렌더링 요청 키워드
# NOTE: "알려줘", "설명해"는 너무 일반적이라 제외 (암시적 차트 키워드와 충돌)
TEXT_KEYWORDS: List[str] = [
    "텍스트로",
    "텍스트 형태",
    "글로",
    "글로 보여",
    "요약으로",
    "요약해줘",
    "요약 형태",
]

# ============================================
# 시계열 필드 감지용 키워드
# ============================================

TIME_FIELD_KEYWORDS: List[str] = [
    "date",
    "time",
    "day",
    "month",
    "year",
    "week",
    "quarter",
    "period",
    "날짜",
    "일자",
    "월",
    "연도",
]

# ============================================
# 필드 타입 분류 (차트 타입 자동 결정용)
# ============================================

# 시계열 필드 - line chart 기본
# camelCase, snake_case, SQL 파생 필드 모두 포함
DATE_FIELDS: List[str] = [
    # camelCase (QueryPlan 표준)
    "approvedAt",
    "createdAt",
    "updatedAt",
    "settlementDate",
    "timestamp",
    "periodStart",
    "periodEnd",
    "orderDate",
    # snake_case (SQL 결과)
    "approved_at",
    "created_at",
    "updated_at",
    "settlement_date",
    "period_start",
    "period_end",
    "order_date",
    # SQL 파생 필드 (DATE_TRUNC, EXTRACT 결과)
    "month",
    "date",
    "day",
    "week",
    "year",
    "quarter",
]

# 카테고리 필드 - bar chart 기본
# camelCase, snake_case 모두 포함
CATEGORY_FIELDS: List[str] = [
    # camelCase (QueryPlan 표준)
    "status",
    "method",
    "merchantId",
    "type",
    "level",
    "sourceType",
    "cardCompany",
    "reason",
    # snake_case (SQL 결과)
    "merchant_id",
    "source_type",
    "card_company",
]
