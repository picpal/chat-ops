package com.chatops.core.service;

import com.chatops.core.config.ChatOpsProperties;
import com.chatops.core.exception.QueryPlanValidationException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Set;

@Slf4j
@Service
@RequiredArgsConstructor
public class QueryPlanValidatorService {

    private final ChatOpsProperties chatOpsProperties;

    private static final Set<String> VALID_OPERATIONS = Set.of("list", "aggregate", "search");
    private static final Set<String> VALID_OPERATORS = Set.of(
            "eq", "ne", "gt", "gte", "lt", "lte", "in", "like", "between"
    );
    private static final Set<String> VALID_AGGREGATION_FUNCTIONS = Set.of(
            "count", "sum", "avg", "min", "max"
    );
    private static final Set<String> VALID_DIRECTIONS = Set.of("asc", "desc");

    /**
     * QueryPlan 전체 검증
     */
    public void validate(Map<String, Object> queryPlan) {
        log.debug("Validating QueryPlan: {}", queryPlan);

        validateRequiredFields(queryPlan);
        validateEntity(queryPlan);
        validateOperation(queryPlan);
        validateLimit(queryPlan);
        validateFilters(queryPlan);
        validateAggregations(queryPlan);
        validateOrderBy(queryPlan);
        validateTimeRange(queryPlan);

        log.debug("QueryPlan validation passed");
    }

    private void validateRequiredFields(Map<String, Object> queryPlan) {
        if (!queryPlan.containsKey("entity")) {
            throw new QueryPlanValidationException("entity is required", "entity");
        }
        if (!queryPlan.containsKey("operation")) {
            throw new QueryPlanValidationException("operation is required", "operation");
        }
    }

    private void validateEntity(Map<String, Object> queryPlan) {
        String entity = (String) queryPlan.get("entity");
        if (entity == null || entity.isBlank()) {
            throw new QueryPlanValidationException("entity cannot be empty", "entity");
        }
        if (!chatOpsProperties.hasEntity(entity)) {
            throw new QueryPlanValidationException(
                    "INVALID_ENTITY",
                    "Unknown entity: " + entity + ". Allowed entities: " +
                            chatOpsProperties.getEntityMappings().keySet(),
                    "entity"
            );
        }
    }

    private void validateOperation(Map<String, Object> queryPlan) {
        String operation = (String) queryPlan.get("operation");
        if (operation == null || operation.isBlank()) {
            throw new QueryPlanValidationException("operation cannot be empty", "operation");
        }
        if (!VALID_OPERATIONS.contains(operation)) {
            throw new QueryPlanValidationException(
                    "INVALID_OPERATION",
                    "Unknown operation: " + operation + ". Allowed operations: " + VALID_OPERATIONS,
                    "operation"
            );
        }
    }

    private void validateLimit(Map<String, Object> queryPlan) {
        Object limitObj = queryPlan.get("limit");
        if (limitObj != null) {
            int limit;
            if (limitObj instanceof Integer) {
                limit = (Integer) limitObj;
            } else if (limitObj instanceof Long) {
                limit = ((Long) limitObj).intValue();
            } else {
                throw new QueryPlanValidationException("limit must be an integer", "limit");
            }

            if (limit < 1) {
                throw new QueryPlanValidationException("limit must be at least 1", "limit");
            }
            if (limit > chatOpsProperties.getQuery().getMaxLimit()) {
                throw new QueryPlanValidationException(
                        "LIMIT_EXCEEDED",
                        "limit cannot exceed " + chatOpsProperties.getQuery().getMaxLimit(),
                        "limit"
                );
            }
        }
    }

    @SuppressWarnings("unchecked")
    private void validateFilters(Map<String, Object> queryPlan) {
        List<Map<String, Object>> filters = (List<Map<String, Object>>) queryPlan.get("filters");
        if (filters == null || filters.isEmpty()) {
            return;
        }

        String entity = (String) queryPlan.get("entity");

        for (int i = 0; i < filters.size(); i++) {
            Map<String, Object> filter = filters.get(i);
            validateFilter(filter, entity, i);
        }
    }

    private void validateFilter(Map<String, Object> filter, String entity, int index) {
        String field = (String) filter.get("field");
        String operator = (String) filter.get("operator");
        Object value = filter.get("value");

        if (field == null || field.isBlank()) {
            throw new QueryPlanValidationException(
                    "filter[" + index + "].field is required",
                    "filters[" + index + "].field"
            );
        }

        if (!chatOpsProperties.hasField(entity, field)) {
            throw new QueryPlanValidationException(
                    "INVALID_FIELD",
                    "Unknown field: " + field + " for entity: " + entity,
                    "filters[" + index + "].field"
            );
        }

        if (operator == null || !VALID_OPERATORS.contains(operator)) {
            throw new QueryPlanValidationException(
                    "INVALID_OPERATOR",
                    "Invalid operator: " + operator + ". Allowed operators: " + VALID_OPERATORS,
                    "filters[" + index + "].operator"
            );
        }

        if (value == null) {
            throw new QueryPlanValidationException(
                    "filter[" + index + "].value is required",
                    "filters[" + index + "].value"
            );
        }

        // Validate 'in' operator value is array
        if ("in".equals(operator) && !(value instanceof List)) {
            throw new QueryPlanValidationException(
                    "filter[" + index + "].value must be an array for 'in' operator",
                    "filters[" + index + "].value"
            );
        }

        // Validate 'between' operator value is array with 2 elements
        if ("between".equals(operator)) {
            if (!(value instanceof List)) {
                throw new QueryPlanValidationException(
                        "filter[" + index + "].value must be an array for 'between' operator",
                        "filters[" + index + "].value"
                );
            }
            List<?> betweenValues = (List<?>) value;
            if (betweenValues.size() != 2) {
                throw new QueryPlanValidationException(
                        "filter[" + index + "].value must have exactly 2 elements for 'between' operator",
                        "filters[" + index + "].value"
                );
            }
        }
    }

    @SuppressWarnings("unchecked")
    private void validateAggregations(Map<String, Object> queryPlan) {
        List<Map<String, Object>> aggregations = (List<Map<String, Object>>) queryPlan.get("aggregations");
        if (aggregations == null || aggregations.isEmpty()) {
            return;
        }

        String entity = (String) queryPlan.get("entity");
        String operation = (String) queryPlan.get("operation");

        if (!"aggregate".equals(operation)) {
            log.warn("aggregations provided but operation is not 'aggregate'");
        }

        for (int i = 0; i < aggregations.size(); i++) {
            Map<String, Object> aggregation = aggregations.get(i);
            validateAggregation(aggregation, entity, i);
        }
    }

    private void validateAggregation(Map<String, Object> aggregation, String entity, int index) {
        String function = (String) aggregation.get("function");
        String field = (String) aggregation.get("field");

        if (function == null || !VALID_AGGREGATION_FUNCTIONS.contains(function)) {
            throw new QueryPlanValidationException(
                    "INVALID_AGGREGATION",
                    "Invalid aggregation function: " + function + ". Allowed: " + VALID_AGGREGATION_FUNCTIONS,
                    "aggregations[" + index + "].function"
            );
        }

        if (field == null || field.isBlank()) {
            throw new QueryPlanValidationException(
                    "aggregations[" + index + "].field is required",
                    "aggregations[" + index + "].field"
            );
        }

        // count(*) is special case
        if (!"*".equals(field) && !chatOpsProperties.hasField(entity, field)) {
            throw new QueryPlanValidationException(
                    "INVALID_FIELD",
                    "Unknown field: " + field + " for entity: " + entity,
                    "aggregations[" + index + "].field"
            );
        }
    }

    @SuppressWarnings("unchecked")
    private void validateOrderBy(Map<String, Object> queryPlan) {
        List<Map<String, Object>> orderByList = (List<Map<String, Object>>) queryPlan.get("orderBy");
        if (orderByList == null || orderByList.isEmpty()) {
            return;
        }

        String entity = (String) queryPlan.get("entity");

        for (int i = 0; i < orderByList.size(); i++) {
            Map<String, Object> orderBy = orderByList.get(i);
            validateOrderByItem(orderBy, entity, i);
        }
    }

    private void validateOrderByItem(Map<String, Object> orderBy, String entity, int index) {
        String field = (String) orderBy.get("field");
        String direction = (String) orderBy.get("direction");

        if (field == null || field.isBlank()) {
            throw new QueryPlanValidationException(
                    "orderBy[" + index + "].field is required",
                    "orderBy[" + index + "].field"
            );
        }

        if (!chatOpsProperties.hasField(entity, field)) {
            throw new QueryPlanValidationException(
                    "INVALID_FIELD",
                    "Unknown field: " + field + " for entity: " + entity,
                    "orderBy[" + index + "].field"
            );
        }

        if (direction != null && !VALID_DIRECTIONS.contains(direction.toLowerCase())) {
            throw new QueryPlanValidationException(
                    "INVALID_DIRECTION",
                    "Invalid direction: " + direction + ". Allowed: " + VALID_DIRECTIONS,
                    "orderBy[" + index + "].direction"
            );
        }
    }

    @SuppressWarnings("unchecked")
    private void validateTimeRange(Map<String, Object> queryPlan) {
        String entity = (String) queryPlan.get("entity");

        if (chatOpsProperties.isTimeRangeRequired(entity)) {
            Map<String, Object> timeRange = (Map<String, Object>) queryPlan.get("timeRange");
            if (timeRange == null) {
                throw new QueryPlanValidationException(
                        "TIME_RANGE_REQUIRED",
                        "timeRange is required for entity: " + entity,
                        "timeRange"
                );
            }
            if (!timeRange.containsKey("start") || !timeRange.containsKey("end")) {
                throw new QueryPlanValidationException(
                        "timeRange.start and timeRange.end are required",
                        "timeRange"
                );
            }
        }
    }
}
