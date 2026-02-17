-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Recall Memories table for semantic search
CREATE TABLE IF NOT EXISTS recall_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- OpenAI text-embedding-3-small dimension
    importance FLOAT NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
    access_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMPTZ
);

-- Use HNSW to avoid IVF training requirements on empty tables.
CREATE INDEX IF NOT EXISTS recall_memories_embedding_idx
    ON recall_memories
    USING hnsw (embedding vector_cosine_ops);

-- Index for user_id queries
CREATE INDEX IF NOT EXISTS recall_memories_user_id_idx
    ON recall_memories(user_id);

-- Index for importance filtering
CREATE INDEX IF NOT EXISTS recall_memories_importance_idx
    ON recall_memories(importance);

-- Archival Memories table for long-term storage
CREATE TABLE IF NOT EXISTS archival_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    session_id TEXT,
    compressed BOOLEAN NOT NULL DEFAULT FALSE,
    compressed_into_id UUID REFERENCES archival_memories(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for user_id queries
CREATE INDEX IF NOT EXISTS archival_memories_user_id_idx
    ON archival_memories(user_id);

-- Index for source queries
CREATE INDEX IF NOT EXISTS archival_memories_source_idx
    ON archival_memories(source);

-- Index for session queries
CREATE INDEX IF NOT EXISTS archival_memories_session_id_idx
    ON archival_memories(session_id)
    WHERE session_id IS NOT NULL;

-- GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS archival_memories_metadata_idx
    ON archival_memories USING gin (metadata);

-- Index for compressed status
CREATE INDEX IF NOT EXISTS archival_memories_compressed_idx
    ON archival_memories(compressed)
    WHERE compressed = true;

-- Index for content text search
CREATE INDEX IF NOT EXISTS archival_memories_content_idx
    ON archival_memories USING gin (to_tsvector('english', content));

-- Generic trigger to keep updated_at consistent.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to set last_accessed whenever access_count changes.
CREATE OR REPLACE FUNCTION set_last_accessed_on_access()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.access_count IS DISTINCT FROM OLD.access_count THEN
        NEW.last_accessed = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS recall_memories_set_updated_at ON recall_memories;
CREATE TRIGGER recall_memories_set_updated_at
    BEFORE UPDATE ON recall_memories
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS archival_memories_set_updated_at ON archival_memories;
CREATE TRIGGER archival_memories_set_updated_at
    BEFORE UPDATE ON archival_memories
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS recall_memories_set_last_accessed ON recall_memories;
CREATE TRIGGER recall_memories_set_last_accessed
    BEFORE UPDATE ON recall_memories
    FOR EACH ROW
    EXECUTE FUNCTION set_last_accessed_on_access();
