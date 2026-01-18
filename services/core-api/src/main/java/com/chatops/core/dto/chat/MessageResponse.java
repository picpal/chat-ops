package com.chatops.core.dto.chat;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MessageResponse {
    private String messageId;
    private String role;
    private String content;
    private Object renderSpec;
    private Object queryResult;
    private Object queryPlan;
    private String status;
    private OffsetDateTime createdAt;
}
