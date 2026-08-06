# Engineering roadmap

This roadmap records direction without promising dates or silently changing the current architecture. Release-specific history lives in `docs/releases/` and architectural commitments live in `docs/adr/`.

## Now: make the foundation repeatable

- Keep Mac build/test/commit and Linux deploy/diagnose procedures current.
- Maintain CI parity for backend lint/tests, frontend build, and container builds.
- Require tenant-isolation and security review on every relevant pull request.
- Consolidate architecture, API, UI, release, and operational documentation.

## Next: harden pre-release engineering

- Define and test a complete cross-tenant access matrix.
- Decide and record a database migration and rollback strategy before ending the fresh-database policy.
- Add focused API-contract documentation and automated contract coverage.
- Establish dependency, secret, backup-restore, and disaster-recovery verification routines.
- Add worker reliability coverage for retries, duplicate work, and Ollama outages.

## Later: production-readiness decisions

- Define observability, retention, capacity, and recovery objectives.
- Review authentication, session storage, browser token handling, and authorization against the intended threat model.
- Validate Apache/TLS hardening and localhost-only publishing in the target server environment.
- Define release promotion, compatibility, and support policies.

Product features and delivery dates require separate prioritization. See [roadmap working agreement](roadmap/README.md).

