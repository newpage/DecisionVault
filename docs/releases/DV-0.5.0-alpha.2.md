# DecisionVault 0.5.0-alpha.2 — Live Executive Intelligence

Sprint 5.1.1b upgrades the dashboard from a presentation layer into a live,
tenant-isolated executive analytics service.

## Backend

- Unified `/api/v1/dashboard` response.
- Decision status, risk, readiness, trend, and business-unit analytics.
- Deterministic executive briefing.
- Executive insights and actionable alerts.
- 30-second in-process tenant cache.
- Explicit `?refresh=true` cache bypass.
- No database migration.

## Frontend

- Eight live executive KPIs.
- Six-month decision trend.
- Risk, readiness, status, and business-unit visualizations.
- Executive insights and alert panels.
- Operating indicator summary.
- Automatic refresh every 60 seconds.
- Manual forced refresh.
- Existing collapsible sidebar support.

## Design Principle

The executive briefing is deterministic and auditable. It does not require an
LLM, and it never invents organizational conditions.
