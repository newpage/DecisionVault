# DecisionVault agent guidance

## Scope and workflow

- Read `README.md`, `docs/ARCHITECTURE.md`, `docs/CODING-STANDARDS.md`, and `docs/ENGINEERING-HANDBOOK.md` before material changes.
- Preserve the Mac workstation → GitHub → Linux server delivery path.
- Develop, build, test, inspect, and commit source changes on the Mac workstation.
- Treat `dv deploy`, `dv doctor`, and the other `dv` operations as Linux server commands, not Mac development commands.
- Do not commit, push, deploy, reset data, or change external systems unless the user explicitly authorizes that action.
- Keep changes narrowly scoped and preserve unrelated user work.

## Architecture and safety invariants

- Document and extend the architecture that exists; do not silently introduce a replacement architecture.
- Preserve multi-tenancy and explicit tenant filtering for all tenant-owned reads, writes, joins, aggregates, caches, storage keys, retrieval, background jobs, and audit records.
- Derive tenant identity from the authenticated principal. Foreign-tenant identifiers must not disclose resource existence.
- Preserve authentication, revocable sessions, roles/permissions, classification, and access-policy checks.
- Preserve PostgreSQL/pgvector, FastAPI, Next.js, worker, Ollama integration, Docker Compose, Apache HTTPS proxy, and localhost-only service publishing unless an explicitly approved task changes them.
- Never expose PostgreSQL or the worker publicly. Never commit secrets, `.env`, backups, diagnostics, uploaded data, or generated build output.
- The current pre-release database policy is recorded in `docs/adr/ADR-0001-pre-release-breaking-changes.md`; do not imply that migrations or automated restore exist.

## Required verification

- Backend: from `apps/backend`, run `ruff check app tests` and `pytest`.
- Frontend: from `apps/frontend`, run `npm run build`.
- Runtime/Compose changes: run `docker compose build` and inspect resolved configuration when practical.
- Tenant-data changes: add or run cross-tenant tests and review authorization before retrieval or AI processing.
- UI changes: verify relevant states and provide screenshots.
- Documentation changes: verify commands against scripts/configuration and check links and scope.

Report files changed, tests run, assumptions, and unresolved facts. Do not claim a check passed unless it was actually run.
