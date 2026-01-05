-- Documents table for RAG (Retrieval-Augmented Generation)
-- Uses pgvector for vector similarity search

-- Enable pgvector extension (in case not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,

    -- Document metadata
    doc_type VARCHAR(50) NOT NULL,  -- entity, business_logic, error_code, faq
    title VARCHAR(255) NOT NULL,

    -- Document content
    content TEXT NOT NULL,

    -- Vector embedding (OpenAI text-embedding-ada-002 uses 1536 dimensions)
    embedding vector(1536),

    -- Additional metadata as JSON
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for vector similarity search (using IVFFlat for better performance)
-- Note: IVFFlat requires data to be present first, so we use HNSW which works with empty tables
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents
    USING hnsw (embedding vector_cosine_ops);

-- Index for filtering by doc_type
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents (doc_type);

-- Index for full-text search on content (using simple config for compatibility)
CREATE INDEX IF NOT EXISTS idx_documents_content_gin ON documents
    USING gin (to_tsvector('simple', content));

COMMENT ON TABLE documents IS 'RAG documents for AI context augmentation';
COMMENT ON COLUMN documents.doc_type IS 'Document category: entity, business_logic, error_code, faq';
COMMENT ON COLUMN documents.embedding IS 'Vector embedding from OpenAI text-embedding-ada-002 (1536 dimensions)';
COMMENT ON COLUMN documents.metadata IS 'Additional metadata as JSON (e.g., entity_name, error_code, etc.)';
