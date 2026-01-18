package com.chatops.core.domain.repository;

import com.chatops.core.domain.entity.ChatMessageEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ChatMessageRepository extends JpaRepository<ChatMessageEntity, String> {

    /**
     * Find messages by session ID, ordered by created_at ascending
     */
    List<ChatMessageEntity> findBySessionIdOrderByCreatedAtAsc(String sessionId);
}
