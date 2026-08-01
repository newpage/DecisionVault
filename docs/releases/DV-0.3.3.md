# DecisionVault 0.3.3 — Transparent Decision Intelligence

## Delivered

- Explainable Decision Readiness score.
- Clickable metric explanations.
- Weighted score-factor breakdown.
- Knowledge-gap and governance findings.
- Detection for pending approval, low trust, stale knowledge, and AI restrictions.
- Recommended action for every finding.
- Unit tests for scoring and detection rules.

## Decision Readiness formula

The score is calculated from existing governed business data:

- Approved knowledge: 40 points
- Trust score at or above 80%: 30 points
- Knowledge created in the last 180 days: 20 points
- Knowledge permitted for governed AI use: 10 points

No language model is used to calculate this score.

## Database

No schema changes. A database reset is not required.
