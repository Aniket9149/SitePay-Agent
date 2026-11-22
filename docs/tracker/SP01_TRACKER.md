# SP-01 ARCHITECT Tracker

Last updated: 2026-11-20.

## Workstream identity

SP-01 Architect, one of six parallel workstreams (SP-02 Evidence, SP-03 Quantum, SP-04 Contract, SP-05 Ledger, SP-06 Sentinel).
Owns the shared backend foundation, database architecture and migrations, authentication and authorisation, shared configuration,
API conventions and cross-workstream contracts.

## Current status

Phase 1 backend executed in CI on commit `b3306cd` (Run 4 in `TEST_RECORDS.md`): 264 tests pass including all 15 integration tests, the real server smoke test passes, migrations pass up and down on SQLite and PostgreSQL 16. The Phase 1 executable exit checks listed in the 2026-11-22 session brief are met. Remaining gaps are listed under Verified vs unverified.

## Completed in this workstream so far

- Phase 0: rules, docs, rule checker with tests, change control, decision log, risk register.
- Phase 1: all 39 roadmap files plus security modules, audit hash chain, append-only triggers, refresh token rotation, organisation and member management.
- Shared contracts: record ownership map, typed references, review states with human-only approval, audit action namespaces,
  quantity and money shapes, paging envelope. Documented in `docs/interface_contracts/SP01_SHARED_CONTRACTS.md`.
- Phase 1 documents 05, 08, 09, 26.
- Login and registration rate limiting: lock after repeated failures per email and address, address wide limit, registration limit per address, trusted proxy handling for client addresses, 429 with Retry-After. In memory, per process.

## Tests executed (actual)

CI run on `b3306cd` (GitHub Actions, Python 3.12.16): tests 264 passed, 0 skipped. Lint, rules, smoke test, migrations (SQLite and PostgreSQL 16) all passed.
Local sandbox: 249 passed, 15 skipped (no FastAPI here). Detail in `TEST_RECORDS.md` Run 4.

## Verified vs unverified

Terms: **tested** means a recorded run passed. **Verified** here means the Phase 1 exit check was run against real execution with evidence. It does not mean independently reviewed.

- **Executed and passing (CI)**: startup through the factory, config loading, SQLite and PostgreSQL migrations up and down, audit log append-only triggers on both databases, register, login, `/auth/me`, refresh rotation and theft revocation, logout, validation errors (422), duplicate (409), consistent error bodies, tenant separation (404), roles, last owner protection, exact money in project responses, health routes, security headers, login lockout and registration limits including the faked X-Forwarded-For case, data surviving a server restart.
- **SQLite savepoints**: the duplicate email, duplicate project and audit write tests pass on SQLite, and the smoke test passed on a SQLite file. The risk did not show up. Not proven under concurrent writers.
- **Still unverified**: concurrent requests, several server processes (rate limits are in memory per process, a known limitation), Docker Compose, load, token expiry timing in real time, independent security review, other workstreams' integration (none seen).
- **Not a defect but noted**: httpx deprecation warning from Starlette's test client.

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
