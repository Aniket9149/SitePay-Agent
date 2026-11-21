# SP-01 ARCHITECT Tracker

Last updated: 2026-11-20.

## Workstream identity

SP-01 Architect, one of six parallel workstreams (SP-02 Evidence, SP-03 Quantum, SP-04 Contract, SP-05 Ledger, SP-06 Sentinel).
Owns the shared backend foundation, database architecture and migrations, authentication and authorisation, shared configuration,
API conventions and cross-workstream contracts.

## Current status

Phase 1 foundation and shared contracts are written. Pure logic is tested. Database and web code is written but never executed.

## Completed in this workstream so far

- Phase 0: rules, docs, rule checker with tests, change control, decision log, risk register.
- Phase 1: all 39 roadmap files plus security modules, audit hash chain, append-only triggers, refresh token rotation, organisation and member management.
- Shared contracts: record ownership map, typed references, review states with human-only approval, audit action namespaces,
  quantity and money shapes, paging envelope. Documented in `docs/interface_contracts/SP01_SHARED_CONTRACTS.md`.
- Phase 1 documents 05, 08, 09, 26.
- Login and registration rate limiting: lock after repeated failures per email and address, address wide limit, registration limit per address, trusted proxy handling for client addresses, 429 with Retry-After. In memory, per process.

## Tests executed (actual)

`python -m pytest tests backend/tests`: 249 passed, 2 skipped modules (15 integration tests, need FastAPI/SQLAlchemy/httpx).
`python scripts/check_project_rules.py .`: 0 violations, 99 files.
Detail in `TEST_RECORDS.md`.

## Verified vs unverified

- **Verified**: nothing (no phase exit check has been met).
- **Tested**: rate limiting logic, config, errors, logging, feature flags, password hashing, tokens, permissions, audit hash chain, SQLite audit triggers, request formats, all shared contracts, rule checker.
- **Statically checked only**: models, migration, services, routes, app assembly. 7 model tables match the migration column for column.
- **Unverified**: everything that needs a database or web server. Docker Compose and CI have never run.

## Dependencies on other agents

Recorded in section 8 of `docs/interface_contracts/SP01_SHARED_CONTRACTS.md`. **No other workstream's code has been seen, so no integration is claimed.**
Migration chain is linear: the next migration needs `down_revision = "0001"`. Other workstreams must tell SP-01 before adding one.

## Interface decisions

Record ownership, `kind:uuid` references, `namespace.verb` audit actions, review state machine, `Quantity` and `Money` shapes, limit/offset paging with `has_more`.
All are **proposals to other workstreams**, implemented in SP-01's code only.

## GitHub status

- Repository: `Aniket9149/SitePay-Agent` (public). It was empty when first pushed, so nothing was overwritten.
- Branch `sp-01/architect-foundation` was pushed on 2026-11-20 with commits `af40196` and `ef4f5d3`. Verified: `git ls-remote`, the GitHub branches list and the GitHub commits list all showed `ef4f5d3`, and 94 files were in the remote tree.
- Rate limiting work was committed and pushed afterwards. The current head is in the latest `git log`, see `SP01_EXECUTION_LOG.md` for the verification.
- No `main` branch exists. Nothing was pushed to `main`. No force push was used.

## Next execution checkpoint

See `SP01_CHECKPOINT.md`.
