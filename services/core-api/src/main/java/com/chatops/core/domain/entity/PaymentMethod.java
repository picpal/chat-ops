package com.chatops.core.domain.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

@Entity
@Table(name = "payment_methods")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PaymentMethod {

    @Id
    @Column(name = "payment_method_id", length = 50)
    private String paymentMethodId;

    @Column(name = "customer_id", nullable = false, length = 50)
    private String customerId;

    @Column(name = "type", nullable = false, length = 30)
    private String type;

    @Column(name = "card_company", length = 50)
    private String cardCompany;

    @Column(name = "card_number_masked", length = 20)
    private String cardNumberMasked;

    @Column(name = "card_type", length = 20)
    private String cardType;

    @Column(name = "card_owner_type", length = 20)
    private String cardOwnerType;

    @Column(name = "card_exp_month")
    private Integer cardExpMonth;

    @Column(name = "card_exp_year")
    private Integer cardExpYear;

    @Column(name = "card_issuer_code", length = 10)
    private String cardIssuerCode;

    @Column(name = "card_acquirer_code", length = 10)
    private String cardAcquirerCode;

    @Column(name = "bank_code", length = 10)
    private String bankCode;

    @Column(name = "account_number", length = 50)
    private String accountNumber;

    @Column(name = "account_holder", length = 100)
    private String accountHolder;

    @Column(name = "easy_pay_provider", length = 50)
    private String easyPayProvider;

    @Column(name = "billing_key", length = 100)
    private String billingKey;

    @Column(name = "billing_key_expires_at")
    private OffsetDateTime billingKeyExpiresAt;

    @Column(name = "is_default")
    @Builder.Default
    private Boolean isDefault = false;

    @Column(name = "status", length = 20)
    @Builder.Default
    private String status = "ACTIVE";

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
