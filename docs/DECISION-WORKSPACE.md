# Decision Workspace

The Decision Workspace is the tenant-scoped view for a single Decision Case at `/decisions/{id}`. It assembles decision metadata, status, readiness, risk, confidence, evidence, related business concepts, and audit history.

## Current behavior and boundaries

- The FastAPI intelligence routes load the Decision Case using both its ID and the authenticated principal's tenant ID.
- Invalid and foreign-tenant identifiers are intentionally indistinguishable and return not found.
- Evidence is drawn from tenant-owned Knowledge Cards and is constrained by user clearance.
- Decision status changes occur only through explicit review and approval
  actions and create audit events.
- Readiness and evidence summaries are stored on the Decision Case and presented by the workspace UI.

## Reviewer discovery and assignment

- `User` is a platform identity; tenant-scoped reviewer accountability is
  represented by `Membership`.
- Authorized managers discover candidates through
  `GET /api/v1/decisions/{decision_id}/reviewer-candidates` using bounded
  name, email, or organization search.
- Results contain business-safe identity and role labels only. Inactive,
  foreign-tenant, permission-ineligible, under-cleared, and evidence-policy
  ineligible members are excluded.
- Assignment accepts a membership identifier, controlled review type, and
  rationale. Eligibility is revalidated and never trusted from a prior search.
- A Decision may have multiple reviews and one member may hold different review
  types. Duplicate active member/type assignments are rejected.
- Final self-review by the Decision creator and approval by the final reviewer
  are prohibited. Reassignment is allowed only before work starts, requires a
  rationale, and preserves prior assignment history.
- These membership and review constraint changes require a clean pre-release
  database recreation under ADR-0001. No migration or compatibility adapter is
  provided.

## Engineering checklist for changes

- Preserve tenant predicates on the decision, business concept, knowledge, evidence, and audit queries.
- Test a valid tenant-owned ID, a nonexistent ID, and another tenant's ID.
- Recalculate and display scores consistently; document any formula change.
- Preserve safe empty states for missing evidence and timeline entries.
- Verify responsive/collapsed navigation behavior and attach screenshots for UI changes.
- Run backend tests and the frontend production build.

The sprint-level manual checks currently maintained by the repository are in `QA.md`.
