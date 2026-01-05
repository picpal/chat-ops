package com.chatops.core.domain.repository;

import com.chatops.core.domain.entity.Order;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {

    // Find orders by status
    List<Order> findByStatus(String status);

    // Find recent orders (limit handled in controller)
    List<Order> findAllByOrderByOrderDateDesc();

    // Find orders by customer
    List<Order> findByCustomerId(Long customerId);
}
