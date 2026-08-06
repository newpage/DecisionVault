# ADR-001: Enterprise Decision Intelligence Platform

## Status

Proposed

## Date

2026-08-06

## Context

DecisionVault currently provides a pre-release multi-tenant foundation for governed Knowledge Cards, evidence, retrieval, Decision Cases, readiness scoring, audit, dashboard, and decision workspace experiences. Some current Decision Case attributes and demonstrations are supplier-specific. The product needs a durable architectural direction that supports regulated enterprises and multiple industries without presenting proposed capability as implemented or replacing a manageable system with premature distributed infrastructure.

Material enterprise decisions connect signals, evidence, organizational knowledge, risks, controls, policies, requirements, human approvals, AI assistance, execution, outcomes, and learning. Document management, ticketing, workflow, or generic chat alone cannot provide the necessary accountability and historical reconstruction.

The north star is:

> DecisionVault manages enterprise confidence through connected decisions, governed evidence, organizational knowledge, enterprise risks and controls, explainable AI, human accountability, and measurable outcomes.

## Decision

DecisionVault will evolve as **DecisionVault — The Enterprise Decision Intelligence Platform**.

The platform will:

1. Center the domain on explicit, tenant-scoped Decisions connected to governed Evidence, Knowledge Assets, Risks, Controls, Policies, Requirements, Regulations, Recommendations, Explanations, Approvals, Enterprise Events, Outcomes, Lessons, Relationships, Audit Events, AI Execution Records, and immutable/versioned Snapshots.
2. Retain a modular monolith as the preferred near-term architecture, with logical service/module boundaries and PostgreSQL as the primary system of record. Distribution requires evidence.
3. Preserve industry configurability through versioned Decision Packs containing validated templates, workflows, evidence requirements, risk/control/obligation mappings, scoring rules, prompts, reports, and dashboard configuration.
4. Use explicit domain persistence plus selected shared capabilities/interfaces and typed relationships; it will not adopt a universal-object/EAV model.
5. Make tenant isolation, object authorization, classification, durable audit, human accountability, transparent scoring, cited AI, outcome measurement, and decision-time reproducibility architectural invariants.
6. Use a PostgreSQL transactional outbox/inbox model before considering a distributed event broker, and PostgreSQL relationship structures before considering a graph database.
7. Preserve the Mac workstation → GitHub PR/CI → Linux deployment workflow, Compose/Apache topology, and `dv deploy`/`dv doctor` as Linux operations unless separately decided.

The modular monolith is the explicit near-term deployment architecture. Decision Packs are configuration packages consumed by it, not independently deployed services. Application-level tenant filtering remains mandatory if PostgreSQL RLS is later added as defense in depth. AI-disabled and deterministic modes remain supported platform operation.

This ADR establishes direction, not current implementation. The detailed blueprint labels **Current**, **Transitional**, **Target**, and **Future** capability.

## Rationale

A shared decision platform avoids rebuilding evidence, approval, audit, AI, security, and outcome mechanics for every domain. Explicit domain models preserve invariants and comprehensible data. Decision Packs allow regulated-industry variation without putting arbitrary code or infrastructure in configuration. A modular monolith matches current maturity/team operations and retains atomic transactions for cross-cutting decision facts. Human-reviewed, cited, versioned intelligence makes AI useful without assigning it accountability. Outcomes and snapshots make the platform an organizational memory rather than a point-in-time workflow.

## Alternatives considered

### Continue as a governed document/knowledge application

Rejected as the north star. Governed knowledge remains essential, but it does not by itself model accountability, risk/control alignment, execution, outcomes, or enterprise confidence.

### Build separate applications for each industry use case

Rejected as the default. It duplicates security, audit, evidence, workflow, AI, and analytics. Decision Packs provide bounded variation; truly distinct invariants may still justify a specialized module.

### Universal Enterprise Object / EAV platform

Rejected. It appears flexible but degrades relational integrity, validation, queryability, authorization review, migrations, and audit meaning. A shared interface and typed relationship table provide common behavior without erasing domains.

### Microservices, Kafka, and a graph database immediately

Rejected for the current stage. They add failure modes and operating cost without demonstrated scale or ownership need. Logical boundaries, outbox events, and PostgreSQL traversal retain an evolution path.

### AI-first autonomous decision maker

Rejected. It conflicts with human accountability, explainability, reproducibility, and regulated-enterprise risk management. AI remains bounded assistance.

## Consequences

Positive consequences include a coherent platform identity; reusable governed capabilities; clear domain ownership; safer multi-industry extensibility; traceable recommendations and scores; and a staged path that preserves current operations.

Costs include additional domain modeling and governance; immutable/versioned storage growth; workflow/configuration validation; migration and compatibility work; stronger authorization/evaluation testing; and organizational ownership for taxonomies, prompts, scoring, outcomes, and packs.

The current supplier qualification experience must eventually become a pack/reference scenario rather than remain embedded in the core. Current features keep their verified status until replaced through tested, documented increments.

## Risks

- Scope expansion may outpace product validation or team capacity.
- Configuration could become an unsafe programming language or obscure domain rules.
- Scores could create false precision or incentives to game inputs.
- Snapshots and audit retention may conflict with privacy/deletion requirements.
- AI/provider changes may prevent exact replay or create disclosure/model risk.
- Incomplete tenant/object authorization could expose sensitive relationships or aggregates.
- Premature abstraction could merely rename supplier-specific behavior.
- Regulatory mappings may be mistaken for legal advice or become stale.

Mitigations are staged delivery, explicit exit criteria, representative contrasting packs, schema/rule validation, named governance owners, threat/model-risk review, tenant isolation tests, transparent uncertainty, and separate ADRs for material infrastructure/security choices.

## Migration approach

1. Approve this direction and maintain the current-state architecture document.
2. **PR 1:** establish Alembic and verify a baseline migration path before substantial production schema expansion. Add no target entities.
3. **PR 2:** generalize the Decision application boundary through DTOs, a tenant-scoped service/repository, transition policy, and compatible adapters over current `DecisionCase` persistence. Do not preemptively create new domain tables.
4. **PR 3:** expand tenant-isolation and authorization tests, including foreign-ID non-disclosure, retrieval, caches, and transitions. Explicit application predicates remain mandatory with or without future RLS.
5. In later deliberate migrations, add explicit domain capabilities in thin vertical slices: Evidence; Risk/Control; Policy/Requirement; Workflow/Approval; Recommendation/Explanation/AI execution; Snapshot; Outcome/Relationship.
6. Extract the existing supplier scenario into a versioned internal Decision Pack and validate the core with a contrasting regulated-domain pack.
7. Add organizational memory and Enterprise Confidence only after versioned data and outcome quality support them.

Every increment remains deployable and follows the existing Mac → GitHub → Linux path. The current fresh-database policy remains governed by ADR-0001 until explicitly replaced; this ADR does not claim migrations or restore automation already exist.

Because there are currently no external customers, breaking internal changes are allowed under the pre-release policy, but each must be deliberate and coordinated across migrations or data reset decisions, backend, frontend, tests, documentation, and release review.

## Review triggers

Review this ADR when:

- external customers or contractual compatibility obligations exist;
- the first two Decision Packs reveal incompatible core invariants;
- regulatory, residency, retention, legal-hold, or assurance requirements materially change;
- measured scale or team ownership suggests service extraction, a broker, graph database, or external analytics system;
- RLS, federation, customer-managed keys, or break-glass architecture is selected;
- AI becomes consequential enough to change the human-accountability boundary;
- Enterprise Confidence or Digital Twin capability is proposed for production;
- the supported deployment topology or data migration/restore policy changes.

## Related decisions and documents

- [DecisionVault Platform Blueprint](../architecture/DECISIONVAULT-PLATFORM-BLUEPRINT.md)
- [Domain Model](../architecture/DOMAIN-MODEL.md)
- [Service Boundaries](../architecture/SERVICE-BOUNDARIES.md)
- [Event Model](../architecture/EVENT-MODEL.md)
- [Security and Tenancy](../architecture/SECURITY-AND-TENANCY.md)
- [AI Architecture](../architecture/AI-ARCHITECTURE.md)
- [Extensibility Model](../architecture/EXTENSIBILITY-MODEL.md)
- [Platform Capability Map](../roadmap/PLATFORM-CAPABILITY-MAP.md)
- [ADR-0001: Pre-release breaking changes](ADR-0001-pre-release-breaking-changes.md)
