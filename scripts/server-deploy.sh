#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${REPO_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_DIR}/.env"
  set +a
fi

BRANCH="${DV_DEPLOY_BRANCH:-main}"
BACKEND_PORT="${DV_BACKEND_PORT:-8200}"
FRONTEND_PORT="${DV_FRONTEND_PORT:-3200}"
HEALTH_TIMEOUT="${DV_HEALTH_TIMEOUT:-180}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-decisionvault}"

RESET_DATABASE=false
SKIP_PULL=false
SKIP_BUILD=false
RUN_TESTS=false

usage() {
  cat <<'EOF'
DecisionVault Linux deployment

Usage:
  ./scripts/server-deploy.sh [options]

Options:
  --branch <name>       Deploy this branch. Default: main
  --reset-db            Delete the PostgreSQL volume before deployment
  --skip-pull           Do not fetch or pull from GitHub
  --skip-build          Start existing images without rebuilding
  --test                Run backend tests before starting the application
  -h, --help            Show this help

Environment:
  DV_BACKEND_PORT       Host-only backend port. Default: 8200
  DV_FRONTEND_PORT      Host-only frontend port. Default: 3200
  DV_HEALTH_TIMEOUT     Seconds to wait for healthy services. Default: 180
  DV_DEPLOY_BRANCH      Default branch when --branch is omitted
  COMPOSE_PROJECT_NAME  Docker Compose project name. Default: decisionvault

Examples:
  ./scripts/server-deploy.sh
  ./scripts/server-deploy.sh --reset-db
  ./scripts/server-deploy.sh --test
  DV_BACKEND_PORT=8200 ./scripts/server-deploy.sh
EOF
}

log() {
  printf '\033[1;34m[DecisionVault]\033[0m %s\n' "$*"
}

success() {
  printf '\033[1;32m[DecisionVault]\033[0m %s\n' "$*"
}

warn() {
  printf '\033[1;33m[DecisionVault]\033[0m %s\n' "$*" >&2
}

fail() {
  printf '\033[1;31m[DecisionVault]\033[0m %s\n' "$*" >&2
  exit 1
}

show_failure_diagnostics() {
  warn "Deployment failed. Showing service state and recent logs."
  (
    cd "${REPO_DIR}"
    docker compose \
      -p "${COMPOSE_PROJECT_NAME}" \
      -f docker-compose.yml \
      -f docker-compose.server.yml \
      ps || true
    docker compose \
      -p "${COMPOSE_PROJECT_NAME}" \
      -f docker-compose.yml \
      -f docker-compose.server.yml \
      logs --tail=120 backend frontend worker db || true
  )
}

trap show_failure_diagnostics ERR

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      [[ $# -ge 2 ]] || fail "--branch requires a value"
      BRANCH="$2"
      shift 2
      ;;
    --reset-db)
      RESET_DATABASE=true
      shift
      ;;
    --skip-pull)
      SKIP_PULL=true
      shift
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --test)
      RUN_TESTS=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

command -v git >/dev/null 2>&1 || fail "git is required"
command -v docker >/dev/null 2>&1 || fail "docker is required"
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required"

cd "${REPO_DIR}"

[[ -d .git ]] || fail "${REPO_DIR} is not a Git repository"
[[ -f docker-compose.yml ]] || fail "docker-compose.yml is missing"
[[ -f docker-compose.server.yml ]] || fail "docker-compose.server.yml is missing"
[[ -f .env ]] || fail ".env is missing. Create it from .env.example before deployment."

if [[ -n "$(git status --porcelain)" ]]; then
  fail "Repository contains uncommitted changes. Commit or stash them before deploying."
fi

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "${CURRENT_BRANCH}" != "${BRANCH}" ]]; then
  log "Switching from ${CURRENT_BRANCH:-detached HEAD} to ${BRANCH}"
  git switch "${BRANCH}"
fi

if [[ "${SKIP_PULL}" == false ]]; then
  log "Fetching origin/${BRANCH}"
  git fetch --prune origin "${BRANCH}"

  LOCAL_SHA="$(git rev-parse HEAD)"
  REMOTE_SHA="$(git rev-parse "origin/${BRANCH}")"

  if [[ "${LOCAL_SHA}" != "${REMOTE_SHA}" ]]; then
    log "Updating ${LOCAL_SHA:0:8} -> ${REMOTE_SHA:0:8}"
    git pull --ff-only origin "${BRANCH}"
  else
    log "Repository is already current at ${LOCAL_SHA:0:8}"
  fi
fi

export DV_BACKEND_PORT="${BACKEND_PORT}"
export DV_FRONTEND_PORT="${FRONTEND_PORT}"

COMPOSE=(
  docker compose
  -p "${COMPOSE_PROJECT_NAME}"
  -f docker-compose.yml
  -f docker-compose.server.yml
)

if [[ "${RESET_DATABASE}" == true ]]; then
  warn "Resetting the complete DecisionVault database and storage volumes."
  "${COMPOSE[@]}" down --volumes --remove-orphans
else
  "${COMPOSE[@]}" down --remove-orphans
fi

if [[ "${RUN_TESTS}" == true ]]; then
  log "Building backend test image"
  "${COMPOSE[@]}" build backend
  log "Running backend tests"
  "${COMPOSE[@]}" run --rm --no-deps backend pytest
fi

if [[ "${SKIP_BUILD}" == true ]]; then
  log "Starting existing images"
  "${COMPOSE[@]}" up -d
else
  log "Building and starting DecisionVault"
  "${COMPOSE[@]}" up -d --build
fi

log "Waiting for backend health on 127.0.0.1:${BACKEND_PORT}"
deadline=$((SECONDS + HEALTH_TIMEOUT))
until curl --silent --fail --max-time 5 \
  "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null; do
  if (( SECONDS >= deadline )); then
    fail "Backend did not become healthy within ${HEALTH_TIMEOUT} seconds"
  fi
  sleep 3
done

log "Waiting for frontend on 127.0.0.1:${FRONTEND_PORT}"
deadline=$((SECONDS + HEALTH_TIMEOUT))
until curl --silent --fail --max-time 5 \
  "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null; do
  if (( SECONDS >= deadline )); then
    fail "Frontend did not become available within ${HEALTH_TIMEOUT} seconds"
  fi
  sleep 3
done

DEPLOYED_SHA="$(git rev-parse --short HEAD)"
success "Deployment complete"
printf '  Commit:  %s\n' "${DEPLOYED_SHA}"
printf '  Backend: http://127.0.0.1:%s/health\n' "${BACKEND_PORT}"
printf '  Frontend: http://127.0.0.1:%s/\n' "${FRONTEND_PORT}"
printf '\n'
"${COMPOSE[@]}" ps
