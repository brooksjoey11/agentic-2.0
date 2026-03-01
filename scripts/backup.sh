#!/usr/bin/env bash
# backup.sh — back up the PostgreSQL database and upload to S3
set -euo pipefail

DB_URL="${DATABASE_URL:-postgresql://user:password@localhost:5432/agenticdb}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/agenticdb_${TIMESTAMP}.sql.gz"
S3_BUCKET="${S3_BUCKET:-}"

mkdir -p "$BACKUP_DIR"

echo "==> Backing up database to ${BACKUP_FILE}..."
pg_dump "$DB_URL" | gzip > "$BACKUP_FILE"

if [ -n "$S3_BUCKET" ]; then
  echo "==> Uploading backup to s3://${S3_BUCKET}/backups/..."
  aws s3 cp "$BACKUP_FILE" "s3://${S3_BUCKET}/backups/"
fi

echo "==> Backup complete: ${BACKUP_FILE}"
