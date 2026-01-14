package com.chatops.core.controller;

import com.chatops.core.service.PaginationService;
import com.chatops.core.service.QueryExecutorService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/query")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class QueryController {

    private final QueryExecutorService queryExecutorService;
    private final PaginationService paginationService;

    /**
     * Step 5: QueryPlan 실행 엔진
     * - QueryPlan 검증
     * - 논리 엔티티 → SQL 변환
     * - 쿼리 실행
     * - 페이지네이션 지원
     */
    @PostMapping("/start")
    public ResponseEntity<Map<String, Object>> startQuery(@RequestBody Map<String, Object> queryPlan) {
        log.info("Received QueryPlan: {}", queryPlan);

        Map<String, Object> result = queryExecutorService.executeQuery(queryPlan);

        String status = (String) result.get("status");
        if ("error".equals(status)) {
            // Check error code to determine HTTP status
            @SuppressWarnings("unchecked")
            Map<String, Object> error = (Map<String, Object>) result.get("error");
            String errorCode = (String) error.get("code");

            if ("VALIDATION_ERROR".equals(errorCode) ||
                    "INVALID_ENTITY".equals(errorCode) ||
                    "INVALID_OPERATION".equals(errorCode) ||
                    "INVALID_FIELD".equals(errorCode) ||
                    "INVALID_OPERATOR".equals(errorCode)) {
                return ResponseEntity.badRequest().body(result);
            }
            return ResponseEntity.internalServerError().body(result);
        }

        return ResponseEntity.ok(result);
    }

    /**
     * 다음 페이지 조회
     */
    @GetMapping("/page/{token}")
    public ResponseEntity<Map<String, Object>> getPage(@PathVariable String token) {
        log.info("Page requested with token: {}", token);

        PaginationService.PaginationContext context = paginationService.getContext(token);

        if (context == null) {
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("requestId", "unknown");
            errorResponse.put("status", "error");
            errorResponse.put("error", Map.of(
                    "code", "INVALID_TOKEN",
                    "message", "Query token is invalid or expired"
            ));
            return ResponseEntity.badRequest().body(errorResponse);
        }

        // Execute query using the pagination context
        Map<String, Object> queryPlanWithToken = new HashMap<>();
        queryPlanWithToken.put("queryToken", token);
        queryPlanWithToken.put("requestId", "page-" + token.substring(0, 8));

        Map<String, Object> result = queryExecutorService.executeQuery(queryPlanWithToken);

        return ResponseEntity.ok(result);
    }

    /**
     * 특정 페이지 번호로 이동
     */
    @GetMapping("/page/{token}/goto/{pageNumber}")
    public ResponseEntity<Map<String, Object>> goToPage(
            @PathVariable String token,
            @PathVariable int pageNumber
    ) {
        log.info("Go to page {} requested with token: {}", pageNumber, token);

        PaginationService.PaginationContext context = paginationService.getContext(token);

        if (context == null) {
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("requestId", "unknown");
            errorResponse.put("status", "error");
            errorResponse.put("error", Map.of(
                    "code", "INVALID_TOKEN",
                    "message", "Query token is invalid or expired"
            ));
            return ResponseEntity.badRequest().body(errorResponse);
        }

        // Validate page number
        if (pageNumber < 1 || pageNumber > context.getTotalPages()) {
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("requestId", "page-" + token.substring(0, 8));
            errorResponse.put("status", "error");
            errorResponse.put("error", Map.of(
                    "code", "INVALID_PAGE",
                    "message", "Page number must be between 1 and " + context.getTotalPages()
            ));
            return ResponseEntity.badRequest().body(errorResponse);
        }

        // Create context for the target page (updates the stored context with new offset)
        PaginationService.PaginationContext pageContext = paginationService.createContextForPage(context, pageNumber);

        if (pageContext == null) {
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("requestId", "page-" + token.substring(0, 8));
            errorResponse.put("status", "error");
            errorResponse.put("error", Map.of(
                    "code", "PAGE_ERROR",
                    "message", "Failed to navigate to page " + pageNumber
            ));
            return ResponseEntity.internalServerError().body(errorResponse);
        }

        // Execute query using the updated context
        Map<String, Object> queryPlanWithToken = new HashMap<>();
        queryPlanWithToken.put("queryToken", token);
        queryPlanWithToken.put("requestId", "page-" + token.substring(0, 8));

        Map<String, Object> result = queryExecutorService.executeQuery(queryPlanWithToken);

        // Override pagination info with accurate values
        Map<String, Object> pagination = new HashMap<>();
        pagination.put("queryToken", token);
        pagination.put("currentPage", pageNumber);
        pagination.put("totalPages", pageContext.getTotalPages());
        pagination.put("totalRows", pageContext.getTotalRows());
        pagination.put("pageSize", pageContext.getPageSize());
        pagination.put("hasMore", pageNumber < pageContext.getTotalPages());
        result.put("pagination", pagination);

        return ResponseEntity.ok(result);
    }

    /**
     * Health check endpoint
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of(
                "status", "UP",
                "service", "core-api",
                "step", "5-query-engine"
        ));
    }
}
