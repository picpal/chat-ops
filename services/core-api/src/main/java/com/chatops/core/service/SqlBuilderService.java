package com.chatops.core.service;

import com.chatops.core.config.ChatOpsProperties;
import lombok.Getter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.StringJoiner;

@Slf4j
@Service
@RequiredArgsConstructor
public class SqlBuilderService {

    private final ChatOpsProperties chatOpsProperties;

    /**
     * QueryPlan을 기반으로 SQL과 파라미터를 생성
     */
    public SqlQuery buildQuery(Map<String, Object> queryPlan) {
        String entity = (String) queryPlan.get("entity");
        String operation = (String) queryPlan.get("operation");
        String tableName = chatOpsProperties.getTableName(entity);

        switch (operation) {
            case "list":
                return buildListQuery(queryPlan, entity, tableName);
            case "aggregate":
                return buildAggregateQuery(queryPlan, entity, tableName);
            case "search":
                return buildSearchQuery(queryPlan, entity, tableName);
            default:
                throw new IllegalArgumentException("Unsupported operation: " + operation);
        }
    }

    @SuppressWarnings("unchecked")
    private SqlQuery buildListQuery(Map<String, Object> queryPlan, String entity, String tableName) {
        List<Object> params = new ArrayList<>();
        StringBuilder sql = new StringBuilder();

        // SELECT
        sql.append("SELECT * FROM ").append(tableName);

        // WHERE
        String whereClause = buildWhereClause(queryPlan, entity, params);
        if (!whereClause.isEmpty()) {
            sql.append(" WHERE ").append(whereClause);
        }

        // ORDER BY
        String orderByClause = buildOrderByClause(queryPlan, entity);
        if (!orderByClause.isEmpty()) {
            sql.append(" ORDER BY ").append(orderByClause);
        } else {
            // Use default order by
            String defaultOrderBy = chatOpsProperties.getDefaultOrderBy(entity);
            if (defaultOrderBy != null && !defaultOrderBy.isEmpty()) {
                sql.append(" ORDER BY ").append(defaultOrderBy);
            }
        }

        // LIMIT
        int limit = getLimit(queryPlan);
        sql.append(" LIMIT ?");
        params.add(limit);

        // OFFSET (for pagination)
        Integer offset = (Integer) queryPlan.get("offset");
        if (offset != null && offset > 0) {
            sql.append(" OFFSET ?");
            params.add(offset);
        }

        log.debug("Built SQL: {} with params: {}", sql, params);
        return new SqlQuery(sql.toString(), params);
    }

    @SuppressWarnings("unchecked")
    private SqlQuery buildAggregateQuery(Map<String, Object> queryPlan, String entity, String tableName) {
        List<Object> params = new ArrayList<>();
        StringBuilder sql = new StringBuilder();

        // SELECT with aggregations
        List<Map<String, Object>> aggregations = (List<Map<String, Object>>) queryPlan.get("aggregations");
        List<String> groupByFields = (List<String>) queryPlan.get("groupBy");

        StringJoiner selectJoiner = new StringJoiner(", ");

        // Add group by fields to select
        if (groupByFields != null && !groupByFields.isEmpty()) {
            for (String field : groupByFields) {
                String column = chatOpsProperties.getColumnName(entity, field);
                selectJoiner.add(column + " AS " + field);
            }
        }

        // Add aggregations to select
        if (aggregations != null) {
            for (Map<String, Object> agg : aggregations) {
                String function = (String) agg.get("function");
                String field = (String) agg.get("field");
                String alias = (String) agg.getOrDefault("alias", function + "_" + field);

                String aggExpression;
                if ("*".equals(field)) {
                    aggExpression = function.toUpperCase() + "(*)";
                } else {
                    String column = chatOpsProperties.getColumnName(entity, field);
                    aggExpression = function.toUpperCase() + "(" + column + ")";
                }
                selectJoiner.add(aggExpression + " AS " + alias);
            }
        }

        sql.append("SELECT ").append(selectJoiner.toString());
        sql.append(" FROM ").append(tableName);

        // WHERE
        String whereClause = buildWhereClause(queryPlan, entity, params);
        if (!whereClause.isEmpty()) {
            sql.append(" WHERE ").append(whereClause);
        }

        // GROUP BY
        if (groupByFields != null && !groupByFields.isEmpty()) {
            StringJoiner groupByJoiner = new StringJoiner(", ");
            for (String field : groupByFields) {
                String column = chatOpsProperties.getColumnName(entity, field);
                groupByJoiner.add(column);
            }
            sql.append(" GROUP BY ").append(groupByJoiner.toString());
        }

        // ORDER BY (for aggregations, typically by the aggregated value)
        String orderByClause = buildOrderByClause(queryPlan, entity);
        if (!orderByClause.isEmpty()) {
            sql.append(" ORDER BY ").append(orderByClause);
        }

        // LIMIT
        int limit = getLimit(queryPlan);
        sql.append(" LIMIT ?");
        params.add(limit);

        log.debug("Built aggregate SQL: {} with params: {}", sql, params);
        return new SqlQuery(sql.toString(), params);
    }

    @SuppressWarnings("unchecked")
    private SqlQuery buildSearchQuery(Map<String, Object> queryPlan, String entity, String tableName) {
        // Search is similar to list but with LIKE filters
        return buildListQuery(queryPlan, entity, tableName);
    }

    @SuppressWarnings("unchecked")
    private String buildWhereClause(Map<String, Object> queryPlan, String entity, List<Object> params) {
        List<Map<String, Object>> filters = (List<Map<String, Object>>) queryPlan.get("filters");
        Map<String, Object> timeRange = (Map<String, Object>) queryPlan.get("timeRange");

        StringJoiner whereJoiner = new StringJoiner(" AND ");

        // Process filters
        if (filters != null && !filters.isEmpty()) {
            for (Map<String, Object> filter : filters) {
                String condition = buildFilterCondition(filter, entity, params);
                whereJoiner.add(condition);
            }
        }

        // Process time range
        if (timeRange != null) {
            String start = (String) timeRange.get("start");
            String end = (String) timeRange.get("end");
            String timestampField = getTimestampField(entity);

            if (timestampField != null && start != null && end != null) {
                String column = chatOpsProperties.getColumnName(entity, timestampField);
                whereJoiner.add(column + " >= ?");
                params.add(parseDateTime(start));
                whereJoiner.add(column + " <= ?");
                params.add(parseDateTime(end));
            }
        }

        return whereJoiner.toString();
    }

    private String buildFilterCondition(Map<String, Object> filter, String entity, List<Object> params) {
        String field = (String) filter.get("field");
        String operator = (String) filter.get("operator");
        Object value = filter.get("value");

        String column = chatOpsProperties.getColumnName(entity, field);

        switch (operator) {
            case "eq":
                params.add(value);
                return column + " = ?";

            case "ne":
                params.add(value);
                return column + " != ?";

            case "gt":
                params.add(value);
                return column + " > ?";

            case "gte":
                params.add(value);
                return column + " >= ?";

            case "lt":
                params.add(value);
                return column + " < ?";

            case "lte":
                params.add(value);
                return column + " <= ?";

            case "like":
                params.add("%" + value + "%");
                return column + " LIKE ?";

            case "in":
                @SuppressWarnings("unchecked")
                List<Object> inValues = (List<Object>) value;
                StringJoiner placeholders = new StringJoiner(", ");
                for (Object v : inValues) {
                    placeholders.add("?");
                    params.add(v);
                }
                return column + " IN (" + placeholders.toString() + ")";

            case "between":
                @SuppressWarnings("unchecked")
                List<Object> betweenValues = (List<Object>) value;
                params.add(betweenValues.get(0));
                params.add(betweenValues.get(1));
                return column + " BETWEEN ? AND ?";

            default:
                throw new IllegalArgumentException("Unsupported operator: " + operator);
        }
    }

    @SuppressWarnings("unchecked")
    private String buildOrderByClause(Map<String, Object> queryPlan, String entity) {
        List<Map<String, Object>> orderByList = (List<Map<String, Object>>) queryPlan.get("orderBy");
        if (orderByList == null || orderByList.isEmpty()) {
            return "";
        }

        StringJoiner orderByJoiner = new StringJoiner(", ");
        for (Map<String, Object> orderBy : orderByList) {
            String field = (String) orderBy.get("field");
            String direction = (String) orderBy.getOrDefault("direction", "asc");

            String column = chatOpsProperties.getColumnName(entity, field);
            orderByJoiner.add(column + " " + direction.toUpperCase());
        }

        return orderByJoiner.toString();
    }

    private int getLimit(Map<String, Object> queryPlan) {
        Object limitObj = queryPlan.get("limit");
        if (limitObj == null) {
            return chatOpsProperties.getQuery().getDefaultLimit();
        }
        if (limitObj instanceof Integer) {
            return (Integer) limitObj;
        }
        if (limitObj instanceof Long) {
            return ((Long) limitObj).intValue();
        }
        return chatOpsProperties.getQuery().getDefaultLimit();
    }

    private String getTimestampField(String entity) {
        // Common timestamp field names
        if (chatOpsProperties.hasField(entity, "timestamp")) {
            return "timestamp";
        }
        if (chatOpsProperties.hasField(entity, "orderDate")) {
            return "orderDate";
        }
        if (chatOpsProperties.hasField(entity, "createdAt")) {
            return "createdAt";
        }
        return null;
    }

    /**
     * ISO-8601 날짜 문자열을 OffsetDateTime으로 파싱
     * 다양한 형식 지원: 2024-01-01T00:00:00Z, 2024-01-01T00:00:00, 2024-01-01
     */
    private OffsetDateTime parseDateTime(String dateTimeStr) {
        try {
            // ISO-8601 with offset (e.g., 2024-01-01T00:00:00Z)
            return OffsetDateTime.parse(dateTimeStr);
        } catch (DateTimeParseException e1) {
            try {
                // ISO-8601 without offset (e.g., 2024-01-01T00:00:00)
                LocalDateTime localDateTime = LocalDateTime.parse(dateTimeStr);
                return localDateTime.atOffset(ZoneOffset.UTC);
            } catch (DateTimeParseException e2) {
                try {
                    // Date only (e.g., 2024-01-01)
                    LocalDateTime localDateTime = LocalDateTime.parse(
                            dateTimeStr + "T00:00:00",
                            DateTimeFormatter.ISO_LOCAL_DATE_TIME
                    );
                    return localDateTime.atOffset(ZoneOffset.UTC);
                } catch (DateTimeParseException e3) {
                    log.warn("Failed to parse date time string: {}", dateTimeStr);
                    throw new IllegalArgumentException("Invalid date time format: " + dateTimeStr);
                }
            }
        }
    }

    /**
     * SQL 쿼리와 파라미터를 담는 클래스
     */
    @Getter
    @RequiredArgsConstructor
    public static class SqlQuery {
        private final String sql;
        private final List<Object> params;
    }
}
