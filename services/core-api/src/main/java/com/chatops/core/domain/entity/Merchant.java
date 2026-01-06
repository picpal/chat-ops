package com.chatops.core.domain.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

@Entity
@Table(name = "merchants")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Merchant {

    @Id
    @Column(name = "merchant_id", length = 50)
    private String merchantId;

    @Column(name = "business_name", nullable = false)
    private String businessName;

    @Column(name = "business_number", nullable = false, unique = true, length = 20)
    private String businessNumber;

    @Column(name = "representative_name", nullable = false, length = 100)
    private String representativeName;

    @Column(name = "business_type", length = 50)
    private String businessType;

    @Column(name = "business_category", length = 100)
    private String businessCategory;

    @Column(name = "email", nullable = false)
    private String email;

    @Column(name = "phone", length = 20)
    private String phone;

    @Column(name = "address", columnDefinition = "TEXT")
    private String address;

    @Column(name = "postal_code", length = 10)
    private String postalCode;

    @Column(name = "settlement_bank_code", length = 10)
    private String settlementBankCode;

    @Column(name = "settlement_account_number", length = 50)
    private String settlementAccountNumber;

    @Column(name = "settlement_account_holder", length = 100)
    private String settlementAccountHolder;

    @Column(name = "settlement_cycle", length = 20)
    @Builder.Default
    private String settlementCycle = "D+1";

    @Column(name = "fee_rate", precision = 5, scale = 4)
    @Builder.Default
    private BigDecimal feeRate = new BigDecimal("0.0350");

    @Column(name = "api_key_live", length = 100)
    private String apiKeyLive;

    @Column(name = "api_key_test", length = 100)
    private String apiKeyTest;

    @Column(name = "status", length = 20)
    @Builder.Default
    private String status = "PENDING";

    @Column(name = "verified_at")
    private OffsetDateTime verifiedAt;

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
