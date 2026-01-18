package com.chatops.core.dto.chat;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MessageCreateRequest {
    private String messageId;
    private String role;
    private String content;
    private Object renderSpec;
    private Object queryResult;
    private Object queryPlan;
    private String status;
}
