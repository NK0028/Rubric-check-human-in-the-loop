#!/usr/bin/env bash
set -euo pipefail

database_path="${DATABASE_PATH:-backend/rubricheck.db}"
uploads_path="${UPLOADS_PATH:-backend/uploads}"
backup_root="${BACKUP_DIR:-backups}"
timestamp="$(date +%Y%m%d-%H%M%S)"
target_directory="${backup_root}/rubricheck-${timestamp}"

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 is required to create a consistent SQLite backup." >&2
  exit 1
fi
if [ ! -f "${database_path}" ]; then
  echo "Database not found: ${database_path}" >&2
  exit 1
fi

mkdir -p "${target_directory}"
sqlite3 "${database_path}" ".backup '${target_directory}/rubricheck.db'"
if [ -d "${uploads_path}" ]; then
  tar -C "$(dirname "${uploads_path}")" -czf "${target_directory}/uploads.tar.gz" "$(basename "${uploads_path}")"
fi
echo "Backup created in ${target_directory}"
