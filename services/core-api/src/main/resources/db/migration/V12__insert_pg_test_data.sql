-- PG 테스트 데이터 삽입 (중규모: 가맹점 10개, 고객 100명, 결제 1,000건)

-- ============================================================================
-- 1. 가맹점 데이터 (10개)
-- ============================================================================
INSERT INTO merchants (merchant_id, business_name, business_number, representative_name, business_type, business_category, email, phone, address, postal_code, settlement_bank_code, settlement_account_number, settlement_account_holder, settlement_cycle, fee_rate, status, verified_at, created_at, updated_at) VALUES
('mer_001', '테스트 온라인몰', '123-45-67890', '홍길동', '소매업', '전자상거래', 'merchant1@test.com', '02-1234-5678', '서울시 강남구 테헤란로 123', '06234', '004', '12345678901234', '홍길동', 'D+1', 0.0350, 'ACTIVE', NOW() - INTERVAL '90 days', NOW() - INTERVAL '100 days', NOW()),
('mer_002', '패션 쇼핑몰', '234-56-78901', '김철수', '소매업', '의류판매', 'merchant2@test.com', '02-2345-6789', '서울시 서초구 서초대로 456', '06542', '088', '98765432109876', '김철수', 'D+1', 0.0330, 'ACTIVE', NOW() - INTERVAL '60 days', NOW() - INTERVAL '70 days', NOW()),
('mer_003', '식품 마켓', '345-67-89012', '이영희', '도매업', '식품유통', 'merchant3@test.com', '02-3456-7890', '서울시 송파구 올림픽로 789', '05510', '020', '55555666677778', '이영희', 'D+2', 0.0300, 'ACTIVE', NOW() - INTERVAL '45 days', NOW() - INTERVAL '50 days', NOW()),
('mer_004', '전자기기 스토어', '456-78-90123', '박민수', '소매업', '전자제품', 'merchant4@test.com', '02-4567-8901', '서울시 영등포구 여의대로 101', '07241', '004', '11112222333344', '박민수', 'D+1', 0.0350, 'ACTIVE', NOW() - INTERVAL '30 days', NOW() - INTERVAL '40 days', NOW()),
('mer_005', '뷰티 코스메틱', '567-89-01234', '최지은', '소매업', '화장품', 'merchant5@test.com', '02-5678-9012', '서울시 마포구 홍대입구로 202', '04066', '011', '99998888777766', '최지은', 'D+1', 0.0320, 'ACTIVE', NOW() - INTERVAL '25 days', NOW() - INTERVAL '30 days', NOW()),
('mer_006', '스포츠 용품점', '678-90-12345', '정대호', '소매업', '스포츠용품', 'merchant6@test.com', '02-6789-0123', '서울시 용산구 한강대로 303', '04383', '020', '44443333222211', '정대호', 'D+2', 0.0340, 'ACTIVE', NOW() - INTERVAL '20 days', NOW() - INTERVAL '25 days', NOW()),
('mer_007', '홈인테리어', '789-01-23456', '윤서연', '소매업', '가구인테리어', 'merchant7@test.com', '02-7890-1234', '서울시 성동구 왕십리로 404', '04764', '088', '77776666555544', '윤서연', 'D+1', 0.0350, 'ACTIVE', NOW() - INTERVAL '15 days', NOW() - INTERVAL '20 days', NOW()),
('mer_008', '도서출판사', '890-12-34567', '임재현', '서비스업', '출판', 'merchant8@test.com', '02-8901-2345', '서울시 종로구 종로 505', '03142', '004', '33332222111100', '임재현', 'WEEKLY', 0.0280, 'ACTIVE', NOW() - INTERVAL '10 days', NOW() - INTERVAL '15 days', NOW()),
('mer_009', '신규 심사중 가맹점', '901-23-45678', '강민지', '소매업', '잡화', 'merchant9@test.com', '02-9012-3456', '서울시 중구 을지로 606', '04539', NULL, NULL, NULL, 'D+1', 0.0350, 'PENDING', NULL, NOW() - INTERVAL '5 days', NOW()),
('mer_010', '정지된 가맹점', '012-34-56789', '송준호', '소매업', '기타', 'merchant10@test.com', '02-0123-4567', '서울시 동작구 동작대로 707', '06958', '004', '22221111000099', '송준호', 'D+1', 0.0350, 'SUSPENDED', NOW() - INTERVAL '60 days', NOW() - INTERVAL '80 days', NOW() - INTERVAL '3 days');

-- ============================================================================
-- 2. PG 고객 데이터 (100명 - 가맹점별 분배)
-- ============================================================================
DO $$
DECLARE
    i INTEGER;
    mer_id VARCHAR(50);
    cus_id VARCHAR(50);
    cus_name VARCHAR(100);
    names TEXT[] := ARRAY['김민준', '이서연', '박지호', '최예은', '정우진', '강하늘', '조은비', '윤현우', '임서윤', '한지민',
                          '오민석', '서유진', '권도현', '유채원', '안준영', '배수아', '신재원', '양하린', '허준혁', '문다은',
                          '장민호', '구서현', '류태양', '남유나', '홍지훈', '손예린', '마성진', '노하윤', '황동현', '전소미',
                          '변우주', '송이준', '천유빈', '방시우', '복민아', '표재윤', '탁서희', '피준서', '하윤아', '원동건'];
BEGIN
    FOR i IN 1..100 LOOP
        -- 가맹점 ID 할당 (mer_001~mer_008에 분배, 009/010 제외)
        mer_id := 'mer_00' || ((i - 1) % 8 + 1);
        cus_id := 'cus_' || LPAD(i::TEXT, 3, '0');
        cus_name := names[((i - 1) % 40) + 1];

        INSERT INTO pg_customers (customer_id, merchant_id, email, name, phone, shipping_name, shipping_phone, shipping_address, shipping_postal_code, created_at, updated_at)
        VALUES (
            cus_id,
            mer_id,
            'customer' || i || '@test.com',
            cus_name,
            '010-' || LPAD((1000 + i)::TEXT, 4, '0') || '-' || LPAD((5000 + i)::TEXT, 4, '0'),
            cus_name,
            '010-' || LPAD((1000 + i)::TEXT, 4, '0') || '-' || LPAD((5000 + i)::TEXT, 4, '0'),
            '서울시 테스트구 테스트로 ' || i || '번지',
            LPAD((10000 + i)::TEXT, 5, '0'),
            NOW() - (INTERVAL '1 day' * (100 - i)),
            NOW()
        );
    END LOOP;
END $$;

-- ============================================================================
-- 3. 결제수단 데이터 (150개 - 고객별 1~2개)
-- ============================================================================
DO $$
DECLARE
    i INTEGER;
    cus_id VARCHAR(50);
    pm_id VARCHAR(50);
    pm_type VARCHAR(30);
    card_companies TEXT[] := ARRAY['신한카드', '삼성카드', 'KB국민카드', '현대카드', '롯데카드', '하나카드', 'NH농협카드', '우리카드', 'BC카드', '씨티카드'];
    easy_pay_providers TEXT[] := ARRAY['KAKAOPAY', 'NAVERPAY', 'TOSSPAY', 'PAYCO', 'SAMSUNGPAY'];
BEGIN
    FOR i IN 1..150 LOOP
        cus_id := 'cus_' || LPAD(((i - 1) % 100 + 1)::TEXT, 3, '0');
        pm_id := 'pm_' || LPAD(i::TEXT, 3, '0');

        -- 60% 카드, 30% 간편결제, 10% 기타
        IF i % 10 <= 5 THEN
            pm_type := 'CARD';
            INSERT INTO payment_methods (payment_method_id, customer_id, type, card_company, card_number_masked, card_type, card_owner_type, card_exp_month, card_exp_year, is_default, status, created_at, updated_at)
            VALUES (
                pm_id, cus_id, pm_type,
                card_companies[((i - 1) % 10) + 1],
                LPAD((1000 + i)::TEXT, 4, '0') || '-****-****-' || LPAD((5000 + i)::TEXT, 4, '0'),
                CASE WHEN i % 3 = 0 THEN 'DEBIT' ELSE 'CREDIT' END,
                CASE WHEN i % 5 = 0 THEN 'CORPORATE' ELSE 'PERSONAL' END,
                (i % 12) + 1,
                2026 + (i % 3),
                i <= 100,
                'ACTIVE',
                NOW() - (INTERVAL '1 day' * (150 - i)),
                NOW()
            );
        ELSIF i % 10 <= 8 THEN
            pm_type := 'EASY_PAY';
            INSERT INTO payment_methods (payment_method_id, customer_id, type, easy_pay_provider, is_default, status, created_at, updated_at)
            VALUES (
                pm_id, cus_id, pm_type,
                easy_pay_providers[((i - 1) % 5) + 1],
                i > 100 AND i <= 130,
                'ACTIVE',
                NOW() - (INTERVAL '1 day' * (150 - i)),
                NOW()
            );
        ELSE
            pm_type := 'VIRTUAL_ACCOUNT';
            INSERT INTO payment_methods (payment_method_id, customer_id, type, bank_code, is_default, status, created_at, updated_at)
            VALUES (
                pm_id, cus_id, pm_type,
                CASE WHEN i % 3 = 0 THEN '004' WHEN i % 3 = 1 THEN '088' ELSE '020' END,
                FALSE,
                'ACTIVE',
                NOW() - (INTERVAL '1 day' * (150 - i)),
                NOW()
            );
        END IF;
    END LOOP;
END $$;

-- ============================================================================
-- 4. 결제 데이터 (1,000건 - 다양한 시나리오)
-- 분포: 정상완료 70%, 전체취소 10%, 부분취소 10%, 가상계좌대기 5%, 실패 5%
-- ============================================================================
DO $$
DECLARE
    i INTEGER;
    mer_id VARCHAR(50);
    cus_id VARCHAR(50);
    pm_id VARCHAR(50);
    pay_key VARCHAR(200);
    order_id VARCHAR(64);
    pay_status VARCHAR(30);
    pay_method VARCHAR(30);
    pay_amount BIGINT;
    balance_amt BIGINT;
    canceled_amt BIGINT;
    card_companies TEXT[] := ARRAY['신한카드', '삼성카드', 'KB국민카드', '현대카드', '롯데카드'];
    order_names TEXT[] := ARRAY['테스트 상품 A', '패션 의류', '전자기기', '식품 세트', '화장품 세트', '스포츠 용품', '도서 3권', '가구 소품', '생활용품', '기타 상품'];
    cancel_reasons TEXT[] := ARRAY['고객 변심', '상품 불량', '배송 지연', '단순 취소', '주문 실수'];
    failure_codes TEXT[] := ARRAY['CARD_LIMIT_EXCEEDED', 'INVALID_CARD', 'EXPIRED_CARD', 'INSUFFICIENT_BALANCE', 'NETWORK_ERROR'];
    random_val FLOAT;
    approved_time TIMESTAMP WITH TIME ZONE;
BEGIN
    FOR i IN 1..1000 LOOP
        mer_id := 'mer_00' || ((i - 1) % 8 + 1);
        cus_id := 'cus_' || LPAD(((i - 1) % 100 + 1)::TEXT, 3, '0');
        pm_id := 'pm_' || LPAD(((i - 1) % 150 + 1)::TEXT, 3, '0');
        pay_key := 'pay_' || TO_CHAR(NOW(), 'YYYYMMDD') || '_' || LPAD(i::TEXT, 6, '0');
        order_id := 'ORD-' || TO_CHAR(NOW() - (INTERVAL '1 hour' * (1000 - i)), 'YYYYMMDD-HH24MI') || '-' || LPAD(i::TEXT, 4, '0');

        -- 금액 설정 (10,000 ~ 1,000,000)
        pay_amount := (10000 + (random() * 990000)::INTEGER);
        pay_amount := (pay_amount / 1000) * 1000; -- 1000원 단위 정리

        random_val := random();
        approved_time := NOW() - (INTERVAL '1 hour' * (1000 - i));

        -- 시나리오 분배
        IF random_val < 0.70 THEN
            -- 정상 완료 (70%)
            pay_status := 'DONE';
            balance_amt := pay_amount;
            canceled_amt := 0;

            IF i % 10 <= 5 THEN
                pay_method := 'CARD';
            ELSIF i % 10 <= 8 THEN
                pay_method := 'EASY_PAY';
            ELSE
                pay_method := 'BANK_TRANSFER';
            END IF;

            INSERT INTO payments (payment_key, order_id, merchant_id, customer_id, payment_method_id, order_name, amount, currency, method, balance_amount, supplied_amount, vat, status, approved_at, card_approval_number, card_installment_months, card_is_interest_free, created_at, updated_at)
            VALUES (
                pay_key, order_id, mer_id, cus_id, pm_id,
                order_names[((i - 1) % 10) + 1] || ' 외 ' || (i % 5) || '건',
                pay_amount, 'KRW', pay_method,
                pay_amount,
                (pay_amount * 10 / 11),
                (pay_amount / 11),
                pay_status,
                approved_time,
                LPAD((10000000 + i)::TEXT, 8, '0'),
                CASE WHEN pay_amount >= 500000 THEN (i % 6) * 3 ELSE 0 END,
                pay_amount >= 500000 AND (i % 3) = 0,
                approved_time - INTERVAL '1 minute',
                NOW()
            );

        ELSIF random_val < 0.80 THEN
            -- 전체 취소 (10%)
            pay_status := 'CANCELED';
            pay_method := 'CARD';
            balance_amt := 0;
            canceled_amt := pay_amount;

            INSERT INTO payments (payment_key, order_id, merchant_id, customer_id, payment_method_id, order_name, amount, currency, method, balance_amount, supplied_amount, vat, status, approved_at, canceled_at, canceled_amount, cancel_reason, card_approval_number, created_at, updated_at)
            VALUES (
                pay_key, order_id, mer_id, cus_id, pm_id,
                order_names[((i - 1) % 10) + 1],
                pay_amount, 'KRW', pay_method,
                0,
                (pay_amount * 10 / 11),
                (pay_amount / 11),
                pay_status,
                approved_time - INTERVAL '6 hours',
                approved_time,
                pay_amount,
                cancel_reasons[((i - 1) % 5) + 1],
                LPAD((20000000 + i)::TEXT, 8, '0'),
                approved_time - INTERVAL '6 hours' - INTERVAL '1 minute',
                NOW()
            );

            -- 환불 레코드
            INSERT INTO refunds (refund_key, payment_key, amount, reason, status, approved_at, requested_by, created_at, updated_at)
            VALUES (
                'rf_' || LPAD(i::TEXT, 6, '0'),
                pay_key,
                pay_amount,
                cancel_reasons[((i - 1) % 5) + 1],
                'SUCCEEDED',
                approved_time,
                CASE WHEN i % 2 = 0 THEN 'CUSTOMER' ELSE 'MERCHANT' END,
                approved_time - INTERVAL '10 minutes',
                NOW()
            );

        ELSIF random_val < 0.90 THEN
            -- 부분 취소 (10%)
            pay_status := 'PARTIAL_CANCELED';
            pay_method := 'CARD';
            canceled_amt := (pay_amount * (20 + (i % 30))) / 100; -- 20~50% 취소
            canceled_amt := (canceled_amt / 1000) * 1000;
            balance_amt := pay_amount - canceled_amt;

            INSERT INTO payments (payment_key, order_id, merchant_id, customer_id, payment_method_id, order_name, amount, currency, method, balance_amount, supplied_amount, vat, status, approved_at, canceled_amount, cancel_reason, card_approval_number, created_at, updated_at)
            VALUES (
                pay_key, order_id, mer_id, cus_id, pm_id,
                order_names[((i - 1) % 10) + 1] || ' 외 2건',
                pay_amount, 'KRW', pay_method,
                balance_amt,
                (pay_amount * 10 / 11),
                (pay_amount / 11),
                pay_status,
                approved_time - INTERVAL '12 hours',
                canceled_amt,
                '상품 1건 취소',
                LPAD((30000000 + i)::TEXT, 8, '0'),
                approved_time - INTERVAL '12 hours' - INTERVAL '1 minute',
                NOW()
            );

            -- 환불 레코드
            INSERT INTO refunds (refund_key, payment_key, amount, reason, status, approved_at, requested_by, created_at, updated_at)
            VALUES (
                'rf_' || LPAD(i::TEXT, 6, '0'),
                pay_key,
                canceled_amt,
                '상품 1건 취소',
                'SUCCEEDED',
                approved_time,
                'MERCHANT',
                approved_time - INTERVAL '5 minutes',
                NOW()
            );

        ELSIF random_val < 0.95 THEN
            -- 가상계좌 대기 (5%)
            pay_status := 'WAITING_FOR_DEPOSIT';
            pay_method := 'VIRTUAL_ACCOUNT';
            balance_amt := pay_amount;
            canceled_amt := 0;

            INSERT INTO payments (payment_key, order_id, merchant_id, customer_id, order_name, amount, currency, method, balance_amount, supplied_amount, vat, status, virtual_account_bank_code, virtual_account_number, virtual_account_holder, virtual_account_due_date, created_at, updated_at)
            VALUES (
                pay_key, order_id, mer_id, cus_id,
                order_names[((i - 1) % 10) + 1],
                pay_amount, 'KRW', pay_method,
                pay_amount,
                (pay_amount * 10 / 11),
                (pay_amount / 11),
                pay_status,
                CASE WHEN i % 3 = 0 THEN '004' WHEN i % 3 = 1 THEN '088' ELSE '020' END,
                '123' || LPAD(i::TEXT, 10, '0') || '456',
                '테스트고객' || ((i - 1) % 100 + 1),
                NOW() + INTERVAL '3 days',
                NOW() - (INTERVAL '1 hour' * (50 - (i % 50))),
                NOW()
            );

        ELSE
            -- 결제 실패 (5%)
            pay_status := 'ABORTED';
            pay_method := 'CARD';
            balance_amt := 0;
            canceled_amt := 0;

            INSERT INTO payments (payment_key, order_id, merchant_id, customer_id, payment_method_id, order_name, amount, currency, method, balance_amount, status, failure_code, failure_message, created_at, updated_at)
            VALUES (
                pay_key, order_id, mer_id, cus_id, pm_id,
                order_names[((i - 1) % 10) + 1],
                pay_amount, 'KRW', pay_method,
                0,
                pay_status,
                failure_codes[((i - 1) % 5) + 1],
                CASE failure_codes[((i - 1) % 5) + 1]
                    WHEN 'CARD_LIMIT_EXCEEDED' THEN '카드 한도 초과'
                    WHEN 'INVALID_CARD' THEN '유효하지 않은 카드'
                    WHEN 'EXPIRED_CARD' THEN '만료된 카드'
                    WHEN 'INSUFFICIENT_BALANCE' THEN '잔액 부족'
                    ELSE '네트워크 오류'
                END,
                NOW() - (INTERVAL '1 hour' * (1000 - i)),
                NOW()
            );
        END IF;
    END LOOP;
END $$;

-- ============================================================================
-- 5. 결제 이력 데이터 (DONE 상태 결제에 대한 이력)
-- ============================================================================
INSERT INTO payment_history (payment_key, previous_status, new_status, amount_change, balance_after, reason, processed_by, created_at)
SELECT
    payment_key,
    'READY',
    'IN_PROGRESS',
    0,
    amount,
    '결제 시작',
    'SYSTEM',
    created_at
FROM payments
WHERE status IN ('DONE', 'CANCELED', 'PARTIAL_CANCELED');

INSERT INTO payment_history (payment_key, previous_status, new_status, amount_change, balance_after, reason, processed_by, created_at)
SELECT
    payment_key,
    'IN_PROGRESS',
    'DONE',
    0,
    amount,
    '결제 승인 완료',
    'SYSTEM',
    approved_at
FROM payments
WHERE status IN ('DONE', 'CANCELED', 'PARTIAL_CANCELED') AND approved_at IS NOT NULL;

INSERT INTO payment_history (payment_key, previous_status, new_status, amount_change, balance_after, reason, processed_by, created_at)
SELECT
    payment_key,
    'DONE',
    status,
    -canceled_amount,
    balance_amount,
    cancel_reason,
    'MERCHANT',
    canceled_at
FROM payments
WHERE status IN ('CANCELED', 'PARTIAL_CANCELED') AND canceled_at IS NOT NULL;

-- ============================================================================
-- 6. 잔액 거래 내역 데이터 (정산 가능한 결제 건)
-- ============================================================================
INSERT INTO balance_transactions (transaction_id, merchant_id, source_type, source_id, amount, fee, net, status, available_on, description, created_at)
SELECT
    'txn_' || LPAD(ROW_NUMBER() OVER (ORDER BY created_at)::TEXT, 6, '0'),
    merchant_id,
    'PAYMENT',
    payment_key,
    amount,
    (amount * 35 / 1000), -- 3.5% 수수료
    amount - (amount * 35 / 1000),
    CASE
        WHEN approved_at < NOW() - INTERVAL '1 day' THEN 'AVAILABLE'
        ELSE 'PENDING'
    END,
    CASE
        WHEN approved_at < NOW() - INTERVAL '1 day' THEN approved_at + INTERVAL '1 day'
        ELSE approved_at + INTERVAL '1 day'
    END,
    order_name || ' 결제',
    approved_at
FROM payments
WHERE status = 'DONE' AND approved_at IS NOT NULL;

-- 환불 거래 내역
INSERT INTO balance_transactions (transaction_id, merchant_id, source_type, source_id, amount, fee, net, status, available_on, description, created_at)
SELECT
    'txn_rf_' || LPAD(ROW_NUMBER() OVER (ORDER BY r.created_at)::TEXT, 6, '0'),
    p.merchant_id,
    'REFUND',
    r.refund_key,
    -r.amount,
    0,
    -(r.amount - (r.amount * 35 / 1000)),
    'AVAILABLE',
    r.approved_at + INTERVAL '1 day',
    r.reason,
    r.approved_at
FROM refunds r
JOIN payments p ON r.payment_key = p.payment_key
WHERE r.status = 'SUCCEEDED' AND r.approved_at IS NOT NULL;

-- ============================================================================
-- 7. 정산 데이터 (최근 30일 - 가맹점별 일별 정산)
-- ============================================================================
DO $$
DECLARE
    settlement_day DATE;
    mer_id VARCHAR(50);
    mer_ids VARCHAR(50)[] := ARRAY['mer_001', 'mer_002', 'mer_003', 'mer_004', 'mer_005', 'mer_006', 'mer_007', 'mer_008'];
    total_pay BIGINT;
    total_ref BIGINT;
    total_f BIGINT;
    pay_cnt INTEGER;
    ref_cnt INTEGER;
BEGIN
    -- 최근 30일 정산 (오늘 제외)
    FOR day_offset IN 1..30 LOOP
        settlement_day := CURRENT_DATE - day_offset;

        FOREACH mer_id IN ARRAY mer_ids LOOP
            -- 해당 가맹점, 해당 날짜의 결제 합계
            SELECT
                COALESCE(SUM(amount), 0),
                COUNT(*)
            INTO total_pay, pay_cnt
            FROM payments
            WHERE merchant_id = mer_id
                AND status = 'DONE'
                AND DATE(approved_at) = settlement_day - 1; -- D+1 정산

            -- 환불 합계
            SELECT
                COALESCE(SUM(r.amount), 0),
                COUNT(*)
            INTO total_ref, ref_cnt
            FROM refunds r
            JOIN payments p ON r.payment_key = p.payment_key
            WHERE p.merchant_id = mer_id
                AND r.status = 'SUCCEEDED'
                AND DATE(r.approved_at) = settlement_day - 1;

            -- 정산 건이 있는 경우만 INSERT
            IF total_pay > 0 OR total_ref > 0 THEN
                total_f := ((total_pay - total_ref) * 35 / 1000);

                INSERT INTO settlements (settlement_id, merchant_id, settlement_date, period_start, period_end, total_payment_amount, total_refund_amount, total_fee, net_amount, payment_count, refund_count, status, payout_bank_code, payout_account_number, payout_account_holder, payout_reference, processed_at, paid_out_at, created_at, updated_at)
                SELECT
                    'stl_' || mer_id || '_' || TO_CHAR(settlement_day, 'YYYYMMDD'),
                    mer_id,
                    settlement_day,
                    settlement_day - 1,
                    settlement_day - 1,
                    total_pay,
                    total_ref,
                    total_f,
                    total_pay - total_ref - total_f,
                    pay_cnt,
                    ref_cnt,
                    'COMPLETED',
                    m.settlement_bank_code,
                    m.settlement_account_number,
                    m.settlement_account_holder,
                    'PAY-' || TO_CHAR(settlement_day, 'YYYYMMDD') || '-' || LPAD(day_offset::TEXT, 3, '0'),
                    settlement_day + TIME '09:00:00',
                    settlement_day + TIME '10:00:00',
                    settlement_day,
                    settlement_day
                FROM merchants m
                WHERE m.merchant_id = mer_id;
            END IF;
        END LOOP;
    END LOOP;
END $$;

-- ============================================================================
-- 8. 정산 상세 데이터 (정산에 포함된 개별 거래 - 실제 존재하는 정산만)
-- ============================================================================
INSERT INTO settlement_details (settlement_id, transaction_type, payment_key, amount, fee, net_amount, method, transaction_at, created_at)
SELECT
    s.settlement_id,
    'PAYMENT',
    p.payment_key,
    p.amount,
    (p.amount * 35 / 1000),
    p.amount - (p.amount * 35 / 1000),
    p.method,
    p.approved_at,
    p.approved_at
FROM payments p
JOIN settlements s ON s.settlement_id = 'stl_' || p.merchant_id || '_' || TO_CHAR(DATE(p.approved_at) + 1, 'YYYYMMDD')
WHERE p.status = 'DONE'
    AND p.approved_at IS NOT NULL;

INSERT INTO settlement_details (settlement_id, transaction_type, refund_key, payment_key, amount, fee, net_amount, method, transaction_at, created_at)
SELECT
    s.settlement_id,
    'REFUND',
    r.refund_key,
    r.payment_key,
    -r.amount,
    0,
    -(r.amount - (r.amount * 35 / 1000)),
    p.method,
    r.approved_at,
    r.approved_at
FROM refunds r
JOIN payments p ON r.payment_key = p.payment_key
JOIN settlements s ON s.settlement_id = 'stl_' || p.merchant_id || '_' || TO_CHAR(DATE(r.approved_at) + 1, 'YYYYMMDD')
WHERE r.status = 'SUCCEEDED'
    AND r.approved_at IS NOT NULL;

-- ============================================================================
-- 9. 결제 건 정산 완료 표시 업데이트 (실제 존재하는 정산만)
-- ============================================================================
UPDATE payments p
SET is_settled = TRUE,
    settlement_id = s.settlement_id
FROM settlements s
WHERE s.settlement_id = 'stl_' || p.merchant_id || '_' || TO_CHAR(DATE(p.approved_at) + 1, 'YYYYMMDD')
    AND p.status = 'DONE'
    AND p.approved_at IS NOT NULL;

-- ============================================================================
-- 10. 통계 확인용 쿼리 (주석)
-- ============================================================================
-- SELECT '가맹점 수' as metric, COUNT(*) as value FROM merchants;
-- SELECT '고객 수' as metric, COUNT(*) as value FROM pg_customers;
-- SELECT '결제수단 수' as metric, COUNT(*) as value FROM payment_methods;
-- SELECT '결제 건수' as metric, COUNT(*) as value FROM payments;
-- SELECT status, COUNT(*) FROM payments GROUP BY status;
-- SELECT '환불 건수' as metric, COUNT(*) as value FROM refunds;
-- SELECT '잔액거래 건수' as metric, COUNT(*) as value FROM balance_transactions;
-- SELECT '정산 건수' as metric, COUNT(*) as value FROM settlements;
-- SELECT '정산상세 건수' as metric, COUNT(*) as value FROM settlement_details;

COMMENT ON TABLE merchants IS 'PG 가맹점 정보 (테스트 데이터 10개)';
COMMENT ON TABLE pg_customers IS 'PG 고객 정보 (테스트 데이터 100개)';
COMMENT ON TABLE payment_methods IS '결제수단 정보 (테스트 데이터 150개)';
COMMENT ON TABLE payments IS 'PG 결제 트랜잭션 (테스트 데이터 1,000건)';
