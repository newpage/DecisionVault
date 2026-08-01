# DV-0002A — RUP-2.3 Linux Deployment Automation

## Added

- `docker-compose.server.yml`
- `scripts/server-deploy.sh`
- `scripts/server-status.sh`
- `scripts/server-logs.sh`
- Linux deployment documentation

## Behavior

The normal deployment is now:

```bash
./scripts/server-deploy.sh
```

A breaking fresh-database deployment is:

```bash
./scripts/server-deploy.sh --reset-db
```

## Network security

The server override binds the backend and frontend to `127.0.0.1`, keeping
ports 8200 and 3000 inaccessible from the public network. Apache remains the
only public entry point.

## Database

No schema changes.
