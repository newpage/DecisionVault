# API documentation

The current FastAPI application exposes `/health` and mounts domain routers under `/api/v1` for authentication, workspaces, knowledge/ingestion, intelligence/decisions, dashboard data, and business concepts. FastAPI's generated OpenAPI document is available at runtime unless separately disabled.

Protected endpoints use `Authorization: Bearer <JWT>`. The authenticated session establishes tenant identity; clients must not be trusted to choose a tenant. Any endpoint documentation added here must describe authorization, tenant scope, request/response shape, errors, and side effects, and must be checked against the router and schema implementation.

The browser uses `NEXT_PUBLIC_API_URL`. Local and server values differ: the Linux Apache deployment uses `/api/v1`, while direct local access must match the backend host port actually selected by Compose.

