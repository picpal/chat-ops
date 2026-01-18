package com.chatops.core.service;

import com.chatops.core.domain.entity.ChatMessageEntity;
import com.chatops.core.domain.entity.ChatSession;
import com.chatops.core.domain.entity.ChatUser;
import com.chatops.core.domain.repository.ChatMessageRepository;
import com.chatops.core.domain.repository.ChatSessionRepository;
import com.chatops.core.domain.repository.ChatUserRepository;
import com.chatops.core.dto.chat.*;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatPersistenceService {

    private final ChatUserRepository userRepository;
    private final ChatSessionRepository sessionRepository;
    private final ChatMessageRepository messageRepository;
    private final ObjectMapper objectMapper;

    /**
     * Login or create user
     */
    @Transactional
    public UserLoginResponse loginOrCreateUser(String email, String displayName) {
        log.info("Login or create user: email={}, displayName={}", email, displayName);

        var existingUser = userRepository.findByEmail(email);

        if (existingUser.isPresent()) {
            ChatUser user = existingUser.get();
            log.info("User found: userId={}", user.getUserId());
            return UserLoginResponse.builder()
                    .userId(user.getUserId())
                    .email(user.getEmail())
                    .displayName(user.getDisplayName())
                    .isNewUser(false)
                    .build();
        }

        // Create new user
        String userId = "user-" + UUID.randomUUID().toString().substring(0, 8);
        ChatUser newUser = ChatUser.builder()
                .userId(userId)
                .email(email)
                .displayName(displayName != null ? displayName : email.split("@")[0])
                .status("ACTIVE")
                .build();

        userRepository.save(newUser);
        log.info("New user created: userId={}", userId);

        return UserLoginResponse.builder()
                .userId(userId)
                .email(email)
                .displayName(newUser.getDisplayName())
                .isNewUser(true)
                .build();
    }

    /**
     * Get sessions by user ID
     */
    @Transactional(readOnly = true)
    public List<SessionResponse> getSessionsByUserId(String userId) {
        log.info("Get sessions by userId={}", userId);

        List<ChatSession> sessions = sessionRepository.findByUserIdAndStatusOrderByUpdatedAtDesc(userId, "ACTIVE");

        return sessions.stream()
                .map(this::toSessionResponse)
                .collect(Collectors.toList());
    }

    /**
     * Create new session
     */
    @Transactional
    public SessionResponse createSession(String userId, SessionCreateRequest request) {
        log.info("Create session: userId={}, title={}", userId, request.getTitle());

        String sessionId = "session-" + UUID.randomUUID().toString();
        ChatSession session = ChatSession.builder()
                .sessionId(sessionId)
                .userId(userId)
                .title(request.getTitle())
                .subtitle(request.getSubtitle())
                .icon(request.getIcon() != null ? request.getIcon() : "chat")
                .status("ACTIVE")
                .build();

        sessionRepository.save(session);
        log.info("Session created: sessionId={}", sessionId);

        return toSessionResponse(session);
    }

    /**
     * Get session with messages
     */
    @Transactional(readOnly = true)
    public SessionResponse getSessionWithMessages(String sessionId) {
        log.info("Get session with messages: sessionId={}", sessionId);

        ChatSession session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new IllegalArgumentException("Session not found: " + sessionId));

        List<ChatMessageEntity> messages = messageRepository.findBySessionIdOrderByCreatedAtAsc(sessionId);

        SessionResponse response = toSessionResponse(session);
        response.setMessages(messages.stream()
                .map(this::toMessageResponse)
                .collect(Collectors.toList()));

        return response;
    }

    /**
     * Update session title
     */
    @Transactional
    public SessionResponse updateSessionTitle(String sessionId, SessionUpdateRequest request) {
        log.info("Update session title: sessionId={}, title={}", sessionId, request.getTitle());

        ChatSession session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new IllegalArgumentException("Session not found: " + sessionId));

        if (request.getTitle() != null) {
            session.setTitle(request.getTitle());
        }
        if (request.getSubtitle() != null) {
            session.setSubtitle(request.getSubtitle());
        }

        sessionRepository.save(session);
        log.info("Session updated: sessionId={}", sessionId);

        return toSessionResponse(session);
    }

    /**
     * Delete session (soft delete)
     */
    @Transactional
    public void deleteSession(String sessionId) {
        log.info("Delete session: sessionId={}", sessionId);

        ChatSession session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new IllegalArgumentException("Session not found: " + sessionId));

        session.setStatus("DELETED");
        sessionRepository.save(session);
        log.info("Session deleted: sessionId={}", sessionId);
    }

    /**
     * Add message to session
     */
    @Transactional
    public MessageResponse addMessage(String sessionId, MessageCreateRequest request) {
        log.info("Add message: sessionId={}, messageId={}, role={}", sessionId, request.getMessageId(), request.getRole());

        // Verify session exists
        sessionRepository.findById(sessionId)
                .orElseThrow(() -> new IllegalArgumentException("Session not found: " + sessionId));

        ChatMessageEntity message = ChatMessageEntity.builder()
                .messageId(request.getMessageId())
                .sessionId(sessionId)
                .role(request.getRole())
                .content(request.getContent())
                .renderSpec(toJsonString(request.getRenderSpec()))
                .queryResult(toJsonString(request.getQueryResult()))
                .queryPlan(toJsonString(request.getQueryPlan()))
                .status(request.getStatus() != null ? request.getStatus() : "success")
                .build();

        messageRepository.save(message);

        // Update session's updated_at
        ChatSession session = sessionRepository.findById(sessionId).orElseThrow();
        session.setUpdatedAt(java.time.OffsetDateTime.now());
        sessionRepository.save(session);

        log.info("Message added: messageId={}", request.getMessageId());

        return toMessageResponse(message);
    }

    /**
     * Convert ChatSession to SessionResponse
     */
    private SessionResponse toSessionResponse(ChatSession session) {
        return SessionResponse.builder()
                .sessionId(session.getSessionId())
                .title(session.getTitle())
                .subtitle(session.getSubtitle())
                .icon(session.getIcon())
                .status(session.getStatus())
                .createdAt(session.getCreatedAt())
                .updatedAt(session.getUpdatedAt())
                .build();
    }

    /**
     * Convert ChatMessageEntity to MessageResponse
     */
    private MessageResponse toMessageResponse(ChatMessageEntity message) {
        return MessageResponse.builder()
                .messageId(message.getMessageId())
                .role(message.getRole())
                .content(message.getContent())
                .renderSpec(parseJsonString(message.getRenderSpec()))
                .queryResult(parseJsonString(message.getQueryResult()))
                .queryPlan(parseJsonString(message.getQueryPlan()))
                .status(message.getStatus())
                .createdAt(message.getCreatedAt())
                .build();
    }

    /**
     * Convert object to JSON string
     */
    private String toJsonString(Object obj) {
        if (obj == null) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("Failed to convert object to JSON", e);
            return null;
        }
    }

    /**
     * Parse JSON string to object
     */
    private Object parseJsonString(String json) {
        if (json == null) {
            return null;
        }
        try {
            return objectMapper.readValue(json, Object.class);
        } catch (JsonProcessingException e) {
            log.error("Failed to parse JSON string", e);
            return null;
        }
    }
}
