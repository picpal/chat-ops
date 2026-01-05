package com.chatops.core.domain.repository;

import com.chatops.core.domain.entity.Order;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.ActiveProfiles;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@ActiveProfiles("test")
@DisplayName("OrderRepository 테스트")
class OrderRepositoryTest {

    @Autowired
    private OrderRepository orderRepository;

    @Test
    @DisplayName("주문 저장 및 조회")
    void saveAndFind() {
        // Given
        Order order = Order.builder()
                .customerId(101L)
                .orderDate(LocalDateTime.now())
                .totalAmount(new BigDecimal("2499.00"))
                .status("PAID")
                .paymentGateway("Stripe")
                .build();

        // When
        Order saved = orderRepository.save(order);

        // Then
        assertThat(saved.getOrderId()).isNotNull();
        assertThat(saved.getCustomerId()).isEqualTo(101L);
        assertThat(saved.getTotalAmount()).isEqualByComparingTo("2499.00");
        assertThat(saved.getStatus()).isEqualTo("PAID");
    }

    @Test
    @DisplayName("상태별 주문 조회")
    void findByStatus() {
        // Given
        orderRepository.save(createOrder(101L, "PAID"));
        orderRepository.save(createOrder(102L, "PENDING"));
        orderRepository.save(createOrder(103L, "PAID"));

        // When
        List<Order> paidOrders = orderRepository.findByStatus("PAID");

        // Then
        assertThat(paidOrders).hasSize(2);
        assertThat(paidOrders).allMatch(order -> order.getStatus().equals("PAID"));
    }

    @Test
    @DisplayName("최신 주문 순으로 조회")
    void findAllByOrderByOrderDateDesc() {
        // Given
        Order order1 = createOrder(101L, "PAID");
        order1.setOrderDate(LocalDateTime.now().minusDays(2));
        orderRepository.save(order1);

        Order order2 = createOrder(102L, "PENDING");
        order2.setOrderDate(LocalDateTime.now().minusDays(1));
        orderRepository.save(order2);

        Order order3 = createOrder(103L, "SHIPPED");
        order3.setOrderDate(LocalDateTime.now());
        orderRepository.save(order3);

        // When
        List<Order> orders = orderRepository.findAllByOrderByOrderDateDesc();

        // Then
        assertThat(orders).hasSize(3);
        assertThat(orders.get(0).getCustomerId()).isEqualTo(103L); // 가장 최신
        assertThat(orders.get(1).getCustomerId()).isEqualTo(102L);
        assertThat(orders.get(2).getCustomerId()).isEqualTo(101L); // 가장 오래됨
    }

    @Test
    @DisplayName("고객별 주문 조회")
    void findByCustomerId() {
        // Given
        orderRepository.save(createOrder(101L, "PAID"));
        orderRepository.save(createOrder(101L, "PENDING"));
        orderRepository.save(createOrder(102L, "PAID"));

        // When
        List<Order> customerOrders = orderRepository.findByCustomerId(101L);

        // Then
        assertThat(customerOrders).hasSize(2);
        assertThat(customerOrders).allMatch(order -> order.getCustomerId().equals(101L));
    }

    private Order createOrder(Long customerId, String status) {
        return Order.builder()
                .customerId(customerId)
                .orderDate(LocalDateTime.now())
                .totalAmount(new BigDecimal("1000.00"))
                .status(status)
                .paymentGateway("Stripe")
                .build();
    }
}
