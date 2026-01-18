package com.chatops.core.domain.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

@Entity
@Table(name = "chat_messages")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChatMessageEntity {

    @Id
    @Column(name = "message_id", length = 100)
    private String messageId;

    @Column(name = "session_id", nullable = false, length = 100)
    private String sessionId;

    @Column(name = "role", nullable = false, length = 20)
    private String role;

    @Column(name = "content", columnDefinition = "TEXT")
    private String content;

    @Column(name = "render_spec", columnDefinition = "jsonb")
    private String renderSpec;

    @Column(name = "query_result", columnDefinition = "jsonb")
    private String queryResult;

    @Column(name = "query_plan", columnDefinition = "jsonb")
    private String queryPlan;

    @Column(name = "status", length = 20)
    @Builder.Default
    private String status = "success";

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = OffsetDateTime.now();
    }
}
