package com.chatops.core.service;

import com.chatops.core.config.ChatOpsProperties;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
@DisplayName("SqlBuilderService 테스트")
class SqlBuilderServiceTest {

    @Autowired
    private SqlBuilderService sqlBuilderService;

    @Nested
    @DisplayName("기본 SELECT 쿼리")
    class BasicSelect {

        @Test
        @DisplayName("Order 엔티티 기본 조회")
        void basicOrderQuery() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql())
                .contains("SELECT")
                .contains("FROM orders")
                .contains("LIMIT");
            assertThat(result.getParams()).contains(10);
        }

        @Test
        @DisplayName("Customer 엔티티 조회")
        void customerQuery() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "PgCustomer",
                "operation", "list",
                "limit", 5
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("FROM pg_customers");
        }
    }

    @Nested
    @DisplayName("필터 조건")
    class FilterConditions {

        @Test
        @DisplayName("eq 연산자")
        void filterWithEq() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "eq", "value", "PAID")
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("WHERE");
            assertThat(result.getSql()).contains("status = ?");
            assertThat(result.getParams()).contains("PAID");
        }

        @Test
        @DisplayName("gt/lt 연산자")
        void filterWithGtLt() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "totalAmount", "operator", "gt", "value", 1000)
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("total_amount > ?");
            assertThat(result.getParams()).contains(1000);
        }

        @Test
        @DisplayName("in 연산자")
        void filterWithIn() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "in", "value", List.of("PAID", "SHIPPED"))
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("status IN (?, ?)");
            assertThat(result.getParams()).contains("PAID", "SHIPPED");
        }

        @Test
        @DisplayName("like 연산자")
        void filterWithLike() {
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
        @DisplayName("다중 필터")
        void multipleFilters() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "status", "operator", "eq", "value", "PAID"),
                    Map.of("field", "totalAmount", "operator", "gte", "value", 500)
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("status = ?");
            assertThat(result.getSql()).contains("total_amount >= ?");
            assertThat(result.getSql()).contains("AND");
        }
    }

    @Nested
    @DisplayName("정렬 조건")
    class OrderByConditions {

        @Test
        @DisplayName("단일 정렬")
        void singleOrderBy() {
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
        @DisplayName("다중 정렬")
        void multipleOrderBy() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "orderBy", List.of(
                    Map.of("field", "status", "direction", "asc"),
                    Map.of("field", "orderDate", "direction", "desc")
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("ORDER BY status ASC, order_date DESC");
        }
    }

    @Nested
    @DisplayName("집계 쿼리")
    class AggregateQueries {

        @Test
        @DisplayName("COUNT 집계")
        void countAggregate() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate",
                "aggregations", List.of(
                    Map.of("function", "count", "field", "*", "alias", "total_count")
                ),
                "limit", 100
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("COUNT(*)");
            assertThat(result.getSql()).contains("AS \"total_count\"");
        }

        @Test
        @DisplayName("SUM 집계")
        void sumAggregate() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate",
                "aggregations", List.of(
                    Map.of("function", "sum", "field", "totalAmount", "alias", "total_revenue")
                ),
                "limit", 100
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("SUM(total_amount)");
            assertThat(result.getSql()).contains("AS \"total_revenue\"");
        }

        @Test
        @DisplayName("GROUP BY")
        void groupByAggregate() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "aggregate",
                "aggregations", List.of(
                    Map.of("function", "count", "field", "*", "alias", "count")
                ),
                "groupBy", List.of("status"),
                "limit", 100
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            assertThat(result.getSql()).contains("GROUP BY status");
        }
    }

    @Nested
    @DisplayName("필드 매핑")
    class FieldMapping {

        @Test
        @DisplayName("논리 필드가 물리 컬럼으로 변환됨")
        void logicalToPhysicalMapping() {
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "filters", List.of(
                    Map.of("field", "orderId", "operator", "eq", "value", 1)
                ),
                "limit", 10
            );

            SqlBuilderService.SqlQuery result = sqlBuilderService.buildQuery(queryPlan);

            // orderId -> order_id
            assertThat(result.getSql()).contains("order_id = ?");
        }
    }
}
