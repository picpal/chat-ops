package com.chatops.core.service;

import com.chatops.core.config.ChatOpsProperties;
import com.chatops.core.exception.QueryPlanValidationException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;

/**
 * QueryPlanValidatorService 순수 단위 테스트
 */
@DisplayName("QueryPlanValidatorService 단위 테스트")
class QueryPlanValidatorServiceUnitTest {

    private QueryPlanValidatorService validatorService;
    private ChatOpsProperties properties;

    @BeforeEach
    void setUp() {
        properties = createTestProperties();
        validatorService = new QueryPlanValidatorService(properties);
    }

    private ChatOpsProperties createTestProperties() {
        ChatOpsProperties props = new ChatOpsProperties();

        ChatOpsProperties.QueryConfig queryConfig = new ChatOpsProperties.QueryConfig();
        queryConfig.setMaxLimit(1000);
        queryConfig.setDefaultLimit(10);
        props.setQuery(queryConfig);

        Map<String, ChatOpsProperties.EntityMapping> mappings = new HashMap<>();

        // Order entity
        ChatOpsProperties.EntityMapping orderMapping = new ChatOpsProperties.EntityMapping();
        orderMapping.setTable("orders");
        Map<String, String> orderFields = new HashMap<>();
        orderFields.put("orderId", "order_id");
        orderFields.put("customerId", "customer_id");
        orderFields.put("status", "status");
        orderFields.put("totalAmount", "total_amount");
        orderFields.put("orderDate", "order_date");
        orderMapping.setFields(orderFields);
        mappings.put("Order", orderMapping);

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
    @DisplayName("필수 필드 검증")
    class RequiredFieldValidation {

        @Test
        @DisplayName("entity 필드 누락 시 예외 발생")
        void shouldThrowWhenEntityMissing() {
            Map<String, Object> queryPlan = Map.of(
                "operation", "list"
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("entity is required");
        }

        @Test
        @DisplayName("operation 필드 누락 시 예외 발생")
        void shouldThrowWhenOperationMissing() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order"
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("operation is required");
        }

        @Test
        @DisplayName("유효한 QueryPlan은 통과")
        void shouldPassValidQueryPlan() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 10
            );

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }
    }

    @Nested
    @DisplayName("엔티티 검증")
    class EntityValidation {

        @Test
        @DisplayName("존재하지 않는 엔티티 시 예외 발생")
        void shouldThrowForUnknownEntity() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "UnknownEntity",
                "operation", "list"
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("Unknown entity");
        }

        @Test
        @DisplayName("빈 문자열 엔티티 시 예외 발생")
        void shouldThrowForEmptyEntity() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "",
                "operation", "list"
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("cannot be empty");
        }
    }

    @Nested
    @DisplayName("Operation 검증")
    class OperationValidation {

        @Test
        @DisplayName("유효한 operation: list")
        void shouldAcceptListOperation() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list"
            );

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }

        @Test
        @DisplayName("유효한 operation: aggregate")
        void shouldAcceptAggregateOperation() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate"
            );

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }

        @Test
        @DisplayName("유효한 operation: search")
        void shouldAcceptSearchOperation() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "search"
            );

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }

        @Test
        @DisplayName("잘못된 operation 시 예외 발생")
        void shouldThrowForInvalidOperation() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "delete"
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("Unknown operation");
        }
    }

    @Nested
    @DisplayName("Limit 검증")
    class LimitValidation {

        @Test
        @DisplayName("limit이 maxLimit 초과 시 예외 발생")
        void shouldThrowWhenLimitExceedsMax() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 5000  // maxLimit is 1000
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("cannot exceed");
        }

        @Test
        @DisplayName("limit이 0 이하 시 예외 발생")
        void shouldThrowWhenLimitIsZeroOrNegative() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 0
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("at least 1");
        }

        @Test
        @DisplayName("유효한 limit 통과")
        void shouldAcceptValidLimit() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 100
            );

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }
    }

    @Nested
    @DisplayName("필터 검증")
    class FilterValidation {

        @Test
        @DisplayName("존재하지 않는 필드 시 예외 발생")
        void shouldThrowForUnknownField() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "unknownField", "operator", "eq", "value", "test")
                )
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("Unknown field");
        }

        @Test
        @DisplayName("잘못된 연산자 시 예외 발생")
        void shouldThrowForInvalidOperator() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "regex", "value", ".*")
                )
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("Invalid operator");
        }

        @Test
        @DisplayName("in 연산자에 배열이 아닌 값 시 예외 발생")
        void shouldThrowWhenInOperatorHasNonArrayValue() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "in", "value", "PAID")
                )
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("must be an array");
        }

        @Test
        @DisplayName("between 연산자에 2개 요소가 아닌 배열 시 예외 발생")
        void shouldThrowWhenBetweenHasWrongArraySize() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "totalAmount", "operator", "between", "value", List.of(100))
                )
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("exactly 2 elements");
        }

        @Test
        @DisplayName("유효한 필터 통과")
        void shouldAcceptValidFilters() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "eq", "value", "PAID"),
                    Map.of("field", "totalAmount", "operator", "gt", "value", 1000),
                    Map.of("field", "status", "operator", "in", "value", List.of("PAID", "SHIPPED"))
                )
            );

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }
    }

    @Nested
    @DisplayName("집계 함수 검증")
    class AggregationValidation {

        @Test
        @DisplayName("잘못된 집계 함수 시 예외 발생")
        void shouldThrowForInvalidAggregationFunction() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate",
                "aggregations", List.of(
                    Map.of("function", "median", "field", "totalAmount")
                )
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("Invalid aggregation function");
        }

        @Test
        @DisplayName("유효한 집계 함수 통과")
        void shouldAcceptValidAggregations() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate",
                "aggregations", List.of(
                    Map.of("function", "count", "field", "*"),
                    Map.of("function", "sum", "field", "totalAmount"),
                    Map.of("function", "avg", "field", "totalAmount"),
                    Map.of("function", "min", "field", "totalAmount"),
                    Map.of("function", "max", "field", "totalAmount")
                )
            );

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }
    }

    @Nested
    @DisplayName("정렬 조건 검증")
    class OrderByValidation {

        @Test
        @DisplayName("잘못된 정렬 방향 시 예외 발생")
        void shouldThrowForInvalidDirection() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "orderBy", List.of(
                    Map.of("field", "orderDate", "direction", "random")
                )
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("Invalid direction");
        }

        @Test
        @DisplayName("유효한 정렬 조건 통과")
        void shouldAcceptValidOrderBy() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "orderBy", List.of(
                    Map.of("field", "orderDate", "direction", "desc"),
                    Map.of("field", "status", "direction", "asc")
                )
            );

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }
    }

    @Nested
    @DisplayName("시간 범위 검증")
    class TimeRangeValidation {

        @Test
        @DisplayName("시간 범위 필수 엔티티에서 timeRange 누락 시 예외 발생")
        void shouldThrowWhenTimeRangeRequiredButMissing() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "PaymentLog",
                "operation", "list"
            );

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("timeRange is required");
        }

        @Test
        @DisplayName("시간 범위 필수 엔티티에서 start/end 누락 시 예외 발생")
        void shouldThrowWhenTimeRangeIncomplete() {
            Map<String, Object> queryPlan = new HashMap<>();
            queryPlan.put("entity", "PaymentLog");
            queryPlan.put("operation", "list");
            queryPlan.put("timeRange", Map.of("start", "2024-01-01"));

            assertThatThrownBy(() -> validatorService.validate(queryPlan))
                .isInstanceOf(QueryPlanValidationException.class)
                .hasMessageContaining("start and timeRange.end are required");
        }

        @Test
        @DisplayName("시간 범위 필수 엔티티에서 완전한 timeRange 통과")
        void shouldAcceptCompleteTimeRange() {
            Map<String, Object> queryPlan = new HashMap<>();
            queryPlan.put("entity", "PaymentLog");
            queryPlan.put("operation", "list");
            queryPlan.put("timeRange", Map.of(
                "start", "2024-01-01T00:00:00Z",
                "end", "2024-01-31T23:59:59Z"
            ));

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }
    }

    @Nested
    @DisplayName("복합 QueryPlan 검증")
    class ComplexQueryPlanValidation {

        @Test
        @DisplayName("필터 + 정렬 + limit 조합 통과")
        void shouldAcceptComplexQueryPlan() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "in", "value", List.of("PAID", "SHIPPED")),
                    Map.of("field", "totalAmount", "operator", "gte", "value", 1000)
                ),
                "orderBy", List.of(
                    Map.of("field", "orderDate", "direction", "desc")
                ),
                "limit", 50
            );

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }

        @Test
        @DisplayName("집계 + groupBy + 필터 조합 통과")
        void shouldAcceptAggregateWithGroupBy() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate",
                "aggregations", List.of(
                    Map.of("function", "count", "field", "*", "alias", "count"),
                    Map.of("function", "sum", "field", "totalAmount", "alias", "revenue")
                ),
                "groupBy", List.of("status"),
                "filters", List.of(
                    Map.of("field", "totalAmount", "operator", "gt", "value", 0)
                ),
                "limit", 100
            );

            assertThatCode(() -> validatorService.validate(queryPlan))
                .doesNotThrowAnyException();
        }
    }
}
