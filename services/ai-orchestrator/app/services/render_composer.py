"""
RenderComposerService: QueryResult를 RenderSpec으로 변환
UI에서 렌더링할 수 있는 명세를 생성
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# 엔티티별 컬럼 정의
ENTITY_COLUMNS = {
    "Order": [
        {"key": "orderId", "label": "주문 ID", "type": "number", "align": "center"},
        {"key": "customerId", "label": "고객 ID", "type": "number", "align": "center"},
        {"key": "orderDate", "label": "주문일시", "type": "date", "format": "YYYY-MM-DD HH:mm"},
        {"key": "totalAmount", "label": "주문금액", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "status", "label": "상태", "type": "string", "align": "center"},
        {"key": "paymentGateway", "label": "결제수단", "type": "string", "align": "center"}
    ],
    "Customer": [
        {"key": "customerId", "label": "고객 ID", "type": "number", "align": "center"},
        {"key": "name", "label": "이름", "type": "string"},
        {"key": "email", "label": "이메일", "type": "string"},
        {"key": "phone", "label": "전화번호", "type": "string"}
    ],
    "Product": [
        {"key": "productId", "label": "상품 ID", "type": "number", "align": "center"},
        {"key": "name", "label": "상품명", "type": "string"},
        {"key": "price", "label": "가격", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "category", "label": "카테고리", "type": "string"}
    ],
    "Inventory": [
        {"key": "inventoryId", "label": "재고 ID", "type": "number", "align": "center"},
        {"key": "productId", "label": "상품 ID", "type": "number", "align": "center"},
        {"key": "quantity", "label": "수량", "type": "number", "align": "right"},
        {"key": "warehouse", "label": "창고", "type": "string"}
    ],
    "PaymentLog": [
        {"key": "timestamp", "label": "시간", "type": "date", "format": "YYYY-MM-DD HH:mm:ss"},
        {"key": "level", "label": "레벨", "type": "string", "align": "center"},
        {"key": "orderId", "label": "주문 ID", "type": "number", "align": "center"},
        {"key": "message", "label": "메시지", "type": "string"},
        {"key": "errorCode", "label": "에러코드", "type": "string", "align": "center"}
    ]
}


class RenderComposerService:
    """
    QueryResult를 RenderSpec으로 변환하는 서비스
    데이터 형태에 따라 적절한 렌더링 타입을 결정
    """

    def compose(
        self,
        query_result: Dict[str, Any],
        query_plan: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """
        QueryResult를 RenderSpec으로 변환

        Args:
            query_result: Core API에서 반환된 쿼리 결과
            query_plan: 실행된 QueryPlan
            user_message: 원본 사용자 메시지

        Returns:
            RenderSpec 딕셔너리
        """
        logger.info(f"Composing RenderSpec for entity: {query_plan.get('entity')}")

        status = query_result.get("status", "error")

        if status == "error":
            return self._compose_error_spec(query_result, user_message)

        operation = query_plan.get("operation", "list")
        entity = query_plan.get("entity", "Order")

        if operation == "aggregate":
            return self._compose_aggregate_spec(query_result, query_plan, user_message)
        elif operation == "search":
            return self._compose_search_spec(query_result, query_plan, user_message)
        elif entity == "PaymentLog":
            return self._compose_log_spec(query_result, query_plan, user_message)
        else:
            return self._compose_table_spec(query_result, query_plan, user_message)

    def _compose_table_spec(
        self,
        query_result: Dict[str, Any],
        query_plan: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """테이블 형태의 RenderSpec 생성"""
        entity = query_plan.get("entity", "Order")
        data = query_result.get("data", {})
        rows = data.get("rows", [])
        metadata = query_result.get("metadata", {})
        pagination = query_result.get("pagination", {})

        # 엔티티에 맞는 컬럼 정의
        columns = ENTITY_COLUMNS.get(entity, self._infer_columns(rows))

        render_spec = {
            "type": "table",
            "title": self._generate_title(entity, len(rows)),
            "description": f"'{user_message}'에 대한 조회 결과입니다.",
            "table": {
                "columns": columns,
                "dataRef": "data.rows",
                "actions": [
                    {"label": "CSV 내보내기", "action": "export-csv", "icon": "download"},
                    {"label": "전체화면", "action": "fullscreen", "icon": "expand"}
                ],
                "pagination": {
                    "enabled": pagination.get("hasMore", False),
                    "type": "load-more",
                    "pageSize": query_plan.get("limit", 10)
                }
            },
            "data": data,
            "metadata": {
                "requestId": query_result.get("requestId"),
                "generatedAt": datetime.utcnow().isoformat() + "Z",
                "rowCount": len(rows),
                "executionTimeMs": metadata.get("executionTimeMs", 0)
            }
        }

        # 페이지네이션 토큰 추가
        if pagination.get("queryToken"):
            render_spec["pagination"] = {
                "queryToken": pagination["queryToken"],
                "hasMore": pagination.get("hasMore", False),
                "currentPage": pagination.get("currentPage", 1)
            }

        return render_spec

    def _compose_aggregate_spec(
        self,
        query_result: Dict[str, Any],
        query_plan: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """집계 결과를 차트 또는 텍스트 형태로 변환"""
        data = query_result.get("data", {})
        rows = data.get("rows", [])
        aggregations = data.get("aggregations", {})
        group_by = query_plan.get("groupBy", [])

        # 그룹화가 있으면 차트, 없으면 텍스트
        if group_by and len(rows) > 1:
            return self._compose_chart_spec(query_result, query_plan, user_message)
        else:
            return self._compose_text_spec(query_result, query_plan, user_message)

    def _compose_chart_spec(
        self,
        query_result: Dict[str, Any],
        query_plan: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """차트 형태의 RenderSpec 생성"""
        data = query_result.get("data", {})
        rows = data.get("rows", [])
        group_by = query_plan.get("groupBy", [])
        aggregations = query_plan.get("aggregations", [])

        # 첫 번째 그룹화 필드를 X축으로
        x_axis_key = group_by[0] if group_by else "category"

        # 첫 번째 집계 결과를 Y축으로
        y_axis_key = "count"
        if aggregations:
            first_agg = aggregations[0]
            y_axis_key = first_agg.get("alias") or f"{first_agg['function']}_{first_agg['field']}"

        return {
            "type": "chart",
            "title": f"'{user_message}' 분석 결과",
            "description": "집계 결과를 시각화한 차트입니다.",
            "chart": {
                "chartType": "bar",
                "dataRef": "data.rows",
                "xAxis": {
                    "dataKey": x_axis_key,
                    "label": x_axis_key,
                    "type": "category"
                },
                "yAxis": {
                    "dataKey": y_axis_key,
                    "label": y_axis_key,
                    "type": "number"
                },
                "legend": True,
                "tooltip": True
            },
            "data": data,
            "metadata": {
                "requestId": query_result.get("requestId"),
                "generatedAt": datetime.utcnow().isoformat() + "Z"
            }
        }

    def _compose_text_spec(
        self,
        query_result: Dict[str, Any],
        query_plan: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """텍스트 형태의 RenderSpec 생성 (단일 집계 결과)"""
        data = query_result.get("data", {})
        aggregations = data.get("aggregations", data.get("rows", [{}])[0] if data.get("rows") else {})

        # 집계 결과를 마크다운으로 포맷팅
        content_lines = [f"## '{user_message}' 결과\n"]

        for key, value in aggregations.items():
            if value is not None:
                formatted_value = self._format_value(value)
                content_lines.append(f"- **{key}**: {formatted_value}")

        return {
            "type": "text",
            "title": "분석 결과",
            "text": {
                "content": "\n".join(content_lines),
                "format": "markdown"
            },
            "data": data,
            "metadata": {
                "requestId": query_result.get("requestId"),
                "generatedAt": datetime.utcnow().isoformat() + "Z"
            }
        }

    def _compose_log_spec(
        self,
        query_result: Dict[str, Any],
        query_plan: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """로그 뷰어 형태의 RenderSpec 생성"""
        data = query_result.get("data", {})
        rows = data.get("rows", [])
        filters = query_plan.get("filters", [])

        # 하이라이트할 키워드 추출
        highlight_keywords = []
        for f in filters:
            if f.get("field") == "message" and f.get("operator") == "like":
                highlight_keywords.append(str(f.get("value", "")))

        return {
            "type": "log",
            "title": f"결제 로그 조회 결과 ({len(rows)}건)",
            "description": f"'{user_message}'에 해당하는 로그입니다.",
            "log": {
                "dataRef": "data.rows",
                "timestampKey": "timestamp",
                "levelKey": "level",
                "messageKey": "message",
                "highlight": highlight_keywords,
                "filter": {
                    "levels": ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"],
                    "searchable": True
                }
            },
            "data": data,
            "metadata": {
                "requestId": query_result.get("requestId"),
                "generatedAt": datetime.utcnow().isoformat() + "Z",
                "rowCount": len(rows)
            }
        }

    def _compose_search_spec(
        self,
        query_result: Dict[str, Any],
        query_plan: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """검색 결과 RenderSpec (테이블과 유사하지만 하이라이트 포함)"""
        # 기본적으로 테이블 형태 사용
        spec = self._compose_table_spec(query_result, query_plan, user_message)
        spec["title"] = f"검색 결과: '{user_message}'"
        return spec

    def _compose_error_spec(
        self,
        query_result: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """에러 발생 시 RenderSpec 생성"""
        error = query_result.get("error", {})

        return {
            "type": "text",
            "title": "오류 발생",
            "text": {
                "content": f"## 쿼리 실행 중 오류가 발생했습니다\n\n"
                          f"- **에러 코드**: {error.get('code', 'UNKNOWN')}\n"
                          f"- **메시지**: {error.get('message', '알 수 없는 오류')}\n\n"
                          f"요청하신 내용: '{user_message}'",
                "format": "markdown",
                "sections": [
                    {
                        "type": "error",
                        "title": "오류 정보",
                        "content": error.get("message", "알 수 없는 오류가 발생했습니다.")
                    }
                ]
            },
            "metadata": {
                "requestId": query_result.get("requestId"),
                "generatedAt": datetime.utcnow().isoformat() + "Z"
            }
        }

    def _generate_title(self, entity: str, row_count: int) -> str:
        """엔티티에 맞는 제목 생성"""
        entity_names = {
            "Order": "주문",
            "Customer": "고객",
            "Product": "상품",
            "Inventory": "재고",
            "PaymentLog": "결제 로그"
        }
        name = entity_names.get(entity, entity)
        return f"{name} 목록 ({row_count}건)"

    def _infer_columns(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """데이터에서 컬럼 정의 추론"""
        if not rows:
            return []

        columns = []
        first_row = rows[0]

        for key, value in first_row.items():
            col = {
                "key": key,
                "label": key,
                "type": self._infer_type(value)
            }
            columns.append(col)

        return columns

    def _infer_type(self, value: Any) -> str:
        """값에서 타입 추론"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "number"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            # 날짜 형식 체크
            if "T" in value and ("Z" in value or "+" in value):
                return "date"
            return "string"
        else:
            return "string"

    def _format_value(self, value: Any) -> str:
        """값을 표시용 문자열로 포맷팅"""
        if isinstance(value, float):
            return f"{value:,.2f}"
        elif isinstance(value, int):
            return f"{value:,}"
        else:
            return str(value)


# 싱글톤 인스턴스
_render_composer_instance: Optional[RenderComposerService] = None


def get_render_composer() -> RenderComposerService:
    """RenderComposerService 싱글톤 인스턴스 반환"""
    global _render_composer_instance
    if _render_composer_instance is None:
        _render_composer_instance = RenderComposerService()
    return _render_composer_instance
