#!/usr/bin/env bash
# Database Backup Script

set -e

BACKUP_DIR=${BACKUP_DIR:-./backups}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/agentic-shell-${TIMESTAMP}.sql.gz"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Get database URL from environment
DB_URL=${DATABASE_URL:-postgresql://agentic:agentic123@localhost:5432/agentic}

echo "📦 Creating database backup: ${BACKUP_FILE}"

# Perform backup
pg_dump "${DB_URL}" | gzip > "${BACKUP_FILE}"

# Get file size
SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)

echo "✅ Backup completed: ${BACKUP_FILE} (${SIZE})"

# Clean up old backups (keep last 30 days)
find "${BACKUP_DIR}" -name "agentic-shell-*.sql.gz" -mtime +30 -delete

echo "🧹 Cleaned up backups older than 30 days"