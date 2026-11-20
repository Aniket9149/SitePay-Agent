# Development Tracker

Last updated: 2026-11-20. Reports only what is true. Status words (defined in `PROJECT_RULES.md`):
**not started**, **implemented** (code exists, not executed), **tested** (executed by a recorded passing run), **verified** (phase exit check or independent review confirmed it).

Nothing is verified yet. Workstream detail for SP-01 is in `SP01_TRACKER.md`. Where to resume is in `SP01_CHECKPOINT.md`.

## Phase status

| Phase | Name | Roadmap files | Status |
|---|---|---|---|
| 0 | Foundation and validation gate | 21 | All 21 files exist. **Exit check not met**: validation gate has no evidence, scope not frozen |
| 1 | Backend core | 39 | 39 of 39 roadmap files exist (orders 22 to 60). **Exit check not met**: the register, log in, create project flow has never run |
| 2 to 10 | See roadmap | 335 | Not started |

Honest reading of Phase 1: the pure logic is tested and passing. The code that needs FastAPI and SQLAlchemy is written and statically
checked only. It has never been executed.

## Phase 1 files by status (roadmap order numbers)

**Tested** (executed, passing, in `TEST_RECORDS.md`):
22 `app/__init__`, 23 `config`, 25 `errors`, 38 `auth_schema`, 39 `project_schema`, 54 `logging_setup`, 60 `feature_flags`.

**Implemented, not executed** (compiled and structure checked only):
24 `database`, 26 `dependencies`, 27 `main`, 28 to 34 and 55 models, 35 `migrations/env`, 36 migration `0001`, 37 and 40 and 43 package files,
41 `auth_routes`, 42 `project_routes`, 44 `auth_service`, 45 `audit_service`, 46 `conftest`, 47 `test_auth_flow`, 56 `health_routes`,
57 `organization_routes`, 58 `site_routes`.

**Parsed only** (valid YAML and no hard coded secrets, never run by Docker or GitHub): 48 `docker-compose.yml`, 53 CI workflow. 59 PR template is plain text.

**Written** (documents): 49 `05_data_model`, 50 `08_security_privacy`, 51 `09_testing_plan`, 52 `26_environments_and_release_process`.

## Files added beyond the roadmap list (decision D-005, D-008)

- `app/security/` (password hasher, token service, permissions, audit hash chain), `app/database_triggers.py`, `app/models/refresh_token_model.py`,
  `app/schemas/organization_schema.py`. All tested except the refresh token model.
- `app/contracts/` shared cross-workstream contracts (6 files), tested.
- `backend/alembic.ini`, `backend/tests/unit/` (4 files), `backend/tests/integration/test_tenant_and_roles.py`.
- `tests/unit/` structure and infrastructure checks, `docs/interface_contracts/SP01_SHARED_CONTRACTS.md`, tracker files.

## Numbers (2026-11-20)

- 94 files in the workspace. 5,665 lines of Python including tests. Longest code file 267 lines (limit 300).
- Last full run: **211 passed, 2 skipped modules**, rule checker 0 violations on 94 files.
- The 2 skipped modules hold **12 integration tests that have never run**. Skipped is not passed.

## Known risks to check first when FastAPI and SQLAlchemy are available

1. Nested transactions (savepoints) on SQLite are used for duplicate detection and audit writes. SQLite's driver is known to mishandle them
   unless configured. Watch the duplicate email and duplicate project tests.
2. PostgreSQL audit trigger SQL has never been executed.
3. The migration has never been run, up or down, on any database.
4. `ruff` lint has never been run on this code.
5. Response model validation of Decimal fields in `ProjectResponse` is unverified. The integration test accepts either text or number for the value.

## Blockers

- No FastAPI, SQLAlchemy, Alembic, httpx or ruff here, and installs are blocked (D-003).
- GitHub repository `Aniket9149/SitePay-Agent` is not visible to this session (D-007).
- Phase 0 validation gate needs real interviews and documents from the owner.

## Next actions

1. Owner: create the repository `Aniket9149/SitePay-Agent` (empty is fine) and grant this session access, or upload the ZIP. Instructions in `docs/GIT_UPLOAD_INSTRUCTIONS.md`.
2. Environment with dependencies: run the full suite and fix whatever the 12 integration tests find. This is the Phase 1 exit check.
3. SP-01: adopt the paging envelope in list routes, add rate limiting, then invitations and password reset.
4. Owner: gate evidence, and decide who may approve claims in a small company.
