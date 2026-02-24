package com.chatops.core.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class QueryExecutorService {

    private final JdbcTemplate jdbcTemplate;
    private final QueryPlanValidatorService validatorService;
    private final SqlBuilderService sqlBuilderService;
    private final PaginationService paginationService;

    /**
     * QueryPlan을 실행하고 QueryResult를 반환
     */
    public Map<String, Object> executeQuery(Map<String, Object> queryPlan) {
        String requestId = (String) queryPlan.getOrDefault("requestId", "unknown");
        long startTime = System.currentTimeMillis();

        try {
            // 1. Validate QueryPlan
            validatorService.validate(queryPlan);

            // 2. Check for pagination token
            String queryToken = (String) queryPlan.get("queryToken");
            if (queryToken != null && !queryToken.isEmpty()) {
                return executePaginatedQuery(requestId, queryToken, startTime);
            }

            // 3. Build SQL
            SqlBuilderService.SqlQuery sqlQuery = sqlBuilderService.buildQuery(queryPlan);

            // 4. Execute SQL
            List<Map<String, Object>> rows = executeRawQuery(sqlQuery);

            // 5. Build response
            return buildSuccessResponse(requestId, queryPlan, rows, startTime);

        } catch (Exception e) {
            log.error("Query execution failed for requestId: {}", requestId, e);
            return buildErrorResponse(requestId, e, startTime);
        }
    }

    private List<Map<String, Object>> executeRawQuery(SqlBuilderService.SqlQuery sqlQuery) {
        log.debug("Executing SQL: {}", sqlQuery.getSql());
        log.debug("With params: {}", sqlQuery.getParams());

        return jdbcTemplate.queryForList(
                sqlQuery.getSql(),
                sqlQuery.getParams().toArray()
        );
    }

    /**
     * COUNT 쿼리를 실행하여 총 건수 반환
     */
    private int executeCountQuery(Map<String, Object> queryPlan) {
        try {
            SqlBuilderService.SqlQuery countQuery = sqlBuilderService.buildCountQuery(queryPlan);
            log.debug("Executing count SQL: {}", countQuery.getSql());
            Integer count = jdbcTemplate.queryForObject(
                    countQuery.getSql(),
                    Integer.class,
                    countQuery.getParams().toArray()
            );
            return count != null ? count : 0;
        } catch (Exception e) {
            log.warn("Failed to execute count query: {}", e.getMessage());
            return 0;
        }
    }

    private Map<String, Object> executePaginatedQuery(String requestId, String queryToken, long startTime) {
        // Retrieve stored query context from token
        PaginationService.PaginationContext context = paginationService.getContext(queryToken);

        if (context == null) {
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("requestId", requestId);
            errorResponse.put("status", "error");
            errorResponse.put("error", Map.of(
                    "code", "INVALID_TOKEN",
                    "message", "Query token is invalid or expired"
            ));
            return errorResponse;
        }

        // Execute with stored context
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                context.getSql(),
                context.getParams().toArray()
        );

        long executionTime = System.currentTimeMillis() - startTime;

        Map<String, Object> response = new HashMap<>();
        response.put("requestId", requestId);
        response.put("status", "success");
        response.put("data", Map.of("rows", rows));
        response.put("metadata", Map.of(
                "executionTimeMs", executionTime,
                "rowsReturned", rows.size(),
                "dataSource", "postgresql",
                "executedAt", Instant.now().toString()
        ));

        // Build pagination with all required fields
        Map<String, Object> pagination = new HashMap<>();
        pagination.put("currentPage", context.getCurrentPage() + 1);
        pagination.put("totalRows", context.getTotalRows());
        pagination.put("totalPages", context.getTotalPages());
        pagination.put("pageSize", context.getPageSize());

        if (context.hasNextPage(rows.size())) {
            String nextToken = paginationService.createNextPageToken(context);
            pagination.put("queryToken", nextToken);
            pagination.put("hasMore", true);
        } else {
            pagination.put("hasMore", false);
        }
        response.put("pagination", pagination);

        return response;
    }

    private Map<String, Object> buildSuccessResponse(
            String requestId,
            Map<String, Object> queryPlan,
            List<Map<String, Object>> rows,
            long startTime
    ) {
        long executionTime = System.currentTimeMillis() - startTime;
        String operation = (String) queryPlan.get("operation");

        Map<String, Object> response = new HashMap<>();
        response.put("requestId", requestId);
        response.put("status", "success");

        // Data section
        Map<String, Object> data = new HashMap<>();
        if ("aggregate".equals(operation)) {
            // For aggregations, put results in aggregations field
            if (!rows.isEmpty()) {
                data.put("aggregations", rows.get(0));
            }
            data.put("rows", rows);
        } else {
            data.put("rows", rows);
        }
        response.put("data", data);

        // Metadata section
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("executionTimeMs", executionTime);
        metadata.put("rowsReturned", rows.size());
        metadata.put("dataSource", "postgresql");
        metadata.put("executedAt", Instant.now().toString());

        // list/search/aggregate 작업에서 totalRows 계산
        int totalRows = 0;
        if ("list".equals(operation) || "search".equals(operation) || "aggregate".equals(operation)) {
            totalRows = executeCountQuery(queryPlan);
            metadata.put("totalRows", totalRows);
        }
        response.put("metadata", metadata);

        // Pagination (always included for list/search operations)
        int limit = getLimit(queryPlan);
        if ("list".equals(operation) || "search".equals(operation)) {
            boolean hasMore = rows.size() >= limit;
            int totalPages = totalRows > 0 ? (int) Math.ceil((double) totalRows / limit) : 1;

            Map<String, Object> pagination = new HashMap<>();
            pagination.put("hasMore", hasMore);
            pagination.put("currentPage", 1);
            pagination.put("totalPages", totalPages);
            pagination.put("totalRows", totalRows);
            pagination.put("pageSize", limit);

            // hasMore인 경우에만 queryToken 생성
            if (hasMore) {
                String queryToken = paginationService.createToken(queryPlan, rows, limit, totalRows);
                pagination.put("queryToken", queryToken);
            }

            response.put("pagination", pagination);
        }

        log.info("Query executed successfully. requestId={}, rows={}, totalRows={}, time={}ms",
                requestId, rows.size(), totalRows, executionTime);

        return response;
    }

    private Map<String, Object> buildErrorResponse(String requestId, Exception e, long startTime) {
        long executionTime = System.currentTimeMillis() - startTime;

        Map<String, Object> response = new HashMap<>();
        response.put("requestId", requestId);
        response.put("status", "error");

        Map<String, Object> error = new HashMap<>();
        String errorCode = "EXECUTION_ERROR";

        if (e instanceof com.chatops.core.exception.QueryPlanValidationException) {
            com.chatops.core.exception.QueryPlanValidationException validationEx =
                    (com.chatops.core.exception.QueryPlanValidationException) e;
            errorCode = validationEx.getErrorCode();
            if (validationEx.getField() != null) {
                error.put("field", validationEx.getField());
            }
        }

        error.put("code", errorCode);
        error.put("message", e.getMessage());
        error.put("details", e.getClass().getSimpleName());
        response.put("error", error);

        response.put("metadata", Map.of(
                "executionTimeMs", executionTime,
                "executedAt", Instant.now().toString()
        ));

        return response;
    }

    private int getLimit(Map<String, Object> queryPlan) {
        Object limitObj = queryPlan.get("limit");
        if (limitObj == null) return 10;
        if (limitObj instanceof Integer) return (Integer) limitObj;
        if (limitObj instanceof Long) return ((Long) limitObj).intValue();
        return 10;
    }
}
