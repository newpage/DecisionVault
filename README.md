# DecisionVault

## Trusted Decision Intelligence

Make faster, smarter, and more confident decisions with knowledge you can trust.

This repository is a **brand-new, pre-release DecisionVault foundation**. It intentionally provides no backward compatibility and assumes a complete database refresh for each build until that policy is changed.

## Architectural center

DecisionVault does not manage customer documents. Existing repositories remain authoritative. DecisionVault connects information to governed **Knowledge Cards**, evidence, approvals, and decisions.

```text
Source Information → Ingestion → Draft Knowledge Card → Human Review → Published Knowledge → Decision Intelligence
```

### Services

- `frontend`: Next.js investor/customer experience
- `backend`: FastAPI API and domain services
- `worker`: asynchronous document extraction and Knowledge Card generation
- `db`: PostgreSQL with pgvector
- `storage`: local Docker volume; no MinIO and no OCR

## Run

```bash
cp .env.example .env
# Edit JWT_SECRET before use
# Set CORS_ORIGINS=http://localhost:3200
# Set NEXT_PUBLIC_API_URL=http://localhost:8200/api/v1
docker compose down -v
docker compose up --build
```

Open `http://localhost:3200`.

For the local demo login, use the `DEMO_TENANT_SLUG`, `DEMO_EMAIL`, and
`DEMO_PASSWORD` values configured in your uncommitted `.env` file.

Required Ollama models:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

Ollama is optional. Search and deterministic grounded summaries continue to work when it is unavailable.

## Product areas included

- Tenant and organization foundation
- Authentication and revocable sessions
- Workspace management
- Source upload and asynchronous ingestion
- PDF/DOCX/TXT/MD/CSV/JSON extraction without OCR
- Knowledge Cards as the canonical knowledge object
- Governance review and publication
- Hybrid lexical/vector retrieval
- Grounded Ask DecisionVault answers with citations
- Decision Cases with retained evidence
- Audit timeline and dashboard

## Development policy

See `docs/adr/ADR-0001-pre-release-breaking-changes.md`.

## Platform architecture

The current implementation is described in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The proposed evolution toward **DecisionVault — The Enterprise Decision Intelligence Platform** is documented in the [DecisionVault Platform Blueprint](docs/architecture/DECISIONVAULT-PLATFORM-BLUEPRINT.md); proposed capabilities there are not current product behavior.
