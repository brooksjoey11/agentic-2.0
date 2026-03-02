-- =============================================================================
-- Agentic Shell 2.0 - PostgreSQL Schema
-- Version: 2.0.0
-- Compatible with: PostgreSQL 15+
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- USERS TABLE (for authentication and authorization)
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar VARCHAR(512),
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    google_id VARCHAR(255) UNIQUE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ, -- Soft delete for GDPR compliance
    
    CONSTRAINT valid_role CHECK (role IN ('user', 'admin', 'billing'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_created_at ON users(created_at);

-- =============================================================================
-- SESSIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    agent_assignments JSONB NOT NULL DEFAULT '{}',
    context JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_last_active ON sessions(last_active);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_sessions_metadata ON sessions USING gin(metadata);

-- =============================================================================
-- CONVERSATIONS TABLE (message history)
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    correlation_id VARCHAR(64) NOT NULL,
    role VARCHAR(16) NOT NULL,
    content TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_role CHECK (role IN ('user', 'agent', 'system', 'tool'))
);

CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_correlation_id ON conversations(correlation_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);
CREATE INDEX idx_conversations_role ON conversations(role);
CREATE INDEX idx_conversations_metadata ON conversations USING gin(metadata);
CREATE INDEX idx_conversations_embedding ON conversations USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =============================================================================
-- TOOL_EXECUTIONS TABLE (audit log)
-- =============================================================================
CREATE TABLE IF NOT EXISTS tool_executions (
    id BIGSERIAL PRIMARY KEY,
    execution_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    correlation_id VARCHAR(64) NOT NULL,
    tool_name VARCHAR(64) NOT NULL,
    arguments JSONB NOT NULL,
    result JSONB,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    duration_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE INDEX idx_tool_executions_session_id ON tool_executions(session_id);
CREATE INDEX idx_tool_executions_correlation_id ON tool_executions(correlation_id);
CREATE INDEX idx_tool_executions_tool_name ON tool_executions(tool_name);
CREATE INDEX idx_tool_executions_status ON tool_executions(status);
CREATE INDEX idx_tool_executions_created_at ON tool_executions(created_at);

-- =============================================================================
-- AGENT_METRICS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_metrics (
    id BIGSERIAL PRIMARY KEY,
    agent_type VARCHAR(32) NOT NULL,
    correlation_id VARCHAR(64) NOT NULL,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    avg_response_time_ms FLOAT,
    p95_response_time_ms FLOAT,
    p99_response_time_ms FLOAT,
    memory_usage_mb INTEGER,
    cpu_usage_percent FLOAT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_metrics_agent_type ON agent_metrics(agent_type);
CREATE INDEX idx_agent_metrics_timestamp ON agent_metrics(timestamp);

-- =============================================================================
-- IDEMPOTENCY KEYS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS idempotency_keys (
    id BIGSERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    response JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_idempotency_keys_key ON idempotency_keys(key);
CREATE INDEX idx_idempotency_keys_expires_at ON idempotency_keys(expires_at);

-- =============================================================================
-- DEAD LETTER QUEUE TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id BIGSERIAL PRIMARY KEY,
    original_message_id VARCHAR(64),
    queue_name VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    error JSONB,
    retry_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'failed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dlq_status ON dead_letter_queue(status);
CREATE INDEX idx_dlq_created_at ON dead_letter_queue(created_at);

-- =============================================================================
-- FEEDBACK TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS feedback (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    conversation_id BIGINT REFERENCES conversations(id) ON DELETE SET NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feedback_session_id ON feedback(session_id);
CREATE INDEX idx_feedback_rating ON feedback(rating);

-- =============================================================================
-- KNOWLEDGE_BASE TABLE (RAG)
-- =============================================================================
CREATE TABLE IF NOT EXISTS knowledge_base (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255),
    content TEXT,
    embedding vector(1536),
    source VARCHAR(255),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_knowledge_base_source ON knowledge_base(source);
CREATE INDEX idx_knowledge_base_created_at ON knowledge_base(created_at);
CREATE INDEX idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =============================================================================
-- FUNCTIONS AND TRIGGERS
-- =============================================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dead_letter_queue_updated_at BEFORE UPDATE ON dead_letter_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VIEWS FOR REPORTING
-- =============================================================================

CREATE OR REPLACE VIEW session_summary AS
SELECT 
    s.session_id,
    s.user_id,
    COUNT(DISTINCT c.id) as message_count,
    MAX(c.created_at) as last_message,
    COUNT(DISTINCT te.id) as tool_executions,
    COALESCE(AVG(te.duration_ms), 0) as avg_tool_duration,
    s.created_at as session_start,
    EXTRACT(EPOCH FROM (NOW() - s.created_at)) / 3600 as session_duration_hours
FROM sessions s
LEFT JOIN conversations c ON s.session_id = c.session_id
LEFT JOIN tool_executions te ON s.session_id = te.session_id
GROUP BY s.session_id, s.user_id, s.created_at;

CREATE OR REPLACE VIEW agent_performance AS
SELECT 
    agent_type,
    COUNT(*) as measurements,
    AVG(tasks_completed) as avg_tasks_completed,
    AVG(tasks_failed) as avg_tasks_failed,
    AVG(avg_response_time_ms) as avg_response_time,
    AVG(p95_response_time_ms) as p95_response_time,
    AVG(p99_response_time_ms) as p99_response_time,
    AVG(memory_usage_mb) as avg_memory_mb,
    AVG(cpu_usage_percent) as avg_cpu_percent,
    MAX(timestamp) as last_seen
FROM agent_metrics
GROUP BY agent_type;

-- =============================================================================
-- CLEANUP FUNCTION (for expired sessions)
-- =============================================================================
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    -- Move expired session data to archive (if archiving enabled)
    -- For now, just delete
    DELETE FROM sessions 
    WHERE expires_at < NOW() 
       OR last_active < NOW() - INTERVAL '30 days';
    
    -- Delete old tool executions (keep 90 days)
    DELETE FROM tool_executions 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    -- Delete old conversations (keep 90 days)
    DELETE FROM conversations 
    WHERE created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;
