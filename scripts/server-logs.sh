#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

BACKEND_PORT="${DV_BACKEND_PORT:-8200}"
FRONTEND_PORT="${DV_FRONTEND_PORT:-3000}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-decisionvault}"
LINES="${1:-150}"

cd "${REPO_DIR}"

export DV_BACKEND_PORT="${BACKEND_PORT}"
export DV_FRONTEND_PORT="${FRONTEND_PORT}"

docker compose \
  -p "${COMPOSE_PROJECT_NAME}" \
  -f docker-compose.yml \
  -f docker-compose.server.yml \
  logs --follow --tail="${LINES}" backend frontend worker db
