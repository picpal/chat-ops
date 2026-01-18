#!/usr/bin/env python3
"""
PG 결제 서비스 테스트 데이터 시딩 스크립트

규모별 데이터 생성:
- small: 가맹점 3개, 결제 300건 (빠른 테스트용)
- medium: 가맹점 10개, 결제 1,000건 (일반 개발용)
- large: 가맹점 30개, 결제 10,000건 (대용량 테스트)

사용법:
    python3 scripts/seed-test-data.py --scale medium
    python3 scripts/seed-test-data.py --scale large --period 60
"""

import argparse
import os
import sys
import random
from datetime import datetime, timedelta
from decimal import Decimal

# psycopg2는 main()에서 lazy import
psycopg2 = None
execute_values = None


# =============================================================================
# 설정
# =============================================================================

SCALE_CONFIG = {
    "small": {
        "merchants": 3,
        "customers_per_merchant": 10,
        "payment_methods_per_customer": 1.5,
        "payments": 300,
        "refund_rate": 0.15,  # 15% 환불
    },
    "medium": {
        "merchants": 10,
        "customers_per_merchant": 10,
        "payment_methods_per_customer": 1.5,
        "payments": 1000,
        "refund_rate": 0.15,
    },
    "large": {
        "merchants": 30,
        "customers_per_merchant": 16,
        "payment_methods_per_customer": 1.5,
        "payments": 10000,
        "refund_rate": 0.15,
    },
}

# 이름 목록
KOREAN_NAMES = [
    "김민준", "이서연", "박지호", "최예은", "정우진", "강하늘", "조은비", "윤현우", "임서윤", "한지민",
    "오민석", "서유진", "권도현", "유채원", "안준영", "배수아", "신재원", "양하린", "허준혁", "문다은",
    "장민호", "구서현", "류태양", "남유나", "홍지훈", "손예린", "마성진", "노하윤", "황동현", "전소미",
    "변우주", "송이준", "천유빈", "방시우", "복민아", "표재윤", "탁서희", "피준서", "하윤아", "원동건",
    "김준서", "이다은", "박서준", "최하은", "정민재", "강서영", "조시우", "윤지아", "임도윤", "한예준",
]

BUSINESS_NAMES = [
    ("테스트 온라인몰", "소매업", "전자상거래"),
    ("패션 쇼핑몰", "소매업", "의류판매"),
    ("식품 마켓", "도매업", "식품유통"),
    ("전자기기 스토어", "소매업", "전자제품"),
    ("뷰티 코스메틱", "소매업", "화장품"),
    ("스포츠 용품점", "소매업", "스포츠용품"),
    ("홈인테리어", "소매업", "가구인테리어"),
    ("도서출판사", "서비스업", "출판"),
    ("게임 스토어", "서비스업", "게임"),
    ("건강식품샵", "소매업", "건강식품"),
    ("유아용품점", "소매업", "유아용품"),
    ("반려동물샵", "소매업", "반려동물"),
    ("악세서리몰", "소매업", "패션잡화"),
    ("주방용품몰", "소매업", "생활용품"),
    ("캠핑용품점", "소매업", "레저용품"),
    ("자동차용품", "소매업", "자동차부품"),
    ("공구마켓", "도매업", "공구"),
    ("문구팜", "소매업", "문구"),
    ("화훼마켓", "소매업", "화훼"),
    ("와인샵", "소매업", "주류"),
    ("커피원두샵", "소매업", "식품"),
    ("수공예마켓", "소매업", "공예품"),
    ("골프용품점", "소매업", "골프용품"),
    ("등산용품점", "소매업", "등산용품"),
    ("낚시마트", "소매업", "낚시용품"),
    ("악기상점", "소매업", "악기"),
    ("컴퓨터마트", "소매업", "컴퓨터"),
    ("가전제품몰", "소매업", "가전제품"),
    ("인테리어소품", "소매업", "인테리어"),
    ("헬스용품샵", "소매업", "헬스용품"),
]

ORDER_NAMES = [
    "테스트 상품 A", "패션 의류", "전자기기", "식품 세트", "화장품 세트",
    "스포츠 용품", "도서 3권", "가구 소품", "생활용품", "기타 상품",
]

CARD_COMPANIES = ["신한카드", "삼성카드", "KB국민카드", "현대카드", "롯데카드", "하나카드", "NH농협카드", "우리카드", "BC카드", "씨티카드"]
EASY_PAY_PROVIDERS = ["KAKAOPAY", "NAVERPAY", "TOSSPAY", "PAYCO", "SAMSUNGPAY"]
BANK_CODES = ["004", "088", "020", "011", "023", "081", "003"]
CANCEL_REASONS = ["고객 변심", "상품 불량", "배송 지연", "단순 취소", "주문 실수"]
FAILURE_CODES = [
    ("CARD_LIMIT_EXCEEDED", "카드 한도 초과"),
    ("INVALID_CARD", "유효하지 않은 카드"),
    ("EXPIRED_CARD", "만료된 카드"),
    ("INSUFFICIENT_BALANCE", "잔액 부족"),
    ("NETWORK_ERROR", "네트워크 오류"),
]

# 데이터 prefix (기존 마이그레이션 데이터와 충돌 방지)
PREFIX = "seed_"


# =============================================================================
# 유틸리티 함수
# =============================================================================

def get_db_connection():
    """PostgreSQL 연결"""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "chatops")
    user = os.getenv("POSTGRES_USER", "chatops_user")
    password = os.getenv("POSTGRES_PASSWORD", "chatops_pass")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )


def random_phone():
    """임의 전화번호 생성"""
    return f"010-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"


def random_amount(min_amt=10000, max_amt=1000000):
    """1000원 단위 임의 금액 생성"""
    amt = random.randint(min_amt, max_amt)
    return (amt // 1000) * 1000


def progress_bar(current, total, prefix="", length=50):
    """진행률 표시"""
    percent = current / total
    filled = int(length * percent)
    bar = "=" * filled + "-" * (length - filled)
    print(f"\r{prefix} [{bar}] {current}/{total} ({percent*100:.1f}%)", end="", flush=True)


# =============================================================================
# 데이터 생성 함수
# =============================================================================

def clear_seeded_data(conn):
    """기존 시딩 데이터 삭제"""
    print("기존 시딩 데이터 삭제 중...")
    with conn.cursor() as cur:
        # FK 순서 역순으로 삭제
        tables = [
            ("settlement_details", "settlement_id", f"'{PREFIX}%'"),
            ("settlements", "settlement_id", f"'{PREFIX}%'"),
            ("balance_transactions", "transaction_id", f"'{PREFIX}%'"),
            ("refunds", "refund_key", f"'{PREFIX}%'"),
            ("payment_history", "payment_key", f"'{PREFIX}%'"),
            ("payments", "payment_key", f"'{PREFIX}%'"),
            ("payment_methods", "payment_method_id", f"'{PREFIX}%'"),
            ("pg_customers", "customer_id", f"'{PREFIX}%'"),
            ("merchants", "merchant_id", f"'{PREFIX}%'"),
        ]
        for table, col, pattern in tables:
            cur.execute(f"DELETE FROM {table} WHERE {col} LIKE {pattern}")
            deleted = cur.rowcount
            if deleted > 0:
                print(f"  - {table}: {deleted}건 삭제")
    conn.commit()


def generate_merchants(conn, count, period_days):
    """가맹점 데이터 생성"""
    print(f"가맹점 {count}개 생성 중...")
    merchants = []
    now = datetime.now()

    for i in range(count):
        merchant_id = f"{PREFIX}mer_{str(i+1).zfill(3)}"
        biz = BUSINESS_NAMES[i % len(BUSINESS_NAMES)]

        # 상태: 80% ACTIVE, 10% PENDING, 10% SUSPENDED
        rand = random.random()
        if rand < 0.8:
            status = "ACTIVE"
            verified_at = now - timedelta(days=random.randint(30, 180))
        elif rand < 0.9:
            status = "PENDING"
            verified_at = None
        else:
            status = "SUSPENDED"
            verified_at = now - timedelta(days=random.randint(60, 180))

        # settlement_cycle 분포
        cycles = ["D+1"] * 6 + ["D+2"] * 2 + ["WEEKLY"] + ["D+0"]

        merchant = {
            "merchant_id": merchant_id,
            "business_name": f"{biz[0]} #{i+1}",
            "business_number": f"{100+i}-{10+i%90}-{10000+i*100}",
            "representative_name": KOREAN_NAMES[i % len(KOREAN_NAMES)],
            "business_type": biz[1],
            "business_category": biz[2],
            "email": f"merchant_{i+1}@test.com",
            "phone": f"02-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            "address": f"서울시 테스트구 테스트로 {i+1}번길 {random.randint(1, 100)}",
            "postal_code": f"{random.randint(10000, 99999)}",
            "settlement_bank_code": random.choice(BANK_CODES) if status != "PENDING" else None,
            "settlement_account_number": f"{random.randint(10000000000000, 99999999999999)}" if status != "PENDING" else None,
            "settlement_account_holder": KOREAN_NAMES[i % len(KOREAN_NAMES)] if status != "PENDING" else None,
            "settlement_cycle": random.choice(cycles),
            "fee_rate": Decimal(str(round(random.uniform(0.025, 0.038), 4))),
            "status": status,
            "verified_at": verified_at,
            "created_at": now - timedelta(days=random.randint(period_days, period_days + 90)),
            "updated_at": now,
        }
        merchants.append(merchant)

    with conn.cursor() as cur:
        columns = list(merchants[0].keys())
        values = [[m[col] for col in columns] for m in merchants]

        insert_sql = f"""
            INSERT INTO merchants ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (merchant_id) DO NOTHING
        """
        execute_values(cur, insert_sql, values)

    conn.commit()
    print(f"  가맹점 {count}개 생성 완료")
    return [m["merchant_id"] for m in merchants if m["status"] == "ACTIVE"]


def generate_customers(conn, active_merchant_ids, customers_per_merchant):
    """고객 데이터 생성"""
    total_customers = int(len(active_merchant_ids) * customers_per_merchant)
    print(f"고객 {total_customers}개 생성 중...")

    customers = []
    now = datetime.now()

    for i in range(total_customers):
        customer_id = f"{PREFIX}cus_{str(i+1).zfill(4)}"
        merchant_id = active_merchant_ids[i % len(active_merchant_ids)]
        name = KOREAN_NAMES[i % len(KOREAN_NAMES)]

        customer = {
            "customer_id": customer_id,
            "merchant_id": merchant_id,
            "email": f"customer_{i+1}@test.com",
            "name": name,
            "phone": random_phone(),
            "shipping_name": name,
            "shipping_phone": random_phone(),
            "shipping_address": f"서울시 테스트구 테스트로 {i+1}번지",
            "shipping_postal_code": f"{random.randint(10000, 99999)}",
            "created_at": now - timedelta(days=random.randint(1, 90)),
            "updated_at": now,
        }
        customers.append(customer)

        if (i + 1) % 100 == 0:
            progress_bar(i + 1, total_customers, "  고객 생성")

    print()  # 줄바꿈

    with conn.cursor() as cur:
        columns = list(customers[0].keys())
        values = [[c[col] for col in columns] for c in customers]

        insert_sql = f"""
            INSERT INTO pg_customers ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (customer_id) DO NOTHING
        """
        execute_values(cur, insert_sql, values)

    conn.commit()
    print(f"  고객 {total_customers}개 생성 완료")
    return [c["customer_id"] for c in customers]


def generate_payment_methods(conn, customer_ids, methods_per_customer):
    """결제수단 데이터 생성"""
    total_methods = int(len(customer_ids) * methods_per_customer)
    print(f"결제수단 {total_methods}개 생성 중...")

    payment_methods = []
    now = datetime.now()

    for i in range(total_methods):
        pm_id = f"{PREFIX}pm_{str(i+1).zfill(4)}"
        customer_id = customer_ids[i % len(customer_ids)]

        # 유형 분포: 60% 카드, 30% 간편결제, 10% 가상계좌
        rand = random.random()
        if rand < 0.6:
            pm_type = "CARD"
            pm = {
                "payment_method_id": pm_id,
                "customer_id": customer_id,
                "type": pm_type,
                "card_company": random.choice(CARD_COMPANIES),
                "card_number_masked": f"{random.randint(1000,9999)}-****-****-{random.randint(1000,9999)}",
                "card_type": "CREDIT" if random.random() > 0.3 else "DEBIT",
                "card_owner_type": "PERSONAL" if random.random() > 0.2 else "CORPORATE",
                "card_exp_month": random.randint(1, 12),
                "card_exp_year": random.randint(2026, 2029),
                "is_default": i < len(customer_ids),
                "status": "ACTIVE",
                "created_at": now - timedelta(days=random.randint(1, 60)),
                "updated_at": now,
            }
        elif rand < 0.9:
            pm_type = "EASY_PAY"
            pm = {
                "payment_method_id": pm_id,
                "customer_id": customer_id,
                "type": pm_type,
                "easy_pay_provider": random.choice(EASY_PAY_PROVIDERS),
                "is_default": False,
                "status": "ACTIVE",
                "created_at": now - timedelta(days=random.randint(1, 60)),
                "updated_at": now,
            }
        else:
            pm_type = "VIRTUAL_ACCOUNT"
            pm = {
                "payment_method_id": pm_id,
                "customer_id": customer_id,
                "type": pm_type,
                "bank_code": random.choice(BANK_CODES),
                "is_default": False,
                "status": "ACTIVE",
                "created_at": now - timedelta(days=random.randint(1, 60)),
                "updated_at": now,
            }

        payment_methods.append(pm)

        if (i + 1) % 100 == 0:
            progress_bar(i + 1, total_methods, "  결제수단 생성")

    print()  # 줄바꿈

    # 카드, 간편결제, 가상계좌로 분리하여 insert
    with conn.cursor() as cur:
        for pm in payment_methods:
            pm_type = pm["type"]
            pm_copy = pm.copy()

            # None이 아닌 필드만 추출
            pm_filtered = {k: v for k, v in pm_copy.items() if v is not None}
            columns = list(pm_filtered.keys())
            placeholders = ', '.join(['%s'] * len(columns))

            insert_sql = f"""
                INSERT INTO payment_methods ({', '.join(columns)})
                VALUES ({placeholders})
                ON CONFLICT (payment_method_id) DO NOTHING
            """
            cur.execute(insert_sql, [pm_filtered[col] for col in columns])

    conn.commit()
    print(f"  결제수단 {total_methods}개 생성 완료")
    return [pm["payment_method_id"] for pm in payment_methods]


def generate_payments(conn, active_merchant_ids, customer_ids, pm_ids, count, period_days):
    """결제 데이터 생성"""
    print(f"결제 {count}건 생성 중...")

    # 고객-가맹점 매핑 가져오기
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT customer_id, merchant_id FROM pg_customers
            WHERE customer_id LIKE '{PREFIX}%'
        """)
        customer_merchant_map = {row[0]: row[1] for row in cur.fetchall()}

    # 고객-결제수단 매핑 가져오기
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT payment_method_id, customer_id FROM payment_methods
            WHERE payment_method_id LIKE '{PREFIX}%'
        """)
        pm_customer_map = {row[0]: row[1] for row in cur.fetchall()}

    payments = []
    payment_histories = []
    refunds = []
    now = datetime.now()

    for i in range(count):
        pay_key = f"{PREFIX}pay_{str(i+1).zfill(6)}"
        order_id = f"ORD-{now.strftime('%Y%m%d')}-{str(i+1).zfill(6)}"

        customer_id = random.choice(customer_ids)
        merchant_id = customer_merchant_map.get(customer_id, active_merchant_ids[0])

        # 해당 고객의 결제수단 찾기
        customer_pms = [pm for pm, cus in pm_customer_map.items() if cus == customer_id]
        pm_id = random.choice(customer_pms) if customer_pms else None

        amount = random_amount(10000, 1000000)

        # 시간 분포 (period_days 내)
        payment_time = now - timedelta(
            days=random.randint(0, period_days),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        # 결제 상태 분포: 70% DONE, 10% CANCELED, 10% PARTIAL_CANCELED, 5% WAITING, 5% ABORTED
        status_rand = random.random()

        if status_rand < 0.70:
            # 정상 완료
            status = "DONE"
            balance_amount = amount
            canceled_amount = 0
            approved_at = payment_time
            canceled_at = None
            cancel_reason = None
            failure_code = None
            failure_message = None

            method = random.choice(["CARD"] * 6 + ["EASY_PAY"] * 3 + ["BANK_TRANSFER"])

        elif status_rand < 0.80:
            # 전체 취소
            status = "CANCELED"
            balance_amount = 0
            canceled_amount = amount
            approved_at = payment_time - timedelta(hours=6)
            canceled_at = payment_time
            cancel_reason = random.choice(CANCEL_REASONS)
            failure_code = None
            failure_message = None
            method = "CARD"

            # 환불 레코드 추가
            refunds.append({
                "refund_key": f"{PREFIX}rf_{str(len(refunds)+1).zfill(6)}",
                "payment_key": pay_key,
                "amount": amount,
                "reason": cancel_reason,
                "status": "SUCCEEDED",
                "approved_at": payment_time,
                "requested_by": random.choice(["CUSTOMER", "MERCHANT"]),
                "created_at": payment_time - timedelta(minutes=10),
                "updated_at": now,
            })

        elif status_rand < 0.90:
            # 부분 취소
            status = "PARTIAL_CANCELED"
            partial_cancel_rate = random.uniform(0.2, 0.5)
            canceled_amount = int((amount * partial_cancel_rate) // 1000) * 1000
            balance_amount = amount - canceled_amount
            approved_at = payment_time - timedelta(hours=12)
            canceled_at = None  # 부분 취소는 canceled_at 없이
            cancel_reason = "상품 1건 취소"
            failure_code = None
            failure_message = None
            method = "CARD"

            # 환불 레코드 추가
            refunds.append({
                "refund_key": f"{PREFIX}rf_{str(len(refunds)+1).zfill(6)}",
                "payment_key": pay_key,
                "amount": canceled_amount,
                "reason": cancel_reason,
                "status": "SUCCEEDED",
                "approved_at": payment_time,
                "requested_by": "MERCHANT",
                "created_at": payment_time - timedelta(minutes=5),
                "updated_at": now,
            })

        elif status_rand < 0.95:
            # 가상계좌 대기
            status = "WAITING_FOR_DEPOSIT"
            balance_amount = amount
            canceled_amount = 0
            approved_at = None
            canceled_at = None
            cancel_reason = None
            failure_code = None
            failure_message = None
            method = "VIRTUAL_ACCOUNT"
            pm_id = None  # 가상계좌는 결제수단 없음

        else:
            # 실패
            status = "ABORTED"
            balance_amount = 0
            canceled_amount = 0
            approved_at = None
            canceled_at = None
            cancel_reason = None
            failure = random.choice(FAILURE_CODES)
            failure_code = failure[0]
            failure_message = failure[1]
            method = "CARD"

        payment = {
            "payment_key": pay_key,
            "order_id": order_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "payment_method_id": pm_id,
            "order_name": f"{random.choice(ORDER_NAMES)} 외 {random.randint(0, 5)}건",
            "amount": amount,
            "currency": "KRW",
            "method": method,
            "balance_amount": balance_amount,
            "supplied_amount": int(amount * 10 / 11),
            "vat": int(amount / 11),
            "status": status,
            "approved_at": approved_at,
            "canceled_at": canceled_at,
            "canceled_amount": canceled_amount if canceled_amount > 0 else None,
            "cancel_reason": cancel_reason,
            "failure_code": failure_code,
            "failure_message": failure_message,
            "card_approval_number": f"{random.randint(10000000, 99999999)}" if status in ("DONE", "CANCELED", "PARTIAL_CANCELED") else None,
            "card_installment_months": random.choice([0] * 7 + [3, 6, 12]) if method == "CARD" and amount >= 50000 else 0,
            "card_is_interest_free": random.random() > 0.7 if method == "CARD" and amount >= 50000 else False,
            "virtual_account_bank_code": random.choice(BANK_CODES) if method == "VIRTUAL_ACCOUNT" else None,
            "virtual_account_number": f"123{random.randint(1000000000, 9999999999)}456" if method == "VIRTUAL_ACCOUNT" else None,
            "virtual_account_holder": random.choice(KOREAN_NAMES) if method == "VIRTUAL_ACCOUNT" else None,
            "virtual_account_due_date": (now + timedelta(days=3)) if method == "VIRTUAL_ACCOUNT" else None,
            "created_at": payment_time - timedelta(minutes=1),
            "updated_at": now,
        }
        payments.append(payment)

        # 결제 이력 생성 (완료된 결제에 대해)
        if status in ("DONE", "CANCELED", "PARTIAL_CANCELED"):
            payment_histories.append({
                "payment_key": pay_key,
                "previous_status": "READY",
                "new_status": "IN_PROGRESS",
                "amount_change": 0,
                "balance_after": amount,
                "reason": "결제 시작",
                "processed_by": "SYSTEM",
                "created_at": payment_time - timedelta(minutes=1),
            })
            payment_histories.append({
                "payment_key": pay_key,
                "previous_status": "IN_PROGRESS",
                "new_status": "DONE",
                "amount_change": 0,
                "balance_after": amount,
                "reason": "결제 승인 완료",
                "processed_by": "SYSTEM",
                "created_at": approved_at if approved_at else payment_time,
            })

            if status in ("CANCELED", "PARTIAL_CANCELED"):
                payment_histories.append({
                    "payment_key": pay_key,
                    "previous_status": "DONE",
                    "new_status": status,
                    "amount_change": -canceled_amount,
                    "balance_after": balance_amount,
                    "reason": cancel_reason,
                    "processed_by": "MERCHANT",
                    "created_at": payment_time,
                })

        if (i + 1) % 500 == 0:
            progress_bar(i + 1, count, "  결제 생성")

    print()  # 줄바꿈

    # 결제 데이터 삽입
    with conn.cursor() as cur:
        for pay in payments:
            # None 값 제외
            pay_filtered = {k: v for k, v in pay.items() if v is not None}
            columns = list(pay_filtered.keys())
            placeholders = ', '.join(['%s'] * len(columns))

            insert_sql = f"""
                INSERT INTO payments ({', '.join(columns)})
                VALUES ({placeholders})
                ON CONFLICT (payment_key) DO NOTHING
            """
            cur.execute(insert_sql, [pay_filtered[col] for col in columns])

    conn.commit()
    print(f"  결제 {count}건 생성 완료")

    # 결제 이력 삽입
    if payment_histories:
        with conn.cursor() as cur:
            columns = list(payment_histories[0].keys())
            values = [[h[col] for col in columns] for h in payment_histories]

            insert_sql = f"""
                INSERT INTO payment_history ({', '.join(columns)})
                VALUES %s
            """
            execute_values(cur, insert_sql, values)
        conn.commit()
        print(f"  결제 이력 {len(payment_histories)}건 생성 완료")

    # 환불 삽입
    if refunds:
        with conn.cursor() as cur:
            columns = list(refunds[0].keys())
            values = [[r[col] for col in columns] for r in refunds]

            insert_sql = f"""
                INSERT INTO refunds ({', '.join(columns)})
                VALUES %s
                ON CONFLICT (refund_key) DO NOTHING
            """
            execute_values(cur, insert_sql, values)
        conn.commit()
        print(f"  환불 {len(refunds)}건 생성 완료")

    # 완료된 결제 키 반환
    done_payments = [p for p in payments if p["status"] == "DONE"]
    return [p["payment_key"] for p in done_payments], refunds


def generate_balance_transactions(conn, active_merchant_ids, period_days):
    """잔액 거래 내역 생성"""
    print("잔액 거래 내역 생성 중...")

    now = datetime.now()

    with conn.cursor() as cur:
        # 완료된 결제에 대한 잔액 거래 생성
        cur.execute(f"""
            INSERT INTO balance_transactions
            (transaction_id, merchant_id, source_type, source_id, amount, fee, net, status, available_on, description, created_at)
            SELECT
                '{PREFIX}txn_' || LPAD(ROW_NUMBER() OVER (ORDER BY created_at)::TEXT, 6, '0'),
                merchant_id,
                'PAYMENT',
                payment_key,
                amount,
                (amount * 35 / 1000),
                amount - (amount * 35 / 1000),
                CASE
                    WHEN approved_at < NOW() - INTERVAL '1 day' THEN 'AVAILABLE'
                    ELSE 'PENDING'
                END,
                approved_at + INTERVAL '1 day',
                order_name || ' 결제',
                approved_at
            FROM payments
            WHERE payment_key LIKE '{PREFIX}%'
                AND status = 'DONE'
                AND approved_at IS NOT NULL
        """)
        payment_txn_count = cur.rowcount

        # 환불에 대한 잔액 거래 생성
        cur.execute(f"""
            INSERT INTO balance_transactions
            (transaction_id, merchant_id, source_type, source_id, amount, fee, net, status, available_on, description, created_at)
            SELECT
                '{PREFIX}txn_rf_' || LPAD(ROW_NUMBER() OVER (ORDER BY r.created_at)::TEXT, 6, '0'),
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
            WHERE r.refund_key LIKE '{PREFIX}%'
                AND r.status = 'SUCCEEDED'
                AND r.approved_at IS NOT NULL
        """)
        refund_txn_count = cur.rowcount

    conn.commit()
    print(f"  잔액 거래 내역 {payment_txn_count + refund_txn_count}건 생성 완료")


def generate_settlements(conn, active_merchant_ids, period_days):
    """정산 데이터 생성"""
    print("정산 데이터 생성 중...")

    now = datetime.now()
    settlements = []
    settlement_details = []

    with conn.cursor() as cur:
        for day_offset in range(1, period_days + 1):
            settlement_day = (now - timedelta(days=day_offset)).date()
            target_day = settlement_day - timedelta(days=1)  # D+1 정산

            for merchant_id in active_merchant_ids:
                # 해당 가맹점, 해당 날짜의 결제 합계
                cur.execute(f"""
                    SELECT COALESCE(SUM(amount), 0), COUNT(*)
                    FROM payments
                    WHERE merchant_id = %s
                        AND payment_key LIKE '{PREFIX}%'
                        AND status = 'DONE'
                        AND DATE(approved_at) = %s
                """, (merchant_id, target_day))
                total_pay, pay_cnt = cur.fetchone()

                # 환불 합계
                cur.execute(f"""
                    SELECT COALESCE(SUM(r.amount), 0), COUNT(*)
                    FROM refunds r
                    JOIN payments p ON r.payment_key = p.payment_key
                    WHERE p.merchant_id = %s
                        AND r.refund_key LIKE '{PREFIX}%'
                        AND r.status = 'SUCCEEDED'
                        AND DATE(r.approved_at) = %s
                """, (merchant_id, target_day))
                total_ref, ref_cnt = cur.fetchone()

                if total_pay > 0 or total_ref > 0:
                    total_fee = int((total_pay - total_ref) * 35 / 1000)
                    net_amount = total_pay - total_ref - total_fee

                    settlement_id = f"{PREFIX}stl_{merchant_id.replace(PREFIX, '')}_{settlement_day.strftime('%Y%m%d')}"

                    # 가맹점 정산 계좌 정보 가져오기
                    cur.execute("""
                        SELECT settlement_bank_code, settlement_account_number, settlement_account_holder
                        FROM merchants WHERE merchant_id = %s
                    """, (merchant_id,))
                    bank_info = cur.fetchone()

                    settlements.append({
                        "settlement_id": settlement_id,
                        "merchant_id": merchant_id,
                        "settlement_date": settlement_day,
                        "period_start": target_day,
                        "period_end": target_day,
                        "total_payment_amount": total_pay,
                        "total_refund_amount": total_ref,
                        "total_fee": total_fee,
                        "net_amount": net_amount,
                        "payment_count": pay_cnt,
                        "refund_count": ref_cnt,
                        "status": "COMPLETED",
                        "payout_bank_code": bank_info[0] if bank_info else None,
                        "payout_account_number": bank_info[1] if bank_info else None,
                        "payout_account_holder": bank_info[2] if bank_info else None,
                        "payout_reference": f"PAY-{settlement_day.strftime('%Y%m%d')}-{len(settlements)+1:03d}",
                        "processed_at": datetime.combine(settlement_day, datetime.min.time()) + timedelta(hours=9),
                        "paid_out_at": datetime.combine(settlement_day, datetime.min.time()) + timedelta(hours=10),
                        "created_at": settlement_day,
                        "updated_at": settlement_day,
                    })

    # 정산 삽입
    if settlements:
        with conn.cursor() as cur:
            for stl in settlements:
                stl_filtered = {k: v for k, v in stl.items() if v is not None}
                columns = list(stl_filtered.keys())
                placeholders = ', '.join(['%s'] * len(columns))

                insert_sql = f"""
                    INSERT INTO settlements ({', '.join(columns)})
                    VALUES ({placeholders})
                    ON CONFLICT (settlement_id) DO NOTHING
                """
                cur.execute(insert_sql, [stl_filtered[col] for col in columns])

        conn.commit()
        print(f"  정산 {len(settlements)}건 생성 완료")

        # 정산 상세 생성
        generate_settlement_details(conn)

        # 결제 건 정산 완료 표시
        update_payment_settled_status(conn)
    else:
        print("  생성할 정산 데이터 없음")


def generate_settlement_details(conn):
    """정산 상세 데이터 생성"""
    print("정산 상세 데이터 생성 중...")

    with conn.cursor() as cur:
        # 결제 상세
        cur.execute(f"""
            INSERT INTO settlement_details
            (settlement_id, transaction_type, payment_key, amount, fee, net_amount, method, transaction_at, created_at)
            SELECT
                '{PREFIX}stl_' || REPLACE(p.merchant_id, '{PREFIX}', '') || '_' || TO_CHAR(DATE(p.approved_at) + 1, 'YYYYMMDD'),
                'PAYMENT',
                p.payment_key,
                p.amount,
                (p.amount * 35 / 1000),
                p.amount - (p.amount * 35 / 1000),
                p.method,
                p.approved_at,
                p.approved_at
            FROM payments p
            WHERE p.payment_key LIKE '{PREFIX}%'
                AND p.status = 'DONE'
                AND p.approved_at IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM settlements s
                    WHERE s.settlement_id = '{PREFIX}stl_' || REPLACE(p.merchant_id, '{PREFIX}', '') || '_' || TO_CHAR(DATE(p.approved_at) + 1, 'YYYYMMDD')
                )
        """)
        payment_detail_count = cur.rowcount

        # 환불 상세
        cur.execute(f"""
            INSERT INTO settlement_details
            (settlement_id, transaction_type, refund_key, payment_key, amount, fee, net_amount, method, transaction_at, created_at)
            SELECT
                '{PREFIX}stl_' || REPLACE(p.merchant_id, '{PREFIX}', '') || '_' || TO_CHAR(DATE(r.approved_at) + 1, 'YYYYMMDD'),
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
            WHERE r.refund_key LIKE '{PREFIX}%'
                AND r.status = 'SUCCEEDED'
                AND r.approved_at IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM settlements s
                    WHERE s.settlement_id = '{PREFIX}stl_' || REPLACE(p.merchant_id, '{PREFIX}', '') || '_' || TO_CHAR(DATE(r.approved_at) + 1, 'YYYYMMDD')
                )
        """)
        refund_detail_count = cur.rowcount

    conn.commit()
    print(f"  정산 상세 {payment_detail_count + refund_detail_count}건 생성 완료")


def update_payment_settled_status(conn):
    """결제 건 정산 완료 표시 업데이트"""
    print("결제 정산 상태 업데이트 중...")

    with conn.cursor() as cur:
        cur.execute(f"""
            UPDATE payments p
            SET is_settled = TRUE,
                settlement_id = '{PREFIX}stl_' || REPLACE(p.merchant_id, '{PREFIX}', '') || '_' || TO_CHAR(DATE(p.approved_at) + 1, 'YYYYMMDD')
            WHERE p.payment_key LIKE '{PREFIX}%'
                AND p.status = 'DONE'
                AND p.approved_at IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM settlements s
                    WHERE s.settlement_id = '{PREFIX}stl_' || REPLACE(p.merchant_id, '{PREFIX}', '') || '_' || TO_CHAR(DATE(p.approved_at) + 1, 'YYYYMMDD')
                )
        """)
        updated = cur.rowcount

    conn.commit()
    print(f"  결제 {updated}건 정산 완료 표시")


def print_statistics(conn):
    """생성된 데이터 통계 출력"""
    print("\n" + "=" * 60)
    print("데이터 시딩 완료 - 통계")
    print("=" * 60)

    with conn.cursor() as cur:
        tables = [
            ("merchants", "가맹점"),
            ("pg_customers", "고객"),
            ("payment_methods", "결제수단"),
            ("payments", "결제"),
            ("payment_history", "결제이력"),
            ("refunds", "환불"),
            ("balance_transactions", "잔액거래"),
            ("settlements", "정산"),
            ("settlement_details", "정산상세"),
        ]

        print(f"\n{'테이블':<25} {'전체':<12} {'시딩 데이터':<12}")
        print("-" * 50)

        for table, name in tables:
            # 전체 건수
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            total = cur.fetchone()[0]

            # 시딩 데이터 건수
            if table in ("payment_history",):
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE payment_key LIKE '{PREFIX}%'")
            elif table == "settlements":
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE settlement_id LIKE '{PREFIX}%'")
            elif table == "settlement_details":
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE settlement_id LIKE '{PREFIX}%'")
            elif table == "balance_transactions":
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE transaction_id LIKE '{PREFIX}%'")
            else:
                pk_col = list({"merchants": "merchant_id", "pg_customers": "customer_id",
                              "payment_methods": "payment_method_id", "payments": "payment_key",
                              "refunds": "refund_key"}.get(table, "id"))
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {pk_col[0] if isinstance(pk_col, list) else pk_col} LIKE '{PREFIX}%'")

            seeded = cur.fetchone()[0]
            print(f"{name:<25} {total:<12} {seeded:<12}")

        # 결제 상태별 통계
        print("\n결제 상태별 통계 (시딩 데이터):")
        print("-" * 40)
        cur.execute(f"""
            SELECT status, COUNT(*), COALESCE(SUM(amount), 0)
            FROM payments
            WHERE payment_key LIKE '{PREFIX}%'
            GROUP BY status
            ORDER BY COUNT(*) DESC
        """)
        for row in cur.fetchall():
            print(f"  {row[0]:<20} {row[1]:>6}건  {row[2]:>15,}원")

    print("\n" + "=" * 60)


# =============================================================================
# 메인
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="PG 결제 서비스 테스트 데이터 시딩")
    parser.add_argument("--scale", choices=["small", "medium", "large"], default="medium",
                       help="데이터 규모 (default: medium)")
    parser.add_argument("--period", type=int, default=30,
                       help="데이터 기간 (일) (default: 30)")
    parser.add_argument("--clear-only", action="store_true",
                       help="기존 시딩 데이터만 삭제")

    args = parser.parse_args()

    # psycopg2 lazy import
    global psycopg2, execute_values
    try:
        import psycopg2 as pg2
        from psycopg2.extras import execute_values as ev
        psycopg2 = pg2
        execute_values = ev
    except ImportError:
        print("Error: psycopg2 패키지가 필요합니다.")
        print("설치: pip install psycopg2-binary")
        sys.exit(1)

    config = SCALE_CONFIG[args.scale]

    print("=" * 60)
    print("PG 결제 서비스 테스트 데이터 시딩")
    print("=" * 60)
    print(f"규모: {args.scale}")
    print(f"기간: {args.period}일")
    print(f"예상 데이터량:")
    print(f"  - 가맹점: {config['merchants']}개")
    print(f"  - 고객: ~{int(config['merchants'] * config['customers_per_merchant'])}명")
    print(f"  - 결제: {config['payments']}건")
    print()

    try:
        conn = get_db_connection()
        print("PostgreSQL 연결 성공")
    except Exception as e:
        print(f"PostgreSQL 연결 실패: {e}")
        print("\n환경 변수를 확인하세요:")
        print("  POSTGRES_HOST (default: localhost)")
        print("  POSTGRES_PORT (default: 5432)")
        print("  POSTGRES_DB (default: chatops)")
        print("  POSTGRES_USER (default: chatops_user)")
        print("  POSTGRES_PASSWORD (default: chatops_pass)")
        sys.exit(1)

    try:
        # 기존 시딩 데이터 삭제
        clear_seeded_data(conn)

        if args.clear_only:
            print("\n기존 시딩 데이터 삭제 완료")
            return

        print()

        # 1. 가맹점 생성
        active_merchant_ids = generate_merchants(conn, config["merchants"], args.period)

        if not active_merchant_ids:
            print("Error: 활성 가맹점이 없습니다")
            sys.exit(1)

        # 2. 고객 생성
        customer_ids = generate_customers(conn, active_merchant_ids, config["customers_per_merchant"])

        # 3. 결제수단 생성
        pm_ids = generate_payment_methods(conn, customer_ids, config["payment_methods_per_customer"])

        # 4. 결제 생성 (환불, 결제이력 포함)
        done_payment_keys, refunds = generate_payments(
            conn, active_merchant_ids, customer_ids, pm_ids, config["payments"], args.period
        )

        # 5. 잔액 거래 내역 생성
        generate_balance_transactions(conn, active_merchant_ids, args.period)

        # 6. 정산 생성 (정산 상세 포함)
        generate_settlements(conn, active_merchant_ids, args.period)

        # 통계 출력
        print_statistics(conn)

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
