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

## Tests executed (actual)

`python -m pytest tests backend/tests`: 211 passed, 2 skipped modules (12 integration tests, need FastAPI/SQLAlchemy/httpx).
`python scripts/check_project_rules.py .`: 0 violations, 94 files.
Detail in `TEST_RECORDS.md`.

## Verified vs unverified

- **Verified**: nothing (no phase exit check has been met).
- **Tested**: config, errors, logging, feature flags, password hashing, tokens, permissions, audit hash chain, SQLite audit triggers, request formats, all shared contracts, rule checker.
- **Statically checked only**: models, migration, services, routes, app assembly. 7 model tables match the migration column for column.
- **Unverified**: everything that needs a database or web server. Docker Compose and CI have never run.

## Dependencies on other agents

Recorded in section 8 of `docs/interface_contracts/SP01_SHARED_CONTRACTS.md`. **No other workstream's code has been seen, so no integration is claimed.**
Migration chain is linear: the next migration needs `down_revision = "0001"`. Other workstreams must tell SP-01 before adding one.

## Interface decisions

Record ownership, `kind:uuid` references, `namespace.verb` audit actions, review state machine, `Quantity` and `Money` shapes, limit/offset paging with `has_more`.
All are **proposals to other workstreams**, implemented in SP-01's code only.

## GitHub status

- Target: `Aniket9149/SitePay-Agent`.
- Checked 2026-11-20 with the session's authorised access: the repository was **not found or not accessible**. The accessible account lists only
  `aniket_24`, `Aniket_249` and `Aniket9149`. Nothing was pushed anywhere. The token in the shell environment is invalid.
- Local Git repository initialised in the workspace on branch `sp-01/architect-foundation`. Commits are local only.
- Push status: **not pushed**. Next step is in `docs/GIT_UPLOAD_INSTRUCTIONS.md`.

## Next execution checkpoint

See `SP01_CHECKPOINT.md`.
