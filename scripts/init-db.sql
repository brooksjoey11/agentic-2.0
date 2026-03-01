-- =============================================================================
-- Agentic Shell 2.0 - Database Schema
-- =============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- CONVERSATIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    role VARCHAR(16) NOT NULL,
    content TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_role ON conversations(role);
CREATE INDEX IF NOT EXISTS idx_conversations_metadata ON conversations USING gin(metadata);

-- =============================================================================
-- SESSIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64),
    agent_assignments JSONB DEFAULT '{}'::jsonb,
    context JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- =============================================================================
-- TOOL_EXECUTIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS tool_executions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    tool_name VARCHAR(64) NOT NULL,
    arguments JSONB NOT NULL,
    result JSONB,
    status VARCHAR(16) DEFAULT 'pending',
    duration_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_tool_executions_session_id ON tool_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool_name ON tool_executions(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_executions_status ON tool_executions(status);
CREATE INDEX IF NOT EXISTS idx_tool_executions_created_at ON tool_executions(created_at);

-- =============================================================================
-- AGENT_METRICS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_metrics (
    id BIGSERIAL PRIMARY KEY,
    agent_type VARCHAR(32) NOT NULL,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    avg_response_time_ms FLOAT,
    p95_response_time_ms FLOAT,
    p99_response_time_ms FLOAT,
    memory_usage_mb INTEGER,
    cpu_usage_percent FLOAT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent_type ON agent_metrics(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_timestamp ON agent_metrics(timestamp);

-- =============================================================================
-- FEEDBACK TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS feedback (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    conversation_id BIGINT REFERENCES conversations(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_session_id ON feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);

-- =============================================================================
-- KNOWLEDGE_BASE TABLE (for RAG)
-- =============================================================================
CREATE TABLE IF NOT EXISTS knowledge_base (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255),
    content TEXT,
    embedding vector(1536),
    source VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_source ON knowledge_base(source);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_created_at ON knowledge_base(created_at);

-- =============================================================================
-- FUNCTIONS AND TRIGGERS
-- =============================================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers
CREATE TRIGGER update_conversations_updated_at 
    BEFORE UPDATE ON conversations 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at 
    BEFORE UPDATE ON knowledge_base 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Session summary view
CREATE OR REPLACE VIEW session_summary AS
SELECT 
    s.session_id,
    s.user_id,
    COUNT(DISTINCT c.id) as message_count,
    MAX(c.created_at) as last_message,
    COUNT(DISTINCT te.id) as tool_executions,
    AVG(te.duration_ms) as avg_tool_duration,
    s.created_at as session_start,
    EXTRACT(EPOCH FROM (NOW() - s.created_at)) / 3600 as session_duration_hours
FROM sessions s
LEFT JOIN conversations c ON s.session_id = c.session_id
LEFT JOIN tool_executions te ON s.session_id = te.session_id
GROUP BY s.session_id, s.user_id, s.created_at;

-- Agent performance view
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
-- INDEXES FOR VECTOR SEARCH
-- =============================================================================

-- Create vector similarity search index (if using pgvector with ivfflat)
CREATE INDEX IF NOT EXISTS idx_conversations_embedding 
    ON conversations 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding 
    ON knowledge_base 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- =============================================================================
-- INITIAL DATA
-- =============================================================================

-- Insert default tool definitions
INSERT INTO tool_executions (session_id, tool_name, arguments, result, status)
VALUES 
    ('system', 'kubernetes', '{"description": "Kubernetes cluster management"}', '{"available": true}', 'completed'),
    ('system', 'docker', '{"description": "Docker container management"}', '{"available": true}', 'completed'),
    ('system', 'aws', '{"description": "AWS cloud services"}', '{"available": true}', 'completed'),
    ('system', 'github', '{"description": "GitHub operations"}', '{"available": true}', 'completed'),
    ('system', 'shell', '{"description": "Local shell execution"}', '{"available": true}', 'completed')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE conversations IS 'Stores all conversation messages with embeddings';
COMMENT ON TABLE sessions IS 'Active session metadata and context';
COMMENT ON TABLE tool_executions IS 'Audit log of all tool executions';
COMMENT ON TABLE agent_metrics IS 'Performance metrics for each agent type';
COMMENT ON TABLE feedback IS 'User feedback on agent responses';
COMMENT ON TABLE knowledge_base IS 'Vector store for RAG (Retrieval Augmented Generation)';

-- =============================================================================
-- CLEANUP FUNCTION
-- =============================================================================

-- Function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM sessions 
    WHERE expires_at < NOW() 
       OR last_active < NOW() - INTERVAL '30 days';
    
    -- Archive old conversations (optional - move to archive table)
    -- This keeps the main table performant
    DELETE FROM conversations 
    WHERE created_at < NOW() - INTERVAL '90 days'
    AND session_id NOT IN (SELECT session_id FROM sessions);
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (if using pg_cron)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('0 2 * * *', 'SELECT cleanup_expired_sessions()');