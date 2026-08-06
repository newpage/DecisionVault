# Extensibility and Decision Pack Model

## Intent

DecisionVault is industry-configurable without turning tenant configuration into arbitrary software execution. Shared capabilities remain platform-owned; domain language and governed variations are packaged as versioned **Decision Packs**.

A Decision Pack is installed configuration consumed by the modular monolith. It is not an independently deployed service, container, database, or network endpoint.

Example packs include merchant onboarding, fraud escalation, third-party risk, PCI compliance, AML/KYC review, cybersecurity exceptions, software validation, CAPA, change control, and supplier qualification. A regulated enterprise-payments archetype is illustrative only and does not imply an actual customer relationship or non-public knowledge.

## Pack contents

A pack manifest may declare:

- business-domain definitions and vocabulary;
- Decision Templates and versioned workflow definitions;
- evidence types, requirements, fitness/freshness rules, and readiness calculations;
- risk taxonomy, controls, policies, requirements, and mappings;
- approval roles, segregation rules, SLAs, escalation, and reassessment;
- prompt templates and approved AI use-case policies;
- report definitions, dashboard widgets, metrics, and explanation text;
- optional sample data explicitly marked non-production.

Executable Python, shell, SQL, arbitrary templates, provider credentials, and infrastructure changes are not pack content. New code-based extension points use reviewed platform releases/plugins with separate trust and deployment controls.

## Manifest and lifecycle

```yaml
pack_id: dv.third_party_risk
version: 1.2.0
platform_compatibility: ">=1.0 <2.0"
publisher: decisionvault
status: published
dependencies: []
artifacts:
  decision_templates: []
  evidence_requirements: []
  workflows: []
  risk_taxonomy: []
  controls: []
  requirements: []
  prompts: []
  reports: []
```

The actual schema is a **Target** design; this example is illustrative. Packs progress draft → validated → approved → published → deprecated → retired. Published artifacts are immutable and content-hashed/signed as assurance needs mature. Semantic versioning communicates compatibility, but each artifact also has its own stable ID and immutable version.

## Installation

Installation is a privileged, tenant-scoped, audited transaction/job:

1. Validate publisher/trust, manifest schema, platform compatibility, dependencies, uniqueness, security declarations, and artifact references.
2. Produce a dry-run impact report: additions, conflicts, required roles, provider/data use, migrations, and sample data.
3. Obtain required tenant/platform approvals.
4. Copy immutable pack artifacts into a registry and create a tenant installation record; do not share mutable tenant rows across tenants.
5. Activate explicitly, seed no sample data unless separately selected, and emit installation/audit events.

Failure leaves the previous active version intact. Installation never changes ports, Compose, secrets, authentication, or production code.

## Tenant customization

Customization uses controlled overlays, not edits to published pack artifacts. Allowed overlays may change display labels, assignments, SLAs within bounds, optional steps, thresholds/weights within governed ranges, report selection, and stricter evidence/approval rules. Core invariants, audit fields, tenant isolation, segregation minimums, protected regulatory mappings, and safe AI/provider policy cannot be relaxed.

Each override stores base artifact/version, changed fields, rationale, owner/approver, effective dates, validation result, and version. The resolved configuration is deterministic and snapshot-addressable. Excessive divergence signals that a new pack variant or platform capability is needed.

## Upgrade and compatibility

An upgrade compares installed and target manifests and classifies changes as additive, deprecating, behavioral, breaking, or data-affecting. The plan reports active Decisions pinned to older definitions, tenant overrides, removed roles/fields, score changes, prompt/model changes, and migration/rollback limits.

Running Decisions remain pinned unless an authorized migration maps state, requirements, snapshots, and approvals. New Decisions use the newly activated version. Historical snapshots retain old artifacts indefinitely under retention policy. Upgrade supports validate/dry-run, staged activation, idempotent execution, audit, and recovery to the prior active version when no irreversible data transformation occurred.

## Safe removal

A pack cannot be hard-deleted while referenced by decisions, evidence, approvals, snapshots, outcomes, reports, or audit records. Removal means deactivate for new use, resolve dependents, archive installation, and retain immutable referenced definitions. Tenant-created operational data remains tenant-owned. Optional sample data can be removed only through an explicit, previewed, reference-safe operation.

## Extension points and governance

| Extension | Configuration boundary | Required validation |
| --- | --- | --- |
| Decision template | Fields, evidence, workflow/approval/readiness references | Typed schema, lifecycle/role completeness, no invariant bypass. |
| Workflow | States, guarded transitions, assignments, timers | Reachability, terminal states, safe DSL, segregation and SLA checks. |
| Readiness/confidence rule | Named inputs, normalization, weights/bands, missing-data behavior | Weights/ranges, explainability, version owner, test vectors. |
| Prompt | Template and structured schema | Allowed data/provider, injection controls, citations, evaluation approval. |
| Report/widget | Approved query/metric IDs and layout | Tenant/security-aware data source, bounded load, accessible rendering. |
| Connector mapping | External schema to Enterprise Event | Credential binding, tenant mapping, idempotency, classification, replay. |

The platform registry owns schemas and validators. Pack publisher, domain owner, Risk/Compliance, Security/Privacy, Model Risk (for AI), and tenant administrator have explicit approval responsibilities proportional to content. Marketplace/distribution, third-party signing, licensing, and cross-tenant aggregate packs are **Future** choices, not current capabilities.

## Current mapping and transitional path

**Current.** Business Concepts, supplier-oriented Decision Case attributes, deterministic readiness logic, and seeded domain content demonstrate domain configuration needs but are code/schema-bound; no pack registry exists.

**Transitional.** First generalize the Decision aggregate and introduce immutable template/workflow/score definitions. Extract the existing supplier qualification scenario into an internal reference pack only after behavior and tests are preserved. A second contrasting pack should prove that the core has not merely renamed supplier fields.

Open questions include publisher trust/signing, localization, jurisdiction variants, dependency policy, tenant override limits, artifact migration language, licensing, pack evaluation datasets, and ownership of regulatory updates.
