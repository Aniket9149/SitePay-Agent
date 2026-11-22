# Development Tracker

Last updated: 2026-11-20. Reports only what is true. Status words (defined in `PROJECT_RULES.md`):
**not started**, **implemented** (code exists, not executed), **tested** (executed by a recorded passing run), **verified** (phase exit check or independent review confirmed it).

Nothing is verified yet. Workstream detail for SP-01 is in `SP01_TRACKER.md`. Where to resume is in `SP01_CHECKPOINT.md`.

## Phase status

| Phase | Name | Roadmap files | Status |
|---|---|---|---|
| 0 | Foundation and validation gate | 21 | All 21 files exist. **Exit check not met**: validation gate has no evidence, scope not frozen |
| 1 | Backend core | 39 | 39 of 39 roadmap files exist (orders 22 to 60). **Executable exit checks met in CI on `b3306cd`** (register, log in, create project flow, migrations, restart persistence). Not independently reviewed |
| 2 to 10 | See roadmap | 335 | Not started |

Honest reading of Phase 1: executed in GitHub Actions on 2026-11-22, 264 tests passing (Run 4). Not run in this sandbox. Concurrency, multi-process limits and Docker Compose are still unverified.

## Phase 1 files by status (roadmap order numbers)

**Tested** (executed, passing, in `TEST_RECORDS.md`):
22 `app/__init__`, 23 `config`, 25 `errors`, plus rate limiting (`attempt_tracker`, `login_throttle`, `client_address`), 38 `auth_schema`, 39 `project_schema`, 54 `logging_setup`, 60 `feature_flags`.

**Executed in CI on 2026-11-22, passing** (Run 4; not run in this sandbox):
24 `database`, 26 `dependencies`, 27 `main`, 28 to 34 and 55 models, 35 `migrations/env`, 36 migration `0001`, 37 and 40 and 43 package files,
41 `auth_routes`, 42 `project_routes`, 44 `auth_service`, 45 `audit_service`, 46 `conftest`, 47 `test_auth_flow`, 56 `health_routes`,
57 `organization_routes`, 58 `site_routes`.

**CI workflow (53) has run on GitHub and passed. `docker-compose.yml` (48) is parsed only, never run by Docker.** 59 PR template is plain text.

**Written** (documents): 49 `05_data_model`, 50 `08_security_privacy`, 51 `09_testing_plan`, 52 `26_environments_and_release_process`.

## Files added beyond the roadmap list (decision D-005, D-008)

- `app/security/` (password hasher, token service, permissions, audit hash chain), `app/database_triggers.py`, `app/models/refresh_token_model.py`,
  `app/schemas/organization_schema.py`. All tested except the refresh token model.
- `app/contracts/` shared cross-workstream contracts (6 files), tested.
- `backend/alembic.ini`, `backend/tests/unit/` (4 files), `backend/tests/integration/test_tenant_and_roles.py`.
- `tests/unit/` structure and infrastructure checks, `docs/interface_contracts/SP01_SHARED_CONTRACTS.md`, tracker files.

## Numbers (2026-11-22)

- 101 files in the workspace. 6,411 lines of Python including tests. Longest code file 270 lines (limit 300).
- Last CI run (`b3306cd`): **264 passed, 0 skipped**. Local sandbox: 249 passed, 15 skipped. Rule checker 0 violations on 101 files.
- The 15 integration tests ran and passed in CI. They still skip in this sandbox, which lacks FastAPI. Skipped is not passed, so the CI run is the evidence.

## Risks checked on 2026-11-22 (Run 4)

1. SQLite savepoints: duplicate and audit tests pass, smoke test passes. Not shown under concurrent writers.
2. PostgreSQL audit trigger SQL: executed on PostgreSQL 16, UPDATE and DELETE refused.
3. Migration: up, down, up on SQLite and PostgreSQL 16.
4. `ruff`: passes in CI and here.
5. Rate limiting routes: integration tests and the smoke test pass. Still per process, in memory.
6. Decimal in project responses: the integration test passes. Format on the wire is still whatever Pydantic emits, and the contract documents it.

## Blockers

- No FastAPI, SQLAlchemy, Alembic, httpx or ruff here, and installs are blocked (D-003).
- GitHub: resolved. Branch `sp-01/architect-foundation` is pushed and verified. See `SP01_TRACKER.md`.
- Phase 0 validation gate needs real interviews and documents from the owner.

## Next actions

1. Owner: create the repository `Aniket9149/SitePay-Agent` (empty is fine) and grant this session access, or upload the ZIP. Instructions in `docs/GIT_UPLOAD_INSTRUCTIONS.md`.
2. Environment with dependencies: run the full suite and fix whatever the 15 integration tests find. This is the Phase 1 exit check.
3. SP-01: adopt the paging envelope in list routes, then organisation invitations and password reset. Login and registration rate limiting is done (in memory only, see `08_security_privacy.md`).
4. Owner: gate evidence, and decide who may approve claims in a small company.
