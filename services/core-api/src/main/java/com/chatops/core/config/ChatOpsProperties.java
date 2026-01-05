package com.chatops.core.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Data
@Component
@ConfigurationProperties(prefix = "chatops")
public class ChatOpsProperties {

    private QueryConfig query = new QueryConfig();
    private Map<String, EntityMapping> entityMappings = new HashMap<>();

    @Data
    public static class QueryConfig {
        private int maxLimit = 1000;
        private int defaultLimit = 10;
        private int tokenExpiryMinutes = 60;
    }

    @Data
    public static class EntityMapping {
        private String table;
        private Map<String, String> fields = new HashMap<>();
        private String defaultOrderBy;
        private boolean timeRangeRequired = false;
    }

    /**
     * 논리 엔티티명으로 물리 테이블명 조회
     */
    public String getTableName(String entity) {
        EntityMapping mapping = entityMappings.get(entity);
        if (mapping == null) {
            throw new IllegalArgumentException("Unknown entity: " + entity);
        }
        return mapping.getTable();
    }

    /**
     * 논리 필드명으로 물리 컬럼명 조회
     */
    public String getColumnName(String entity, String field) {
        EntityMapping mapping = entityMappings.get(entity);
        if (mapping == null) {
            throw new IllegalArgumentException("Unknown entity: " + entity);
        }
        String column = mapping.getFields().get(field);
        if (column == null) {
            throw new IllegalArgumentException("Unknown field: " + field + " for entity: " + entity);
        }
        return column;
    }

    /**
     * 엔티티 존재 여부 확인
     */
    public boolean hasEntity(String entity) {
        return entityMappings.containsKey(entity);
    }

    /**
     * 필드 존재 여부 확인
     */
    public boolean hasField(String entity, String field) {
        EntityMapping mapping = entityMappings.get(entity);
        return mapping != null && mapping.getFields().containsKey(field);
    }

    /**
     * 엔티티의 기본 정렬 조건 조회
     */
    public String getDefaultOrderBy(String entity) {
        EntityMapping mapping = entityMappings.get(entity);
        return mapping != null ? mapping.getDefaultOrderBy() : null;
    }

    /**
     * 시계열 데이터 여부 확인
     */
    public boolean isTimeRangeRequired(String entity) {
        EntityMapping mapping = entityMappings.get(entity);
        return mapping != null && mapping.isTimeRangeRequired();
    }
}
