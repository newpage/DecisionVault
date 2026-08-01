# QA — DecisionVault 0.3.4

- [ ] `bash -n scripts/*.sh scripts/lib/*.sh` passes.
- [ ] `./scripts/install-dv-cli.sh` installs the repository-managed CLI.
- [ ] `dv version` shows 0.3.4.
- [ ] `dv doctor` validates ports 8200 and 3200.
- [ ] `dv status` shows version, commit, containers, and health.
- [ ] `dv logs frontend 50` follows only frontend logs.
- [ ] `dv backup` creates SQL, storage, and manifest files.
- [ ] `dv diag` creates a redacted diagnostics archive.
- [ ] `dv deploy` does not stop the database during a normal deployment.
- [ ] Backend `/health` reports version 0.3.4.
- [ ] Sidebar displays Release 0.3.4.
