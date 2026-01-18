package com.chatops.core.domain.repository;

import com.chatops.core.domain.entity.ChatSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ChatSessionRepository extends JpaRepository<ChatSession, String> {

    /**
     * Find sessions by user ID, ordered by updated_at descending
     */
    List<ChatSession> findByUserIdOrderByUpdatedAtDesc(String userId);

    /**
     * Find sessions by user ID and status, ordered by updated_at descending
     */
    List<ChatSession> findByUserIdAndStatusOrderByUpdatedAtDesc(String userId, String status);
}
