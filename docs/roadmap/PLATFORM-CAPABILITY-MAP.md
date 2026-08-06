# Platform Capability Map

This roadmap separates verified capability from proposed evolution. **Target** is direction, not a delivery promise; **Future** requires its own evidence and decisions.

## Capability map

| Capability | Current | Transitional | Target / Future |
| --- | --- | --- | --- |
| Executive experiences | Tenant dashboard, metrics, alerts, trends, Executive Briefing components. | Versioned metric definitions, secure projections, drill-down. | Portfolio Enterprise Confidence and outcomes with transparent lineage (**Target**). |
| Domain applications | Business Concepts and supplier-qualification-oriented Decision Cases. | Generic Business Domain and Decision Template; internal reference pack. | Versioned industry Decision Packs and controlled tenant overlays (**Target**). |
| Decisions | Cases, statuses, recommendation text, transparent readiness, Decision Workspace. | Decision aggregate/service, optimistic version, validated commands, snapshots. | Configurable full lifecycle, reassessment, outcomes, Decision DNA (**Target**). |
| Evidence | Source provenance, Knowledge Evidence, retained Decision Evidence IDs/scores. | Explicit governed Evidence lifecycle and exact version references. | Assertions, fitness, conflicts, expiration, immutable decision-time manifests (**Target**). |
| Knowledge | Governed Knowledge Cards, review/publication, chunks, classification, access policy, AI eligibility. | Immutable versions, applicability/freshness, indexing contracts. | Organizational learning and governed lessons (**Target**). |
| Risk/control | Decision risk level and named control areas in calculation detail. | Explicit Risk, Control, effectiveness, test and exception models. | Traceability from obligations through outcomes (**Target**). |
| Policy/requirements | Access policies only; no business-policy model. | Versioned Policy, Regulation metadata, Requirement and mappings. | Applicability automation and regulatory-change decisions (**Target**). |
| Workflow/approval | Literal decision statuses; knowledge submit/approve permission. | Versioned workflow definitions, transition service, approval facts. | SLA, escalation, delegation, reassignment, periodic review (**Target**). |
| Enterprise events | Audit events and polling ingestion jobs. | Enterprise Event, inbox/outbox, idempotent consumers. | Governed external connectors; broker only if justified (**Target/Future**). |
| Relationships | Explicit foreign keys and Business Concept associations. | Typed tenant-scoped relationship table. | Authorized temporal graph traversal; dedicated graph DB conditional (**Target/Future**). |
| AI/retrieval | Ollama embeddings/generation, hybrid retrieval, citations, deterministic fallback. | Provider port, registries, structured outputs, execution record, evaluations. | Approved provider adapters and reproducible recommendations (**Target**). |
| Outcomes/learning | Not implemented. | Outcome schema and manual governed lessons. | Similar decisions, outcome analytics, evaluated improvement loop (**Target**). |
| Historical reconstruction | Audit timeline and mutable record references. | Immutable versions and sealed Decision Snapshot. | Enterprise Time Machine with effective-time reconstruction (**Target**). |
| Analytics | Direct SQL dashboard and tenant-keyed in-memory cache. | Versioned definitions, security-aware projections/background rollups. | Advanced outcome/confidence analytics; external warehouse conditional (**Target/Future**). |
| Security/tenancy | Principal-derived tenant, explicit predicates, roles/permissions, clearance/access policy, revocable sessions. | Authorization matrix/helpers, isolation suite, service identity, RLS pilot. | Federation/MFA, governed break-glass, RLS expansion if validated (**Target**). |
| API/platform | `/api/v1`, FastAPI schemas, ingestion jobs. | DTO/error/pagination/idempotency/concurrency/correlation standards. | Stable integration contracts under declared compatibility policy (**Target**). |
| Operations | Compose, Apache HTTPS, localhost publishing, `dv` Linux operations, Mac→GitHub→Linux flow. | Alembic, restore drills, structured telemetry and playbooks. | Availability/recovery objectives based on customer needs (**Target**). |

## Phase 1 — Existing Foundation

**State:** **Current**

- Business value: governed organizational knowledge, tenant-aware retrieval, accountable human review, basic decisions/readiness, executive and workspace views.
- Technical foundation: FastAPI, Next.js, PostgreSQL/pgvector, worker, optional Ollama, Compose, Apache, `dv` operations.
- Key risks: pre-release fresh-database policy, supplier-specific core fields, application-only isolation, partial service boundaries, limited historical/AI reconstruction.
- Exit criteria: current behavior, deployment path, limitations, and tenant controls accurately documented; baseline checks remain green.

## Phase 2 — Architecture Stabilization

**State:** **Transitional**

- Business value: lower change risk and a stable base for multiple industries.
- Work, in order: Alembic foundation; Decision/Knowledge module boundaries and explicit DTO/errors; generic Decision application boundary over current persistence; authorization matrix and cross-tenant suite; then aggregate versions, durable jobs, audit contract, transactional outbox, and normalized configuration registries through migrations.
- Prerequisites: approved domain terminology and current behavior characterization.
- Key risks: horizontal refactor without user value, breaking seeded/demo UI, incomplete migration/rollback, authorization regressions.
- Exit criteria: migrations build a database from zero and upgrade supported baselines; two contrasting decision scenarios fit the generic model; commands enforce authorization/concurrency; outbox and isolation tests pass; deployability preserved.

## Phase 3 — Enterprise Decision Intelligence

**State:** **Target**

- Business value: repeatable, explainable, governed decisions across domains.
- Work: Business Domains/Templates; governed Evidence; Risk/Control; Policy/Requirement/Regulation; Workflow/Approval; structured Recommendation/Explanation; AI execution records; first versioned Decision Pack.
- Prerequisites: Phase 2 contracts, governance owners, reference scenario and threat model.
- Key risks: over-configuration, false explainability, uncontrolled regulatory content, role/segregation complexity.
- Exit criteria: one material decision completes signal-to-approval with citations, exact versions, controls/requirements, human accountability, audit, AI-disabled mode, and tenant isolation; second pack validates extensibility.

## Phase 4 — Organizational Memory

**State:** **Target**

- Business value: reconstruct prior decisions and improve future work from governed outcomes.
- Work: Outcomes, Lessons Learned, similar-decision retrieval, immutable snapshots, effective dates, relationship model, Enterprise Time Machine.
- Prerequisites: retention/legal-hold decisions, stable version identities, representative outcome data.
- Key risks: hindsight bias, unauthorized similarity, storage growth, inability to replay hosted models exactly.
- Exit criteria: a historical decision is reconstructed from sealed inputs/configuration/execution/approvals; outcomes propose but cannot silently publish learning; access controls hold across traversals.

## Phase 5 — Enterprise Confidence

**State:** **Target**

- Business value: executives see where confidence is strong, weak, stale, or unmeasurable and can act on causes.
- Work: governed Decision DNA, scoped Enterprise Confidence, data-quality indicators, drill-down, trends, outcome/control analytics, security-aware projections.
- Prerequisites: sufficient outcome history, score governance and validation, stable metric definitions.
- Key risks: false precision, incentivized metric gaming, incomparable portfolios, restricted-data leakage through aggregates.
- Exit criteria: each displayed value exposes formula/version/input lineage/missingness; model changes preserve history; governance approves comparison scope; users can reach actionable causes.

## Phase 6 — Enterprise Digital Twin

**State:** **Future, conditional**

- Potential value: governed scenario analysis across interconnected decisions, risks, controls, capabilities, and outcomes.
- Preconditions: proven relationship workloads, mature temporal data, outcome coverage, model validation, scenario governance, scale/availability needs, accountable operating model.
- Key risks: false causal claims, automation bias, security inference, high model risk, operational complexity and cost.
- Exit criteria to begin—not to ship: separate ADR/business case, validated user decisions, benchmark data, threat/model-risk assessment, and evidence that simpler analytics/graphs are insufficient.

## Cross-phase quality gates

Every increment keeps the supported Mac → GitHub PR/CI → Linux `dv deploy`/`dv doctor` path, explicit tenant filtering, auth/classification/access policies, safe AI fallback, deployable Compose topology, and current pre-release data policy until a replacement ADR is accepted. No phase implies Kubernetes, Kafka, microservices, or a graph database.

## First three implementation PRs

1. **PR 1 — Alembic migration foundation.** Add migration tooling, establish and document the baseline for the current pre-release schema, verify clean-database creation, and define migration test and recovery expectations. This PR adds no target domain entities.
2. **PR 2 — Generic Decision application boundary.** Add Decision request/response DTOs, a tenant-scoped repository, application service, transition policy, and compatibility adapter around current `DecisionCase` persistence. It must not create new Decision or target-domain tables. Any unavoidable schema change uses Alembic and stays narrowly scoped.
3. **PR 3 — Tenant isolation and authorization test expansion.** Add comprehensive cross-tenant, foreign-ID non-disclosure, role/permission, object-authorization, retrieval, cache, and transition tests for the boundary. Explicit application tenant filtering remains required even if RLS is later piloted.

Substantial production schema expansion begins only after these foundations are reviewed. Decision Packs remain versioned configuration packages consumed by the modular monolith, not independently deployed services.
