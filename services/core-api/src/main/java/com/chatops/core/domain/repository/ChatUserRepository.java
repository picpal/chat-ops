package com.chatops.core.domain.repository;

import com.chatops.core.domain.entity.ChatUser;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface ChatUserRepository extends JpaRepository<ChatUser, String> {

    /**
     * Find user by email
     */
    Optional<ChatUser> findByEmail(String email);
}
