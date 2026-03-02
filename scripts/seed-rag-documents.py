#!/usr/bin/env python3
"""
PG 서비스용 RAG 문서 시드 데이터 생성
실제 토스페이먼츠/아임포트 스타일의 상세한 문서를 생성합니다.
"""

import requests
import json
import sys

API_BASE = "http://localhost:8000/api/v1/documents"

# ============================================================
# 1. ENTITY 문서 (7개 핵심 테이블)
# ============================================================

ENTITY_DOCS = [
    {
        "doc_type": "entity",
        "title": "Payments 엔티티 - 결제 트랜잭션",
        "content": """## Payments 엔티티

결제 트랜잭션의 전체 생명주기를 관리하는 핵심 엔티티입니다.

### 주요 필드

**결제 식별**
- payment_key (PK): PG사에서 발급하는 결제 고유키. 형식: pay_XXXXXXXX
- order_id: 가맹점에서 생성한 주문번호. 가맹점 내 중복 불가
- merchant_id: 가맹점 ID (FK → merchants)
- customer_id: 구매자 ID (FK → pg_customers)

**금액 정보**
- amount: 결제 요청 금액 (원 단위, 양수)
- balance_amount: 취소 가능한 잔액. 부분 취소 시 감소
- supplied_amount: 공급가액 (VAT 제외, amount의 10/11)
- vat: 부가세 (기본: amount의 1/11)
- tax_free_amount: 면세 금액 (면세 상품인 경우)
- currency: 통화 코드 (기본값: KRW)

**결제 수단**
- method: 결제 수단 유형
  - CARD: 신용/체크카드
  - VIRTUAL_ACCOUNT: 가상계좌
  - BANK_TRANSFER: 계좌이체
  - MOBILE: 휴대폰 결제
  - EASY_PAY: 간편결제 (카카오페이, 네이버페이 등)
- method_detail (JSONB): 결제 수단별 상세 정보 (카드사, 은행 등)

**카드 결제 전용 필드**
- card_approval_number: 카드 승인번호 (8자리)
- card_installment_months: 할부 개월 수 (0=일시불, 2~12개월)
- card_is_interest_free: 무이자 할부 여부

**가상계좌 전용 필드**
- virtual_account_bank_code: 은행 코드 (예: 004=KB국민, 088=신한)
- virtual_account_number: 가상계좌 번호
- virtual_account_holder: 예금주명
- virtual_account_due_date: 입금 기한 (보통 발급 후 7일)
- virtual_account_refund_status: 환불 상태 (NONE, PENDING, COMPLETED, FAILED)

**결제 상태 (status)**
- READY: 결제 대기 (결제창 진입)
- IN_PROGRESS: 결제 진행중 (PG사 처리중)
- WAITING_FOR_DEPOSIT: 입금 대기 (가상계좌)
- DONE: 결제 완료
- CANCELED: 전액 취소
- PARTIAL_CANCELED: 부분 취소
- ABORTED: 결제 중단 (사용자 취소 또는 오류)
- EXPIRED: 만료 (가상계좌 입금 기한 초과)

**취소 정보**
- canceled_at: 취소 일시
- canceled_amount: 취소된 총 금액
- cancel_reason: 취소 사유

**실패 정보**
- failure_code: 실패 코드 (예: INVALID_CARD_NUMBER)
- failure_message: 실패 메시지

**정산 정보**
- is_settled: 정산 완료 여부 (true=정산됨)
- settlement_id: 정산 ID (FK → settlements)

**기타**
- order_name: 상품명 (결제창에 표시, 최대 100자)
- receipt_url: 영수증 URL
- request_id: 멱등성 키 (중복 결제 방지)
- metadata (JSONB): 가맹점 커스텀 데이터

### 결제 상태 전이도

```
READY → IN_PROGRESS → DONE → CANCELED
                          → PARTIAL_CANCELED
                    → ABORTED
READY → WAITING_FOR_DEPOSIT → DONE (입금 완료)
                            → EXPIRED (기한 초과)
```

### 주요 조회 패턴

1. 가맹점별 결제 조회: WHERE merchant_id = ? AND created_at BETWEEN ? AND ?
2. 정산 대상 조회: WHERE is_settled = false AND status = 'DONE'
3. 취소 가능 결제: WHERE status IN ('DONE', 'PARTIAL_CANCELED') AND balance_amount > 0
4. 상태별 현황: GROUP BY status
5. 결제 수단별 현황: GROUP BY method
6. **거래 건수 집계 (중요!)**: 가맹점별/월별 거래 건수를 조회할 때는 반드시 payments 테이블에서 COUNT(*)를 사용하세요.
   - 월별 평균 거래 건수: 먼저 월별 COUNT(*) GROUP BY, 그 다음 AVG()
   - settlements.payment_count는 일별 정산 레코드의 건수이므로 거래 건수 집계에 부적합합니다.""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "entity",
        "title": "Merchants 엔티티 - 가맹점 정보",
        "content": """## Merchants 엔티티

PG 서비스를 이용하는 가맹점(사업자) 정보를 관리합니다.

### 주요 필드

**가맹점 식별**
- merchant_id (PK): 가맹점 고유 ID. 형식: mer_XXXXXXXX
- business_number: 사업자등록번호 (UNIQUE, 10자리)
- business_name: 상호명

**사업자 정보**
- representative_name: 대표자명
- business_type: 업종 (예: 소매업, 서비스업)
- business_category: 업태 (예: 전자상거래, 음식점)

**연락처**
- email: 대표 이메일 (고유, 알림 수신용)
- phone: 대표 전화번호
- address: 사업장 주소
- postal_code: 우편번호

**정산 계좌 정보**
- settlement_bank_code: 정산 은행 코드 (예: 004=KB국민)
- settlement_account_number: 정산 계좌번호
- settlement_account_holder: 예금주명

**정산 설정**
- settlement_cycle: 정산 주기
  - D+0: 당일 정산
  - D+1: 익일 정산 (기본값)
  - D+2: 2일 후 정산
  - WEEKLY: 주간 정산 (매주 월요일)
  - MONTHLY: 월간 정산 (매월 1일)
- fee_rate: 수수료율 (DECIMAL 5,4)
  - 기본값: 0.0350 (3.5%)
  - 카드: 2.5%~3.5%
  - 간편결제: 3.0%~3.5%
  - 가상계좌: 300원~500원/건

**API 키**
- api_key_live: 운영환경 API 키 (보안 저장)
- api_key_test: 테스트환경 API 키

**가맹점 상태 (status)**
- PENDING: 심사 대기 (신규 가입)
- ACTIVE: 활성화 (정상 운영)
- SUSPENDED: 정지 (계약 위반, 미정산 등)
- TERMINATED: 해지

**심사 정보**
- verified_at: 심사 완료 일시

**기타**
- metadata (JSONB): 추가 설정 (한도, 허용 결제 수단 등)

### 가맹점 상태 전이

```
PENDING → ACTIVE (심사 승인)
        → TERMINATED (심사 거절)
ACTIVE → SUSPENDED (일시 정지)
       → TERMINATED (계약 해지)
SUSPENDED → ACTIVE (정지 해제)
          → TERMINATED (계약 해지)
```

### 주요 조회 패턴

1. 활성 가맹점 조회: WHERE status = 'ACTIVE'
2. 심사 대기 가맹점: WHERE status = 'PENDING'
3. 수수료율별 현황: GROUP BY fee_rate
4. 정산 주기별 현황: GROUP BY settlement_cycle""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "entity",
        "title": "Refunds 엔티티 - 환불 트랜잭션",
        "content": """## Refunds 엔티티

결제 취소/환불 트랜잭션을 관리합니다. 하나의 결제(Payment)에 여러 환불이 있을 수 있습니다.

### 주요 필드

**환불 식별**
- refund_key (PK): 환불 고유키. 형식: ref_XXXXXXXX
- payment_key (FK → payments): 원 결제 키

**환불 금액**
- amount: 환불 금액 (원 결제의 balance_amount 이하)
- tax_free_amount: 면세 환불 금액

**환불 사유**
- reason: 환불 사유 (고객에게 표시)
- cancel_reason_code: 환불 사유 코드
  - CUSTOMER_REQUEST: 고객 요청
  - PRODUCT_DEFECT: 상품 불량
  - DELIVERY_DELAY: 배송 지연
  - ORDER_MISTAKE: 주문 실수
  - OTHER: 기타

**환불 상태 (status)**
- PENDING: 환불 대기 (가맹점 요청)
- SUCCEEDED: 환불 완료
- FAILED: 환불 실패

**처리 정보**
- approved_at: 환불 승인 일시
- failure_code: 실패 코드
- failure_message: 실패 메시지

**환불 계좌 (가상계좌/계좌이체 환불 시)**
- refund_bank_code: 환불 은행 코드
- refund_account_number: 환불 계좌번호
- refund_account_holder: 예금주명

**요청 정보**
- request_id: 멱등성 키
- requested_by: 요청자 유형 (MERCHANT, ADMIN, CUSTOMER)
- requester_id: 요청자 ID

### 환불 유형

1. **전액 환불**: amount = 원 결제 amount
2. **부분 환불**: amount < 원 결제 balance_amount
3. **카드 환불**: 카드사로 자동 환불 (7~14일)
4. **계좌 환불**: 지정 계좌로 입금 (가상계좌/계좌이체)

### 환불 상태 전이

```
PENDING → SUCCEEDED (환불 승인)
        → FAILED (환불 실패)
```

### 주요 조회 패턴

1. 결제별 환불 내역: WHERE payment_key = ?
2. 환불 대기 건: WHERE status = 'PENDING'
3. 기간별 환불 현황: WHERE created_at BETWEEN ? AND ?
4. 환불 사유별 통계: GROUP BY cancel_reason_code""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "entity",
        "title": "Settlements 엔티티 - 정산 정보",
        "content": """## Settlements 엔티티

가맹점별 정산 내역을 관리합니다. 정산은 일정 기간의 결제를 집계하여 수수료를 제외한 금액을 가맹점에게 지급하는 프로세스입니다.

### 주요 필드

**정산 식별**
- settlement_id (PK): 정산 고유 ID. 형식: stl_YYYYMMDD_merXXX
- merchant_id (FK → merchants): 가맹점 ID

**정산 기간**
- settlement_date: 정산 예정일 (정산 주기에 따라 결정)
- period_start: 정산 대상 기간 시작일
- period_end: 정산 대상 기간 종료일

**정산 금액**
- total_payment_amount: 총 결제 금액
- total_refund_amount: 총 환불 금액
- total_fee: 총 수수료 (결제 금액 × 수수료율)
- net_amount: 정산 금액 = 결제금액 - 환불금액 - 수수료

**정산 건수 (⚠️ 정산 기간 단위)**
- payment_count: 해당 정산 기간(period_start~period_end) 내 포함된 결제 건수.
  - 주의: 이 값은 일별/주별 정산 레코드 하나에 포함된 건수입니다.
  - "가맹점의 총 거래 건수"나 "월별 평균 거래 건수"를 구할 때는 payments 테이블에서 COUNT(*)를 사용하세요.
- refund_count: 해당 정산 기간 내 환불 건수

**정산 상태 (status)**
- PENDING: 정산 대기 (집계 완료, 지급 대기)
- PROCESSING: 정산 진행중 (은행 이체 중)
- COMPLETED: 정산 완료 (지급 완료)
- FAILED: 정산 실패 (계좌 오류 등)

**지급 계좌 정보**
- payout_bank_code: 지급 은행 코드
- payout_account_number: 지급 계좌번호
- payout_account_holder: 예금주명
- payout_reference: 지급 참조번호 (은행 거래 번호)

**처리 정보**
- processed_at: 정산 처리 시작 일시
- paid_out_at: 실제 지급 일시
- failure_code: 실패 코드
- failure_message: 실패 메시지

### 정산 계산 예시

```
총 결제금액: 10,000,000원 (100건)
총 환불금액: 500,000원 (5건)
수수료율: 3.5%
수수료: (10,000,000 - 500,000) × 0.035 = 332,500원
정산금액: 10,000,000 - 500,000 - 332,500 = 9,167,500원
```

### 정산 상태 전이

```
PENDING → PROCESSING (지급 시작)
        → FAILED (계좌 오류)
PROCESSING → COMPLETED (지급 완료)
           → FAILED (이체 실패)
FAILED → PENDING (재시도)
```

### 주요 조회 패턴

1. 가맹점별 정산: WHERE merchant_id = ?
2. 정산 예정 건: WHERE status = 'PENDING' AND settlement_date = ?
3. 기간별 정산: WHERE settlement_date BETWEEN ? AND ?
4. 미완료 정산: WHERE status IN ('PENDING', 'PROCESSING')""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "entity",
        "title": "PG_Customers 엔티티 - 구매자 정보",
        "content": """## PG_Customers 엔티티

PG 서비스를 통해 결제하는 구매자(최종 소비자) 정보를 관리합니다.
가맹점별로 고객을 관리하며, 빌링키 결제나 결제 수단 저장에 활용됩니다.

### 주요 필드

**고객 식별**
- customer_id (PK): 고객 고유 ID. 형식: cus_XXXXXXXX
- merchant_id (FK → merchants): 가맹점 ID (고객은 가맹점별로 관리)

**기본 정보**
- email: 이메일 (결제 알림용)
- name: 고객명
- phone: 연락처

**배송 정보**
- shipping_name: 수령인명
- shipping_phone: 수령인 연락처
- shipping_address: 배송 주소
- shipping_postal_code: 우편번호

**결제 수단**
- default_payment_method_id (FK → payment_methods): 기본 결제 수단

### 주요 조회 패턴

1. 가맹점별 고객: WHERE merchant_id = ?
2. 이메일로 조회: WHERE email = ?
3. 신규 고객: WHERE created_at >= ? (최근 가입)
4. 결제 이력 있는 고객: JOIN payments ON customer_id""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "entity",
        "title": "Payment_Methods 엔티티 - 저장된 결제 수단",
        "content": """## Payment_Methods 엔티티

고객이 저장한 결제 수단 정보를 관리합니다. 빌링키 결제(정기결제)에 사용됩니다.

### 주요 필드

**결제 수단 식별**
- payment_method_id (PK): 결제 수단 고유 ID. 형식: pm_XXXXXXXX
- customer_id (FK → pg_customers): 고객 ID

**결제 수단 유형 (type)**
- CARD: 신용/체크카드
- VIRTUAL_ACCOUNT: 가상계좌
- BANK_TRANSFER: 계좌이체
- MOBILE: 휴대폰
- EASY_PAY: 간편결제

**카드 정보**
- card_company: 카드사 (예: 삼성카드, 신한카드)
- card_number_masked: 마스킹된 카드번호 (예: 1234-****-****-5678)
- card_type: 카드 유형 (CREDIT, DEBIT, PREPAID)
- card_owner_type: 소유자 유형 (PERSONAL, CORPORATE)
- card_exp_month: 만료 월
- card_exp_year: 만료 년
- card_issuer_code: 발급사 코드
- card_acquirer_code: 매입사 코드

**계좌 정보**
- bank_code: 은행 코드
- account_number: 계좌번호 (마스킹)
- account_holder: 예금주명

**간편결제 정보**
- easy_pay_provider: 제공사 (KAKAOPAY, NAVERPAY, TOSSPAY, PAYCO 등)

**빌링키 정보**
- billing_key: 빌링키 (암호화 저장)
- billing_key_expires_at: 빌링키 만료일

**상태**
- is_default: 기본 결제 수단 여부
- status: 상태 (ACTIVE, INACTIVE, EXPIRED)

### 주요 조회 패턴

1. 고객별 결제 수단: WHERE customer_id = ?
2. 활성 카드: WHERE type = 'CARD' AND status = 'ACTIVE'
3. 기본 결제 수단: WHERE is_default = true
4. 만료 예정 카드: WHERE card_exp_year = ? AND card_exp_month <= ?""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "entity",
        "title": "Balance_Transactions 엔티티 - 잔액 변동 내역",
        "content": """## Balance_Transactions 엔티티

가맹점 잔액의 모든 변동 내역을 추적합니다. 결제, 환불, 수수료, 정산 지급 등 모든 금액 변동을 기록합니다.

### 주요 필드

**거래 식별**
- transaction_id (PK): 거래 고유 ID. 형식: bal_XXXXXXXX
- merchant_id (FK → merchants): 가맹점 ID

**거래 유형 (source_type)**
- PAYMENT: 결제 (잔액 증가)
- REFUND: 환불 (잔액 감소)
- FEE: 수수료 (잔액 감소)
- PAYOUT: 정산 지급 (잔액 감소)
- ADJUSTMENT: 수동 조정 (증가/감소)

**금액 정보**
- source_id: 원 거래 ID (payment_key, refund_key 등)
- amount: 거래 금액 (양수: 증가, 음수: 감소)
- fee: 수수료 (PAYMENT일 때만)
- net: 순 변동액 = amount - fee
- currency: 통화 (기본: KRW)

**잔액 정보**
- balance_before: 거래 전 잔액
- balance_after: 거래 후 잔액

**상태 (status)**
- PENDING: 대기 (처리 예정)
- AVAILABLE: 가용 (정산 가능)
- SETTLED: 정산됨

**가용 시점**
- available_on: 가용 예정일 (D+1 등 정산 주기에 따라)

**설명**
- description: 거래 설명 (예: "카드 결제 승인", "부분 환불")

### 잔액 계산 예시

```
[거래 1] PAYMENT: +100,000원, fee: -3,500원, net: +96,500원
         balance_before: 1,000,000원 → balance_after: 1,096,500원

[거래 2] REFUND: -30,000원, fee: +1,050원(환불 수수료 복원), net: -28,950원
         balance_before: 1,096,500원 → balance_after: 1,067,550원

[거래 3] PAYOUT: -1,000,000원
         balance_before: 1,067,550원 → balance_after: 67,550원
```

### 주요 조회 패턴

1. 가맹점 잔액 내역: WHERE merchant_id = ?
2. 결제 거래: WHERE source_type = 'PAYMENT'
3. 가용 잔액 조회: WHERE status = 'AVAILABLE'
4. 기간별 거래: WHERE created_at BETWEEN ? AND ?""",
        "status": "active",
        "submitted_by": "system"
    }
]

# ============================================================
# 2. BUSINESS_LOGIC 문서
# ============================================================

BUSINESS_LOGIC_DOCS = [
    {
        "doc_type": "business_logic",
        "title": "결제 처리 플로우",
        "content": """## 결제 처리 플로우

### 1. 일반 결제 (카드/간편결제)

```
1. 결제 요청 (READY)
   - 가맹점 → PG: 주문정보 + 결제 수단 전달
   - payment_key 발급

2. 결제 진행 (IN_PROGRESS)
   - 결제창 노출 또는 간편결제 연동
   - 카드사/VAN 승인 요청

3. 결제 완료 (DONE)
   - 승인번호 발급
   - approved_at 기록
   - balance_amount = amount
   - 가맹점 웹훅 전송

4. 결제 실패 (ABORTED)
   - failure_code, failure_message 기록
   - 가맹점 웹훅 전송
```

### 2. 가상계좌 결제

```
1. 가상계좌 발급 (WAITING_FOR_DEPOSIT)
   - 은행별 가상계좌 번호 생성
   - 입금 기한 설정 (기본 7일)
   - virtual_account_* 필드 기록

2. 입금 완료 (DONE)
   - 은행 입금 통지 수신
   - approved_at 기록
   - 가맹점 웹훅 전송

3. 입금 기한 초과 (EXPIRED)
   - 배치로 상태 변경
   - 가상계좌 재사용 불가
```

### 3. 빌링키 결제 (정기결제)

```
1. 빌링키 발급
   - 최초 카드 등록 시 billing_key 생성
   - payment_methods 테이블에 저장

2. 자동 결제 요청
   - billing_key로 결제 요청
   - 결제창 없이 즉시 승인

3. 재시도 로직
   - 실패 시 최대 3회 재시도
   - 24시간 간격으로 재시도
```

### 결제 제한 규칙

- 1회 최대 결제금액: 1억원
- 1일 최대 결제금액: 가맹점별 설정
- 최소 결제금액: 100원
- 주문번호(order_id) 중복 불가 (가맹점 내)""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "business_logic",
        "title": "환불 처리 규칙",
        "content": """## 환불 처리 규칙

### 환불 가능 조건

1. **상태 조건**
   - status가 DONE 또는 PARTIAL_CANCELED
   - balance_amount > 0 (취소 가능 잔액 존재)

2. **금액 조건**
   - 환불 금액 ≤ balance_amount
   - 면세 환불 금액 ≤ 남은 면세 금액

3. **기간 조건**
   - 카드: 승인 후 180일 이내
   - 가상계좌: 입금 후 1년 이내
   - 계좌이체: 입금 후 180일 이내

### 환불 유형별 처리

#### 1. 카드 환불
```
승인 취소: 당일 취소 (00:00~23:59)
→ 카드사에 직접 취소 요청
→ 고객 청구서에 결제 없음

매입 취소: 익일 이후 취소
→ 카드사에 환불 요청
→ 7~14영업일 후 카드 계좌 입금
```

#### 2. 가상계좌 환불
```
환불 계좌 필수 입력:
- refund_bank_code
- refund_account_number
- refund_account_holder

처리 시간: 1~3영업일
```

#### 3. 계좌이체 환불
```
원 계좌로 자동 환불 또는
별도 환불 계좌 지정 가능

처리 시간: 1~3영업일
```

### 부분 환불

- 동일 결제에 대해 여러 번 부분 환불 가능
- 환불 시마다 balance_amount 차감
- 전액 환불 시 status → CANCELED
- 부분 환불 시 status → PARTIAL_CANCELED

### 환불 수수료

- 기본적으로 결제 수수료는 환불되지 않음
- 가맹점 계약에 따라 수수료 복원 가능
- 복원 시 balance_transactions에 FEE 거래 기록""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "business_logic",
        "title": "정산 규칙 및 계산 방식",
        "content": """## 정산 규칙 및 계산 방식

### 정산 주기

| 주기 | 설명 | 정산일 | 대상 기간 |
|------|------|--------|----------|
| D+0 | 당일 정산 | 당일 | 전일 00:00~23:59 |
| D+1 | 익일 정산 | T+1 | T일 00:00~23:59 |
| D+2 | 2일 후 정산 | T+2 | T일 00:00~23:59 |
| WEEKLY | 주간 정산 | 매주 월요일 | 전주 월~일 |
| MONTHLY | 월간 정산 | 매월 1일 | 전월 1일~말일 |

### 정산 금액 계산

```
정산금액 = 총결제금액 - 총환불금액 - 총수수료

총수수료 = Σ(결제금액 × 수수료율) - Σ(환불금액 × 수수료율)
```

### 결제 수단별 수수료율 (기본값)

| 결제 수단 | 수수료율 | 비고 |
|----------|----------|------|
| 신용카드 | 3.3% | 일반 가맹점 |
| 체크카드 | 2.5% | 우대 적용 |
| 가상계좌 | 300원/건 | 건당 정액 |
| 계좌이체 | 1.8% | 최소 300원 |
| 휴대폰 | 5.5% | 통신사 정산 포함 |
| 카카오페이 | 3.3% | 간편결제 |
| 네이버페이 | 3.3% | 간편결제 |

### 정산 프로세스

```
1. 정산 대상 집계 (00:00 배치)
   - 전일/전주/전월 DONE 상태 결제 집계
   - 환불 내역 반영
   - 수수료 계산

2. 정산 생성 (PENDING)
   - settlements 레코드 생성
   - settlement_details 상세 내역 기록
   - payments.is_settled = true 업데이트

3. 정산 지급 (PROCESSING)
   - 가맹점 정산 계좌로 이체 요청
   - payout_reference 기록

4. 정산 완료 (COMPLETED)
   - 이체 완료 확인
   - paid_out_at 기록
```

### 정산 보류 조건

- 가맹점 상태가 SUSPENDED인 경우
- 정산 계좌 정보 오류
- 분쟁 건 포함 시 (chargeback)
- 이상 거래 탐지 시""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "business_logic",
        "title": "수수료 계산 및 정책",
        "content": """## 수수료 계산 및 정책

### 수수료 구조

PG 수수료는 결제 금액에 대한 비율 또는 건당 정액으로 부과됩니다.

### 기본 수수료율

가맹점 계약 시 기본 수수료율이 설정되며, merchants.fee_rate 필드에 저장됩니다.

```
fee_rate = 0.0350  →  3.5%
fee_rate = 0.0250  →  2.5%
fee_rate = 0.0180  →  1.8%
```

### 수수료 계산 공식

```
수수료 = 결제금액 × 수수료율
부가세 = 수수료 × 0.1 (VAT 10%)
총 수수료 = 수수료 + 부가세
```

### 결제 금액별 수수료 예시

| 결제금액 | 수수료율 | 수수료 | VAT | 총 수수료 |
|---------|---------|--------|-----|----------|
| 10,000원 | 3.5% | 350원 | 35원 | 385원 |
| 50,000원 | 3.5% | 1,750원 | 175원 | 1,925원 |
| 100,000원 | 3.5% | 3,500원 | 350원 | 3,850원 |
| 1,000,000원 | 3.5% | 35,000원 | 3,500원 | 38,500원 |

### 환불 시 수수료 처리

**기본 정책: 수수료 미복원**
- 환불 시에도 원 결제 수수료는 유지
- 예: 100,000원 결제 후 전액 환불 → 수수료 3,850원은 가맹점 부담

**우대 정책: 수수료 복원**
- 특정 가맹점 계약 시 환불 수수료 복원
- balance_transactions에 FEE(양수) 기록

### 부가 수수료

| 항목 | 금액 | 적용 조건 |
|------|------|----------|
| 가상계좌 발급 | 300원/건 | 가상계좌 결제 시 |
| 영수증 발행 | 무료 | 기본 제공 |
| 현금영수증 | 무료 | 요청 시 |
| 세금계산서 | 무료 | 월 1회 |

### 월별 수수료 집계 쿼리 예시

```sql
SELECT
    DATE_TRUNC('month', approved_at) as month,
    SUM(amount) as total_payment,
    SUM(amount * 0.035) as total_fee
FROM payments
WHERE status = 'DONE'
  AND merchant_id = ?
GROUP BY DATE_TRUNC('month', approved_at)
```""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "business_logic",
        "title": "결제 수단별 특성 및 제약",
        "content": """## 결제 수단별 특성 및 제약

### 1. 신용/체크카드 (CARD)

**특성**
- 가장 일반적인 결제 수단
- 실시간 승인/취소
- 할부 결제 지원 (신용카드만)

**필드 매핑**
- method = 'CARD'
- card_approval_number: 승인번호
- card_installment_months: 할부 개월
- card_is_interest_free: 무이자 여부

**제약**
- 최소 결제금액: 100원
- 최대 결제금액: 5,000만원
- 할부: 5만원 이상, 2~12개월

### 2. 가상계좌 (VIRTUAL_ACCOUNT)

**특성**
- 은행별 고유 계좌번호 발급
- 입금 시까지 WAITING_FOR_DEPOSIT 상태
- 입금 기한 초과 시 자동 만료

**필드 매핑**
- method = 'VIRTUAL_ACCOUNT'
- virtual_account_bank_code: 은행 코드
- virtual_account_number: 계좌번호
- virtual_account_due_date: 입금 기한

**은행 코드**
- 004: KB국민
- 088: 신한
- 020: 우리
- 011: 농협
- 023: SC제일
- 081: 하나
- 003: IBK기업

**제약**
- 최소 결제금액: 1,000원
- 최대 결제금액: 3억원
- 기본 입금 기한: 7일

### 3. 계좌이체 (BANK_TRANSFER)

**특성**
- 실시간 계좌이체
- 공인인증서/생체인증 필요
- 즉시 승인

**제약**
- 최소: 1,000원
- 최대: 이체한도 적용

### 4. 휴대폰 결제 (MOBILE)

**특성**
- 통신요금과 합산 청구
- 월 한도 제한 있음

**제약**
- 성인: 월 100만원
- 미성년: 월 30만원
- 결제당 최대 50만원

### 5. 간편결제 (EASY_PAY)

**종류**
- KAKAOPAY: 카카오페이
- NAVERPAY: 네이버페이
- TOSSPAY: 토스페이
- PAYCO: 페이코
- SAMSUNGPAY: 삼성페이

**특성**
- 각 플랫폼 앱/웹 연동
- 빠른 결제 경험
- 포인트 사용 가능

**필드 매핑**
- method = 'EASY_PAY'
- method_detail.provider: 제공사명
- method_detail.points_used: 사용 포인트""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "business_logic",
        "title": "가맹점 상태 및 계약 관리",
        "content": """## 가맹점 상태 및 계약 관리

### 가맹점 상태 (status)

| 상태 | 설명 | 결제 가능 | 정산 가능 |
|------|------|----------|----------|
| PENDING | 심사 대기 | ❌ | ❌ |
| ACTIVE | 활성화 | ✅ | ✅ |
| SUSPENDED | 정지 | ❌ | ❌ (보류) |
| TERMINATED | 해지 | ❌ | ❌ |

### 가맹점 등록 프로세스

```
1. 가입 신청
   - 사업자 정보 입력
   - 서류 제출 (사업자등록증, 통장사본 등)
   - status = PENDING

2. 심사
   - 사업자 진위 확인
   - 업종 심사 (고위험 업종 제한)
   - 신용도 확인

3. 승인
   - status = ACTIVE
   - API 키 발급
   - 테스트 환경 제공

4. 거절
   - status = TERMINATED
   - 거절 사유 안내
```

### 정지 사유

1. **결제 이상**
   - 분쟁율 1% 초과
   - 환불율 10% 초과
   - 이상 거래 탐지

2. **계약 위반**
   - 허위 정보 등록
   - 금지 상품 판매
   - 약관 위반

3. **정산 문제**
   - 정산 계좌 오류
   - 세금 체납

### 수수료율 차등 기준

| 조건 | 수수료율 |
|------|----------|
| 월 거래액 1억 이상 | 2.5% ~ 3.0% |
| 월 거래액 5천만원 이상 | 3.0% ~ 3.3% |
| 월 거래액 5천만원 미만 | 3.3% ~ 3.5% |
| 고위험 업종 | 4.0% ~ 5.0% |

### API 키 관리

```
api_key_test: 테스트 환경용 (결제 실제 안됨)
api_key_live: 운영 환경용 (실결제)

키 발급 조건:
- test: 가입 즉시
- live: 심사 통과 후
```

### 한도 관리

가맹점별로 metadata에 한도 설정 가능:

```json
{
  "limits": {
    "daily_amount": 100000000,    // 일 최대 1억
    "monthly_amount": 3000000000, // 월 최대 30억
    "per_transaction": 50000000   // 건당 최대 5천만
  }
}
```""",
        "status": "active",
        "submitted_by": "system"
    }
]

# ============================================================
# 3. ERROR_CODE 문서
# ============================================================

ERROR_CODE_DOCS = [
    {
        "doc_type": "error_code",
        "title": "결제 실패 에러 코드",
        "content": """## 결제 실패 에러 코드

결제 실패 시 payments.failure_code와 failure_message에 기록됩니다.

### 카드 관련 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| INVALID_CARD_NUMBER | 유효하지 않은 카드번호 | 카드번호 오입력 | 카드번호 재확인 |
| EXPIRED_CARD | 유효기간 만료 카드 | 카드 만료 | 다른 카드 사용 |
| INVALID_EXPIRY_DATE | 유효기간 오류 | 유효기간 오입력 | 유효기간 재확인 |
| INVALID_CVV | CVV 오류 | CVV 오입력 | CVV 재확인 |
| CARD_LIMIT_EXCEEDED | 카드 한도 초과 | 결제/일/월 한도 초과 | 한도 상향 또는 분할 결제 |
| CARD_RESTRICTED | 사용 제한 카드 | 분실/도난/정지 카드 | 카드사 문의 |
| CARD_COMPANY_ERROR | 카드사 오류 | 카드사 시스템 오류 | 재시도 |
| AUTHENTICATION_FAILED | 본인인증 실패 | 3DS 인증 실패 | 재시도 |

### 은행/계좌 관련 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| INVALID_ACCOUNT | 유효하지 않은 계좌 | 계좌번호 오류 | 계좌 재확인 |
| ACCOUNT_SUSPENDED | 정지된 계좌 | 계좌 사용 정지 | 은행 문의 |
| INSUFFICIENT_BALANCE | 잔액 부족 | 출금 가능액 부족 | 잔액 충전 |
| TRANSFER_LIMIT_EXCEEDED | 이체한도 초과 | 일/1회 한도 초과 | 한도 상향 |
| BANK_SYSTEM_ERROR | 은행 시스템 오류 | 은행 점검/장애 | 재시도 |

### 간편결제 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| EASY_PAY_NOT_REGISTERED | 미등록 간편결제 | 간편결제 미가입 | 가입 후 재시도 |
| EASY_PAY_PASSWORD_ERROR | 비밀번호 오류 | 결제 비밀번호 틀림 | 비밀번호 재확인 |
| EASY_PAY_LIMIT_EXCEEDED | 간편결제 한도 초과 | 결제 한도 초과 | 다른 수단 사용 |

### 시스템 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| PG_SYSTEM_ERROR | PG 시스템 오류 | 내부 시스템 오류 | 재시도 |
| TIMEOUT | 요청 시간 초과 | 처리 시간 초과 | 재시도 |
| DUPLICATE_ORDER_ID | 주문번호 중복 | 동일 주문번호 존재 | 새 주문번호 사용 |
| INVALID_AMOUNT | 금액 오류 | 결제 금액 범위 초과 | 금액 확인 |
| MERCHANT_NOT_FOUND | 가맹점 없음 | 잘못된 가맹점 ID | API 키 확인 |
| MERCHANT_SUSPENDED | 가맹점 정지 | 가맹점 이용 정지 | PG사 문의 |""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "error_code",
        "title": "환불 실패 에러 코드",
        "content": """## 환불 실패 에러 코드

환불 실패 시 refunds.failure_code와 failure_message에 기록됩니다.

### 일반 환불 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| ALREADY_CANCELED | 이미 취소된 결제 | 전액 취소 상태 | 취소 불가 |
| EXCEED_CANCEL_AMOUNT | 취소 금액 초과 | balance_amount 초과 | 금액 조정 |
| CANCEL_PERIOD_EXPIRED | 취소 가능 기간 초과 | 180일 경과 | 취소 불가, 별도 환불 처리 |
| PAYMENT_NOT_FOUND | 결제 내역 없음 | 잘못된 payment_key | payment_key 확인 |
| INVALID_CANCEL_STATUS | 취소 불가 상태 | DONE 외 상태 | 상태 확인 |

### 계좌 환불 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| INVALID_REFUND_ACCOUNT | 환불 계좌 오류 | 계좌정보 불일치 | 계좌 재확인 |
| REFUND_ACCOUNT_REQUIRED | 환불 계좌 필요 | 가상계좌 환불 시 계좌 미입력 | 계좌 입력 |
| REFUND_TRANSFER_FAILED | 환불 이체 실패 | 은행 이체 오류 | 재시도 |

### 카드 환불 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| CARD_COMPANY_CANCEL_ERROR | 카드사 취소 오류 | 카드사 시스템 오류 | 재시도 |
| ORIGINAL_TRANSACTION_NOT_FOUND | 원거래 없음 | 카드사에 승인 내역 없음 | PG사 문의 |

### 시스템 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| REFUND_IN_PROGRESS | 환불 처리 중 | 동일 건 중복 요청 | 처리 완료 대기 |
| REFUND_SYSTEM_ERROR | 환불 시스템 오류 | 내부 오류 | 재시도 |""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "error_code",
        "title": "정산 에러 코드",
        "content": """## 정산 에러 코드

정산 실패 시 settlements.failure_code와 failure_message에 기록됩니다.

### 계좌 관련 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| INVALID_SETTLEMENT_ACCOUNT | 정산 계좌 오류 | 계좌번호/예금주 불일치 | 계좌 정보 수정 |
| SETTLEMENT_ACCOUNT_CLOSED | 정산 계좌 해지 | 계좌 해지됨 | 새 계좌 등록 |
| SETTLEMENT_TRANSFER_FAILED | 정산 이체 실패 | 은행 이체 오류 | 재시도 |
| BANK_MAINTENANCE | 은행 점검 중 | 은행 시스템 점검 | 점검 후 재시도 |

### 정산 조건 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| MERCHANT_SUSPENDED | 가맹점 정지 상태 | 정산 보류 중 | PG사 문의 |
| NEGATIVE_SETTLEMENT | 정산 금액 음수 | 환불이 결제보다 많음 | 다음 정산에서 차감 |
| MIN_AMOUNT_NOT_MET | 최소 정산금액 미달 | 1,000원 미만 | 다음 정산으로 이월 |
| DISPUTE_IN_PROGRESS | 분쟁 건 포함 | 차지백 처리 중 | 분쟁 해결 후 정산 |

### 시스템 에러

| 코드 | 메시지 | 원인 | 조치 |
|------|--------|------|------|
| SETTLEMENT_SYSTEM_ERROR | 정산 시스템 오류 | 내부 오류 | 재시도 |
| SETTLEMENT_ALREADY_PROCESSED | 이미 처리된 정산 | 중복 처리 시도 | 무시 |""",
        "status": "active",
        "submitted_by": "system"
    }
]

# ============================================================
# 4. FAQ 문서
# ============================================================

FAQ_DOCS = [
    {
        "doc_type": "faq",
        "title": "결제 상태 확인 방법",
        "content": """## Q: 결제 상태는 어떻게 확인하나요?

### A: 결제 상태 확인 방법

#### 1. 결제 상태 종류

| 상태 | 의미 | 다음 상태 |
|------|------|----------|
| READY | 결제 대기 | IN_PROGRESS, ABORTED |
| IN_PROGRESS | 결제 진행중 | DONE, ABORTED |
| WAITING_FOR_DEPOSIT | 입금 대기 (가상계좌) | DONE, EXPIRED |
| DONE | 결제 완료 | CANCELED, PARTIAL_CANCELED |
| CANCELED | 전액 취소 | - (최종) |
| PARTIAL_CANCELED | 부분 취소 | CANCELED |
| ABORTED | 결제 중단 | - (최종) |
| EXPIRED | 만료 | - (최종) |

#### 2. 조회 질문 예시

- "결제 상태가 DONE인 건 조회해줘"
- "오늘 완료된 결제 보여줘"
- "취소된 결제 내역 확인"
- "입금 대기 중인 가상계좌 건수"

#### 3. 상태별 필터링

- 정상 결제: status = 'DONE'
- 취소 결제: status IN ('CANCELED', 'PARTIAL_CANCELED')
- 진행중: status IN ('READY', 'IN_PROGRESS', 'WAITING_FOR_DEPOSIT')
- 실패/만료: status IN ('ABORTED', 'EXPIRED')""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "faq",
        "title": "환불 가능 여부 확인",
        "content": """## Q: 환불이 가능한지 어떻게 확인하나요?

### A: 환불 가능 조건 확인

#### 1. 기본 조건

환불이 가능하려면 다음 조건을 모두 만족해야 합니다:

1. **결제 상태**: DONE 또는 PARTIAL_CANCELED
2. **잔액**: balance_amount > 0
3. **기간**: 결제일로부터 180일 이내

#### 2. 환불 가능 금액 확인

- 전액 환불: balance_amount 전체
- 부분 환불: 1원 ~ balance_amount 범위

#### 3. 조회 질문 예시

- "환불 가능한 결제 건 조회"
- "취소 가능 잔액이 있는 결제"
- "이번 달 환불 가능 금액 합계"
- "payment_key가 pay_xxx인 결제의 환불 가능 금액"

#### 4. SQL 조건

```
WHERE status IN ('DONE', 'PARTIAL_CANCELED')
  AND balance_amount > 0
  AND approved_at >= NOW() - INTERVAL '180 days'
```""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "faq",
        "title": "정산 금액 계산 방법",
        "content": """## Q: 정산 금액은 어떻게 계산되나요?

### A: 정산 금액 계산 공식

#### 1. 기본 공식

```
정산금액 = 결제금액 - 환불금액 - 수수료

수수료 = (결제금액 - 환불금액) × 수수료율
```

#### 2. 예시

```
결제금액: 10,000,000원 (100건)
환불금액: 500,000원 (5건)
수수료율: 3.5%

순매출: 10,000,000 - 500,000 = 9,500,000원
수수료: 9,500,000 × 0.035 = 332,500원
정산금액: 9,500,000 - 332,500 = 9,167,500원
```

#### 3. 조회 질문 예시

- "이번 달 정산 예정 금액"
- "가맹점 mer_xxx의 정산 내역"
- "오늘 정산 완료된 금액"
- "정산 대기 중인 건 조회"

#### 4. 정산 상태

- PENDING: 정산 대기 (집계 완료)
- PROCESSING: 이체 처리 중
- COMPLETED: 지급 완료
- FAILED: 이체 실패""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "faq",
        "title": "결제 수단별 조회 방법",
        "content": """## Q: 특정 결제 수단으로 조회하려면?

### A: 결제 수단별 조회

#### 1. 결제 수단 종류 (method 필드)

| 코드 | 설명 | 예시 |
|------|------|------|
| CARD | 신용/체크카드 | 삼성카드, 신한카드 |
| VIRTUAL_ACCOUNT | 가상계좌 | KB국민, 신한은행 |
| BANK_TRANSFER | 계좌이체 | 실시간 이체 |
| MOBILE | 휴대폰 결제 | SKT, KT, LGU+ |
| EASY_PAY | 간편결제 | 카카오페이, 네이버페이 |

#### 2. 조회 질문 예시

- "카드 결제 내역 보여줘"
- "가상계좌로 결제된 건"
- "간편결제 사용 현황"
- "이번 달 결제 수단별 금액"

#### 3. 간편결제 세부 조회

간편결제는 method_detail.provider로 세분화:
- KAKAOPAY: 카카오페이
- NAVERPAY: 네이버페이
- TOSSPAY: 토스페이
- PAYCO: 페이코

"카카오페이 결제 건만 조회해줘"
"네이버페이 이번 달 매출"

#### 4. 카드사별 조회

카드 결제는 method_detail로 세분화 가능:
- method_detail.card_company: 카드사명
- method_detail.card_type: CREDIT, DEBIT

"삼성카드 결제 건 조회"
"체크카드 결제 비율"
"할부 결제 현황"
""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "faq",
        "title": "기간별 매출 조회",
        "content": """## Q: 특정 기간 매출을 조회하려면?

### A: 기간별 매출 조회 방법

#### 1. 기간 지정 방식

| 표현 | 의미 | 필드 |
|------|------|------|
| 오늘 | 당일 00:00~23:59 | created_at 또는 approved_at |
| 이번 주 | 이번 주 월~일 | |
| 이번 달 | 이번 달 1일~말일 | |
| 최근 7일 | 오늘 기준 7일 전부터 | |
| 최근 30일 | 오늘 기준 30일 전부터 | |
| 특정 날짜 | 2024-01-15 | |
| 기간 범위 | 1월 1일 ~ 1월 31일 | |

#### 2. 조회 질문 예시

- "오늘 매출 얼마야?"
- "이번 달 총 결제 금액"
- "지난 주 결제 건수"
- "1월 1일부터 15일까지 매출"
- "작년 12월 정산 내역"

#### 3. 매출 조회 시 주의사항

**승인일 기준 (approved_at)**
- 실제 결제 완료 시점
- 매출 집계에 권장
- 가상계좌: 입금 완료 시점

**요청일 기준 (created_at)**
- 결제 요청 시점
- 결제 시도 현황 파악용

#### 4. 집계 조회

- 일별 매출: GROUP BY DATE(approved_at)
- 월별 매출: GROUP BY DATE_TRUNC('month', approved_at)
- 결제 수단별: GROUP BY method
- 가맹점별: GROUP BY merchant_id""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "faq",
        "title": "가맹점별 조회 방법",
        "content": """## Q: 특정 가맹점 데이터만 조회하려면?

### A: 가맹점별 조회 방법

#### 1. 가맹점 식별

- merchant_id: 가맹점 고유 ID (예: mer_abc123)
- business_name: 상호명 (예: "(주)테스트몰")
- business_number: 사업자번호 (예: 123-45-67890)

#### 2. 조회 질문 예시

**가맹점 ID로 조회**
- "mer_abc123 가맹점의 오늘 매출"
- "가맹점 mer_xyz의 결제 현황"

**상호명으로 조회**
- "테스트몰 결제 내역"
- "OOO쇼핑몰 이번 달 정산"

**사업자번호로 조회**
- "사업자번호 123-45-67890 조회"

#### 3. 가맹점 현황 조회

- "활성 가맹점 수"
- "이번 달 신규 가맹점"
- "정지된 가맹점 목록"
- "수수료율 3% 이하 가맹점"

#### 4. 가맹점별 집계

- "가맹점별 매출 순위"
- "가맹점별 환불율"
- "가맹점별 결제 건수 TOP 10"
- "가맹점별 평균 결제 금액"

#### 5. 복합 조회

- "mer_abc123의 이번 달 카드 결제"
- "테스트몰의 환불 내역"
- "가맹점별 정산 예정 금액"
""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "faq",
        "title": "할부 결제 조회",
        "content": """## Q: 할부 결제 현황을 조회하려면?

### A: 할부 결제 조회 방법

#### 1. 할부 관련 필드

- card_installment_months: 할부 개월 수
  - 0: 일시불
  - 2~12: 할부 개월
- card_is_interest_free: 무이자 할부 여부
  - true: 무이자
  - false: 일반 할부

#### 2. 조회 질문 예시

**할부 현황**
- "할부 결제 건 조회"
- "3개월 할부 결제 내역"
- "무이자 할부 현황"

**일시불 vs 할부**
- "일시불 결제 금액"
- "할부 결제 비율"

**할부 개월별**
- "할부 개월별 결제 금액"
- "6개월 이상 할부 건"
- "12개월 할부 총 금액"

#### 3. 할부 조건

- 최소 금액: 50,000원 이상
- 할부 개월: 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12개월
- 무이자 할부: 가맹점/카드사 프로모션에 따름

#### 4. SQL 조건 예시

```
-- 할부 결제만
WHERE card_installment_months > 0

-- 무이자 할부만
WHERE card_is_interest_free = true

-- 6개월 이상 할부
WHERE card_installment_months >= 6
```""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "faq",
        "title": "금액 집계 및 통계",
        "content": """## Q: 금액 합계나 통계를 보려면?

### A: 금액 집계 조회 방법

#### 1. 기본 집계

| 집계 | 질문 예시 |
|------|----------|
| 합계 | "이번 달 총 결제금액" |
| 건수 | "오늘 결제 건수" |
| 평균 | "평균 결제 금액" |
| 최대/최소 | "최대 결제 금액" |

#### 2. 조회 질문 예시

**기간별 합계**
- "오늘 매출 합계"
- "이번 달 총 결제 금액"
- "지난 주 환불 금액"

**상태별 집계**
- "완료된 결제 총액"
- "취소된 결제 합계"

**그룹별 집계**
- "결제 수단별 금액"
- "가맹점별 매출"
- "일별 결제 추이"

#### 3. 비율/비교

- "카드 vs 간편결제 비율"
- "전월 대비 매출 증감"
- "환불율 (환불금액/결제금액)"

#### 4. 순위/TOP N

- "매출 TOP 10 가맹점"
- "결제 금액 상위 100건"
- "환불 많은 가맹점 순위"

#### 5. 주의사항

- 금액 집계 시 status = 'DONE' 필터 권장
- 취소 금액은 별도 집계 (canceled_amount)
- 정산금액 계산 시 수수료 차감 필요

#### 6. 건수 집계 시 테이블 선택 (중요!)

| 원하는 정보 | 사용할 테이블 | SQL 패턴 |
|------------|-------------|---------|
| 가맹점별 총 거래 건수 | payments | COUNT(*) GROUP BY merchant_id |
| 월별 평균 거래 건수 | payments | CTE: 월별 COUNT(*), 외부: AVG() |
| 일별 거래 건수 추이 | payments | COUNT(*) GROUP BY DATE(created_at) |
| 정산 레코드당 건수 | settlements | payment_count 컬럼 직접 사용 |
| 가맹점별 환불율 | payments LEFT JOIN refunds | COUNT(*) FILTER (WHERE r.refund_key IS NOT NULL) / COUNT(*) |

**주의**: settlements.payment_count는 "정산 레코드당 건수"이므로 AVG(payment_count)는 "정산당 평균 건수"입니다.
"월 평균 거래 건수"를 구하려면 payments에서 월별 COUNT 후 AVG를 사용하세요.""",
        "status": "active",
        "submitted_by": "system"
    },
    {
        "doc_type": "faq",
        "title": "환불율 계산 방법",
        "content": """## Q: 환불율은 어떻게 조회하나요?

### A: 환불율 계산 방법

#### 1. 환불율 정의

환불율 = (환불 건수 / 총 결제 건수) × 100

#### 2. 올바른 계산 방법

**반드시 payments 테이블 기준으로 refunds를 LEFT JOIN하여 계산합니다.**

```sql
SELECT p.merchant_id,
       COUNT(*) AS total_payments,
       COUNT(*) FILTER (WHERE r.refund_key IS NOT NULL) AS refund_count,
       ROUND(100.0 * COUNT(*) FILTER (WHERE r.refund_key IS NOT NULL) /
             NULLIF(COUNT(*), 0), 2) AS refund_rate
FROM payments p
LEFT JOIN refunds r ON p.payment_key = r.payment_key
WHERE p.created_at >= NOW() - INTERVAL '1 month'
  AND p.status = 'DONE'
GROUP BY p.merchant_id
```

#### 3. 주의사항

- **settlements.payment_count 사용 금지**: 정산 레코드 단위 건수이므로 환불율 계산에 부적합
- **LEFT JOIN 필수**: 환불이 없는 결제도 포함해야 정확한 비율 계산 가능
- **NULLIF(COUNT(*), 0)**: 0으로 나누기 방지

#### 4. 조회 질문 예시

- "이 가맹점의 환불율"
- "최근 1개월 환불 비율"
- "가맹점별 환불율 순위"
- "환불율이 5% 이상인 가맹점"

#### 5. 금액 기준 환불율

건수 대신 금액 기준으로 계산할 수도 있습니다:
- 금액 환불율 = (총 환불 금액 / 총 결제 금액) × 100
- 금액 기준 시 status IN ('DONE', 'CANCELED', 'PARTIAL_CANCELED') 사용""",
        "status": "active",
        "submitted_by": "system"
    }
]

def add_document(doc):
    """단일 문서 추가"""
    try:
        response = requests.post(API_BASE, json=doc, timeout=30)
        if response.status_code == 201:
            result = response.json()
            print(f"  ✓ [{doc['doc_type']}] {doc['title'][:40]}... (ID: {result.get('id', 'N/A')})")
            return True
        else:
            print(f"  ✗ [{doc['doc_type']}] {doc['title'][:40]}... - {response.status_code}: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"  ✗ [{doc['doc_type']}] {doc['title'][:40]}... - Error: {str(e)[:50]}")
        return False

def main():
    print("=" * 60)
    print("PG 서비스 RAG 문서 시드 데이터 생성")
    print("=" * 60)

    all_docs = []
    all_docs.extend(ENTITY_DOCS)
    all_docs.extend(BUSINESS_LOGIC_DOCS)
    all_docs.extend(ERROR_CODE_DOCS)
    all_docs.extend(FAQ_DOCS)

    print(f"\n총 {len(all_docs)}개 문서 추가 예정")
    print(f"  - Entity: {len(ENTITY_DOCS)}개")
    print(f"  - Business Logic: {len(BUSINESS_LOGIC_DOCS)}개")
    print(f"  - Error Code: {len(ERROR_CODE_DOCS)}개")
    print(f"  - FAQ: {len(FAQ_DOCS)}개")
    print()

    success = 0
    failed = 0

    for i, doc in enumerate(all_docs, 1):
        print(f"[{i}/{len(all_docs)}] 추가 중...")
        if add_document(doc):
            success += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(f"완료: 성공 {success}개, 실패 {failed}개")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
