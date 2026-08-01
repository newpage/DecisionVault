#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/server-common.sh"
dv_init
cd "${REPO_DIR}"

[[ -z "$(git status --porcelain)" ]] || {
  dv_bad "Working tree is dirty. Commit, stash, or reset changes."
  exit 1
}

branch="${DV_DEPLOY_BRANCH:-main}"
dv_info "Refreshing origin/${branch}"
git fetch --prune origin "${branch}"
git checkout "${branch}"
git reset --hard "origin/${branch}"
exec "${SCRIPT_DIR}/server-deploy.sh" --skip-pull "$@"
