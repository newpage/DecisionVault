#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
target="/usr/local/bin/dv"

sudo ln -sfn "${SCRIPT_DIR}/dv" "${target}"
sudo chmod +x "${SCRIPT_DIR}/dv"

echo "Installed ${target} -> ${SCRIPT_DIR}/dv"
"${target}" version
