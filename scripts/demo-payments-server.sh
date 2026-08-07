#!/usr/bin/env bash
set -Eeuo pipefail

root_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${root_dir}"

project="decisionvault-payments-demo"
files=(
  -f docker-compose.yml
  -f compose.demo.yml
  -f compose.demo.server.yml
)
export DV_BACKEND_PORT=8400
export DV_FRONTEND_PORT=3400

case "${1:-start}" in
  start)
    # `up` is intentionally non-destructive: it preserves the isolated demo
    # database and storage volumes and recreates only services whose config or
    # image changed.
    docker compose -p "${project}" "${files[@]}" up --build -d
    ;;
  restart)
    # Force service recreation while retaining the project's named volumes.
    docker compose -p "${project}" "${files[@]}" up --build -d --force-recreate
    ;;
  status)
    ;;
  *)
    printf 'Usage: %s [start|restart|status]\n' "$0" >&2
    exit 2
    ;;
esac

docker compose -p "${project}" "${files[@]}" ps

wait_for_http() {
  local name="$1"
  local url="$2"
  local deadline=$((SECONDS + 180))
  until curl --silent --fail --max-time 5 "${url}" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      printf '%s health check timed out: %s\n' "${name}" "${url}" >&2
      return 1
    fi
    sleep 3
  done
}

wait_for_http "Backend" "http://127.0.0.1:8400/health"
wait_for_http "Frontend" "http://127.0.0.1:3400/"

printf '\nPayments demo services are healthy on Linux loopback.\n'
printf 'Public URL after the authorized Apache change: https://decisionvault.discovera.ai\n'
