#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/server-common.sh"
dv_init
cd "${REPO_DIR}"

printf 'DecisionVault %s (%s)\n' "$(dv_release)" "$(dv_commit)"
printf 'Backend:  127.0.0.1:%s\nFrontend: 127.0.0.1:%s\n\n' "${DV_BACKEND_PORT}" "${DV_FRONTEND_PORT}"
"${COMPOSE[@]}" ps
printf '\n'

dv_http_ok "http://127.0.0.1:${DV_BACKEND_PORT}/health" && dv_ok "Backend health" || dv_bad "Backend health"
dv_http_ok "http://127.0.0.1:${DV_FRONTEND_PORT}/" && dv_ok "Frontend health" || dv_bad "Frontend health"
dv_http_ok "${DV_PUBLIC_URL}/" && dv_ok "Public HTTPS" || dv_warn "Public HTTPS unavailable"
