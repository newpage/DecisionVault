# Coding standards

## General rules

- Keep changes small, reviewable, and scoped to one purpose.
- Preserve current service boundaries and avoid unrelated formatting or generated artifacts.
- Never commit `.env`, credentials, tokens, database dumps, diagnostic bundles, or uploaded data.
- Update documentation when commands, configuration, APIs, architecture, or operational behavior changes.
- Treat tenant isolation and authorization as correctness requirements, not optional hardening.

## Python and FastAPI

- Target Python 3.12 and keep code compatible with the pinned dependencies in `apps/backend/requirements.txt`.
- Run `ruff check app tests` and `pytest` from `apps/backend`.
- Obtain tenant identity through `Principal`; do not accept a caller-selected tenant as authority.
- Put `tenant_id` predicates on every read, update, delete, join, aggregate, cache key, and background-job lookup involving tenant data.
- Return not found for absent and foreign-tenant resources without revealing which case occurred.
- Validate at API boundaries and keep domain operations in services/repositories where those layers already exist.
- Add tests for success, authorization failure, invalid input, and cross-tenant access.

## TypeScript and Next.js

- Target the versions in `apps/frontend/package.json` and keep TypeScript checks clean through `npm run build`.
- Use the shared API helper for authenticated calls and do not hard-code deployment origins.
- Keep server-only secrets out of `NEXT_PUBLIC_*` variables and client bundles.
- Preserve accessible semantics, keyboard operation, useful empty/error/loading states, and responsive layouts.
- Include before/after screenshots with pull requests that change UI appearance.

## Database and worker

- Keep tenant-owned rows explicitly keyed by `tenant_id` and indexed when queried by tenant.
- Ensure worker-created records inherit tenant identity from the claimed tenant-owned source/job.
- Keep job processing idempotence and failure states in mind; never process one tenant's storage key for another tenant.
- pgvector embeddings are 768 dimensions in the current model. Coordinate any dimensional change with data lifecycle and Ollama model changes.
- Until a migration strategy replaces ADR-0001, document whether a change requires a fresh database.

## Shell, Compose, and operations

- Shell scripts use Bash strict mode where practical, quote expansions, and resolve paths relative to the repository.
- Keep public service publishing localhost-only. Do not publish PostgreSQL or the worker.
- Keep Mac development commands separate from Linux `dv` operations.
- Changes to ports, Apache paths, volumes, secrets, or Compose networking require explicit architectural and operational review.

## Commits and reviews

Use imperative, focused commit subjects. Before committing on the Mac, inspect `git status` and `git diff`, run the relevant tests/builds, and ensure generated or secret files are absent. A review must explicitly cover tenant isolation and security for data, auth, ingestion, retrieval, caching, and operational changes.

