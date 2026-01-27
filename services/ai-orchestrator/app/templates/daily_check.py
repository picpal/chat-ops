"""
일일점검 템플릿 모듈

고정된 형식의 일일점검 대시보드 생성
- 쿼리 템플릿: 5개 (오늘 요약, 상태 분포, 환불, 전일 비교, 오류/실패)
- RenderSpec 템플릿: Composite (Table + Pie Chart)
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List


def get_daily_check_queries(target_date: str = None) -> List[Dict[str, Any]]:
    """
    일일점검용 QueryPlan 목록 반환

    Args:
        target_date: 점검 대상 날짜 (YYYY-MM-DD). None이면 오늘

    Returns:
        5개의 QueryPlan 딕셔너리 리스트
    """
    today = target_date or datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (datetime.strptime(today, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    # ISO 8601 형식 시간 범위
    today_start = f"{today}T00:00:00Z"
    today_end = f"{tomorrow}T00:00:00Z"
    yesterday_start = f"{yesterday}T00:00:00Z"
    yesterday_end = f"{today}T00:00:00Z"

    return [
        # 1. 오늘 거래 요약
        {
            "entity": "Payment",
            "operation": "aggregate",
            "timeRange": {"start": today_start, "end": today_end},
            "aggregations": [
                {"function": "count", "field": "paymentKey", "alias": "todayCount"},
                {"function": "sum", "field": "amount", "alias": "todayAmount"}
            ]
        },
        # 2. 상태별 분포
        {
            "entity": "Payment",
            "operation": "aggregate",
            "timeRange": {"start": today_start, "end": today_end},
            "groupBy": ["status"],
            "aggregations": [
                {"function": "count", "field": "paymentKey", "alias": "count"}
            ]
        },
        # 3. 환불 현황
        {
            "entity": "Refund",
            "operation": "aggregate",
            "timeRange": {"start": today_start, "end": today_end},
            "aggregations": [
                {"function": "count", "field": "refundKey", "alias": "refundCount"},
                {"function": "sum", "field": "amount", "alias": "refundAmount"}
            ]
        },
        # 4. 전일 거래 (비교용)
        {
            "entity": "Payment",
            "operation": "aggregate",
            "timeRange": {"start": yesterday_start, "end": yesterday_end},
            "aggregations": [
                {"function": "count", "field": "paymentKey", "alias": "yesterdayCount"},
                {"function": "sum", "field": "amount", "alias": "yesterdayAmount"}
            ]
        },
        # 5. 오류/실패 건 (ABORTED 상태)
        {
            "entity": "Payment",
            "operation": "aggregate",
            "timeRange": {"start": today_start, "end": today_end},
            "filters": [
                {"field": "status", "operator": "eq", "value": "ABORTED"}
            ],
            "aggregations": [
                {"function": "count", "field": "paymentKey", "alias": "errorCount"},
                {"function": "sum", "field": "amount", "alias": "errorAmount"}
            ]
        }
    ]


def compose_daily_check_render_spec(
    results: List[Dict[str, Any]],
    target_date: str,
    user_message: str
) -> Dict[str, Any]:
    """
    일일점검 결과를 Composite RenderSpec으로 변환
    """
    # 결과 파싱
    today_summary = _safe_get_first_row(results[0])
    status_dist = _safe_get_rows(results[1])
    refund_summary = _safe_get_first_row(results[2])
    yesterday_summary = _safe_get_first_row(results[3])
    error_summary = _safe_get_first_row(results[4]) if len(results) > 4 else {}

    # 지표 계산
    metrics = _calculate_metrics(today_summary, yesterday_summary, refund_summary, error_summary)

    return {
        "type": "composite",
        "title": f"일일점검 대시보드 ({target_date})",
        "description": f"'{user_message}'에 대한 결과입니다.",
        "components": [
            _build_summary_table_component(metrics),
            _build_status_chart_component(status_dist)
        ],
        "metadata": {
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "checkDate": target_date,
            "intent": "daily_check",
            "templateVersion": "1.0"
        }
    }


def get_daily_check_context(metrics: Dict, status_dist: List[Dict], target_date: str) -> Dict:
    """꼬리질문 지원을 위한 컨텍스트 생성"""
    return {
        "type": "daily_check_result",
        "targetDate": target_date,
        "metrics": {
            "todayCount": metrics.get("todayCount", 0),
            "todayAmount": metrics.get("todayAmount", 0),
            "statusDistribution": status_dist,
            "refundCount": metrics.get("refundCount", 0),
            "errorCount": metrics.get("errorCount", 0)
        },
        "availableFilters": [
            {"field": "status", "options": ["DONE", "CANCELED", "PENDING", "IN_PROGRESS", "ABORTED"]},
            {"field": "created_at", "value": target_date}
        ]
    }


# ============================================
# 내부 헬퍼 함수
# ============================================

def _safe_get_first_row(result: Dict) -> Dict:
    """결과에서 첫 번째 행 안전하게 추출"""
    rows = result.get("data", {}).get("rows", [])
    return rows[0] if rows else {}


def _safe_get_rows(result: Dict) -> List[Dict]:
    """결과에서 모든 행 추출"""
    return result.get("data", {}).get("rows", [])


def _calculate_metrics(today: Dict, yesterday: Dict, refund: Dict, error: Dict = None) -> Dict:
    """지표 계산"""
    today_count = today.get("todayCount", 0) or 0
    yesterday_count = yesterday.get("yesterdayCount", 0) or 0
    today_amount = today.get("todayAmount", 0) or 0
    yesterday_amount = yesterday.get("yesterdayAmount", 0) or 0
    refund_count = refund.get("refundCount", 0) or 0
    refund_amount = refund.get("refundAmount", 0) or 0
    error_count = (error.get("errorCount", 0) or 0) if error else 0
    error_amount = (error.get("errorAmount", 0) or 0) if error else 0

    count_change = ((today_count - yesterday_count) / max(yesterday_count, 1)) * 100
    amount_change = ((today_amount - yesterday_amount) / max(yesterday_amount, 1)) * 100
    refund_rate = (refund_count / max(today_count, 1)) * 100
    error_rate = (error_count / max(today_count, 1)) * 100

    return {
        "todayCount": today_count,
        "todayAmount": today_amount,
        "countChange": count_change,
        "amountChange": amount_change,
        "refundCount": refund_count,
        "refundAmount": refund_amount,
        "refundRate": refund_rate,
        "errorCount": error_count,
        "errorAmount": error_amount,
        "errorRate": error_rate
    }


def _build_summary_table_component(metrics: Dict) -> Dict:
    """핵심 지표 테이블 컴포넌트 생성"""
    refund_status = "정상" if metrics["refundRate"] < 5 else "주의"
    error_status = "정상" if metrics["errorRate"] < 3 else "주의"

    # 전일 대비 변화율 포맷팅
    count_change = f"{metrics['countChange']:+.1f}%"
    amount_change = f"{metrics['amountChange']:+.1f}%"

    return {
        "type": "table",
        "title": "오늘의 핵심 지표",
        "table": {
            "columns": [
                {"key": "metric", "label": "지표", "width": 120},
                {"key": "today", "label": "오늘", "width": 150, "align": "right"},
                {"key": "change", "label": "비고", "width": 100, "align": "right"}
            ],
            "data": [
                {"metric": "거래 건수", "today": f"{metrics['todayCount']:,}건", "change": count_change},
                {"metric": "거래 금액", "today": f"₩{metrics['todayAmount']:,.0f}", "change": amount_change},
                {"metric": "환불 건수", "today": f"{metrics['refundCount']:,}건", "change": "-"},
                {"metric": "환불율", "today": f"{metrics['refundRate']:.1f}%", "change": refund_status},
                {"metric": "오류/실패 건수", "today": f"{metrics['errorCount']:,}건", "change": "-"},
                {"metric": "오류율", "today": f"{metrics['errorRate']:.1f}%", "change": error_status}
            ]
        }
    }


def _build_status_chart_component(status_dist: List[Dict]) -> Dict:
    """상태별 분포 차트 컴포넌트 생성"""
    # 파이 차트용 summaryStats 계산
    total = sum(row.get("count", 0) for row in status_dist)
    sorted_dist = sorted(status_dist, key=lambda x: x.get("count", 0), reverse=True)
    max_item = sorted_dist[0] if sorted_dist else {}
    min_item = sorted_dist[-1] if sorted_dist else {}

    max_status = max_item.get("status", "-")
    max_count = max_item.get("count", 0)
    max_pct = (max_count / total * 100) if total > 0 else 0

    min_status = min_item.get("status", "-")
    min_count = min_item.get("count", 0)
    min_pct = (min_count / total * 100) if total > 0 else 0

    return {
        "type": "chart",
        "title": "상태별 분포",
        "chart": {
            "chartType": "pie",
            "xAxis": {"dataKey": "status"},
            "yAxis": {"dataKey": "count"},
            "summaryStats": {
                "source": "rule",
                "items": [
                    {"key": "total", "label": "총 건수", "value": total, "type": "number"},
                    {"key": "max_share", "label": "최다 상태", "value": f"{max_status} ({max_pct:.0f}%)", "type": "text", "highlight": True},
                    {"key": "min_share", "label": "최소 상태", "value": f"{min_status} ({min_pct:.0f}%)", "type": "text"},
                    {"key": "categories", "label": "상태 수", "value": f"{len(status_dist)}개", "type": "text"}
                ]
            }
        },
        "data": {
            "rows": status_dist
        }
    }
