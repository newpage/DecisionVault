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

## Outcomes and effectiveness

The Outcomes tab separates four governed records: an expected result, factual
append-oriented observations, a completed effectiveness assessment, and retained
lessons. Expected outcomes may be edited before approval. Approval freezes active
expectations; later corrections create a new revision with a rationale and retain
the approved revision. Observations are allowed only for conditionally approved,
approved, or already closed Decisions. The recorder's tenant Membership cannot
independently verify its own observation.

Numeric calculations use the latest verified observation and the explicit target
direction. Variance is `actual - target`; variance percentage is
`(actual - target) / abs(target) * 100` when target is non-zero. Range, boolean,
and milestone comparisons are deterministic. Qualitative outcomes require an
assessor judgment. Missing, unverified, or premature data is not success.

Decision aggregation is
`sum(weight of verified targets met) / sum(weight of verified assessable outcomes)`.
Any missing outcome makes the aggregate inconclusive, and a failed critical
outcome overrides weighted success. A completed assessment cannot claim met or
exceeded while required approval conditions remain open. Lessons remain scoped
to the Decision and are not promoted into Knowledge Cards.

The new outcome tables and permissions require a clean pre-release database
recreation under ADR-0001; there is no migration or compatibility adapter.

## Decision Memory

The Decision Memory tab discovers tenant-authorized historical Decisions in
`conditionally_approved`, `approved`, `rejected`, or `closed` state. It shows
similarity separately from approval and effectiveness so failed or rejected
precedents remain visible when structurally relevant. Filters support minimum
relevance and historical effectiveness, and pairwise comparison exposes shared
characteristics, differences, governed outcome facts, and lessons.

The `decision_similarity_v1` score is the normalized weighted sum of available
components: Business Concept 20%, structured context 10%, lexical title/question
overlap 20%, authorized evidence profile 20%, authorized governance pattern 10%,
authorized outcome profile 10%, authorized lesson-type overlap 5%, and recency
5%. Jaccard overlap is used for set and term factors. Recency declines linearly
to zero at five years. Thresholds are strongly relevant at 80, relevant at 60,
somewhat relevant at 40, and weakly relevant below 40.

When evidence, review, or outcome permission is absent, the component is not
queried or scored and remaining weights are renormalized. Evidence profiles use
immutable DecisionEvidence metadata and enforce snapshot classification and
access-policy roles in the query. V1 uses no Decision embeddings or AI summary.
Decision-level classification and access policy are also checked before a
historical row can enter candidate retrieval. These new Decision columns require
a clean pre-release database recreation under ADR-0001.

## Engineering checklist for changes

- Preserve tenant predicates on the decision, business concept, knowledge, evidence, and audit queries.
- Test a valid tenant-owned ID, a nonexistent ID, and another tenant's ID.
- Recalculate and display scores consistently; document any formula change.
- Preserve safe empty states for missing evidence and timeline entries.
- Verify responsive/collapsed navigation behavior and attach screenshots for UI changes.
- Run backend tests and the frontend production build.

The sprint-level manual checks currently maintained by the repository are in `QA.md`.
