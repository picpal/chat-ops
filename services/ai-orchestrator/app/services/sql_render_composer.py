"""
SqlRenderComposerService: SQL 실행 결과를 RenderSpec으로 변환

Text-to-SQL 모드에서 사용되는 RenderSpec 구성 로직
차트, 테이블, 집계 결과 등 다양한 렌더링 타입 지원
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple

from app.constants.render_keywords import (
    CHART_KEYWORDS,
    TABLE_KEYWORDS,
    TIME_FIELD_KEYWORDS,
    CHART_TYPE_KEYWORDS,
    DATE_FIELDS,
    CATEGORY_FIELDS,
)

logger = logging.getLogger(__name__)


# ============================================
# 렌더링 타입 감지
# ============================================

def _detect_render_type_from_message(message: str) -> Optional[str]:
    """사용자 메시지에서 렌더링 타입 감지

    상수 파일(render_keywords.py)에서 키워드를 import하여 사용

    우선순위:
    1. 테이블 키워드 ("그래프 말고 표로" 같은 부정 표현 처리)
    2. 차트 키워드 (단독 키워드 "그래프", "차트" 포함)

    Args:
        message: 사용자 질문

    Returns:
        "chart" | "table" | None
    """
    msg = message.lower()

    # 1순위: 테이블 키워드 감지 (부정 표현 처리를 위해 먼저 체크)
    if any(kw in msg for kw in TABLE_KEYWORDS):
        return "table"

    # 2순위: 차트 키워드 감지 (단독 키워드 포함)
    if any(kw in msg for kw in CHART_KEYWORDS):
        return "chart"

    return None


# ============================================
# 차트 타입 결정 (폴백 로직)
# ============================================

def _detect_chart_type(data: List[Dict[str, Any]], columns: List[str], user_message: str = "") -> str:
    """데이터 구조를 분석하여 적절한 차트 타입 결정 (폴백 로직)

    LLM 기반 차트 타입 결정 실패 시 사용되는 규칙 기반 폴백 로직.
    사용자 메시지의 키워드와 데이터 구조를 분석하여 차트 타입 결정.

    Args:
        data: 쿼리 결과 데이터
        columns: 컬럼 목록
        user_message: 사용자 질문 (키워드 분석용)

    Returns:
        "bar" | "line" | "pie"
    """
    if not data or not columns:
        return "bar"

    message_lower = user_message.lower()

    # 시계열 컬럼 감지 (DATE_FIELDS 상수 사용 - camelCase, snake_case 모두 지원)
    has_time_column = any(
        col.lower() in [f.lower() for f in DATE_FIELDS]
        or any(kw in col.lower() for kw in TIME_FIELD_KEYWORDS)
        for col in columns
    )

    # line 키워드 체크 (추이, 변화, 트렌드 등)
    line_keywords = CHART_TYPE_KEYWORDS.get("line", [])
    has_line_keyword = any(kw in message_lower for kw in line_keywords)

    # 시계열 + line 키워드 -> line (데이터 행 수와 무관)
    if has_time_column and has_line_keyword:
        logger.info(f"[ChartType Fallback] time_column + line_keyword -> line")
        return "line"

    # 시계열 + 2행 이상 -> line (기존 임계값 완화: >2 -> >=2)
    if has_time_column and len(data) >= 2:
        logger.info(f"[ChartType Fallback] time_column + data>=2 -> line")
        return "line"

    # pie 키워드 -> pie (10행 이하일 때만)
    pie_keywords = CHART_TYPE_KEYWORDS.get("pie", [])
    if any(kw in message_lower for kw in pie_keywords) and len(data) <= 10:
        logger.info(f"[ChartType Fallback] pie_keyword + data<=10 -> pie")
        return "pie"

    # 카테고리가 적고 (5개 이하) 단일 값 컬럼이면 pie 차트
    # 단, line 키워드가 없는 경우에만
    if len(data) <= 5 and len(columns) == 2 and not has_line_keyword:
        logger.info(f"[ChartType Fallback] small_data + 2_cols + no_line_keyword -> pie")
        return "pie"

    # 기본은 bar 차트
    logger.info(f"[ChartType Fallback] default -> bar")
    return "bar"


def _identify_axis_keys(data: List[Dict[str, Any]], columns: List[str]) -> Tuple[str, str]:
    """X축과 Y축에 사용할 키 식별

    Args:
        data: 쿼리 결과 데이터
        columns: 컬럼 목록

    Returns:
        (x_key, y_key) 튜플
    """
    if not columns:
        return ("", "")

    if len(columns) == 1:
        return (columns[0], columns[0])

    # 숫자형 컬럼 찾기 (Y축 후보)
    numeric_cols = []
    category_cols = []

    if data:
        first_row = data[0]
        for col in columns:
            value = first_row.get(col)
            if isinstance(value, (int, float)):
                numeric_cols.append(col)
            else:
                category_cols.append(col)

    # X축: 카테고리/시간 컬럼, Y축: 숫자 컬럼
    x_key = category_cols[0] if category_cols else columns[0]
    y_key = numeric_cols[0] if numeric_cols else columns[-1]

    return (x_key, y_key)


def _identify_multi_series_axis(
    columns: List[str],
    user_message: str
) -> Tuple[Optional[str], Optional[str], bool]:
    """다중 컬럼에서 멀티 시리즈 차트 축 식별

    컬럼 목록에서 시계열/카테고리 필드를 추론하여 멀티 시리즈 차트 구성

    Args:
        columns: 컬럼 목록
        user_message: 사용자 메시지 (추이/트렌드 키워드 감지용)

    Returns:
        (x_axis_key, series_key, is_multi_series) 튜플
    """
    if len(columns) < 3:  # 최소 x축, 시리즈, 값 컬럼 필요
        return (None, None, False)

    # 컬럼에서 시계열/카테고리 필드 분리
    date_fields = [col for col in columns if col.lower() in [f.lower() for f in DATE_FIELDS]]
    category_fields = [col for col in columns if col.lower() in [f.lower() for f in CATEGORY_FIELDS]]

    # 추이/트렌드 키워드 감지 (로깅용)
    trend_keywords = CHART_TYPE_KEYWORDS.get("line", [])
    message_lower = user_message.lower()
    has_trend = any(kw in message_lower for kw in trend_keywords)

    logger.info(
        f"[MultiSeries SQL] columns={columns}, "
        f"dateFields={date_fields}, categoryFields={category_fields}, "
        f"has_trend={has_trend}"
    )

    # TC-013: 카테고리 + 시계열 → 멀티 시리즈 (has_trend 조건 제거)
    # 시계열과 카테고리 필드가 모두 있으면 멀티 시리즈로 판단
    if category_fields and date_fields:
        x_axis_key = date_fields[0]  # 시계열을 X축으로
        series_key = category_fields[0]  # 카테고리를 시리즈로
        logger.info(
            f"[MultiSeries SQL] Detected! x_axis={x_axis_key}, series={series_key}"
        )
        return (x_axis_key, series_key, True)

    return (None, None, False)


def _pivot_data_for_multi_series(
    rows: List[Dict[str, Any]],
    x_axis_key: str,
    series_key: str,
    value_key: str,
    max_series: int = 5
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """멀티 시리즈 차트를 위한 데이터 피벗

    Args:
        rows: 원본 데이터 행
        x_axis_key: X축 키 (시계열)
        series_key: 시리즈 키 (카테고리)
        value_key: 값 키 (집계값)
        max_series: 최대 시리즈 수

    Returns:
        (pivoted_rows, series_keys) 튜플
    """
    if not rows:
        return ([], [])

    # 1. 시리즈별 총합 계산
    series_totals: Dict[str, float] = {}
    for row in rows:
        s_key = str(row.get(series_key, ""))
        value = row.get(value_key, 0) or 0
        series_totals[s_key] = series_totals.get(s_key, 0) + float(value)

    # 2. 상위 N개 시리즈 선별
    sorted_series = sorted(
        series_totals.items(),
        key=lambda x: x[1],
        reverse=True
    )
    top_series = [s[0] for s in sorted_series[:max_series]]
    has_others = len(sorted_series) > max_series
    others_count = len(sorted_series) - max_series if has_others else 0
    others_label = f"그 외 ({others_count}개)" if has_others else ""

    logger.info(
        f"[MultiSeries SQL] Top {max_series} series: {top_series}, "
        f"has_others={has_others}, others_count={others_count}"
    )

    # 3. X축 값별로 그룹화 및 피벗
    x_axis_groups: Dict[str, Dict[str, float]] = {}
    for row in rows:
        x_val = str(row.get(x_axis_key, ""))
        s_key = str(row.get(series_key, ""))
        value = row.get(value_key, 0) or 0

        if x_val not in x_axis_groups:
            x_axis_groups[x_val] = {x_axis_key: x_val}
            for ts in top_series:
                x_axis_groups[x_val][ts] = 0
            if has_others:
                x_axis_groups[x_val][others_label] = 0

        if s_key in top_series:
            x_axis_groups[x_val][s_key] = float(value)
        elif has_others:
            x_axis_groups[x_val][others_label] += float(value)

    # 4. X축 기준 정렬
    pivoted_rows = sorted(
        x_axis_groups.values(),
        key=lambda x: x.get(x_axis_key, "")
    )

    # 5. 시리즈 키 리스트 반환
    series_keys = top_series.copy()
    if has_others:
        series_keys.append(others_label)

    logger.info(
        f"[MultiSeries SQL] Pivoted {len(rows)} rows to {len(pivoted_rows)} rows, "
        f"series_keys={series_keys}"
    )

    return (pivoted_rows, series_keys)


def _detect_trend(values: List[float]) -> Optional[str]:
    """시계열 데이터의 추세 감지

    Args:
        values: Y축 값 리스트 (시간 순서대로)

    Returns:
        "증가" | "감소" | "유지" | None (데이터 부족시)
    """
    if len(values) < 3:
        return None

    # 전반부와 후반부의 평균 비교
    mid = len(values) // 2
    first_half = sum(values[:mid]) / mid
    second_half = sum(values[mid:]) / (len(values) - mid)

    if first_half == 0:
        return "증가" if second_half > 0 else "유지"

    diff_ratio = (second_half - first_half) / first_half

    if diff_ratio > 0.1:
        return "증가"
    elif diff_ratio < -0.1:
        return "감소"
    return "유지"


# ============================================
# 인사이트 생성
# ============================================

def _generate_insight(
    data: List[Dict[str, Any]],
    x_key: str,
    y_key: str,
    chart_type: str,
    template: Optional[str] = None
) -> Dict[str, Any]:
    """차트 데이터에 대한 인사이트 생성 (LLM 템플릿 우선, 규칙 기반 폴백)

    Args:
        data: 차트 데이터
        x_key: X축 필드 키
        y_key: Y축 필드 키
        chart_type: 차트 타입 (line, bar, pie)
        template: LLM이 생성한 인사이트 템플릿 (선택적)

    Returns:
        {
            "content": "인사이트 텍스트",
            "source": "llm" | "template" | "none"
        }
    """
    import re

    if not data:
        return {"content": None, "source": "none"}

    # 숫자 값 추출
    values = []
    for row in data:
        val = row.get(y_key, 0)
        if isinstance(val, (int, float)):
            values.append(float(val))
        elif val is not None:
            try:
                values.append(float(val))
            except (ValueError, TypeError):
                values.append(0)

    if not values:
        return {"content": None, "source": "none"}

    # 통계 계산
    count = len(data)
    total = sum(values)
    avg = total / count if count > 0 else 0
    max_val = max(values)
    min_val = min(values)

    # 최대/최소 카테고리 찾기
    max_idx = values.index(max_val)
    min_idx = values.index(min_val)
    max_category = str(data[max_idx].get(x_key, ""))
    min_category = str(data[min_idx].get(x_key, ""))

    # 추세 감지 (line 차트에서만)
    trend = _detect_trend(values) if chart_type == "line" else None

    # 필드 라벨 매핑 (snake_case -> 한글)
    FIELD_LABELS = {
        "month": "월",
        "date": "일",
        "week": "주",
        "year": "연도",
        "day": "일",
        "merchant_id": "가맹점",
        "status": "상태",
        "method": "결제수단",
        "amount": "금액",
        "total_amount": "매출",
        "sum_amount": "총금액",
        "count": "건수",
        "payment_count": "결제건수",
        "refund_count": "환불건수",
        "avg_amount": "평균금액",
        "net_amount": "정산금액",
        "total": "합계",
        "avg": "평균",
    }

    # 필드 라벨 추출 (snake_case, camelCase 모두 지원)
    def get_field_label(key: str) -> str:
        key_lower = key.lower()
        if key_lower in FIELD_LABELS:
            return FIELD_LABELS[key_lower]
        # snake_case 처리
        parts = key.split('_')
        for part in parts:
            if part.lower() in FIELD_LABELS:
                return FIELD_LABELS[part.lower()]
        # 기본값: 그대로 반환
        return key.replace('_', ' ').title()

    group_by_label = get_field_label(x_key)
    metric_label = get_field_label(y_key)

    # 금액 포맷팅 함수
    def format_currency(val: float) -> str:
        if val >= 1000:
            return f"₩{int(val):,}"
        return f"{val:,.1f}"

    # 플레이스홀더 값 구성
    placeholders = {
        "{count}": f"{count:,}",
        "{total}": format_currency(total),
        "{avg}": format_currency(avg),
        "{max}": format_currency(max_val),
        "{min}": format_currency(min_val),
        "{maxCategory}": max_category,
        "{minCategory}": min_category,
        "{trend}": trend or "",
        "{groupBy}": group_by_label,
        "{metric}": metric_label,
    }

    # LLM 템플릿이 있으면 플레이스홀더 치환
    if template:
        content = template
        for placeholder, value in placeholders.items():
            content = content.replace(placeholder, value)

        # 미치환 플레이스홀더 제거 (중괄호로 시작하는 항목)
        content = re.sub(r'\{[^}]+\}', '', content)
        content = re.sub(r'\s+', ' ', content).strip()

        logger.info(f"[Insight] Generated from LLM template: {content[:100]}...")
        return {"content": content, "source": "llm"}

    # 폴백: 규칙 기반 템플릿
    if chart_type == "line":
        content = f"{group_by_label}별 {metric_label} 추이입니다. 총 {count:,}개 데이터의 합계는 {format_currency(total)}입니다."
        if trend:
            content += f" 전반적으로 {trend} 추세입니다."
    elif chart_type == "pie":
        content = f"{group_by_label}별 {metric_label} 분포입니다. {max_category}가 가장 큰 비중을 차지합니다."
    else:  # bar
        content = f"{group_by_label}별 {metric_label} 비교입니다. {max_category}가 {format_currency(max_val)}로 가장 높습니다."

    logger.info(f"[Insight] Generated from rule-based template: {content[:100]}...")
    return {"content": content, "source": "template"}


# ============================================
# Summary Stats 생성 (차트 유형별 동적 통계)
# ============================================

def _calculate_extended_stats(
    data: List[Dict[str, Any]],
    x_key: str,
    y_key: str,
    chart_type: str
) -> Dict[str, Any]:
    """차트 유형에 맞는 확장 통계 계산

    Args:
        data: 차트 데이터
        x_key: X축 필드 키
        y_key: Y축 필드 키
        chart_type: 차트 타입 (line, bar, pie)

    Returns:
        확장 통계 딕셔너리
    """
    if not data:
        return {}

    # 기본 통계
    values = []
    for row in data:
        val = row.get(y_key, 0)
        if isinstance(val, (int, float)):
            values.append(float(val))
        elif val is not None:
            try:
                values.append(float(val))
            except (ValueError, TypeError):
                pass

    if not values:
        return {}

    count = len(values)
    total = sum(values)
    avg = total / count if count > 0 else 0
    max_val = max(values)
    min_val = min(values)

    # 최대/최소 인덱스 및 카테고리
    max_idx = values.index(max_val)
    min_idx = values.index(min_val)
    max_category = str(data[max_idx].get(x_key, ""))
    min_category = str(data[min_idx].get(x_key, ""))

    stats = {
        "count": count,
        "total": total,
        "avg": avg,
        "max": max_val,
        "min": min_val,
        "max_category": max_category,
        "min_category": min_category,
        "max_idx": max_idx,
        "min_idx": min_idx,
    }

    # 차트 유형별 확장 통계
    if chart_type == "pie":
        # 파이 차트: 비율 계산
        if total > 0:
            max_share = (max_val / total) * 100
            min_share = (min_val / total) * 100
            stats["max_share"] = max_share
            stats["min_share"] = min_share
            # 집중도 (상위 N개가 차지하는 비율)
            sorted_values = sorted(values, reverse=True)
            top_3_sum = sum(sorted_values[:3]) if len(sorted_values) >= 3 else sum(sorted_values)
            stats["concentration"] = (top_3_sum / total) * 100

    elif chart_type == "line":
        # 라인 차트: 추세, 변동성
        if len(values) >= 2:
            # 추세 계산 (전반부 vs 후반부)
            mid = len(values) // 2
            first_half_avg = sum(values[:mid]) / mid if mid > 0 else 0
            second_half_avg = sum(values[mid:]) / (len(values) - mid)

            if first_half_avg > 0:
                growth_rate = ((second_half_avg - first_half_avg) / first_half_avg) * 100
            else:
                growth_rate = 100 if second_half_avg > 0 else 0

            stats["growth_rate"] = growth_rate
            stats["trend"] = "증가" if growth_rate > 10 else ("감소" if growth_rate < -10 else "유지")

            # 변동성 (표준편차)
            variance = sum((v - avg) ** 2 for v in values) / count
            std_dev = variance ** 0.5
            stats["volatility"] = std_dev
            stats["cv"] = (std_dev / avg * 100) if avg > 0 else 0  # 변동계수

            # 피크 시점
            stats["peak_time"] = max_category

            # 기간 정보
            if count > 1:
                stats["period_start"] = str(data[0].get(x_key, ""))
                stats["period_end"] = str(data[-1].get(x_key, ""))

    elif chart_type == "bar":
        # 바 차트: 범위, 평균 대비 비교
        range_val = max_val - min_val
        stats["range"] = range_val

        # 최대값이 평균의 몇 배인지
        if avg > 0:
            stats["max_vs_avg"] = max_val / avg
        else:
            stats["max_vs_avg"] = 0

    return stats


def _generate_rule_based_stats(
    stats: Dict[str, Any],
    chart_type: str,
    x_key: str,
    y_key: str
) -> Dict[str, Any]:
    """규칙 기반 Summary Stats 생성 (폴백)

    Args:
        stats: 확장 통계 딕셔너리
        chart_type: 차트 타입
        x_key: X축 키
        y_key: Y축 키

    Returns:
        summaryStats 구조
    """
    if not stats:
        return {"items": [], "source": "fallback"}

    items = []

    # 금액 포맷팅 함수
    def fmt_currency(val: float) -> str:
        if val >= 100000000:  # 억 단위
            return f"₩{val/100000000:.1f}억"
        elif val >= 10000:  # 만 단위
            return f"₩{val/10000:.0f}만"
        return f"₩{int(val):,}"

    def fmt_percent(val: float) -> str:
        return f"{val:.1f}%"

    # 차트 유형별 항목 구성
    if chart_type == "pie":
        # 파이 차트: 최대 비중, 최소 비중, 총합, 항목 수, 집중도
        items = [
            {
                "key": "max_share",
                "label": "최대 비중",
                "value": f"{stats.get('max_category', '')} ({fmt_percent(stats.get('max_share', 0))})",
                "type": "text",
                "highlight": True,
                "icon": "emoji_events"
            },
            {
                "key": "min_share",
                "label": "최소 비중",
                "value": f"{stats.get('min_category', '')} ({fmt_percent(stats.get('min_share', 0))})",
                "type": "text",
                "icon": "trending_down"
            },
            {
                "key": "total",
                "label": "총합",
                "value": stats.get("total", 0),
                "type": "currency",
                "icon": "functions"
            },
            {
                "key": "count",
                "label": "항목 수",
                "value": stats.get("count", 0),
                "type": "number",
                "icon": "format_list_numbered"
            },
            {
                "key": "concentration",
                "label": "상위 3개 집중도",
                "value": fmt_percent(stats.get("concentration", 0)),
                "type": "percentage",
                "icon": "donut_large"
            }
        ]

    elif chart_type == "line":
        # 라인 차트: 추세, 피크 시점, 변동성, 기간, 성장률
        trend = stats.get("trend", "유지")
        trend_icon = "trending_up" if trend == "증가" else ("trending_down" if trend == "감소" else "trending_flat")

        items = [
            {
                "key": "trend",
                "label": "전체 추세",
                "value": trend,
                "type": "trend",
                "highlight": True,
                "icon": trend_icon
            },
            {
                "key": "peak_time",
                "label": "피크 시점",
                "value": f"{stats.get('peak_time', '')} ({fmt_currency(stats.get('max', 0))})",
                "type": "text",
                "icon": "show_chart"
            },
            {
                "key": "growth_rate",
                "label": "성장률",
                "value": fmt_percent(stats.get("growth_rate", 0)),
                "type": "percentage",
                "icon": "speed"
            },
            {
                "key": "period",
                "label": "기간",
                "value": f"{stats.get('period_start', '')} ~ {stats.get('period_end', '')}",
                "type": "text",
                "icon": "date_range"
            },
            {
                "key": "avg",
                "label": "평균",
                "value": stats.get("avg", 0),
                "type": "currency",
                "icon": "calculate"
            }
        ]

    elif chart_type == "bar":
        # 바 차트: 1위, 최하위, 평균, 범위, 평균 대비
        max_vs_avg = stats.get("max_vs_avg", 0)
        max_vs_avg_text = f"평균의 {max_vs_avg:.1f}배" if max_vs_avg > 0 else "-"

        items = [
            {
                "key": "rank_1",
                "label": "1위",
                "value": f"{stats.get('max_category', '')} ({fmt_currency(stats.get('max', 0))})",
                "type": "text",
                "highlight": True,
                "icon": "emoji_events"
            },
            {
                "key": "rank_last",
                "label": "최하위",
                "value": f"{stats.get('min_category', '')} ({fmt_currency(stats.get('min', 0))})",
                "type": "text",
                "icon": "trending_down"
            },
            {
                "key": "avg",
                "label": "평균",
                "value": stats.get("avg", 0),
                "type": "currency",
                "icon": "calculate"
            },
            {
                "key": "range",
                "label": "범위",
                "value": fmt_currency(stats.get("range", 0)),
                "type": "currency",
                "icon": "unfold_more"
            },
            {
                "key": "max_vs_avg",
                "label": "1위 vs 평균",
                "value": max_vs_avg_text,
                "type": "text",
                "icon": "compare_arrows"
            }
        ]

    return {"items": items, "source": "rule"}


def _apply_stats_template(
    template: List[Dict[str, Any]],
    stats: Dict[str, Any]
) -> Dict[str, Any]:
    """LLM 템플릿의 플레이스홀더를 실제 값으로 치환

    Args:
        template: LLM이 생성한 summaryStatsTemplate
        stats: 확장 통계 딕셔너리

    Returns:
        완성된 summaryStats 구조
    """
    import re

    if not template or not stats:
        return {"items": [], "source": "llm"}

    # 플레이스홀더 매핑
    placeholders = {
        "{count}": str(stats.get("count", "")),
        "{total}": f"₩{int(stats.get('total', 0)):,}" if stats.get("total") else "",
        "{avg}": f"₩{int(stats.get('avg', 0)):,}" if stats.get("avg") else "",
        "{max}": f"₩{int(stats.get('max', 0)):,}" if stats.get("max") else "",
        "{min}": f"₩{int(stats.get('min', 0)):,}" if stats.get("min") else "",
        "{maxCategory}": str(stats.get("max_category", "")),
        "{minCategory}": str(stats.get("min_category", "")),
        "{maxShare}": f"{stats.get('max_share', 0):.1f}%" if stats.get("max_share") else "",
        "{minShare}": f"{stats.get('min_share', 0):.1f}%" if stats.get("min_share") else "",
        "{concentration}": f"{stats.get('concentration', 0):.1f}%" if stats.get("concentration") else "",
        "{trend}": str(stats.get("trend", "")),
        "{growthRate}": f"{stats.get('growth_rate', 0):.1f}%" if stats.get("growth_rate") else "",
        "{peakTime}": str(stats.get("peak_time", "")),
        "{periodStart}": str(stats.get("period_start", "")),
        "{periodEnd}": str(stats.get("period_end", "")),
        "{range}": f"₩{int(stats.get('range', 0)):,}" if stats.get("range") else "",
        "{maxVsAvg}": f"{stats.get('max_vs_avg', 0):.1f}배" if stats.get("max_vs_avg") else "",
    }

    def substitute(text: str) -> str:
        if not isinstance(text, str):
            return text
        result = text
        for placeholder, value in placeholders.items():
            result = result.replace(placeholder, value)
        # 미치환 플레이스홀더 제거
        result = re.sub(r'\{[^}]+\}', '', result)
        return result.strip()

    items = []
    for item in template:
        new_item = {
            "key": item.get("key", ""),
            "label": item.get("label", ""),
            "value": substitute(str(item.get("value", ""))),
            "type": item.get("type", "text"),
        }
        if item.get("highlight"):
            new_item["highlight"] = True
        if item.get("icon"):
            new_item["icon"] = item.get("icon")
        items.append(new_item)

    return {"items": items, "source": "llm"}


def _generate_summary_stats(
    data: List[Dict[str, Any]],
    x_key: str,
    y_key: str,
    chart_type: str,
    template: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """차트 데이터에 대한 Summary Stats 생성

    LLM 템플릿 우선, 규칙 기반 폴백

    Args:
        data: 차트 데이터
        x_key: X축 필드 키
        y_key: Y축 필드 키
        chart_type: 차트 타입 (line, bar, pie)
        template: LLM이 생성한 summaryStatsTemplate (선택적)

    Returns:
        summaryStats 구조
    """
    if not data:
        return {"items": [], "source": "fallback"}

    # 확장 통계 계산
    stats = _calculate_extended_stats(data, x_key, y_key, chart_type)

    if not stats:
        return {"items": [], "source": "fallback"}

    # LLM 템플릿이 있으면 적용
    if template and isinstance(template, list) and len(template) > 0:
        result = _apply_stats_template(template, stats)
        logger.info(f"[SummaryStats] Generated from LLM template: {len(result.get('items', []))} items")
        return result

    # 폴백: 규칙 기반 생성
    result = _generate_rule_based_stats(stats, chart_type, x_key, y_key)
    logger.info(f"[SummaryStats] Generated from rules: {len(result.get('items', []))} items")
    return result


# ============================================
# SQL에서 테이블명 추출
# ============================================

def _extract_table_from_sql(sql: str) -> Optional[str]:
    """SQL FROM 절에서 테이블명 추출

    Args:
        sql: SQL 쿼리 문자열

    Returns:
        테이블명 또는 None
    """
    import re
    if not sql:
        return None

    # FROM 절에서 테이블명 추출 (정규식)
    # 지원 패턴: FROM table_name, FROM "table_name", FROM schema.table_name
    match = re.search(
        r'\bFROM\s+(?:")?([a-zA-Z_][a-zA-Z0-9_]*)(?:")?',
        sql,
        re.IGNORECASE
    )
    return match.group(1) if match else None


# ============================================
# 멀티 시리즈 통계 계산
# ============================================

def _calculate_multi_series_stats(
    chart_data: List[Dict[str, Any]],
    x_key: str,
    series_keys: List[str],
    chart_type: str
) -> Dict[str, Any]:
    """멀티 시리즈 차트의 확장 통계 계산 (피벗된 데이터 기준)

    각 시리즈별로 통계를 계산하고, 전체 합계도 계산합니다.
    피벗된 데이터를 사용하므로 그래프와 일치하는 통계를 제공합니다.

    Args:
        chart_data: 피벗된 데이터 (각 행에 x_key와 시리즈별 값이 있음)
        x_key: X축 키 (시계열)
        series_keys: 시리즈 키 리스트 (가맹점명 등)
        chart_type: 차트 타입 (line, bar, pie)

    Returns:
        확장 통계 딕셔너리
    """
    if not chart_data or not series_keys:
        return {}

    # 1. 각 X축 포인트별 전체 합계 계산
    x_axis_totals: List[Tuple[str, float]] = []
    for row in chart_data:
        x_val = str(row.get(x_key, ""))
        total = 0.0
        for sk in series_keys:
            val = row.get(sk, 0) or 0
            total += float(val)
        x_axis_totals.append((x_val, total))

    if not x_axis_totals:
        return {}

    # 2. 전체 통계 계산
    all_totals = [t[1] for t in x_axis_totals]
    grand_total = sum(all_totals)
    count = len(all_totals)
    avg = grand_total / count if count > 0 else 0
    max_val = max(all_totals)
    min_val = min(all_totals)

    # 피크 시점 (전체 합계가 가장 높은 X축 값)
    max_idx = all_totals.index(max_val)
    min_idx = all_totals.index(min_val)
    peak_time = x_axis_totals[max_idx][0]
    min_time = x_axis_totals[min_idx][0]

    stats = {
        "count": count,
        "total": grand_total,
        "avg": avg,
        "max": max_val,
        "min": min_val,
        "max_category": peak_time,
        "min_category": min_time,
        "max_idx": max_idx,
        "min_idx": min_idx,
        "peak_time": peak_time,
    }

    # 3. 기간 정보
    if count >= 2:
        stats["period_start"] = x_axis_totals[0][0]
        stats["period_end"] = x_axis_totals[-1][0]

    # 4. 성장률 계산 (전반부 vs 후반부)
    if count >= 2:
        mid = count // 2
        first_half_avg = sum(all_totals[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(all_totals[mid:]) / (count - mid)

        if first_half_avg > 0:
            growth_rate = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        else:
            growth_rate = 100 if second_half_avg > 0 else 0

        stats["growth_rate"] = growth_rate
        stats["trend"] = "증가" if growth_rate > 10 else ("감소" if growth_rate < -10 else "유지")

    # 5. 시리즈별 총합 (어느 시리즈가 가장 높은지)
    series_totals: Dict[str, float] = {sk: 0.0 for sk in series_keys}
    for row in chart_data:
        for sk in series_keys:
            val = row.get(sk, 0) or 0
            series_totals[sk] += float(val)

    top_series = max(series_totals.items(), key=lambda x: x[1])
    stats["top_series"] = top_series[0]
    stats["top_series_total"] = top_series[1]

    logger.info(
        f"[MultiSeriesStats] count={count}, total={grand_total:.0f}, "
        f"peak={peak_time}({max_val:.0f}), period={stats.get('period_start')}~{stats.get('period_end')}, "
        f"top_series={top_series[0]}"
    )

    return stats


def _generate_multi_series_summary_stats(
    chart_data: List[Dict[str, Any]],
    x_key: str,
    series_keys: List[str],
    chart_type: str,
    template: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """멀티 시리즈 차트의 Summary Stats 생성

    피벗된 데이터 기준으로 통계를 계산하여 그래프와 일치하는 정보 제공

    Args:
        chart_data: 피벗된 데이터
        x_key: X축 키
        series_keys: 시리즈 키 리스트
        chart_type: 차트 타입
        template: LLM 템플릿 (선택적)

    Returns:
        summaryStats 구조
    """
    if not chart_data:
        return {"items": [], "source": "fallback"}

    # 멀티 시리즈용 통계 계산
    stats = _calculate_multi_series_stats(chart_data, x_key, series_keys, chart_type)

    if not stats:
        return {"items": [], "source": "fallback"}

    # LLM 템플릿이 있으면 적용
    if template and isinstance(template, list) and len(template) > 0:
        result = _apply_stats_template(template, stats)
        logger.info(f"[MultiSeriesSummaryStats] Generated from LLM template: {len(result.get('items', []))} items")
        return result

    # 규칙 기반 생성 (멀티 시리즈 전용)
    items = []

    # 금액 포맷팅 함수
    def fmt_currency(val: float) -> str:
        if val >= 100000000:  # 억 단위
            return f"₩{val/100000000:.1f}억"
        elif val >= 10000:  # 만 단위
            return f"₩{val/10000:.0f}만"
        return f"₩{int(val):,}"

    def fmt_percent(val: float) -> str:
        return f"{val:.1f}%"

    # 추세
    trend = stats.get("trend", "유지")
    trend_icon = "trending_up" if trend == "증가" else ("trending_down" if trend == "감소" else "trending_flat")

    items.append({
        "key": "trend",
        "label": "전체 추세",
        "value": trend,
        "type": "trend",
        "highlight": True,
        "icon": trend_icon
    })

    # 피크 시점
    items.append({
        "key": "peak_time",
        "label": "피크 시점",
        "value": f"{stats.get('peak_time', '')} ({fmt_currency(stats.get('max', 0))})",
        "type": "text",
        "icon": "show_chart"
    })

    # 기간
    period_start = stats.get("period_start", "")
    period_end = stats.get("period_end", "")
    if period_start and period_end:
        items.append({
            "key": "period",
            "label": "기간",
            "value": f"{period_start} ~ {period_end}",
            "type": "text",
            "icon": "date_range"
        })

    # 평균
    items.append({
        "key": "avg",
        "label": "평균",
        "value": stats.get("avg", 0),
        "type": "currency",
        "icon": "calculate"
    })

    # 성장률
    growth_rate = stats.get("growth_rate")
    if growth_rate is not None:
        items.append({
            "key": "growth_rate",
            "label": "성장률",
            "value": fmt_percent(growth_rate),
            "type": "percentage",
            "icon": "speed"
        })

    logger.info(f"[MultiSeriesSummaryStats] Generated from rules: {len(items)} items")
    return {"items": items, "source": "rule"}


# ============================================
# 차트 RenderSpec 구성
# ============================================

def _compose_chart_render_spec(
    result: Dict[str, Any],
    question: str,
    llm_chart_type: Optional[str] = None,
    insight_template: Optional[str] = None,
    summary_stats_template: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """차트 타입의 RenderSpec 구성 (멀티 시리즈 지원)

    Args:
        result: SQL 실행 결과
        question: 사용자 질문
        llm_chart_type: LLM이 추천한 차트 타입 (우선 사용)
        insight_template: LLM이 생성한 인사이트 템플릿 (선택적)
        summary_stats_template: LLM이 생성한 summaryStats 템플릿 (선택적)

    Returns:
        차트 타입 RenderSpec (insight, summaryStats 필드 포함)
    """
    from datetime import datetime

    data = result.get("data", [])
    row_count = result.get("rowCount", 0)

    if not data:
        return {
            "type": "text",
            "title": "차트 생성 불가",
            "text": {
                "content": "조회 결과가 없어 차트를 생성할 수 없습니다.",
                "format": "plain"
            },
            "metadata": {
                "sql": result.get("sql"),
                "executionTimeMs": result.get("executionTimeMs"),
                "mode": "text_to_sql"
            }
        }

    columns = list(data[0].keys())

    # LLM 추천 차트 타입 우선 사용, 없으면 규칙 기반 폴백
    if llm_chart_type and llm_chart_type in ["line", "bar", "pie"]:
        chart_type = llm_chart_type
        logger.info(f"[ChartType] Using LLM recommendation: {chart_type}")
    else:
        # 폴백: 규칙 기반 로직 (개선 버전 - user_message 전달)
        chart_type = _detect_chart_type(data, columns, question)
        logger.info(f"[ChartType] Fallback to rule-based: {chart_type}")

    x_key, y_key = _identify_axis_keys(data, columns)

    # 멀티 시리즈 감지 (컬럼 목록 + 추이 키워드)
    ms_x_axis, ms_series_key, is_multi_series = _identify_multi_series_axis(
        columns, question
    )

    # 멀티 시리즈인 경우 데이터 피벗
    chart_data = data
    series_keys: List[str] = []
    if is_multi_series and ms_x_axis and ms_series_key:
        pivoted_data, series_keys = _pivot_data_for_multi_series(
            data,
            x_axis_key=ms_x_axis,
            series_key=ms_series_key,
            value_key=y_key
        )
        chart_data = pivoted_data
        x_key = ms_x_axis
        # 멀티 시리즈일 때 line 차트로 강제
        chart_type = "line"

    # X축 라벨 생성
    x_label = x_key.replace("_", " ").title()
    y_label = y_key.replace("_", " ").title()

    # 차트 타입별 제목
    chart_type_names = {
        "bar": "막대 그래프",
        "line": "추이 그래프",
        "pie": "파이 차트"
    }
    title = f"{chart_type_names.get(chart_type, '차트')} ({row_count}건)"

    render_spec = {
        "type": "chart",
        "title": title,
        "chart": {
            "chartType": chart_type,
            "dataRef": "data.rows",
            "xAxis": {
                "dataKey": x_key,
                "label": x_label,
                "type": "category" if chart_type != "line" else "time"
            },
            "yAxis": {
                "dataKey": y_key,
                "label": y_label,
                "type": "number"
            },
            "legend": True,
            "tooltip": True
        },
        "metadata": {
            "sql": result.get("sql"),
            "executionTimeMs": result.get("executionTimeMs"),
            "mode": "text_to_sql",
            "chartType": chart_type,
            "isMultiSeries": is_multi_series,
            "seriesKey": ms_series_key if is_multi_series else None
        }
    }

    # 멀티 시리즈 차트 설정
    if is_multi_series and series_keys:
        render_spec["chart"]["series"] = [
            {
                "dataKey": sk,
                "name": sk,
                "type": "line"
            }
            for sk in series_keys
        ]
        render_spec["data"] = chart_data
        logger.info(f"[MultiSeries SQL] Chart series configured: {series_keys}")
    elif chart_type == "pie":
        # pie 차트의 경우 series 대신 별도 설정
        render_spec["chart"]["series"] = [
            {
                "dataKey": y_key,
                "name": y_label
            }
        ]
        render_spec["data"] = data
    else:
        # 단일 시리즈
        render_spec["chart"]["series"] = [
            {
                "dataKey": y_key,
                "name": y_label,
                "type": chart_type if chart_type in ["bar", "line"] else "bar"
            }
        ]
        render_spec["data"] = data

    # 인사이트 생성 및 추가 (피벗된 데이터가 아닌 원본 데이터로)
    insight = _generate_insight(
        data=data,
        x_key=x_key,
        y_key=y_key,
        chart_type=chart_type,
        template=insight_template
    )
    render_spec["chart"]["insight"] = insight

    # Summary Stats 생성 및 추가
    # 멀티 시리즈인 경우 피벗된 데이터로 통계 계산 (그래프와 일치)
    if is_multi_series and series_keys:
        summary_stats = _generate_multi_series_summary_stats(
            chart_data=chart_data,  # 피벗된 데이터 사용
            x_key=x_key,
            series_keys=series_keys,
            chart_type=chart_type,
            template=summary_stats_template
        )
    else:
        # 단일 시리즈: 기존 로직
        summary_stats = _generate_summary_stats(
            data=data,
            x_key=x_key,
            y_key=y_key,
            chart_type=chart_type,
            template=summary_stats_template
        )
    render_spec["chart"]["summaryStats"] = summary_stats

    # Data Source 정보 추가 (SQL에서 테이블명 추출)
    table_name = _extract_table_from_sql(result.get("sql", ""))
    render_spec["chart"]["dataSource"] = {
        "table": table_name,
        "rowCount": row_count
    }

    return render_spec


# ============================================
# Markdown 테이블 변환
# ============================================

def _escape_markdown_table_cell(value: str) -> str:
    """Markdown 테이블 셀의 특수문자 escape 처리

    테이블이 깨지지 않도록 파이프(|), 백틱(`) 등 처리
    """
    if value is None:
        return "-"
    s = str(value)
    # 파이프 문자는 테이블 구분자와 충돌하므로 escape
    s = s.replace("|", "\\|")
    # 줄바꿈은 공백으로 대체
    s = s.replace("\n", " ").replace("\r", "")
    return s


def _format_aggregation_as_markdown_table(
    row: Dict[str, Any],
    aggregation_context: Optional[Dict[str, Any]] = None
) -> str:
    """집계 결과를 Markdown 테이블로 변환

    Args:
        row: 집계 결과 단일 행 (예: {"total_amount": 14477000, "fee": 86862})
        aggregation_context: 집계 컨텍스트 (humanizedFilters 포함)

    Returns:
        Markdown 형식 문자열
    """
    from decimal import Decimal

    # 컬럼명 -> 한글 라벨 매핑
    COLUMN_LABELS = {
        # SQL 집계 함수 결과명 (PostgreSQL 기본 반환명)
        "sum": "합계",
        "count": "건수",
        "avg": "평균",
        "max": "최대값",
        "min": "최소값",
        # 별칭을 가진 집계 결과
        "original_amount": "원금액",
        "fee": "수수료",
        "amount_excluding_fee": "수수료 제외 금액",
        "total_amount": "총 금액",
        "total_fee": "총 수수료",
        "avg_amount": "평균 금액",
        "average_amount": "평균 금액",
        "max_amount": "최대 금액",
        "min_amount": "최소 금액",
        "sum_amount": "합계 금액",
        "payment_count": "결제 건수",
        "refund_count": "환불 건수",
        "net_amount": "정산 금액",
        "total_payment_amount": "총 결제 금액",
        "total_refund_amount": "총 환불 금액",
        # LLM이 자주 생성하는 별칭
        "completed_payment_count": "완료 결제 건수",
        "total_payments": "총 결제 건수",
        "avg_payment": "평균 결제 금액",
        "canceled_count": "취소 건수",
        "failed_count": "실패 건수",
        "total_sales": "총 매출",
        "total_transactions": "총 거래 건수",
        # 일반 컬럼명
        "amount": "금액",
        "merchant_id": "가맹점 ID",
        "status": "상태",
        "method": "결제수단",
    }

    # 금액 관련 키워드 (통화 포맷팅 적용)
    AMOUNT_KEYWORDS = ["amount", "fee", "total", "sum", "price", "balance", "net"]

    def format_value(key: str, value) -> str:
        """값을 포맷팅 (금액은 통화 형식, 건수는 "건" 접미사)"""
        if value is None:
            return "-"

        # 숫자 타입 체크 (int, float, Decimal, 숫자 문자열)
        numeric_value = None
        if isinstance(value, (int, float, Decimal)):
            numeric_value = float(value)
        elif isinstance(value, str):
            try:
                numeric_value = float(value)
            except ValueError:
                pass

        if numeric_value is not None:
            int_val = int(numeric_value)
            # 금액 관련 필드면 통화 포맷
            if any(kw in key.lower() for kw in AMOUNT_KEYWORDS):
                return f"₩{int_val:,}"
            # count 필드면 "건" 접미사
            elif "count" in key.lower():
                return f"{int_val:,}건"
            else:
                return f"{int_val:,}"

        return _escape_markdown_table_cell(value)

    def get_label(key: str) -> str:
        """컬럼명을 한글 라벨로 변환"""
        if key in COLUMN_LABELS:
            return COLUMN_LABELS[key]
        # 스네이크 케이스를 공백으로 변환하고 Title Case 적용
        return key.replace("_", " ").title()

    # Markdown 테이블 생성
    lines = [
        "## 집계 결과\n",
        "| 항목 | 값 |",
        "|------|------|"
    ]

    for key, value in row.items():
        label = get_label(key)
        formatted = format_value(key, value)
        # escape 처리된 라벨과 값 사용
        safe_label = _escape_markdown_table_cell(label)
        lines.append(f"| {safe_label} | {formatted} |")

    # 구분선
    lines.append("\n---\n")

    # 조회 조건 (humanized 사용)
    if aggregation_context:
        humanized_filters = aggregation_context.get("humanizedFilters", [])
        based_on_filters = aggregation_context.get("basedOnFilters", [])

        # humanizedFilters 우선, 없으면 basedOnFilters 사용
        filters_to_show = humanized_filters if humanized_filters else based_on_filters

        if filters_to_show:
            lines.append("**조회 조건**")
            for filter_desc in filters_to_show:
                safe_filter = _escape_markdown_table_cell(filter_desc)
                lines.append(f"- {safe_filter}")
            lines.append("")

        # 기타 정보
        info_items = []
        source_count = aggregation_context.get("sourceRowCount")
        if source_count is not None:
            info_items.append(f"- 대상 데이터: {source_count:,}건")

        query_type = aggregation_context.get("queryType")
        if query_type:
            qtype_label = "새 쿼리 실행" if query_type == "NEW_QUERY" else "조건 추가"
            info_items.append(f"- 처리 방식: {qtype_label}")

        if info_items:
            lines.append("**기타 정보**")
            lines.extend(info_items)

    return "\n".join(lines)


# ============================================
# 메인 함수: SQL 실행 결과 -> RenderSpec
# ============================================

def compose_sql_render_spec(
    result: Dict[str, Any],
    question: str,
    llm_chart_type: Optional[str] = None,
    insight_template: Optional[str] = None,
    summary_stats_template: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """SQL 실행 결과를 RenderSpec으로 변환

    - 차트 요청: 차트 RenderSpec 반환 (TC-001)
    - 1000건 초과: 다운로드 RenderSpec (테이블 표시 안함)
    - 1000건 이하: 미리보기 10건 + 전체보기 모달

    Args:
        result: SQL 실행 결과
        question: 사용자 질문
        llm_chart_type: LLM이 추천한 차트 타입 (선택적)
        insight_template: LLM이 생성한 인사이트 템플릿 (선택적)
        summary_stats_template: LLM이 생성한 summaryStats 템플릿 (선택적)
    """
    # TC-001: 차트 렌더링 타입 감지
    # 사용자 키워드 기반 렌더링 타입 우선 감지
    render_type = _detect_render_type_from_message(question)

    # TC-001-1: 테이블 키워드 감지 시 LLM chartType 무시
    if render_type == "table":
        logger.info(f"[compose_sql_render_spec] User requested table, ignoring LLM chartType={llm_chart_type}")
        # 테이블 렌더링으로 진행 (아래 로직에서 처리)
    elif llm_chart_type and llm_chart_type in ["line", "bar", "pie"]:
        # LLM 차트 타입이 유효하면 차트 요청으로 처리
        logger.info(f"[compose_sql_render_spec] LLM chart type detected: {llm_chart_type}")
        return _compose_chart_render_spec(result, question, llm_chart_type, insight_template, summary_stats_template)
    elif render_type == "chart":
        # 메시지에서 차트 키워드 감지
        return _compose_chart_render_spec(result, question, llm_chart_type, insight_template, summary_stats_template)

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

    # 집계 컨텍스트 추출
    is_aggregation = result.get("isAggregation", False)
    aggregation_context = result.get("aggregationContext")

    # 단일 행 + 집계 결과처럼 보이면 Markdown 테이블로 표시
    if row_count == 1 and len(data[0]) <= 5:
        row = data[0]
        # Markdown 테이블 + 조회 조건 생성
        content = _format_aggregation_as_markdown_table(row, aggregation_context)

        return {
            "type": "text",
            "title": "집계 결과",
            "text": {
                "content": content,
                "format": "markdown"
            },
            "metadata": {
                "sql": result.get("sql"),
                "executionTimeMs": result.get("executionTimeMs"),
                "mode": "text_to_sql",
                "isAggregation": is_aggregation,
                "aggregationContext": aggregation_context
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
            # TC-004: 최상위 pagination 추가
            "pagination": {
                "totalRows": row_count,
                "totalPages": math.ceil(row_count / PREVIEW_LIMIT) if row_count > 0 else 1,
                "pageSize": PREVIEW_LIMIT,
                "hasMore": has_more
            },
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
