#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/server-common.sh"
dv_init

timestamp="$(date +%Y%m%d-%H%M%S)"
work="$(mktemp -d)"
bundle="${REPO_DIR}/decisionvault-diagnostics-${timestamp}.tar.gz"
trap 'rm -rf "${work}"' EXIT

{
  echo "release=$(dv_release)"
  echo "commit=$(dv_commit)"
  echo "created_at=$(date -Iseconds)"
  uname -a
} > "${work}/system.txt"

git -C "${REPO_DIR}" status --short --branch > "${work}/git-status.txt" 2>&1 || true
"${COMPOSE[@]}" ps -a > "${work}/compose-ps.txt" 2>&1 || true
"${COMPOSE[@]}" config > "${work}/compose-config.yml" 2>&1 || true
"${COMPOSE[@]}" logs --no-color --tail=300 backend frontend worker db > "${work}/logs.txt" 2>&1 || true
"${SCRIPT_DIR}/server-doctor.sh" > "${work}/doctor.txt" 2>&1 || true
apachectl -S > "${work}/apache-vhosts.txt" 2>&1 || true

if [[ -f "${REPO_DIR}/.env" ]]; then
  sed -E \
    -e 's#^(JWT_SECRET|DEMO_PASSWORD|DATABASE_URL)=.*#\1=[REDACTED]#' \
    -e 's#^([A-Z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)=.*#\1=[REDACTED]#' \
    "${REPO_DIR}/.env" > "${work}/environment-redacted.txt"
fi

tar -czf "${bundle}" -C "${work}" .
dv_ok "Diagnostic bundle created: ${bundle}"
