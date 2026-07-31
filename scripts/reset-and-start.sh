#!/usr/bin/env bash
set -euo pipefail
if [[ ! -f .env ]]; then cp .env.example .env; fi
docker compose down -v --remove-orphans
docker compose up --build
