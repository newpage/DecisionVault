# API documentation

The current FastAPI application exposes `/health` and mounts domain routers under `/api/v1` for authentication, workspaces, knowledge/ingestion, intelligence/decisions, dashboard data, and business concepts. FastAPI's generated OpenAPI document is available at runtime unless separately disabled.

Protected endpoints use `Authorization: Bearer <JWT>`. The authenticated session establishes tenant identity; clients must not be trusted to choose a tenant. Any endpoint documentation added here must describe authorization, tenant scope, request/response shape, errors, and side effects, and must be checked against the router and schema implementation.

The browser uses `NEXT_PUBLIC_API_URL`. Local and server values differ: the Linux Apache deployment uses `/api/v1`, while direct local access must match the backend host port actually selected by Compose.

## Decision Intelligence

Decision endpoints require explicit permissions in addition to authentication:
`decision.view` for list/workspace reads, `decision.create` for creation, and
review and approval permissions for lifecycle changes. Tenant-owned workspace, Business
Concept, Decision, and Knowledge Card identifiers are resolved within the
authenticated tenant; absent and foreign-tenant references both return 404.
Decision permissions are seed data; startup seeding does not backfill an
existing populated database.

The generic Decision status mutation endpoint is not exposed. Review and
approval lifecycle changes use explicit assignment, submission, review,
finding, return, approval, conditional-approval, rejection, and condition
endpoints. Decision creation returns 201.

The supported lifecycle is:

```text
draft -> evidence_collection -> in_review
in_review -> conditionally_approved | approved | rejected
conditionally_approved -> approved | rejected | closed
approved | rejected -> closed
```

### Reviewer candidates and membership identity

```text
GET   /decisions/{decision_id}/reviewer-candidates
POST  /decisions/{decision_id}/reviews
PATCH /decisions/{decision_id}/reviews/{review_id}/assignment
```

Candidate discovery requires `decision.view`, `decision.evidence.view`, and
`decision.review.assign`. It accepts `responsibility=decision_reviewer`, a
bounded case-insensitive `query`, `offset`, and `limit` (maximum 50). Results
contain membership ID, display name, email, organization, relevant role labels,
and responsibility; authentication and unrelated role metadata are never
returned.

Assignments use tenant membership rather than a global user ID. Initial
assignment requires membership ID, review type, and rationale. Reassignment
requires membership ID and rationale and is rejected after review work starts.
The backend revalidates active membership/user status, effective Decision and
evidence permissions, clearance, access-policy roles, tenant ownership, and
separation of duties for every assignment command. Foreign membership and
Decision identifiers are non-disclosing.

Directory and review-assignment permissions currently seeded for the tenant
administrator are `decision.review.view`, `decision.review.assign`,
`decision.review.perform`, and `decision.review.manage`; decision authority is
separate through `decision.approve`, `decision.conditionally_approve`,
`decision.reject`, and `decision.return_for_changes`.

### Governed Decision evidence

Evidence endpoints require `decision.evidence.view`,
`decision.evidence.select`, `decision.evidence.remove`, or
`decision.evidence.history` as appropriate:

```text
GET    /decisions/{decision_id}/available-evidence
GET    /decisions/{decision_id}/evidence
GET    /decisions/{decision_id}/evidence/history
POST   /decisions/{decision_id}/evidence
DELETE /decisions/{decision_id}/evidence/{evidence_id}
```

Selection accepts a Knowledge Card ID, optional chunk ID, controlled
relationship (`supporting`, `opposing`, `contextual`, `risk`, or `constraint`),
and required rationale. Removal requires a rationale and retains the immutable
snapshot in history. Both mutation responses include the recalculated Decision
and affected evidence snapshot.

This change replaces the former reference-and-score `decision_evidence` table
with explicit snapshot and removal fields and adds database constraints. It is
a breaking pre-release schema change and requires a complete database refresh;
no migration or compatibility adapter exists.

### Governed outcomes and effectiveness

Outcome reads require `decision.outcome.view`. Mutations use
`decision.outcome.define`, `decision.outcome.record`, `decision.outcome.verify`,
`decision.outcome.assess`, and `decision.lesson.record` as appropriate:

```text
GET   /decisions/{decision_id}/effectiveness
POST  /decisions/{decision_id}/outcomes
PATCH /decisions/{decision_id}/outcomes/{outcome_id}
POST  /decisions/{decision_id}/outcomes/{outcome_id}/observations
POST  /decisions/{decision_id}/outcomes/{outcome_id}/observations/{observation_id}/verify
POST  /decisions/{decision_id}/outcomes/{outcome_id}/observations/{observation_id}/supersede
POST  /decisions/{decision_id}/effectiveness-assessments
POST  /decisions/{decision_id}/effectiveness-assessments/{assessment_id}/complete
POST  /decisions/{decision_id}/lessons
```

Expected outcomes use controlled measurement and direction values. Approval
freezes their accountable fields; `PATCH` after approval requires an amendment
rationale and returns a new active revision. Observations are append-oriented,
retain controlled provenance, and are excluded from authoritative calculations
until independently verified by another active tenant Membership. Governed
actions return 409 when the Decision lifecycle or separation-of-duties rule is
invalid. Foreign tenant Decision, outcome, observation, assessment, membership,
and related-record IDs return non-disclosing 404 responses.

Effectiveness responses include individual calculation explanations, verification
state, deterministic weighted aggregation, open approval conditions, assessments,
and lessons. Missing data is inconclusive; failed critical outcomes override
weighted success. These tables are a breaking clean-schema change and require a
pre-release database reset; no migration is supplied.
