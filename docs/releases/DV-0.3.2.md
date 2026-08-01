# DecisionVault 0.3.2 — Business Concept Workspace

## Added

- Tenant-aware Business Concept workspace endpoint.
- Calculated Knowledge Card, readiness, health, and relationship metrics.
- Curated Decision Intelligence summary with confidence.
- Connected Knowledge list.
- Recent audit activity.
- Related Business Concepts.
- Reusable workspace UI components.
- Click-through navigation from Business Concept cards.

## API

`GET /api/v1/business-concepts/{concept_id}`

## Database

No schema changes beyond Release 0.3.1. A database reset is not required when
upgrading from the successfully deployed Business Concepts release.

## Metric definitions

- **Knowledge Cards:** Count of cards connected to the Business Concept.
- **Decision Readiness:** Percentage of connected cards that are approved.
- **Knowledge Health:** Percentage of connected cards with trust score >= 0.80.
- **Related Concepts:** Number of related concepts returned by the service.

Every metric includes a `source` field. This release returns calculated metrics,
not invented AI scores.
