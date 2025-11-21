#!/bin/bash
set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="${DB_NAME:-appdb}"
DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-admin}"

mkdir -p ${BACKUP_DIR}

echo "Starting backup at ${TIMESTAMP}..."

# PostgreSQL backup
pg_dump -h ${DB_HOST} -U ${DB_USER} ${DB_NAME} | gzip > ${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz

echo "Backup completed: ${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"

# Clean old backups (keep last 30 days)
find ${BACKUP_DIR} -name "backup_*.sql.gz" -mtime +30 -delete

echo "Old backups cleaned"
