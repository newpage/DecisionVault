# Linux Server Deployment

DecisionVault uses the base `docker-compose.yml` for development and
`docker-compose.server.yml` as the Linux server override.

The override:

- Publishes FastAPI only on `127.0.0.1:8200`.
- Publishes Next.js only on `127.0.0.1:3200` by default.
- Uses `/api/v1` as the browser API URL.
- Leaves PostgreSQL and the worker unavailable from the public network.
- Keeps Apache as the only public HTTPS entry point.

## Initial server setup

```bash
git clone https://github.com/newpage/DecisionVault.git
cd DecisionVault
cp .env.example .env
chmod +x scripts/server-*.sh
```

Set at least:

```env
NEXT_PUBLIC_API_URL=/api/v1
CORS_ORIGINS=https://decisionvault.discovera.ai
```

Keep the existing secure `JWT_SECRET`.

## Normal deployment

```bash
cd /path/to/DecisionVault
./scripts/server-deploy.sh
```

The command:

1. Refuses to overwrite uncommitted changes.
2. Fetches and fast-forwards `main`.
3. Rebuilds the containers.
4. Starts the complete stack.
5. Waits for backend and frontend health.
6. Prints logs automatically when deployment fails.

## Fresh database deployment

DecisionVault currently assumes a fresh database between breaking releases:

```bash
./scripts/server-deploy.sh --reset-db
```

This permanently deletes the DecisionVault PostgreSQL and storage volumes.

## Deploy with backend tests

```bash
./scripts/server-deploy.sh --test
```

## Status and logs

```bash
./scripts/server-status.sh
./scripts/server-logs.sh
./scripts/server-logs.sh 300
```

## Apache routing

Apache should route:

```apache
ProxyPass        /api/ http://127.0.0.1:8200/api/
ProxyPassReverse /api/ http://127.0.0.1:8200/api/

ProxyPass        /health http://127.0.0.1:8200/health
ProxyPassReverse /health http://127.0.0.1:8200/health

ProxyPass        / http://127.0.0.1:3200/
ProxyPassReverse / http://127.0.0.1:3200/
```

The `/api/` rules must appear before the `/` frontend rule.
