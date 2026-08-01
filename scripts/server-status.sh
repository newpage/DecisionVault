#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

BACKEND_PORT="${DV_BACKEND_PORT:-8200}"
FRONTEND_PORT="${DV_FRONTEND_PORT:-3000}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-decisionvault}"

cd "${REPO_DIR}"

export DV_BACKEND_PORT="${BACKEND_PORT}"
export DV_FRONTEND_PORT="${FRONTEND_PORT}"

COMPOSE=(
  docker compose
  -p "${COMPOSE_PROJECT_NAME}"
  -f docker-compose.yml
  -f docker-compose.server.yml
)

echo "DecisionVault commit: $(git rev-parse --short HEAD)"
echo
"${COMPOSE[@]}" ps
echo

if curl --silent --fail --max-time 5 \
  "http://127.0.0.1:${BACKEND_PORT}/health"; then
  echo
  echo "Backend health: PASS"
else
  echo "Backend health: FAIL"
fi

if curl --silent --fail --max-time 5 \
  "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null; then
  echo "Frontend health: PASS"
else
  echo "Frontend health: FAIL"
fi
