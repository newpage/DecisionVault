# DecisionVault 0.5.0-alpha.3 — Decision Workspace Foundation

Sprint 5.2.1 introduces the first unified Decision Workspace.

## Backend

- Tenant-safe `GET /api/v1/decisions/{decision_id}` workspace endpoint.
- Decision, business concept, related governed knowledge, readiness
  calculation, missing information, control areas, and audit activity in one
  response.
- Existing decision creation and status APIs preserved.
- No schema migration.

## Frontend

- Decision Center cards now open a dedicated workspace.
- Executive decision header with status management.
- Readiness, risk, confidence, and evidence scorecards.
- Owner, due date, location, business unit, and overdue indicators.
- Workspace tabs:
  - Overview
  - Evidence
  - Timeline
  - AI Analysis
  - Approvals
  - Reports
- Overview includes recommendation, decision question, score calculation,
  missing information, control areas, and decision profile.
- Evidence tab shows trust, approval, authority, and governed AI eligibility.
- Timeline tab shows permanent decision audit events.
- Future Release 0.5 areas are reserved without misleading placeholder data.

## Database

No database reset is required.
