#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/server-common.sh
source "${SCRIPT_DIR}/lib/server-common.sh"
dv_init

failures=0

check() {
  local label="$1"
  shift

  if "$@" >/dev/null 2>&1; then
    dv_ok "${label}"
  else
    dv_bad "${label}"
    failures=$((failures + 1))
  fi
}

printf 'DecisionVault Doctor\n====================\n'
printf 'Release: %s\nCommit:  %s\n\n' "$(dv_release)" "$(dv_commit)"

check ".env present" test -f "${REPO_DIR}/.env"
check "Git repository" test -d "${REPO_DIR}/.git"
check "Git working tree clean" test -z "$(git -C "${REPO_DIR}" status --porcelain)"
check "Docker available" dv_require docker
check "Docker Compose v2" docker compose version
check "curl available" dv_require curl

printf '\nConfiguration\n-------------\n'

if [[ -n "${JWT_SECRET:-}" && "${JWT_SECRET:-}" != replace-* ]]; then
  dv_ok "JWT secret configured"
else
  dv_bad "JWT secret missing or placeholder"
  failures=$((failures + 1))
fi

if [[ -n "${DATABASE_URL:-}" ]]; then
  dv_ok "Database URL configured"
else
  dv_bad "DATABASE_URL missing"
  failures=$((failures + 1))
fi

if [[ -n "${OLLAMA_URL:-}" ]]; then
  dv_ok "Ollama URL configured"
else
  dv_warn "OLLAMA_URL missing"
fi

printf 'Backend port:  %s\n' "${DV_BACKEND_PORT}"
printf 'Frontend port: %s\n' "${DV_FRONTEND_PORT}"

printf '\nCompose\n-------\n'

if config_json="$("${COMPOSE[@]}" config --format json 2>/dev/null)"; then
  dv_ok "Compose configuration resolves"

  CONFIG_JSON="${config_json}" \
    python3 - "${DV_BACKEND_PORT}" "${DV_FRONTEND_PORT}" <<'PY' \
    || failures=$((failures + 1))
import json
import os
import sys

config = json.loads(os.environ["CONFIG_JSON"])
expected = {
    "backend": sys.argv[1],
    "frontend": sys.argv[2],
}

failed = False

for service_name, expected_port in expected.items():
    ports = config["services"][service_name].get("ports") or []
    published = {str(port.get("published")) for port in ports}

    if expected_port in published:
        print(
            f"\033[1;32m✓\033[0m "
            f"{service_name} publishes {expected_port}"
        )
    else:
        print(
            f"\033[1;31m✗\033[0m "
            f"{service_name} expected {expected_port}; "
            f"found {sorted(published)}"
        )
        failed = True

raise SystemExit(1 if failed else 0)
PY
else
  dv_bad "Compose configuration invalid"
  failures=$((failures + 1))
fi

printf '\nRuntime\n-------\n'

check \
  "Backend health" \
  dv_http_ok \
  "http://127.0.0.1:${DV_BACKEND_PORT}/health"

check \
  "Frontend health" \
  dv_http_ok \
  "http://127.0.0.1:${DV_FRONTEND_PORT}/"

check \
  "Public HTTPS" \
  dv_http_ok \
  "${DV_PUBLIC_URL}/"

if [[ "${OLLAMA_ENABLED:-false}" == "true" ]]; then
  OLLAMA_HEALTH_URL="${DV_OLLAMA_HEALTH_URL:-http://127.0.0.1:11434}"

  check \
    "Ollama reachable" \
    dv_http_ok \
    "${OLLAMA_HEALTH_URL%/}/api/tags"
fi

printf '\nStorage\n-------\n'

check \
  "Backup directory writable" \
  mkdir -p \
  "${DV_BACKUP_DIR}"

check \
  "Sufficient disk space (>1 GB)" \
  bash -c \
  "[[ \$(df -Pk '${REPO_DIR}' | awk 'NR==2{print \$4}') -gt 1048576 ]]"

printf '\n'

if (( failures == 0 )); then
  dv_ok "SYSTEM HEALTHY"
else
  dv_bad "${failures} check(s) failed"
fi

exit "${failures}"
