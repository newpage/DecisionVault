#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/server-common.sh"
dv_init

timestamp="$(date +%Y%m%d-%H%M%S)"
target="${DV_BACKUP_DIR}/${timestamp}"
mkdir -p "${target}"

dv_info "Backing up PostgreSQL"
"${COMPOSE[@]}" exec -T db pg_dump -U decisionvault -d decisionvault | gzip > "${target}/decisionvault.sql.gz"

dv_info "Backing up storage volume"
docker run --rm \
  -v "${COMPOSE_PROJECT_NAME}_decisionvault_storage:/data/storage:ro" \
  -v "${target}:/backup" \
  alpine:3.20 \
  sh -c 'tar -czf /backup/storage.tar.gz -C /data/storage .'

cat > "${target}/manifest.json" <<EOF
{
  "release": "$(dv_release)",
  "commit": "$(dv_commit)",
  "created_at": "$(date -Iseconds)",
  "database": "decisionvault.sql.gz",
  "storage": "storage.tar.gz"
}
EOF

dv_ok "Backup created: ${target}"
