# DecisionVault 0.3.4.2 — Ollama Doctor Check Patch

## Fixed

- `dv doctor` now checks Ollama from the Linux host using
  `http://127.0.0.1:11434` by default.
- Container-facing `OLLAMA_URL` remains unchanged and may continue using
  `http://host.docker.internal:11434`.
- Added optional `DV_OLLAMA_HEALTH_URL` support for custom host-side health
  checks.

## Recommended environment

```env
OLLAMA_URL=http://host.docker.internal:11434
DV_OLLAMA_HEALTH_URL=http://127.0.0.1:11434
```

`DV_OLLAMA_HEALTH_URL` is optional because the default is already
`http://127.0.0.1:11434`.

## Database

No database changes.
