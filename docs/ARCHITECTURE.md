# DecisionVault architecture

This document describes the repository at version `0.5.0-alpha.3`. It is descriptive, not a proposal.

## Governed Decision outcomes

Post-approval effectiveness remains inside the Decision Intelligence modular
monolith. `DecisionExpectedOutcome` retains versioned targets,
`DecisionOutcomeObservation` retains append-oriented actuals and independent
Membership verification, `DecisionEffectivenessAssessment` freezes deterministic
calculation details with the assessor's classification, and `DecisionLesson`
retains bounded Decision-specific learning. All relationships use tenant-aware
repository predicates and composite tenant foreign keys. No generic metrics,
time-series, project-management, or external analytics subsystem is introduced.

## System context

DecisionVault is a multi-tenant decision-intelligence application. Existing source repositories remain authoritative; uploaded source material is extracted into draft Knowledge Cards, reviewed as governed knowledge, retrieved for grounded answers, and retained as evidence for Decision Cases.

```text
Browser
  │ HTTPS
  ▼
Apache reverse proxy (Linux server; public entry point)
  ├── /api/* and /health ──► FastAPI backend
  └── /*                  ──► Next.js frontend
                                  │
             ┌────────────────────┼────────────────────┐
             ▼                    ▼                    ▼
      PostgreSQL + pgvector   shared storage      Ollama on host
             ▲                    ▲              (optional models)
             └──────── worker ────┘
```

## Runtime components

| Component | Current implementation | Responsibility |
| --- | --- | --- |
| `frontend` | Next.js 15, React 19, TypeScript | Browser UI and calls to `/api/v1` |
| `backend` | FastAPI, SQLAlchemy, Python 3.12 | Authentication, authorization, tenant-scoped domain APIs, schema creation, and seed data |
| `worker` | Python polling process | Claims queued ingestion jobs, extracts supported files, creates draft cards/chunks/evidence, and requests embeddings |
| `db` | PostgreSQL 16 image with pgvector | Relational system of record and 768-dimensional vector storage |
| storage volume | Docker named volume mounted at `/data/storage` | Uploaded source bytes shared by backend and worker |
| Ollama | Host service reached through `host.docker.internal` | Optional chat and embedding models; configured defaults are `llama3.2` and `nomic-embed-text` |

Docker Compose defines the four containers. Ollama and Apache are not Compose services in this repository.

## Domain and data flow

The ownership chain is `Tenant → Organization → Workspace`. Workspaces contain source documents, Knowledge Cards, and Decision Cases. Business Concepts organize knowledge and decisions. Audit Events retain material activity.

For ingestion, the backend stores an upload under a tenant-prefixed storage key and creates an `IngestionJob`. The worker locks a queued job, extracts PDF, DOCX, TXT, MD, CSV, or JSON content (OCR is intentionally absent), creates a draft Knowledge Card, chunks the text, attempts embeddings through Ollama, creates evidence and an audit event, then marks the job complete or failed.

Search and decision intelligence use tenant-scoped knowledge. Embeddings may be null when Ollama is unavailable; the repository describes lexical retrieval and deterministic grounded summaries as the fallback.

## Authentication and tenant isolation

Login accepts tenant slug, email, and password. Passwords are hashed with the configured `pwdlib` Argon2 implementation. FastAPI issues an HS256 JWT containing user, tenant, and revocable session identifiers. Every protected request resolves an active user, membership, and session, then derives roles and permissions.

Tenant isolation is application-enforced:

- tenant identity comes from the authenticated principal, never from an arbitrary request tenant ID;
- tenant-owned tables carry indexed `tenant_id` columns;
- repositories and API queries filter by `principal.tenant_id` before returning or ranking records;
- uploaded object keys are tenant-prefixed;
- classification and access-policy checks further constrain knowledge retrieval.

There is no confirmed PostgreSQL row-level-security policy in the repository. Every data-access change must therefore preserve explicit tenant predicates, including joins, caches, background processing, and not-found behavior. Cross-tenant identifiers should return the same response as absent identifiers.

## API and UI boundaries

FastAPI mounts application routers under `/api/v1`; `/health` is outside that prefix. The Next.js client reads `NEXT_PUBLIC_API_URL`, attaches the bearer token from browser local storage, and redirects to login on HTTP 401. See [API overview](api/README.md) and [UI notes](ui/README.md).

Decision Intelligence is a backend module under `app/modules/decisions`.
Its router translates HTTP requests, the application service coordinates
authorization and domain operations, the tenant-aware repository owns
persistence and evidence queries, and separate lifecycle and scoring modules
contain deterministic rules. Decision creation and lifecycle transitions write
their audit event in the same database transaction as the decision state.

Decision evidence distinguishes available governed Knowledge from explicitly
selected evidence. Selection validates the authenticated tenant, Decision
workspace, Business Concept, publication and approval state, membership
clearance, Knowledge access policy, and optional chunk ownership before copying
content and governance facts into an immutable `DecisionEvidence` snapshot.
Readiness and recommendations use active snapshots only. Removal retains the
snapshot and records actor, timestamp, and rationale; selection/removal,
recalculation, and audit events commit atomically.

Tenant-member discovery is owned by the focused `app/modules/members`
boundary. A `User` remains a global platform identity, while `Membership` is
the active, tenant-scoped identity used for governed reviewer assignment.
Candidate discovery filters the authenticated tenant before search and returns
only active members whose effective permissions, clearance, and access-policy
roles permit them to view the Decision and all active evidence. Review
assignment stores a tenant-composite membership reference, revalidates
eligibility when the command executes, and retains assignment/reassignment
history with its audit event in the same transaction.

## Deployment topology

Source changes are built, tested, reviewed, and committed on the Mac workstation, pushed to GitHub, then pulled and deployed on the Linux server. On the server, `scripts/dv` combines the base and server Compose files. Backend and frontend ports bind to `127.0.0.1` only; PostgreSQL and the worker have no published ports. Apache is the public HTTPS proxy.

Executable defaults are backend `127.0.0.1:8200` and frontend `127.0.0.1:3200`, overridable with `DV_BACKEND_PORT` and `DV_FRONTEND_PORT`. Container ports remain 8000 and 3000. The `/api/` Apache rule must precede the catch-all frontend rule.

## Current lifecycle constraints

The accepted pre-release policy permits breaking schema and API changes and assumes fresh databases between breaking releases. Startup currently creates the vector extension and tables directly with SQLAlchemy and seeds demo data; no migration framework was found. See [ADR-0001](adr/ADR-0001-pre-release-breaking-changes.md).
