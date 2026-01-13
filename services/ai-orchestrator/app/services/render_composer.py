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
    # ============================================
    # 기존 e-commerce 엔티티
    # ============================================
    "Order": [
        {"key": "order_id", "label": "주문 ID", "type": "number", "align": "center"},
        {"key": "customer_id", "label": "고객 ID", "type": "number", "align": "center"},
        {"key": "order_date", "label": "주문일시", "type": "date", "format": "YYYY-MM-DD HH:mm"},
        {"key": "total_amount", "label": "주문금액", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "status", "label": "상태", "type": "string", "align": "center"},
        {"key": "payment_gateway", "label": "결제수단", "type": "string", "align": "center"}
    ],
    "Customer": [
        {"key": "customer_id", "label": "고객 ID", "type": "number", "align": "center"},
        {"key": "name", "label": "이름", "type": "string"},
        {"key": "email", "label": "이메일", "type": "string"},
        {"key": "phone", "label": "전화번호", "type": "string"}
    ],
    "Product": [
        {"key": "product_id", "label": "상품 ID", "type": "number", "align": "center"},
        {"key": "name", "label": "상품명", "type": "string"},
        {"key": "price", "label": "가격", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "category", "label": "카테고리", "type": "string"}
    ],
    "Inventory": [
        {"key": "inventory_id", "label": "재고 ID", "type": "number", "align": "center"},
        {"key": "product_id", "label": "상품 ID", "type": "number", "align": "center"},
        {"key": "quantity", "label": "수량", "type": "number", "align": "right"},
        {"key": "warehouse", "label": "창고", "type": "string"}
    ],
    "PaymentLog": [
        {"key": "timestamp", "label": "시간", "type": "date", "format": "YYYY-MM-DD HH:mm:ss"},
        {"key": "level", "label": "레벨", "type": "string", "align": "center"},
        {"key": "order_id", "label": "주문 ID", "type": "number", "align": "center"},
        {"key": "message", "label": "메시지", "type": "string"},
        {"key": "error_code", "label": "에러코드", "type": "string", "align": "center"}
    ],
    # ============================================
    # PG 결제 도메인 엔티티
    # ============================================
    "Payment": [
        {"key": "payment_key", "label": "결제키", "type": "string", "width": "120px"},
        {"key": "order_id", "label": "주문번호", "type": "string"},
        {"key": "merchant_id", "label": "가맹점ID", "type": "string"},
        {"key": "order_name", "label": "주문명", "type": "string"},
        {"key": "amount", "label": "결제금액", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "method", "label": "결제수단", "type": "string", "align": "center"},
        {"key": "status", "label": "상태", "type": "string", "align": "center"},
        {"key": "approved_at", "label": "승인시간", "type": "date", "format": "YYYY-MM-DD HH:mm:ss"},
        {"key": "created_at", "label": "생성시간", "type": "date", "format": "YYYY-MM-DD HH:mm:ss"}
    ],
    "Merchant": [
        {"key": "merchant_id", "label": "가맹점ID", "type": "string"},
        {"key": "business_name", "label": "사업체명", "type": "string"},
        {"key": "business_number", "label": "사업자번호", "type": "string"},
        {"key": "representative_name", "label": "대표자", "type": "string"},
        {"key": "status", "label": "상태", "type": "string", "align": "center"},
        {"key": "fee_rate", "label": "수수료율", "type": "percentage", "format": "0.00%", "align": "right"},
        {"key": "settlement_cycle", "label": "정산주기", "type": "string", "align": "center"},
        {"key": "created_at", "label": "등록일", "type": "date", "format": "YYYY-MM-DD"}
    ],
    "PgCustomer": [
        {"key": "customer_id", "label": "고객ID", "type": "string"},
        {"key": "merchant_id", "label": "가맹점ID", "type": "string"},
        {"key": "name", "label": "고객명", "type": "string"},
        {"key": "email", "label": "이메일", "type": "string"},
        {"key": "phone", "label": "전화번호", "type": "string"},
        {"key": "created_at", "label": "등록일", "type": "date", "format": "YYYY-MM-DD"}
    ],
    "PaymentMethod": [
        {"key": "payment_method_id", "label": "결제수단ID", "type": "string"},
        {"key": "customer_id", "label": "고객ID", "type": "string"},
        {"key": "type", "label": "유형", "type": "string", "align": "center"},
        {"key": "card_company", "label": "카드사", "type": "string"},
        {"key": "card_number_masked", "label": "카드번호", "type": "string"},
        {"key": "status", "label": "상태", "type": "string", "align": "center"},
        {"key": "is_default", "label": "기본", "type": "boolean", "align": "center"},
        {"key": "created_at", "label": "등록일", "type": "date", "format": "YYYY-MM-DD"}
    ],
    "PaymentHistory": [
        {"key": "history_id", "label": "이력ID", "type": "number", "align": "center"},
        {"key": "payment_key", "label": "결제키", "type": "string"},
        {"key": "previous_status", "label": "이전상태", "type": "string", "align": "center"},
        {"key": "new_status", "label": "변경상태", "type": "string", "align": "center"},
        {"key": "reason", "label": "사유", "type": "string"},
        {"key": "processed_by", "label": "처리자", "type": "string"},
        {"key": "created_at", "label": "변경시간", "type": "date", "format": "YYYY-MM-DD HH:mm:ss"}
    ],
    "Refund": [
        {"key": "refund_key", "label": "환불키", "type": "string"},
        {"key": "payment_key", "label": "원결제키", "type": "string"},
        {"key": "amount", "label": "환불금액", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "reason", "label": "환불사유", "type": "string"},
        {"key": "status", "label": "상태", "type": "string", "align": "center"},
        {"key": "approved_at", "label": "승인시간", "type": "date", "format": "YYYY-MM-DD HH:mm:ss"},
        {"key": "created_at", "label": "요청시간", "type": "date", "format": "YYYY-MM-DD HH:mm:ss"}
    ],
    "BalanceTransaction": [
        {"key": "transaction_id", "label": "거래ID", "type": "string"},
        {"key": "merchant_id", "label": "가맹점ID", "type": "string"},
        {"key": "source_type", "label": "유형", "type": "string", "align": "center"},
        {"key": "amount", "label": "금액", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "fee", "label": "수수료", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "net", "label": "순금액", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "balance_after", "label": "잔액", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "status", "label": "상태", "type": "string", "align": "center"},
        {"key": "created_at", "label": "거래시간", "type": "date", "format": "YYYY-MM-DD HH:mm:ss"}
    ],
    "Settlement": [
        {"key": "settlement_id", "label": "정산ID", "type": "string"},
        {"key": "merchant_id", "label": "가맹점ID", "type": "string"},
        {"key": "settlement_date", "label": "정산일", "type": "date", "format": "YYYY-MM-DD"},
        {"key": "period_start", "label": "기간시작", "type": "date", "format": "YYYY-MM-DD"},
        {"key": "period_end", "label": "기간종료", "type": "date", "format": "YYYY-MM-DD"},
        {"key": "total_payment_amount", "label": "총결제", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "total_refund_amount", "label": "총환불", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "total_fee", "label": "수수료", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "net_amount", "label": "정산금액", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "payment_count", "label": "결제건수", "type": "number", "align": "right"},
        {"key": "status", "label": "상태", "type": "string", "align": "center"}
    ],
    "SettlementDetail": [
        {"key": "detail_id", "label": "상세ID", "type": "string"},
        {"key": "settlement_id", "label": "정산ID", "type": "string"},
        {"key": "payment_key", "label": "결제키", "type": "string"},
        {"key": "amount", "label": "금액", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "fee", "label": "수수료", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "net_amount", "label": "정산금액", "type": "currency", "format": "currency:KRW", "align": "right"},
        {"key": "type", "label": "유형", "type": "string", "align": "center"}
    ]
}


class RenderComposerService:
    """
    QueryResult를 RenderSpec으로 변환하는 서비스
    데이터 형태에 따라 적절한 렌더링 타입을 결정
    """

    def _detect_render_type_from_message(self, message: str) -> Optional[str]:
        """
        사용자 메시지에서 명시적 렌더링 타입 요청 감지 (하드코딩)

        LLM 판단보다 확실한 키워드 매칭으로 100% 정확도 보장
        """
        msg = message.lower()

        # 표/테이블 요청
        if any(kw in msg for kw in ["표로", "테이블로", "목록으로", "리스트로", "표 형태", "테이블 형태"]):
            return "table"

        # 차트/그래프 요청
        if any(kw in msg for kw in ["그래프로", "차트로", "시각화로", "그래프 형태", "차트 형태"]):
            return "chart"

        # 텍스트 요청
        if any(kw in msg for kw in ["텍스트로", "글로", "요약으로"]):
            return "text"

        return None

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

        # 1순위: 사용자 메시지에서 직접 감지 (하드코딩 - 100% 정확)
        detected_render_type = self._detect_render_type_from_message(user_message)
        if detected_render_type:
            logger.info(f"Detected render type from message: {detected_render_type}")
            if detected_render_type == "table":
                return self._compose_table_spec(query_result, query_plan, user_message)
            elif detected_render_type == "chart":
                return self._compose_chart_spec(query_result, query_plan, user_message)
            elif detected_render_type == "text":
                return self._compose_text_spec(query_result, query_plan, user_message)

        # 2순위: LLM이 설정한 preferredRenderType
        preferred_render_type = query_plan.get("preferredRenderType")
        if preferred_render_type:
            logger.info(f"Using LLM preferred render type: {preferred_render_type}")
            if preferred_render_type == "table":
                return self._compose_table_spec(query_result, query_plan, user_message)
            elif preferred_render_type == "chart":
                return self._compose_chart_spec(query_result, query_plan, user_message)
            elif preferred_render_type == "text":
                return self._compose_text_spec(query_result, query_plan, user_message)

        # 3순위: 기존 자동 결정 로직
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

    def _determine_chart_type(
        self,
        query_plan: Dict[str, Any],
        rows: List[Dict[str, Any]],
        user_message: str
    ) -> str:
        """쿼리 결과와 사용자 의도에 따라 최적 차트 타입 결정"""
        group_by = query_plan.get("groupBy", [])
        time_range = query_plan.get("timeRange")
        message_lower = user_message.lower()

        # 비율/점유율 관련 키워드 → pie chart
        if any(kw in message_lower for kw in ["비율", "점유율", "분포", "비중", "퍼센트", "%"]):
            return "pie"

        # 시계열 데이터 (날짜 기준 그룹화) → line chart
        date_fields = ["approvedAt", "createdAt", "settlementDate", "timestamp", "orderDate", "updatedAt"]
        if group_by and any(field in group_by for field in date_fields):
            return "line"

        # timeRange가 있고 추이/추세 키워드 → line chart
        if time_range and any(kw in message_lower for kw in ["추이", "추세", "변화", "trend", "일별", "월별", "주별"]):
            return "line"

        # 상태별, 결제수단별 등 카테고리 그룹화 → bar chart
        category_fields = ["status", "method", "merchantId", "type", "level", "sourceType"]
        if group_by and any(field in group_by for field in category_fields):
            # 상태별 비율 관련 질문이면 pie
            if "status" in group_by and any(kw in message_lower for kw in ["현황", "통계"]):
                return "pie"
            return "bar"

        # 데이터 포인트가 적으면 (5개 이하) → bar, 많으면 → line
        if len(rows) <= 5:
            return "bar"

        return "line"  # 기본값

    def _is_date_field(self, field: str) -> bool:
        """날짜 필드 여부 확인"""
        date_fields = [
            "approvedAt", "createdAt", "updatedAt", "settlementDate",
            "timestamp", "periodStart", "periodEnd", "orderDate"
        ]
        return field in date_fields

    def _get_axis_label(self, field: str) -> str:
        """필드명을 사용자 친화적 레이블로 변환"""
        labels = {
            "status": "상태",
            "method": "결제수단",
            "merchantId": "가맹점",
            "approvedAt": "승인일시",
            "createdAt": "생성일시",
            "settlementDate": "정산일",
            "count": "건수",
            "totalAmount": "총금액",
            "paymentCount": "결제건수",
            "amount": "금액",
            "netAmount": "정산금액",
            "totalPaymentAmount": "총결제금액",
            "totalRefundAmount": "총환불금액",
            "totalFee": "총수수료",
            "sourceType": "거래유형",
            "type": "유형",
            "level": "로그레벨"
        }
        return labels.get(field, field)

    def _get_series_name(self, aggregation: Dict[str, Any]) -> str:
        """집계 정보를 시리즈 이름으로 변환"""
        func = aggregation.get("function", "")
        field = aggregation.get("field", "")
        alias = aggregation.get("alias")

        if alias:
            return self._get_axis_label(alias)

        names = {
            ("count", "*"): "건수",
            ("sum", "amount"): "총금액",
            ("avg", "amount"): "평균금액",
            ("max", "amount"): "최대금액",
            ("min", "amount"): "최소금액",
            ("sum", "totalAmount"): "총금액",
            ("sum", "netAmount"): "정산금액",
        }
        return names.get((func, field), f"{func}({field})")

    def _generate_chart_title(self, query_plan: Dict[str, Any], user_message: str) -> str:
        """차트 제목 생성"""
        entity = query_plan.get("entity", "")
        group_by = query_plan.get("groupBy", [])

        entity_names = {
            "Payment": "결제",
            "Refund": "환불",
            "Settlement": "정산",
            "Merchant": "가맹점",
            "BalanceTransaction": "잔액거래",
            "PaymentHistory": "결제이력",
            "Order": "주문"
        }
        entity_name = entity_names.get(entity, entity)

        if group_by:
            group_labels = {
                "status": "상태별",
                "method": "결제수단별",
                "merchantId": "가맹점별",
                "approvedAt": "일별",
                "createdAt": "일별",
                "settlementDate": "일별",
                "sourceType": "유형별",
                "type": "유형별"
            }
            group_name = group_labels.get(group_by[0], "")
            return f"{group_name} {entity_name} 현황"

        return f"{entity_name} 분석 결과"

    def _compose_chart_spec(
        self,
        query_result: Dict[str, Any],
        query_plan: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """향상된 차트 형태의 RenderSpec 생성"""
        data = query_result.get("data", {})
        rows = data.get("rows", [])
        group_by = query_plan.get("groupBy", [])
        aggregations = query_plan.get("aggregations", [])

        # 차트 타입 자동 결정
        chart_type = self._determine_chart_type(query_plan, rows, user_message)

        # X축/Y축 키 설정
        x_axis_key = group_by[0] if group_by else "category"
        y_axis_key = "count"

        if aggregations:
            first_agg = aggregations[0]
            y_axis_key = first_agg.get("alias") or f"{first_agg['function']}_{first_agg['field']}"

        # 차트 타입별 설정
        chart_config: Dict[str, Any] = {
            "chartType": chart_type,
            "dataRef": "data.rows",
            "legend": True,
            "tooltip": True
        }

        if chart_type == "pie":
            # Pie 차트는 nameKey와 valueKey 사용
            chart_config["nameKey"] = x_axis_key
            chart_config["valueKey"] = y_axis_key
        else:
            # Line/Bar 차트는 axis 설정
            chart_config["xAxis"] = {
                "dataKey": x_axis_key,
                "label": self._get_axis_label(x_axis_key),
                "type": "time" if self._is_date_field(x_axis_key) else "category"
            }
            chart_config["yAxis"] = {
                "dataKey": y_axis_key,
                "label": self._get_axis_label(y_axis_key),
                "type": "number"
            }

            # 다중 시리즈 지원 (여러 집계가 있는 경우)
            if len(aggregations) > 1:
                chart_config["series"] = [
                    {
                        "dataKey": agg.get("alias") or f"{agg['function']}_{agg['field']}",
                        "name": self._get_series_name(agg),
                        "type": "line" if chart_type == "line" else "bar"
                    }
                    for agg in aggregations
                ]

        return {
            "type": "chart",
            "title": self._generate_chart_title(query_plan, user_message),
            "description": f"'{user_message}' 분석 결과입니다.",
            "chart": chart_config,
            "data": data,
            "metadata": {
                "requestId": query_result.get("requestId"),
                "generatedAt": datetime.utcnow().isoformat() + "Z",
                "chartType": chart_type
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
            # 기존 e-commerce 엔티티
            "Order": "주문",
            "Customer": "고객",
            "Product": "상품",
            "Inventory": "재고",
            "PaymentLog": "결제 로그",
            # PG 결제 도메인 엔티티
            "Payment": "결제",
            "Merchant": "가맹점",
            "PgCustomer": "PG 고객",
            "PaymentMethod": "결제수단",
            "PaymentHistory": "결제 이력",
            "Refund": "환불",
            "BalanceTransaction": "잔액 거래",
            "Settlement": "정산",
            "SettlementDetail": "정산 상세"
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
