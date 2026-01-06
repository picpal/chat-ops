package com.chatops.core.domain.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

@Entity
@Table(name = "payments")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Payment {

    @Id
    @Column(name = "payment_key", length = 200)
    private String paymentKey;

    @Column(name = "order_id", nullable = false, length = 64)
    private String orderId;

    @Column(name = "merchant_id", nullable = false, length = 50)
    private String merchantId;

    @Column(name = "customer_id", length = 50)
    private String customerId;

    @Column(name = "payment_method_id", length = 50)
    private String paymentMethodId;

    @Column(name = "order_name", nullable = false, length = 100)
    private String orderName;

    @Column(name = "amount", nullable = false)
    private Long amount;

    @Column(name = "currency", length = 3)
    @Builder.Default
    private String currency = "KRW";

    @Column(name = "method", nullable = false, length = 30)
    private String method;

    @Column(name = "method_detail", columnDefinition = "jsonb")
    private String methodDetail;

    @Column(name = "balance_amount", nullable = false)
    private Long balanceAmount;

    @Column(name = "supplied_amount")
    private Long suppliedAmount;

    @Column(name = "vat")
    private Long vat;

    @Column(name = "tax_free_amount")
    @Builder.Default
    private Long taxFreeAmount = 0L;

    @Column(name = "status", nullable = false, length = 30)
    @Builder.Default
    private String status = "READY";

    @Column(name = "approved_at")
    private OffsetDateTime approvedAt;

    @Column(name = "receipt_url", length = 500)
    private String receiptUrl;

    @Column(name = "card_approval_number", length = 20)
    private String cardApprovalNumber;

    @Column(name = "card_installment_months")
    @Builder.Default
    private Integer cardInstallmentMonths = 0;

    @Column(name = "card_is_interest_free")
    @Builder.Default
    private Boolean cardIsInterestFree = false;

    @Column(name = "virtual_account_bank_code", length = 10)
    private String virtualAccountBankCode;

    @Column(name = "virtual_account_number", length = 50)
    private String virtualAccountNumber;

    @Column(name = "virtual_account_holder", length = 100)
    private String virtualAccountHolder;

    @Column(name = "virtual_account_due_date")
    private OffsetDateTime virtualAccountDueDate;

    @Column(name = "virtual_account_refund_status", length = 20)
    private String virtualAccountRefundStatus;

    @Column(name = "canceled_at")
    private OffsetDateTime canceledAt;

    @Column(name = "canceled_amount")
    @Builder.Default
    private Long canceledAmount = 0L;

    @Column(name = "cancel_reason", length = 200)
    private String cancelReason;

    @Column(name = "failure_code", length = 50)
    private String failureCode;

    @Column(name = "failure_message", length = 500)
    private String failureMessage;

    @Column(name = "is_settled")
    @Builder.Default
    private Boolean isSettled = false;

    @Column(name = "settlement_id", length = 50)
    private String settlementId;

    @Column(name = "request_id", length = 100)
    private String requestId;

    @Column(name = "client_ip", length = 45)
    private String clientIp;

    @Column(name = "user_agent", length = 500)
    private String userAgent;

    @Column(name = "metadata", columnDefinition = "jsonb")
    private String metadata;

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @Column(name = "updated_at")
    private OffsetDateTime updatedAt;

    @Column(name = "requested_at")
    private OffsetDateTime requestedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = OffsetDateTime.now();
        updatedAt = OffsetDateTime.now();
        requestedAt = OffsetDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = OffsetDateTime.now();
    }
}
