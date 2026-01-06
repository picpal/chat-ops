package com.chatops.core.domain.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

@Entity
@Table(name = "settlement_details")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SettlementDetail {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "detail_id")
    private Long detailId;

    @Column(name = "settlement_id", nullable = false, length = 50)
    private String settlementId;

    @Column(name = "transaction_type", nullable = false, length = 20)
    private String transactionType;

    @Column(name = "payment_key", length = 200)
    private String paymentKey;

    @Column(name = "refund_key", length = 200)
    private String refundKey;

    @Column(name = "amount", nullable = false)
    private Long amount;

    @Column(name = "fee")
    @Builder.Default
    private Long fee = 0L;

    @Column(name = "net_amount", nullable = false)
    private Long netAmount;

    @Column(name = "method", length = 30)
    private String method;

    @Column(name = "transaction_at", nullable = false)
    private OffsetDateTime transactionAt;

    @Column(name = "metadata", columnDefinition = "jsonb")
    private String metadata;

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = OffsetDateTime.now();
    }
}
