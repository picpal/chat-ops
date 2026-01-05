package com.chatops.core.service;

import com.chatops.core.config.ChatOpsProperties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

/**
 * PaginationService 단위 테스트
 * Mockito를 사용하여 의존성 모킹
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("PaginationService 단위 테스트")
class PaginationServiceUnitTest {

    @Mock
    private SqlBuilderService sqlBuilderService;

    private PaginationService paginationService;
    private ChatOpsProperties properties;

    @BeforeEach
    void setUp() {
        properties = createTestProperties();
        paginationService = new PaginationService(properties, sqlBuilderService);
    }

    private ChatOpsProperties createTestProperties() {
        ChatOpsProperties props = new ChatOpsProperties();
        ChatOpsProperties.QueryConfig queryConfig = new ChatOpsProperties.QueryConfig();
        queryConfig.setMaxLimit(1000);
        queryConfig.setDefaultLimit(10);
        queryConfig.setTokenExpiryMinutes(60);
        props.setQuery(queryConfig);
        return props;
    }

    @Nested
    @DisplayName("토큰 생성")
    class TokenCreation {

        @Test
        @DisplayName("첫 페이지 조회 후 토큰 생성")
        void shouldCreateTokenAfterFirstPage() {
            // Given
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 10
            );
            List<Map<String, Object>> currentRows = List.of(
                Map.of("orderId", 1),
                Map.of("orderId", 2)
            );

            when(sqlBuilderService.buildQuery(any()))
                .thenReturn(new SqlBuilderService.SqlQuery(
                    "SELECT * FROM orders LIMIT ? OFFSET ?",
                    List.of(10, 10)
                ));

            // When
            String token = paginationService.createToken(queryPlan, currentRows, 10);

            // Then
            assertThat(token)
                .isNotNull()
                .startsWith("qt_")
                .hasSize(35); // "qt_" + 32 chars UUID
        }

        @Test
        @DisplayName("생성된 토큰으로 컨텍스트 조회 가능")
        void shouldRetrieveContextByToken() {
            // Given
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 10
            );

            when(sqlBuilderService.buildQuery(any()))
                .thenReturn(new SqlBuilderService.SqlQuery(
                    "SELECT * FROM orders LIMIT ? OFFSET ?",
                    List.of(10, 10)
                ));

            String token = paginationService.createToken(queryPlan, List.of(), 10);

            // When
            PaginationService.PaginationContext context = paginationService.getContext(token);

            // Then
            assertThat(context).isNotNull();
            assertThat(context.getToken()).isEqualTo(token);
            assertThat(context.getPageSize()).isEqualTo(10);
            assertThat(context.getCurrentPage()).isEqualTo(1);
            assertThat(context.getCurrentOffset()).isEqualTo(10);
        }
    }

    @Nested
    @DisplayName("다음 페이지 토큰 생성")
    class NextPageTokenCreation {

        @Test
        @DisplayName("현재 컨텍스트에서 다음 페이지 토큰 생성")
        void shouldCreateNextPageToken() {
            // Given
            Map<String, Object> queryPlan = new HashMap<>();
            queryPlan.put("entity", "Order");
            queryPlan.put("operation", "list");
            queryPlan.put("limit", 10);

            when(sqlBuilderService.buildQuery(any()))
                .thenReturn(new SqlBuilderService.SqlQuery(
                    "SELECT * FROM orders LIMIT ? OFFSET ?",
                    List.of(10, 10)
                ));

            String firstToken = paginationService.createToken(queryPlan, List.of(), 10);
            PaginationService.PaginationContext firstContext = paginationService.getContext(firstToken);

            // When
            String nextToken = paginationService.createNextPageToken(firstContext);

            // Then
            assertThat(nextToken).isNotEqualTo(firstToken);

            PaginationService.PaginationContext nextContext = paginationService.getContext(nextToken);
            assertThat(nextContext.getCurrentPage()).isEqualTo(2);
            assertThat(nextContext.getCurrentOffset()).isEqualTo(20);
        }

        @Test
        @DisplayName("다음 페이지 토큰 생성 시 이전 토큰 무효화")
        void shouldInvalidateOldTokenWhenCreatingNext() {
            // Given
            Map<String, Object> queryPlan = new HashMap<>();
            queryPlan.put("entity", "Order");
            queryPlan.put("operation", "list");
            queryPlan.put("limit", 10);

            when(sqlBuilderService.buildQuery(any()))
                .thenReturn(new SqlBuilderService.SqlQuery(
                    "SELECT * FROM orders LIMIT ? OFFSET ?",
                    List.of(10, 10)
                ));

            String firstToken = paginationService.createToken(queryPlan, List.of(), 10);
            PaginationService.PaginationContext firstContext = paginationService.getContext(firstToken);

            // When
            paginationService.createNextPageToken(firstContext);

            // Then
            assertThat(paginationService.getContext(firstToken)).isNull();
        }
    }

    @Nested
    @DisplayName("토큰 조회")
    class TokenRetrieval {

        @Test
        @DisplayName("존재하지 않는 토큰 조회 시 null 반환")
        void shouldReturnNullForNonExistentToken() {
            // When
            PaginationService.PaginationContext context = paginationService.getContext("invalid_token");

            // Then
            assertThat(context).isNull();
        }
    }

    @Nested
    @DisplayName("토큰 무효화")
    class TokenInvalidation {

        @Test
        @DisplayName("토큰 무효화 후 조회 불가")
        void shouldNotRetrieveInvalidatedToken() {
            // Given
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 10
            );

            when(sqlBuilderService.buildQuery(any()))
                .thenReturn(new SqlBuilderService.SqlQuery(
                    "SELECT * FROM orders LIMIT ?",
                    List.of(10)
                ));

            String token = paginationService.createToken(queryPlan, List.of(), 10);

            // When
            paginationService.invalidateToken(token);

            // Then
            assertThat(paginationService.getContext(token)).isNull();
        }
    }

    @Nested
    @DisplayName("PaginationContext")
    class PaginationContextTests {

        @Test
        @DisplayName("만료되지 않은 컨텍스트")
        void shouldNotBeExpiredWhenFresh() {
            PaginationService.PaginationContext context = new PaginationService.PaginationContext();
            context.setExpiresAt(Instant.now().plusSeconds(3600));

            assertThat(context.isExpired()).isFalse();
        }

        @Test
        @DisplayName("만료된 컨텍스트")
        void shouldBeExpiredWhenPastExpiryTime() {
            PaginationService.PaginationContext context = new PaginationService.PaginationContext();
            context.setExpiresAt(Instant.now().minusSeconds(1));

            assertThat(context.isExpired()).isTrue();
        }

        @Test
        @DisplayName("다음 페이지 존재 여부 - pageSize 이상의 결과")
        void shouldHaveNextPageWhenResultsEqualPageSize() {
            PaginationService.PaginationContext context = new PaginationService.PaginationContext();
            context.setPageSize(10);

            assertThat(context.hasNextPage(10)).isTrue();
            assertThat(context.hasNextPage(15)).isTrue();
        }

        @Test
        @DisplayName("다음 페이지 없음 - pageSize 미만의 결과")
        void shouldNotHaveNextPageWhenResultsLessThanPageSize() {
            PaginationService.PaginationContext context = new PaginationService.PaginationContext();
            context.setPageSize(10);

            assertThat(context.hasNextPage(5)).isFalse();
            assertThat(context.hasNextPage(0)).isFalse();
        }
    }

    @Nested
    @DisplayName("만료 토큰 정리")
    class ExpiredTokenCleanup {

        @Test
        @DisplayName("만료된 토큰 정리 메서드 호출 성공")
        void shouldCleanupExpiredTokensWithoutException() {
            // Given
            Map<String, Object> queryPlan = Map.of(
                "entity", "Order",
                "operation", "list",
                "limit", 10
            );

            when(sqlBuilderService.buildQuery(any()))
                .thenReturn(new SqlBuilderService.SqlQuery(
                    "SELECT * FROM orders LIMIT ?",
                    List.of(10)
                ));

            paginationService.createToken(queryPlan, List.of(), 10);

            // When & Then
            assertThatCode(() -> paginationService.cleanupExpiredTokens())
                .doesNotThrowAnyException();
        }
    }
}
