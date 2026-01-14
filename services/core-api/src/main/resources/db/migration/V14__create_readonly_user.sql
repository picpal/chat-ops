-- =============================================
-- Text-to-SQL용 읽기 전용 사용자 생성
-- AI Orchestrator가 직접 DB 조회 시 사용
-- =============================================

-- 읽기 전용 사용자 생성 (이미 존재하면 스킵)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'chatops_readonly') THEN
        CREATE USER chatops_readonly WITH PASSWORD 'readonly_pass';
    END IF;
END
$$;

-- 연결 수 제한 (동시 연결 10개)
ALTER USER chatops_readonly CONNECTION LIMIT 10;

-- 기본 스키마 접근 권한
GRANT USAGE ON SCHEMA public TO chatops_readonly;

-- 비즈니스 테이블 SELECT 권한 부여
-- (documents 테이블은 의도적으로 제외 - RAG 민감 데이터)
GRANT SELECT ON TABLE
    payments,
    merchants,
    pg_customers,
    payment_methods,
    payment_history,
    refunds,
    balance_transactions,
    settlements,
    settlement_details,
    orders
TO chatops_readonly;

-- 향후 생성되는 테이블에 대한 기본 권한 설정 (선택적)
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public
--     GRANT SELECT ON TABLES TO chatops_readonly;

-- 권한 확인용 코멘트
COMMENT ON ROLE chatops_readonly IS 'Read-only user for Text-to-SQL AI queries. No access to documents table.';
