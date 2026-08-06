## Summary

Describe the problem, solution, scope, and any known limitations.

## Validation

- [ ] Backend lint and applicable tests pass (`ruff check app tests`, `pytest`)
- [ ] Frontend production build passes (`npm run build`)
- [ ] Container build passes (`docker compose build`) when Docker/runtime files are affected
- [ ] Additional manual or automated checks are documented below

## Review checklist

- [ ] Tenant isolation was reviewed, including reads, writes, joins, caches, worker jobs, storage, retrieval, and not-found behavior
- [ ] Authentication, authorization, secrets, input handling, logging, and dependency/security impact were reviewed
- [ ] Documentation, ADRs, API notes, runbooks, and release notes were updated where needed
- [ ] UI changes include before/after screenshots, or this PR does not change UI
- [ ] No unrelated production behavior, generated files, credentials, or local data are included
- [ ] Database reset, compatibility, deploy, and rollback implications are stated below

## Operational impact

Database/data impact:

Deploy/rollback notes:

## Screenshots

Required for UI changes; otherwise write “Not applicable.”

