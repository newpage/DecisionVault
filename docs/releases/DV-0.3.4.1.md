# DecisionVault 0.3.4.1 — CLI Symlink Resolution Patch

## Fixed

- `dv version` now resolves the real repository path when invoked through
  `/usr/local/bin/dv`.
- Git commit detection now uses the resolved repository directory.
- `dv shell` now opens the actual DecisionVault repository.
- Installer verifies the installed CLI through the symlink.

## Database

No database changes.
