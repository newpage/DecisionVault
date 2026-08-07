# Global Payments demo through Apache HTTPS

This runbook exposes the isolated `decisionvault-payments-demo` Compose project
through `https://decisionvault.discovera.ai`. It does not deploy the code or
modify Apache by itself. The normal `decisionvault` Compose project and its
volumes are separate and must not be stopped or reset during this procedure.

## Compose model

The server command merges, in order:

1. `docker-compose.yml`
2. `compose.demo.yml`
3. `compose.demo.server.yml`

The final override changes the browser API base to `/api/v1` and backend CORS to
`https://decisionvault.discovera.ai`. The frontend and backend remain published
only on Linux loopback ports `3400` and `8400`. PostgreSQL and the worker have no
published ports. The Compose project remains `decisionvault-payments-demo`, so
its named database and storage volumes remain isolated from normal DecisionVault.

## Safe server start or restart

After the authorized release has been pulled onto the Linux server:

```bash
./scripts/demo-payments-server.sh start
```

For a later idempotent rebuild/restart:

```bash
./scripts/demo-payments-server.sh restart
```

`start` uses `docker compose up --build -d`; `restart` adds
`--force-recreate`. Both preserve named volumes and intentionally do not run
`down`, `--volumes`, `-v`, `--remove-orphans`, or the localhost reset workflow.

## Apache vhost change

Before editing, save the active vhost so rollback restores the exact prior
configuration. Adjust the source path to the server's enabled vhost filename:

```bash
sudo cp -a /etc/apache2/sites-enabled/decisionvault.conf \
  /etc/apache2/sites-enabled/decisionvault.conf.before-payments-demo
```

Inside the existing `*:443` vhost for `decisionvault.discovera.ai`, replace only
the current DecisionVault proxy upstream block with the following rules. Order
is mandatory: `/api/` and `/health` precede the frontend catch-all.

```apache
ProxyPreserveHost On

ProxyPass        /api/ http://127.0.0.1:8400/api/
ProxyPassReverse /api/ http://127.0.0.1:8400/api/

ProxyPass        /health http://127.0.0.1:8400/health
ProxyPassReverse /health http://127.0.0.1:8400/health

ProxyPass        / http://127.0.0.1:3400/
ProxyPassReverse / http://127.0.0.1:3400/
```

Do not change TLS certificates, redirects, security headers, logging, or any
other vhost directive. Validate before an explicitly authorized reload:

```bash
sudo apachectl configtest
sudo systemctl reload apache2
```

## Validation after authorized Apache reload

Local upstream checks:

```bash
curl --fail http://127.0.0.1:8400/health
curl --fail http://127.0.0.1:3400/
curl --fail \
  -H 'Origin: https://decisionvault.discovera.ai' \
  -H 'Access-Control-Request-Method: POST' \
  -X OPTIONS \
  -D - \
  http://127.0.0.1:8400/api/v1/auth/login
```

Public routing and login checks:

```bash
curl --fail https://decisionvault.discovera.ai/health
curl --fail https://decisionvault.discovera.ai/
curl --fail \
  -H 'Content-Type: application/json' \
  --data '{"tenant":"global-payments","email":"presenter@globalpayments.demo","password":"DecisionVault!"}' \
  https://decisionvault.discovera.ai/api/v1/auth/login
```

In a private browser window at presentation resolution, run the complete script
from `docs/DEMO-GLOBAL-PAYMENTS.md`. Confirm the Knowledge Cards, governed
evidence, grounded recommendation, Memory, and Learning states, then verify the
browser console has no warnings or errors. Repeat the restricted CipherPay
direct-URL check with `analyst@globalpayments.demo` and confirm the
non-disclosing `Decision not found` response.

## Rollback to normal DecisionVault

Rollback changes Apache first, then optionally stop the isolated demo. Do not
delete either application's volumes.

Exact normal upstream rules are:

```apache
ProxyPreserveHost On

ProxyPass        /api/ http://127.0.0.1:8200/api/
ProxyPassReverse /api/ http://127.0.0.1:8200/api/

ProxyPass        /health http://127.0.0.1:8200/health
ProxyPassReverse /health http://127.0.0.1:8200/health

ProxyPass        / http://127.0.0.1:3200/
ProxyPassReverse / http://127.0.0.1:3200/
```

Preferred restoration uses the saved vhost:

```bash
sudo cp -a /etc/apache2/sites-enabled/decisionvault.conf.before-payments-demo \
  /etc/apache2/sites-enabled/decisionvault.conf
sudo apachectl configtest
sudo systemctl reload apache2
curl --fail http://127.0.0.1:8200/health
curl --fail http://127.0.0.1:3200/
curl --fail https://decisionvault.discovera.ai/health
```

After public traffic is confirmed on normal DecisionVault, the isolated demo
may be stopped without deleting its volumes:

```bash
DV_BACKEND_PORT=8400 DV_FRONTEND_PORT=3400 \
  docker compose -p decisionvault-payments-demo \
  -f docker-compose.yml \
  -f compose.demo.yml \
  -f compose.demo.server.yml \
  stop
```

Never use `down -v`, `--volumes`, the normal database reset command, or the
localhost `demo-payments.sh` reset workflow during server rollback.
