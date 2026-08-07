# Contributing and GitFlow

- `main`: stable, demonstrable releases only.
- `develop`: integration branch.
- `feature/<short-name>`: branch from and merge into `develop`.
- `release/<version>`: stabilization before `main`.
- `hotfix/<short-name>`: urgent correction from `main`.

A pull request must pass local tests, avoid secrets, update relevant documentation and preserve the portable domain contract. Cloud claims require evidence saved under `docs/evidence/` with sensitive identifiers redacted.
