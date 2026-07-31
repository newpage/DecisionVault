# New Foundation Release Notes

This is a complete replacement codebase, not an upgrade.

## Included
- Fresh tenant and organization model
- Revocable sessions and tenant-aware JWTs
- Normalized roles, permissions, and access policies
- Knowledge Cards as the canonical knowledge object
- Source documents as evidence, not managed content
- Asynchronous extraction worker with no OCR and no MinIO
- Governed review and publication
- Tenant- and policy-filtered hybrid search
- Ollama-grounded answers and retained decision evidence
- Investor-ready Next.js experience

## Required start
```bash
cp .env.example .env
docker compose down -v
docker compose up --build
```
