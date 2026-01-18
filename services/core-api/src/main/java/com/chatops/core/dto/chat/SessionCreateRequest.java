package com.chatops.core.dto.chat;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SessionCreateRequest {
    private String title;
    private String subtitle;
    private String icon;
}
