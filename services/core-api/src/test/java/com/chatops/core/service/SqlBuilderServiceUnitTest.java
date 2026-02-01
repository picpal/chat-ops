package com.chatops.core.service;

import com.chatops.core.config.ChatOpsProperties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;

/**
 * SqlBuilderService 순수 단위 테스트
 * Spring Context 없이 직접 의존성 주입
 */
@DisplayName("SqlBuilderService 단위 테스트")
class SqlBuilderServiceUnitTest {

    private SqlBuilderService sqlBuilderService;
    private ChatOpsProperties properties;

    @BeforeEach
    void setUp() {
        properties = createTestProperties();
        sqlBuilderService = new SqlBuilderService(properties);
    }

    /**
     * 테스트용 ChatOpsProperties 생성
     */
    private ChatOpsProperties createTestProperties() {
        ChatOpsProperties props = new ChatOpsProperties();

        // Query config
        ChatOpsProperties.QueryConfig queryConfig = new ChatOpsProperties.QueryConfig();
        queryConfig.setMaxLimit(1000);
        queryConfig.setDefaultLimit(10);
        props.setQuery(queryConfig);

        // Entity mappings
        Map<String, ChatOpsProperties.EntityMapping> mappings = new HashMap<>();

        // Order entity
        ChatOpsProperties.EntityMapping orderMapping = new ChatOpsProperties.EntityMapping();
        orderMapping.setTable("orders");
        orderMapping.setDefaultOrderBy("order_date DESC");
        Map<String, String> orderFields = new HashMap<>();
        orderFields.put("orderId", "order_id");
        orderFields.put("customerId", "customer_id");
        orderFields.put("orderDate", "order_date");
        orderFields.put("totalAmount", "total_amount");
        orderFields.put("status", "status");
        orderFields.put("paymentGateway", "payment_gateway");
        orderMapping.setFields(orderFields);
        mappings.put("Order", orderMapping);

        // Customer entity
        ChatOpsProperties.EntityMapping customerMapping = new ChatOpsProperties.EntityMapping();
        customerMapping.setTable("customers");
        customerMapping.setDefaultOrderBy("created_at DESC");
        Map<String, String> customerFields = new HashMap<>();
        customerFields.put("customerId", "customer_id");
        customerFields.put("name", "name");
        customerFields.put("email", "email");
        customerFields.put("createdAt", "created_at");
        customerMapping.setFields(customerFields);
        mappings.put("Customer", customerMapping);

        // PaymentLog entity (time range required)
        ChatOpsProperties.EntityMapping logMapping = new ChatOpsProperties.EntityMapping();
        logMapping.setTable("payment_logs");
        logMapping.setTimeRangeRequired(true);
        Map<String, String> logFields = new HashMap<>();
        logFields.put("logId", "log_id");
        logFields.put("timestamp", "timestamp");
        logFields.put("level", "level");
        logFields.put("message", "message");
        logMapping.setFields(logFields);
        mappings.put("PaymentLog", logMapping);

        props.setEntityMappings(mappings);
        return props;
    }

    @Nested
    @DisplayName("기본 SELECT 쿼리 생성")
    class BasicSelectQuery {

        @Test
        @DisplayName("Order 엔티티 기본 조회 - 테이블명과 LIMIT 포함")
        void shouldBuildBasicOrderQuery() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql())
                .contains("SELECT * FROM orders")
                .contains("LIMIT ?");
            assertThat(result.getParams()).contains(10);
        }

        @Test
        @DisplayName("Customer 엔티티 조회 - 다른 테이블 매핑 확인")
        void shouldBuildCustomerQuery() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Customer",
                "operation", "list",
                "limit", 5
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("FROM customers");
            assertThat(result.getParams()).contains(5);
        }

        @Test
        @DisplayName("기본 ORDER BY 적용 확인")
        void shouldApplyDefaultOrderBy() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("ORDER BY order_date DESC");
        }

        @Test
        @DisplayName("OFFSET 처리")
        void shouldHandleOffset() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 10,
                "offset", 20
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("OFFSET ?");
            assertThat(result.getParams()).containsExactly(10, 20);
        }
    }

    @Nested
    @DisplayName("필터 조건 처리")
    class FilterConditions {

        @Test
        @DisplayName("eq 연산자 - 동등 비교")
        void shouldHandleEqOperator() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "eq", "value", "PAID")
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("WHERE status = ?");
            assertThat(result.getParams()).contains("PAID");
        }

        @Test
        @DisplayName("ne 연산자 - 불일치 비교")
        void shouldHandleNeOperator() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "ne", "value", "CANCELLED")
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("status != ?");
            assertThat(result.getParams()).contains("CANCELLED");
        }

        @Test
        @DisplayName("gt/gte/lt/lte 연산자 - 범위 비교")
        void shouldHandleRangeOperators() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "totalAmount", "operator", "gt", "value", 1000),
                    Map.of("field", "totalAmount", "operator", "lte", "value", 5000)
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql())
                .contains("total_amount > ?")
                .contains("total_amount <= ?")
                .contains("AND");
            assertThat(result.getParams()).contains(1000, 5000);
        }

        @Test
        @DisplayName("in 연산자 - 다중 값 비교")
        void shouldHandleInOperator() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "in", "value", List.of("PAID", "SHIPPED", "DELIVERED"))
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("status IN (?, ?, ?)");
            assertThat(result.getParams()).contains("PAID", "SHIPPED", "DELIVERED");
        }

        @Test
        @DisplayName("like 연산자 - 패턴 매칭")
        void shouldHandleLikeOperator() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "like", "value", "PA")
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("status LIKE ?");
            assertThat(result.getParams()).contains("%PA%");
        }

        @Test
        @DisplayName("between 연산자 - 범위 지정")
        void shouldHandleBetweenOperator() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "totalAmount", "operator", "between", "value", List.of(100, 1000))
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("total_amount BETWEEN ? AND ?");
            assertThat(result.getParams()).contains(100, 1000);
        }

        @Test
        @DisplayName("다중 필터 - AND 조합")
        void shouldCombineMultipleFiltersWithAnd() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "eq", "value", "PAID"),
                    Map.of("field", "totalAmount", "operator", "gte", "value", 500),
                    Map.of("field", "paymentGateway", "operator", "eq", "value", "STRIPE")
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql())
                .contains("status = ?")
                .contains("total_amount >= ?")
                .contains("payment_gateway = ?");
            // AND가 2번 나와야 함 (3개 조건)
            assertThat(result.getSql().split("AND").length).isEqualTo(3);
        }
    }

    @Nested
    @DisplayName("정렬 조건 처리")
    class OrderByConditions {

        @Test
        @DisplayName("단일 정렬 조건")
        void shouldHandleSingleOrderBy() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "orderBy", List.of(
                    Map.of("field", "orderDate", "direction", "desc")
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("ORDER BY order_date DESC");
        }

        @Test
        @DisplayName("다중 정렬 조건")
        void shouldHandleMultipleOrderBy() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "orderBy", List.of(
                    Map.of("field", "status", "direction", "asc"),
                    Map.of("field", "totalAmount", "direction", "desc")
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("ORDER BY status ASC, total_amount DESC");
        }
    }

    @Nested
    @DisplayName("집계 쿼리 생성")
    class AggregateQuery {

        @Test
        @DisplayName("COUNT(*) 집계")
        void shouldBuildCountAggregate() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate",
                "aggregations", List.of(
                    Map.of("function", "count", "field", "*", "alias", "total_count")
                ),
                "limit", 100
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql())
                .contains("SELECT COUNT(*) AS \"total_count\"")
                .contains("FROM orders");
        }

        @Test
        @DisplayName("SUM 집계")
        void shouldBuildSumAggregate() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate",
                "aggregations", List.of(
                    Map.of("function", "sum", "field", "totalAmount", "alias", "revenue")
                ),
                "limit", 100
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql())
                .contains("SUM(total_amount) AS \"revenue\"");
        }

        @Test
        @DisplayName("GROUP BY 처리")
        void shouldHandleGroupBy() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate",
                "aggregations", List.of(
                    Map.of("function", "count", "field", "*", "alias", "order_count"),
                    Map.of("function", "sum", "field", "totalAmount", "alias", "total_revenue")
                ),
                "groupBy", List.of("status"),
                "limit", 100
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql())
                .contains("status AS \"status\"")
                .contains("COUNT(*) AS \"order_count\"")
                .contains("SUM(total_amount) AS \"total_revenue\"")
                .contains("GROUP BY status");
        }

        @Test
        @DisplayName("다중 GROUP BY")
        void shouldHandleMultipleGroupBy() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate",
                "aggregations", List.of(
                    Map.of("function", "count", "field", "*", "alias", "count")
                ),
                "groupBy", List.of("status", "paymentGateway"),
                "limit", 100
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("GROUP BY status, payment_gateway");
        }
    }

    @Nested
    @DisplayName("필드 매핑")
    class FieldMapping {

        @Test
        @DisplayName("논리 필드명이 물리 컬럼명으로 변환됨")
        void shouldMapLogicalFieldToPhysicalColumn() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "orderId", "operator", "eq", "value", 123),
                    Map.of("field", "customerId", "operator", "eq", "value", 456)
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql())
                .contains("order_id = ?")
                .contains("customer_id = ?")
                .doesNotContain("orderId")
                .doesNotContain("customerId");
        }
    }

    @Nested
    @DisplayName("예외 처리")
    class ExceptionHandling {

        @Test
        @DisplayName("지원하지 않는 operation - IllegalArgumentException")
        void shouldThrowExceptionForUnsupportedOperation() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "delete",
                "limit", 10
            );

            assertThatThrownBy(() -> sqlBuilderService.buildQuery(queryPlan))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unsupported operation");
        }

        @Test
        @DisplayName("알 수 없는 엔티티 - IllegalArgumentException")
        void shouldThrowExceptionForUnknownEntity() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "UnknownEntity",
                "operation", "list",
                "limit", 10
            );

            assertThatThrownBy(() -> sqlBuilderService.buildQuery(queryPlan))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unknown entity");
        }

        @Test
        @DisplayName("지원하지 않는 연산자 - IllegalArgumentException")
        void shouldThrowExceptionForUnsupportedOperator() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "regex", "value", ".*")
                ),
                "limit", 10
            );

            assertThatThrownBy(() -> sqlBuilderService.buildQuery(queryPlan))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unsupported operator");
        }
    }
}
