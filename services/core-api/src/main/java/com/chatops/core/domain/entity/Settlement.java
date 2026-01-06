package com.chatops.core.domain.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.OffsetDateTime;

@Entity
@Table(name = "settlements")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Settlement {

    @Id
    @Column(name = "settlement_id", length = 50)
    private String settlementId;

    @Column(name = "merchant_id", nullable = false, length = 50)
    private String merchantId;

    @Column(name = "settlement_date", nullable = false)
    private LocalDate settlementDate;

    @Column(name = "period_start", nullable = false)
    private LocalDate periodStart;

    @Column(name = "period_end", nullable = false)
    private LocalDate periodEnd;

    @Column(name = "total_payment_amount", nullable = false)
    private Long totalPaymentAmount;

    @Column(name = "total_refund_amount")
    @Builder.Default
    private Long totalRefundAmount = 0L;

    @Column(name = "total_fee")
    @Builder.Default
    private Long totalFee = 0L;

    @Column(name = "net_amount", nullable = false)
    private Long netAmount;

    @Column(name = "payment_count")
    @Builder.Default
    private Integer paymentCount = 0;

    @Column(name = "refund_count")
    @Builder.Default
    private Integer refundCount = 0;

    @Column(name = "status", nullable = false, length = 30)
    @Builder.Default
    private String status = "PENDING";

    @Column(name = "payout_bank_code", length = 10)
    private String payoutBankCode;

    @Column(name = "payout_account_number", length = 50)
    private String payoutAccountNumber;

    @Column(name = "payout_account_holder", length = 100)
    private String payoutAccountHolder;

    @Column(name = "payout_reference", length = 100)
    private String payoutReference;

    @Column(name = "processed_at")
    private OffsetDateTime processedAt;

    @Column(name = "paid_out_at")
    private OffsetDateTime paidOutAt;

    @Column(name = "failure_code", length = 50)
    private String failureCode;

    @Column(name = "failure_message", length = 500)
    private String failureMessage;

    @Column(name = "metadata", columnDefinition = "jsonb")
    private String metadata;

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @Column(name = "updated_at")
    private OffsetDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = OffsetDateTime.now();
        updatedAt = OffsetDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = OffsetDateTime.now();
    }
}
