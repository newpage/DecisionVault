#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

project="decisionvault-payments-demo"
files=(-f docker-compose.yml -f compose.demo.yml)
export DV_BACKEND_PORT=8400
export DV_FRONTEND_PORT=3400

docker compose -p "$project" "${files[@]}" down -v --remove-orphans
docker compose -p "$project" "${files[@]}" up --build -d
docker compose -p "$project" "${files[@]}" ps

printf '\nPayments demo ready:\n'
printf '  UI: http://127.0.0.1:3400\n'
printf '  Login: presenter@globalpayments.demo / DecisionVault!\n'
printf '  Restricted-user check: analyst@globalpayments.demo / DecisionVault!\n'
