# DecisionVault 0.3.4 — Developer & Operations Experience

Adds the repository-managed `dv` CLI, doctor checks, improved status/logs,
database and storage backup, redacted diagnostic bundles, release metadata,
and post-deployment verification.

## Install

```bash
sudo rm -f /usr/local/bin/dv
./scripts/install-dv-cli.sh
```

## Commands

```bash
dv doctor
dv status
dv update
dv deploy
dv logs backend
dv backup
dv diag
dv version
```

## Security

Diagnostic bundles redact secrets, passwords, tokens, keys, and database URLs.
Review a bundle before sharing it outside the organization.
