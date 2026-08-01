#!/usr/bin/env bash

dv_init() {
  SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[1]}")" && pwd)"
  REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

  if [[ -f "${REPO_DIR}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${REPO_DIR}/.env"
    set +a
  fi

  DV_BACKEND_PORT="${DV_BACKEND_PORT:-8200}"
  DV_FRONTEND_PORT="${DV_FRONTEND_PORT:-3200}"
  DV_HEALTH_TIMEOUT="${DV_HEALTH_TIMEOUT:-180}"
  COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-decisionvault}"
  DV_PUBLIC_URL="${DV_PUBLIC_URL:-https://decisionvault.discovera.ai}"
  DV_BACKUP_DIR="${DV_BACKUP_DIR:-${REPO_DIR}/backups}"

  export DV_BACKEND_PORT DV_FRONTEND_PORT COMPOSE_PROJECT_NAME

  COMPOSE=(
    docker compose
    -p "${COMPOSE_PROJECT_NAME}"
    -f "${REPO_DIR}/docker-compose.yml"
    -f "${REPO_DIR}/docker-compose.server.yml"
  )
}

dv_release() {
  if [[ -f "${REPO_DIR}/VERSION" ]]; then
    tr -d '[:space:]' < "${REPO_DIR}/VERSION"
  else
    printf 'unknown'
  fi
}

dv_commit() {
  git -C "${REPO_DIR}" rev-parse --short HEAD 2>/dev/null || printf 'unknown'
}

dv_ok() { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
dv_warn() { printf '\033[1;33m!\033[0m %s\n' "$*"; }
dv_bad() { printf '\033[1;31m✗\033[0m %s\n' "$*"; }
dv_info() { printf '\033[1;34m[DecisionVault]\033[0m %s\n' "$*"; }

dv_require() {
  command -v "$1" >/dev/null 2>&1 || {
    dv_bad "$1 is required"
    return 1
  }
}

dv_http_ok() {
  curl --silent --show-error --fail --location --max-time "${2:-8}" "$1" >/dev/null
}
