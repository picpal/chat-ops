package com.chatops.core.dto.chat;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SessionResponse {
    private String sessionId;
    private String title;
    private String subtitle;
    private String icon;
    private String status;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private List<MessageResponse> messages;
}
