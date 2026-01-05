#!/usr/bin/env python3
"""
RAG 문서 시딩 스크립트
초기 문서를 PostgreSQL에 삽입합니다.
"""

import os
import sys
import json
import psycopg

# 데이터베이스 연결 정보
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://chatops_user:chatops_pass@localhost:5432/chatops"
)


# 시딩할 문서 데이터
SEED_DOCUMENTS = [
    # === 엔티티 설명 ===
    {
        "doc_type": "entity",
        "title": "Order (주문) 엔티티",
        "content": """
Order 엔티티는 고객의 주문 정보를 나타냅니다.

## 주요 필드
- orderId: 주문 고유 ID (자동 생성)
- customerId: 주문한 고객 ID (Customer 엔티티 참조)
- orderDate: 주문 일시
- totalAmount: 주문 총 금액 (KRW)
- status: 주문 상태 (PENDING, PAID, SHIPPED, DELIVERED, CANCELLED, REFUNDED)
- paymentGateway: 결제 수단 (KAKAO_PAY, NAVER_PAY, TOSS, CARD)

## 자주 사용되는 쿼리 예시
- "최근 주문 보여줘" → operation: list, orderBy: [{"field": "orderDate", "direction": "DESC"}]
- "결제 완료된 주문" → operation: list, filters: [{"field": "status", "operator": "eq", "value": "PAID"}]
- "오늘 주문 건수" → operation: aggregate, filters: [{"field": "orderDate", "operator": "gte", "value": "TODAY"}]
""",
        "metadata": {"entity_name": "Order", "table_name": "orders"}
    },
    {
        "doc_type": "entity",
        "title": "Customer (고객) 엔티티",
        "content": """
Customer 엔티티는 서비스 이용 고객 정보를 나타냅니다.

## 주요 필드
- customerId: 고객 고유 ID
- name: 고객 이름
- email: 이메일 주소
- phone: 연락처
- createdAt: 가입일

## 자주 사용되는 쿼리 예시
- "고객 목록 보여줘" → operation: list, entity: Customer
- "특정 고객 조회" → operation: list, filters: [{"field": "customerId", "operator": "eq", "value": 123}]
""",
        "metadata": {"entity_name": "Customer", "table_name": "customers"}
    },
    {
        "doc_type": "entity",
        "title": "Product (상품) 엔티티",
        "content": """
Product 엔티티는 판매 상품 정보를 나타냅니다.

## 주요 필드
- productId: 상품 고유 ID
- name: 상품명
- price: 상품 가격 (KRW)
- category: 상품 카테고리

## 자주 사용되는 쿼리 예시
- "상품 목록 보여줘" → operation: list, entity: Product
- "가격순으로 정렬" → operation: list, orderBy: [{"field": "price", "direction": "DESC"}]
""",
        "metadata": {"entity_name": "Product", "table_name": "products"}
    },
    {
        "doc_type": "entity",
        "title": "Inventory (재고) 엔티티",
        "content": """
Inventory 엔티티는 상품 재고 정보를 나타냅니다.

## 주요 필드
- inventoryId: 재고 레코드 ID
- productId: 상품 ID (Product 엔티티 참조)
- quantity: 재고 수량
- warehouse: 창고 위치

## 자주 사용되는 쿼리 예시
- "재고 현황 보여줘" → operation: list, entity: Inventory
- "재고 부족 상품" → operation: list, filters: [{"field": "quantity", "operator": "lt", "value": 10}]
""",
        "metadata": {"entity_name": "Inventory", "table_name": "inventory"}
    },
    {
        "doc_type": "entity",
        "title": "PaymentLog (결제 로그) 엔티티",
        "content": """
PaymentLog 엔티티는 결제 서버 로그를 나타냅니다.

## 주요 필드
- timestamp: 로그 발생 시간
- level: 로그 레벨 (DEBUG, INFO, WARN, ERROR, FATAL)
- orderId: 관련 주문 ID
- message: 로그 메시지
- errorCode: 에러 코드 (에러 발생 시)

## 자주 사용되는 쿼리 예시
- "결제 에러 로그 보여줘" → operation: list, entity: PaymentLog, filters: [{"field": "level", "operator": "eq", "value": "ERROR"}]
- "특정 주문 로그" → operation: list, filters: [{"field": "orderId", "operator": "eq", "value": 123}]
""",
        "metadata": {"entity_name": "PaymentLog", "table_name": "payment_logs"}
    },

    # === 비즈니스 로직 ===
    {
        "doc_type": "business_logic",
        "title": "주문 상태 변경 흐름",
        "content": """
## 주문 상태 변경 흐름

주문은 다음과 같은 상태 변경 흐름을 따릅니다:

1. PENDING (대기중): 주문 생성 직후 상태
2. PAID (결제완료): 결제가 성공적으로 완료됨
3. SHIPPED (배송중): 상품이 발송됨
4. DELIVERED (배송완료): 고객이 상품을 수령함
5. CANCELLED (취소됨): 주문이 취소됨
6. REFUNDED (환불됨): 환불이 완료됨

## 상태 전이 규칙
- PENDING → PAID, CANCELLED
- PAID → SHIPPED, REFUNDED
- SHIPPED → DELIVERED
- 한 번 CANCELLED나 REFUNDED가 되면 다른 상태로 변경 불가

## 관련 쿼리
- "미결제 주문" → status = PENDING
- "배송 중인 주문" → status = SHIPPED
- "환불 처리된 주문" → status = REFUNDED
""",
        "metadata": {"category": "order_flow"}
    },
    {
        "doc_type": "business_logic",
        "title": "결제 수단별 특징",
        "content": """
## 결제 수단 (paymentGateway)

시스템에서 지원하는 결제 수단과 특징:

### KAKAO_PAY (카카오페이)
- 모바일 간편결제
- 평균 결제 시간: 5초
- 수수료율: 1.5%

### NAVER_PAY (네이버페이)
- 포인트 적립 가능
- 평균 결제 시간: 7초
- 수수료율: 1.8%

### TOSS (토스)
- 빠른 송금 가능
- 평균 결제 시간: 3초
- 수수료율: 1.2%

### CARD (신용카드)
- 일반 카드 결제
- 평균 결제 시간: 10초
- 수수료율: 2.0%

## 관련 쿼리
- "카카오페이 결제 주문" → filters: [{"field": "paymentGateway", "operator": "eq", "value": "KAKAO_PAY"}]
- "결제 수단별 통계" → operation: aggregate, groupBy: ["paymentGateway"]
""",
        "metadata": {"category": "payment"}
    },

    # === 에러 코드 ===
    {
        "doc_type": "error_code",
        "title": "결제 에러 코드",
        "content": """
## 결제 에러 코드 목록

### PAY_001: 결제 금액 초과
- 원인: 1회 결제 한도 초과
- 해결: 결제 금액 분할 또는 한도 증액

### PAY_002: 카드 잔액 부족
- 원인: 연결된 카드/계좌 잔액 부족
- 해결: 다른 결제 수단 사용 권유

### PAY_003: 결제 시간 초과
- 원인: 결제 응답 대기 시간 초과 (30초)
- 해결: 재시도 또는 다른 결제 수단 사용

### PAY_004: 중복 결제 요청
- 원인: 동일 주문에 대한 중복 결제 시도
- 해결: 기존 결제 상태 확인 후 처리

### PAY_005: PG사 연결 실패
- 원인: 결제 대행사 서버 연결 불가
- 해결: 잠시 후 재시도

### PAY_006: 인증 실패
- 원인: 결제 인증 정보 오류
- 해결: 결제 정보 재입력

## 에러 분석 쿼리
- "결제 에러 현황" → entity: PaymentLog, filters: [{"field": "level", "operator": "eq", "value": "ERROR"}]
- "특정 에러 코드 검색" → filters: [{"field": "errorCode", "operator": "eq", "value": "PAY_003"}]
""",
        "metadata": {"category": "payment_error"}
    },
    {
        "doc_type": "error_code",
        "title": "시스템 에러 코드",
        "content": """
## 시스템 에러 코드 목록

### SYS_001: 데이터베이스 연결 실패
- 원인: DB 서버 연결 불가
- 심각도: FATAL
- 해결: DBA 확인 필요

### SYS_002: 타임아웃
- 원인: 요청 처리 시간 초과
- 심각도: ERROR
- 해결: 쿼리 최적화 또는 리소스 증설

### SYS_003: 메모리 부족
- 원인: 서버 메모리 초과
- 심각도: FATAL
- 해결: 서버 리소스 증설

### SYS_004: 외부 API 실패
- 원인: 외부 서비스 연동 실패
- 심각도: WARN
- 해결: 재시도 후 담당자 확인
""",
        "metadata": {"category": "system_error"}
    },

    # === FAQ ===
    {
        "doc_type": "faq",
        "title": "자주 묻는 질문 - 주문 조회",
        "content": """
## Q: 최근 주문을 어떻게 조회하나요?
"최근 주문 보여줘" 또는 "오늘 주문 목록"이라고 질문하세요.

## Q: 특정 기간의 주문을 보고 싶어요
"어제 주문", "지난주 주문", "이번 달 주문"처럼 기간을 명시하세요.

## Q: 특정 상태의 주문만 보고 싶어요
"결제 완료된 주문", "배송 중인 주문", "취소된 주문"처럼 상태를 명시하세요.

## Q: 주문 건수를 알고 싶어요
"오늘 주문 몇 건이야?", "이번 달 총 주문 건수"처럼 질문하세요.

## Q: 매출 통계를 보고 싶어요
"오늘 매출", "이번 달 총 매출", "결제 수단별 매출"처럼 질문하세요.
""",
        "metadata": {"category": "order_faq"}
    },
    {
        "doc_type": "faq",
        "title": "자주 묻는 질문 - 결제 에러",
        "content": """
## Q: 결제 에러를 어떻게 분석하나요?
"결제 에러 로그 보여줘", "결제 실패 분석해줘"라고 질문하세요.

## Q: 특정 에러 코드의 의미가 뭔가요?
"PAY_003 에러가 뭐야?", "결제 시간 초과 에러 알려줘"처럼 질문하세요.

## Q: 에러 발생 추이를 보고 싶어요
"에러 코드별 분포", "시간대별 에러 현황"처럼 질문하세요.

## Q: 특정 주문의 결제 로그를 보고 싶어요
"주문번호 123의 결제 로그"처럼 주문 ID를 명시하세요.
""",
        "metadata": {"category": "payment_faq"}
    },
    {
        "doc_type": "faq",
        "title": "자주 묻는 질문 - 데이터 분석",
        "content": """
## Q: 차트로 데이터를 보고 싶어요
"결제 수단별 매출 차트", "시간대별 주문 그래프"처럼 '차트' 또는 '그래프'를 포함해서 질문하세요.

## Q: 데이터를 그룹별로 보고 싶어요
"상태별 주문 현황", "고객별 주문 통계"처럼 그룹 기준을 명시하세요.

## Q: 평균, 합계 등 집계를 보고 싶어요
"평균 주문 금액", "총 매출", "최대 주문 금액"처럼 집계 함수를 명시하세요.

## Q: 여러 조건으로 필터링하고 싶어요
"오늘 카카오페이로 결제된 주문"처럼 여러 조건을 조합하세요.
""",
        "metadata": {"category": "analysis_faq"}
    }
]


def seed_documents():
    """문서 시딩 실행"""
    print("=" * 50)
    print("RAG 문서 시딩 시작")
    print("=" * 50)
    print(f"Database URL: {DATABASE_URL}")
    print()

    try:
        conn = psycopg.connect(DATABASE_URL)
        print("✓ 데이터베이스 연결 성공")
    except Exception as e:
        print(f"✗ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    try:
        with conn.cursor() as cur:
            # 기존 문서 삭제 여부 확인
            cur.execute("SELECT COUNT(*) FROM documents")
            existing_count = cur.fetchone()[0]

            if existing_count > 0:
                print(f"\n기존 문서 {existing_count}개가 있습니다.")
                response = input("기존 문서를 삭제하고 새로 시딩할까요? (y/n): ")
                if response.lower() == 'y':
                    cur.execute("DELETE FROM documents")
                    conn.commit()
                    print("✓ 기존 문서 삭제 완료")
                else:
                    print("기존 문서 유지, 신규 문서만 추가합니다.")

            # 문서 삽입
            inserted_count = 0
            for doc in SEED_DOCUMENTS:
                cur.execute(
                    """
                    INSERT INTO documents (doc_type, title, content, metadata)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        doc["doc_type"],
                        doc["title"],
                        doc["content"].strip(),
                        json.dumps(doc["metadata"])
                    )
                )
                doc_id = cur.fetchone()[0]
                inserted_count += 1
                print(f"  [{doc['doc_type']:15}] {doc['title'][:40]} (ID: {doc_id})")

            conn.commit()

            # 결과 출력
            print()
            print("=" * 50)
            print(f"✓ 문서 시딩 완료: {inserted_count}개 추가")
            print("=" * 50)

            # 타입별 개수 출력
            cur.execute(
                """
                SELECT doc_type, COUNT(*) as count
                FROM documents
                GROUP BY doc_type
                ORDER BY doc_type
                """
            )
            rows = cur.fetchall()
            print("\n문서 타입별 현황:")
            for row in rows:
                print(f"  - {row[0]}: {row[1]}개")

    except Exception as e:
        print(f"✗ 문서 시딩 실패: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

    print()
    print("임베딩 생성은 별도로 실행해주세요:")
    print("  OPENAI_API_KEY=sk-... python3 scripts/update-embeddings.py")
    print()


if __name__ == "__main__":
    seed_documents()
