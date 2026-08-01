# DV-0002A — Sprint 2, RUP-2.2

## Purpose

Replace the Knowledge scaffold with a working bounded context while preserving
the current HTTP endpoints and frontend behavior.

## Changes

- Implemented tenant-aware `KnowledgeRepository`.
- Implemented `KnowledgeService` for listing, upload queueing, submission, and approval.
- Moved Knowledge HTTP handling into `app.modules.knowledge.router`.
- Preserved `app.api.knowledge.router` as a compatibility import.
- Added a typed upload response and Knowledge module health endpoint.
- Added service-level tests for governance and validation behavior.

## API Compatibility

The following routes are unchanged:

- `GET /api/v1/knowledge`
- `POST /api/v1/sources/upload`
- `GET /api/v1/ingestion/jobs`
- `POST /api/v1/knowledge/{card_id}/submit`
- `POST /api/v1/knowledge/{card_id}/approve`

New diagnostic route:

- `GET /api/v1/knowledge/module/health`

## Database

No schema changes. Use the existing fresh-database process.

## Commit

```bash
git add .
git commit -m "DV-0002A RUP-2.2 implement Knowledge bounded context"
```
