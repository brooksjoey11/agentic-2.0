# Database Migrations

## Tooling
- `pg-migrate` v7.3.0
- Node.js 20+ for migration scripts
- PostgreSQL 15+

## Directory Structure
```
migrations/
├── README.md
├── 001_initial_schema.sql
├── 002_add_vector_extension.sql
├── 003_create_conversations_table.sql
├── 004_create_sessions_table.sql
├── 005_create_tool_executions_table.sql
├── 006_create_agent_metrics_table.sql
├── 007_create_feedback_table.sql
├── 008_create_knowledge_base_table.sql
├── 009_add_idempotency_keys.sql
├── 010_add_dead_letter_queue.sql
└── run.js
```

## Migration Commands
```bash
# Run all pending migrations
npm run migrate:up

# Rollback last migration
npm run migrate:down

# Create new migration
npm run migrate:create "description"
```

## Requirements
1. Every migration must be reversible (have both `up` and `down`)
2. Migrations must be idempotent (safe to run multiple times)
3. All schema changes must include justification for indexes
4. Vector extension must be enabled before any embedding columns

## Rollback Procedure
1. `npm run migrate:down` to revert last migration
2. If application code was deployed with schema changes, rollback code first
3. Verify data integrity after rollback
