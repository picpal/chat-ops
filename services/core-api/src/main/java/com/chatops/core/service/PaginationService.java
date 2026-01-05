package com.chatops.core.service;

import com.chatops.core.config.ChatOpsProperties;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@RequiredArgsConstructor
public class PaginationService {

    private final ChatOpsProperties chatOpsProperties;
    private final SqlBuilderService sqlBuilderService;

    // In-memory token storage (실제 운영에서는 Redis 사용 권장)
    private final Map<String, PaginationContext> tokenStore = new ConcurrentHashMap<>();

    /**
     * 첫 페이지 조회 후 다음 페이지를 위한 토큰 생성
     */
    public String createToken(Map<String, Object> queryPlan, List<Map<String, Object>> currentRows, int limit) {
        String token = generateToken();

        // Build SQL for next page
        Map<String, Object> nextPagePlan = new HashMap<>(queryPlan);
        nextPagePlan.put("offset", limit);  // Start from where we left off

        SqlBuilderService.SqlQuery sqlQuery = sqlBuilderService.buildQuery(nextPagePlan);

        PaginationContext context = new PaginationContext();
        context.setToken(token);
        context.setSql(sqlQuery.getSql());
        context.setParams(sqlQuery.getParams());
        context.setPageSize(limit);
        context.setCurrentPage(1);
        context.setCurrentOffset(limit);
        context.setCreatedAt(Instant.now());
        context.setExpiresAt(Instant.now().plusSeconds(
                chatOpsProperties.getQuery().getTokenExpiryMinutes() * 60L
        ));
        context.setOriginalQueryPlan(queryPlan);

        tokenStore.put(token, context);

        log.debug("Created pagination token: {} for next page (offset: {})", token, limit);
        return token;
    }

    /**
     * 기존 컨텍스트에서 다음 페이지 토큰 생성
     */
    public String createNextPageToken(PaginationContext currentContext) {
        String token = generateToken();

        // Calculate next offset
        int nextOffset = currentContext.getCurrentOffset() + currentContext.getPageSize();

        // Update query plan with new offset
        Map<String, Object> nextPagePlan = new HashMap<>(currentContext.getOriginalQueryPlan());
        nextPagePlan.put("offset", nextOffset);

        SqlBuilderService.SqlQuery sqlQuery = sqlBuilderService.buildQuery(nextPagePlan);

        PaginationContext nextContext = new PaginationContext();
        nextContext.setToken(token);
        nextContext.setSql(sqlQuery.getSql());
        nextContext.setParams(sqlQuery.getParams());
        nextContext.setPageSize(currentContext.getPageSize());
        nextContext.setCurrentPage(currentContext.getCurrentPage() + 1);
        nextContext.setCurrentOffset(nextOffset);
        nextContext.setCreatedAt(Instant.now());
        nextContext.setExpiresAt(Instant.now().plusSeconds(
                chatOpsProperties.getQuery().getTokenExpiryMinutes() * 60L
        ));
        nextContext.setOriginalQueryPlan(currentContext.getOriginalQueryPlan());

        // Remove old token
        tokenStore.remove(currentContext.getToken());

        // Store new token
        tokenStore.put(token, nextContext);

        log.debug("Created next page token: {} (page: {}, offset: {})",
                token, nextContext.getCurrentPage(), nextOffset);

        return token;
    }

    /**
     * 토큰으로 페이징 컨텍스트 조회
     */
    public PaginationContext getContext(String token) {
        PaginationContext context = tokenStore.get(token);

        if (context == null) {
            log.warn("Token not found: {}", token);
            return null;
        }

        if (context.isExpired()) {
            log.warn("Token expired: {}", token);
            tokenStore.remove(token);
            return null;
        }

        return context;
    }

    /**
     * 토큰 무효화
     */
    public void invalidateToken(String token) {
        tokenStore.remove(token);
        log.debug("Invalidated token: {}", token);
    }

    /**
     * 만료된 토큰 정리 (1분마다 실행)
     */
    @Scheduled(fixedRate = 60000)
    public void cleanupExpiredTokens() {
        int beforeSize = tokenStore.size();
        tokenStore.entrySet().removeIf(entry -> entry.getValue().isExpired());
        int removed = beforeSize - tokenStore.size();
        if (removed > 0) {
            log.info("Cleaned up {} expired pagination tokens", removed);
        }
    }

    private String generateToken() {
        return "qt_" + UUID.randomUUID().toString().replace("-", "");
    }

    /**
     * 페이징 컨텍스트
     */
    @Data
    public static class PaginationContext {
        private String token;
        private String sql;
        private List<Object> params;
        private int pageSize;
        private int currentPage;
        private int currentOffset;
        private Instant createdAt;
        private Instant expiresAt;
        private Map<String, Object> originalQueryPlan;

        public boolean isExpired() {
            return Instant.now().isAfter(expiresAt);
        }

        public boolean hasNextPage(int currentRowCount) {
            return currentRowCount >= pageSize;
        }
    }
}
