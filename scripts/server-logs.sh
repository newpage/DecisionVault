#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/server-common.sh"
dv_init
cd "${REPO_DIR}"

service="${1:-all}"
lines="${2:-150}"
case "${service}" in
  backend|frontend|worker|db)
    services=("${service}")
    ;;
  all)
    services=(backend frontend worker db)
    ;;
  *)
    echo "Usage: dv logs [backend|frontend|worker|db|all] [lines]" >&2
    exit 2
    ;;
esac
"${COMPOSE[@]}" logs --follow --tail="${lines}" "${services[@]}"
