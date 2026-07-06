#!/usr/bin/env bash
# Backup LibreGrades PostgreSQL database (run on district server)
set -euo pipefail
source .env 2>/dev/null || true
STAMP=$(date +%Y%m%d_%H%M%S)
FILE="libregrades_backup_${STAMP}.sql"
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-libregrades}" "${POSTGRES_DB:-libregrades}" > "$FILE"
echo "Backup written to $FILE"
