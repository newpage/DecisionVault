#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/server-common.sh"
dv_init

BRANCH="${DV_DEPLOY_BRANCH:-main}"
RESET_DATABASE=false
SKIP_PULL=false
SKIP_BUILD=false
RUN_TESTS=false

usage() {
  cat <<'EOF'
Usage: dv deploy [--reset-db] [--skip-pull] [--skip-build] [--test]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reset-db) RESET_DATABASE=true ;;
    --skip-pull) SKIP_PULL=true ;;
    --skip-build) SKIP_BUILD=true ;;
    --test) RUN_TESTS=true ;;
    -h|--help) usage; exit 0 ;;
    *) dv_bad "Unknown option: $1"; exit 2 ;;
  esac
  shift
done

for command in git docker curl; do dv_require "${command}"; done
docker compose version >/dev/null
cd "${REPO_DIR}"
[[ -f .env ]] || { dv_bad ".env is missing"; exit 1; }
[[ -z "$(git status --porcelain)" ]] || { dv_bad "Repository contains uncommitted changes"; exit 1; }

if [[ "${SKIP_PULL}" == false ]]; then
  dv_info "Fetching origin/${BRANCH}"
  git fetch --prune origin "${BRANCH}"
  git pull --ff-only origin "${BRANCH}"
fi

if [[ "${RESET_DATABASE}" == true ]]; then
  dv_warn "Deleting DecisionVault database and storage volumes"
  "${COMPOSE[@]}" down --volumes --remove-orphans
fi

if [[ "${RUN_TESTS}" == true ]]; then
  "${COMPOSE[@]}" build backend
  "${COMPOSE[@]}" run --rm --no-deps backend pytest
fi

if [[ "${SKIP_BUILD}" == true ]]; then
  "${COMPOSE[@]}" up -d
else
  "${COMPOSE[@]}" up -d --build --remove-orphans
fi

deadline=$((SECONDS + DV_HEALTH_TIMEOUT))
until dv_http_ok "http://127.0.0.1:${DV_BACKEND_PORT}/health" 5; do
  (( SECONDS < deadline )) || { dv_bad "Backend health timeout"; "${COMPOSE[@]}" logs --tail=100 backend; exit 1; }
  sleep 3
done
dv_ok "Backend healthy"

deadline=$((SECONDS + DV_HEALTH_TIMEOUT))
until dv_http_ok "http://127.0.0.1:${DV_FRONTEND_PORT}/" 5; do
  (( SECONDS < deadline )) || { dv_bad "Frontend health timeout"; "${COMPOSE[@]}" logs --tail=100 frontend; exit 1; }
  sleep 3
done
dv_ok "Frontend healthy"

dv_http_ok "${DV_PUBLIC_URL}/" 10 && dv_ok "Public HTTPS healthy" || dv_warn "Public HTTPS check failed"
printf '\nDecisionVault %s deployed at commit %s\n' "$(dv_release)" "$(dv_commit)"
"${COMPOSE[@]}" ps
