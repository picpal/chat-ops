# ChatOps API 테스트 결과 요약

**테스트 일시:** 2026-01-17
**테스트 방법:** curl + jq (API 직접 호출)
**AI Orchestrator:** http://localhost:8000
**Core API:** http://localhost:8080

---

## TC-001: preferredRenderType 기능 테스트

| 테스트 케이스 | 입력 | renderType | totalRows | 결과 |
|--------------|------|------------|-----------|------|
| TC-001-1 | "표로 보여줘" | table | 8 | ✅ PASS |
| TC-001-2 | "그래프로 보여줘" | chart | 686 | ✅ PASS |
| TC-001-3 | 명시 없음 (list) | table | 30 | ✅ PASS |

**검증 포인트:**
- ✅ "표로" 키워드 감지 → renderType: table
- ✅ "그래프로" 키워드 감지 → renderType: chart
- ✅ 키워드 없을 시 operation 기반 자동 결정

---

## TC-002: 집계 쿼리 테이블 렌더링

| 테스트 케이스 | 입력 | renderType | totalRows | columns | 데이터 구조 | 결과 |
|--------------|------|------------|-----------|---------|------------|------|
| TC-002-1 | 가맹점별 집계 (표로) | table | 8 | merchant_id, payment_count, total_amount | ✅ 정상 | ✅ PASS |
| TC-002-2 | 상태별 현황 (표로) | table | 5 | status, payment_count, total_amount | ✅ 정상 | ✅ PASS |

**검증 포인트:**
- ✅ 집계 쿼리 동적 컬럼 생성 (renderSpec.table.columns)
- ✅ snake_case 필드명으로 데이터 접근 가능
- ✅ currency 타입 지정 (total_amount)
- ✅ 모든 셀 값 정상 표시 (이전 "-" 버그 해결 확인)

**샘플 데이터:**
```json
{
  "merchant_id": "mer_005",
  "payment_count": 125,
  "total_amount": "64936000"
}
```

---

## TC-003: WHERE 조건 체이닝 (연속 대화)

| 단계 | 입력 | SQL WHERE 절 | totalRows | 결과 |
|------|------|-------------|-----------|------|
| Step 1 | "최근 3개월 결제건" | `created_at >= NOW() - INTERVAL '3 months'` | 1000 | ✅ |
| Step 2 | "이중 mer_001 가맹점만" (with history) | `created_at >= ... AND merchant_id = 'mer_001'` | 125 | ✅ |

**검증 포인트:**
- ✅ 참조 표현 ("이중") 감지
- ✅ 이전 시간 조건 유지
- ✅ 새 merchant_id 조건 추가
- ✅ WHERE 절에 두 조건 모두 포함

**실제 SQL (Step 2):**
```sql
SELECT * FROM payments 
WHERE created_at >= NOW() - INTERVAL '3 months' 
  AND merchant_id = 'mer_001' 
LIMIT 1000
```

---

## TC-004: Server-Side Pagination

| 항목 | 기대값 | 실제값 | 결과 |
|------|--------|--------|------|
| renderType | table | table | ✅ |
| totalRows | 686 | 686 | ✅ |
| pageSize | 10 | 10 | ✅ |
| hasMore | true | true | ✅ |
| dataCount | 10 | 10 | ✅ |
| queryToken | 존재 | **null** | ⚠️ |

**검증 포인트:**
- ✅ pagination 메타데이터 전달
- ✅ totalRows 정확히 표시 (686건)
- ⚠️ **queryToken 미구현** (text_to_sql 모드에서는 pagination token 미지원)

**참고:**
- text_to_sql 모드는 전체 데이터를 한 번에 반환
- QueryPlan 모드에서만 queryToken 기반 pagination 지원
- 현재는 클라이언트 사이드 pagination으로 동작

---

## TC-005: 컨텍스트 초기화 후 꼬리 질문 ⭐ NEW

### TC-005-1: 새 쿼리 후 꼬리 질문 (정상 케이스)

| 단계 | 입력 | SQL | totalRows | Table | 결과 |
|------|------|-----|-----------|-------|------|
| Step 1 | "최근 1개월 거래건 조회해줘" | `... WHERE created_at >= NOW() - INTERVAL '1 months'` | 686 | payments | ✅ |
| Step 2 | "mer_008 가맹점만 조회해줘" (with history) | `... WHERE created_at >= ... AND merchant_id = 'mer_008'` | 89 | payments | ✅ |

**검증 포인트:**
- ✅ Step 2에서 payments 테이블 조회 (컨텍스트 유지)
- ✅ 이전 시간 조건(1개월) 유지
- ✅ merchant_id 조건 추가
- ✅ 건수 감소 (686 → 89)

### TC-005-2: 컨텍스트 없이 가맹점 조회 (주의 케이스)

| 항목 | 값 | 결과 |
|------|-----|------|
| 입력 | "mer_008 가맹점만 조회해줘" (history 없음) | |
| SQL | `SELECT * FROM merchants WHERE merchant_id = 'mer_008'` | ✅ |
| totalRows | 1 | ✅ |
| Table | **merchants** (payments 아님!) | ✅ |

**검증 포인트:**
- ✅ conversationHistory 없을 시 가맹점 마스터 정보 조회
- ✅ merchants 테이블 조회 (의도한 동작)
- ⚠️ **주의:** 컨텍스트 없이 "가맹점만"은 결제 내역이 아닌 가맹점 정보 조회

---

## 전체 요약

| 시나리오 | 총 테스트 | 통과 | 실패 | 주의 |
|---------|----------|------|------|------|
| TC-001: preferredRenderType | 3 | 3 | 0 | - |
| TC-002: 집계 쿼리 렌더링 | 2 | 2 | 0 | - |
| TC-003: WHERE 조건 체이닝 | 2 | 2 | 0 | - |
| TC-004: Server-Side Pagination | 1 | 0 | 0 | 1 (queryToken 미구현) |
| TC-005: 컨텍스트 초기화 | 2 | 2 | 0 | - |
| **합계** | **10** | **9** | **0** | **1** |

---

## 주요 발견사항

### ✅ 정상 동작 확인
1. **preferredRenderType**: "표로", "그래프로" 키워드 감지 정상
2. **집계 쿼리 렌더링**: 동적 컬럼 생성 및 데이터 매칭 정상
3. **WHERE 조건 체이닝**: 참조 표현 감지 및 조건 누적 정상
4. **컨텍스트 기반 테이블 선택**: conversationHistory 유무에 따른 테이블 선택 정상

### ⚠️ 제한사항
1. **queryToken (TC-004)**
   - text_to_sql 모드에서는 queryToken 생성 안 됨
   - 전체 데이터 반환 후 클라이언트 사이드 pagination 사용
   - QueryPlan 모드에서만 서버 사이드 pagination 지원

### 💡 개선 제안
1. text_to_sql 모드에서도 대용량 데이터 시 서버 사이드 pagination 지원
2. TC-005-2 같은 컨텍스트 누락 케이스에 대한 사용자 안내 메시지 추가

---

## 테스트 명령어 예시

```bash
# TC-001
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "최근 3개월간 거래를 가맹점 별로 그룹화해서 표로 보여줘"}' | \
  jq '{renderType: .renderSpec.type, totalRows: .renderSpec.pagination.totalRows}'

# TC-003 (WHERE 조건 체이닝)
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "이중 mer_001 가맹점만",
    "conversationHistory": [...]
  }' | jq '{sql: .queryPlan.sql, rows: .renderSpec.pagination.totalRows}'

# TC-005-2 (컨텍스트 없음)
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "mer_008 가맹점만 조회해줘"}' | \
  jq '{sql: .queryPlan.sql, table: (.queryPlan.sql | match("FROM ([a-z_]+)").captures[0].string)}'
```

---

**테스트 완료**
