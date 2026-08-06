# Decision Workspace

The Decision Workspace is the tenant-scoped view for a single Decision Case at `/decisions/{id}`. It assembles decision metadata, status, readiness, risk, confidence, evidence, related business concepts, and audit history.

## Current behavior and boundaries

- The FastAPI intelligence routes load the Decision Case using both its ID and the authenticated principal's tenant ID.
- Invalid and foreign-tenant identifiers are intentionally indistinguishable and return not found.
- Evidence is drawn from tenant-owned Knowledge Cards and is constrained by user clearance.
- Status changes create audit events.
- Readiness and evidence summaries are stored on the Decision Case and presented by the workspace UI.

## Engineering checklist for changes

- Preserve tenant predicates on the decision, business concept, knowledge, evidence, and audit queries.
- Test a valid tenant-owned ID, a nonexistent ID, and another tenant's ID.
- Recalculate and display scores consistently; document any formula change.
- Preserve safe empty states for missing evidence and timeline entries.
- Verify responsive/collapsed navigation behavior and attach screenshots for UI changes.
- Run backend tests and the frontend production build.

The sprint-level manual checks currently maintained by the repository are in `QA.md`.

