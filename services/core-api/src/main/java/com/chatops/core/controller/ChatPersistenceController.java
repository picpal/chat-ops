package com.chatops.core.controller;

import com.chatops.core.dto.chat.*;
import com.chatops.core.service.ChatPersistenceService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/v1/chat")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class ChatPersistenceController {

    private final ChatPersistenceService chatPersistenceService;

    /**
     * Login or create user
     * POST /api/v1/chat/users/login
     */
    @PostMapping("/users/login")
    public ResponseEntity<UserLoginResponse> loginOrCreateUser(@RequestBody UserLoginRequest request) {
        log.info("Login or create user: email={}", request.getEmail());

        if (request.getEmail() == null || request.getEmail().isBlank()) {
            return ResponseEntity.badRequest().build();
        }

        UserLoginResponse response = chatPersistenceService.loginOrCreateUser(
                request.getEmail(),
                request.getDisplayName()
        );

        return ResponseEntity.ok(response);
    }

    /**
     * Get sessions by user ID
     * GET /api/v1/chat/sessions
     * Header: X-User-Id
     */
    @GetMapping("/sessions")
    public ResponseEntity<List<SessionResponse>> getSessionsByUserId(
            @RequestHeader("X-User-Id") String userId
    ) {
        log.info("Get sessions by userId={}", userId);

        if (userId == null || userId.isBlank()) {
            return ResponseEntity.badRequest().build();
        }

        List<SessionResponse> sessions = chatPersistenceService.getSessionsByUserId(userId);

        return ResponseEntity.ok(sessions);
    }

    /**
     * Create new session
     * POST /api/v1/chat/sessions
     * Header: X-User-Id
     */
    @PostMapping("/sessions")
    public ResponseEntity<SessionResponse> createSession(
            @RequestHeader("X-User-Id") String userId,
            @RequestBody SessionCreateRequest request
    ) {
        log.info("Create session: userId={}, title={}", userId, request.getTitle());

        if (userId == null || userId.isBlank()) {
            return ResponseEntity.badRequest().build();
        }

        if (request.getTitle() == null || request.getTitle().isBlank()) {
            return ResponseEntity.badRequest().build();
        }

        SessionResponse response = chatPersistenceService.createSession(userId, request);

        return ResponseEntity.ok(response);
    }

    /**
     * Get session with messages
     * GET /api/v1/chat/sessions/{sessionId}
     */
    @GetMapping("/sessions/{sessionId}")
    public ResponseEntity<SessionResponse> getSessionWithMessages(
            @PathVariable String sessionId
    ) {
        log.info("Get session with messages: sessionId={}", sessionId);

        try {
            SessionResponse response = chatPersistenceService.getSessionWithMessages(sessionId);
            return ResponseEntity.ok(response);
        } catch (IllegalArgumentException e) {
            log.error("Session not found: {}", sessionId);
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * Update session title
     * PATCH /api/v1/chat/sessions/{sessionId}
     */
    @PatchMapping("/sessions/{sessionId}")
    public ResponseEntity<SessionResponse> updateSessionTitle(
            @PathVariable String sessionId,
            @RequestBody SessionUpdateRequest request
    ) {
        log.info("Update session: sessionId={}", sessionId);

        try {
            SessionResponse response = chatPersistenceService.updateSessionTitle(sessionId, request);
            return ResponseEntity.ok(response);
        } catch (IllegalArgumentException e) {
            log.error("Session not found: {}", sessionId);
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * Delete session
     * DELETE /api/v1/chat/sessions/{sessionId}
     */
    @DeleteMapping("/sessions/{sessionId}")
    public ResponseEntity<Void> deleteSession(
            @PathVariable String sessionId
    ) {
        log.info("Delete session: sessionId={}", sessionId);

        try {
            chatPersistenceService.deleteSession(sessionId);
            return ResponseEntity.noContent().build();
        } catch (IllegalArgumentException e) {
            log.error("Session not found: {}", sessionId);
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * Add message to session
     * POST /api/v1/chat/sessions/{sessionId}/messages
     */
    @PostMapping("/sessions/{sessionId}/messages")
    public ResponseEntity<MessageResponse> addMessage(
            @PathVariable String sessionId,
            @RequestBody MessageCreateRequest request
    ) {
        log.info("Add message: sessionId={}, messageId={}", sessionId, request.getMessageId());

        if (request.getMessageId() == null || request.getMessageId().isBlank()) {
            return ResponseEntity.badRequest().build();
        }

        if (request.getRole() == null || request.getRole().isBlank()) {
            return ResponseEntity.badRequest().build();
        }

        try {
            MessageResponse response = chatPersistenceService.addMessage(sessionId, request);
            return ResponseEntity.ok(response);
        } catch (IllegalArgumentException e) {
            log.error("Session not found: {}", sessionId);
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * Health check endpoint
     */
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Chat Persistence API is UP");
    }
}
