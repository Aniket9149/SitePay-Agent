# Test Records

Each entry is a real run. Output is copied from the terminal, not written by hand.

## Run 1: 2026-11-19, Phase 0

Environment: Python 3.13.18, pytest 9.1.1, Linux sandbox.

Command: `python -m pytest tests`

Result: 18 passed in 0.02s.

- 17 tests for `scripts/check_project_rules.py`
- 1 test for the rules copy staying in sync

Command: `python scripts/check_project_rules.py .`

Result at that time: `Scanned 23 files, found 0 violations.`

Not run, because the tools are not installed: ruff (lint and format), any backend or frontend test.

## Run 2: 2026-11-20, Phase 1 and shared contracts

Environment: Python 3.13.18, pytest 9.1.1, pydantic 2.13.5, PyJWT 2.15.0, PyYAML 6.0.3. No FastAPI, SQLAlchemy, Alembic, httpx or ruff.

Command: `python -m pytest tests backend/tests -rs`

Result: **211 passed, 2 skipped** in 1.26s.

| Area | Tests | Result |
|---|---|---|
| Rule checker and rules copy (`tests/unit`) | 18 | passed |
| Static structure checks (`tests/unit/test_backend_static_structure.py`) | 62 | passed |
| Infrastructure file checks (`tests/unit/test_infrastructure_files.py`) | 4 | passed |
| Config, errors, flags, logging (`backend/tests/unit`) | 19 | passed |
| Request formats and SQLite audit triggers | 23 | passed |
| Passwords, tokens, permissions, audit hash chain | 32 | passed |
| Shared contracts | 53 | passed |
| Integration tests (`backend/tests/integration`, 12 test functions in 2 files) | 0 run | **2 modules skipped, need FastAPI, SQLAlchemy, httpx** |

Command: `python scripts/check_project_rules.py .`

Result: `Scanned 90 files, found 0 violations.`

Not run: the 12 integration tests, Alembic migration up and down, PostgreSQL trigger SQL, ruff, Docker Compose, the CI workflow.
Static structure checks prove files compile and match the migration. They do not prove the code runs.

## Run 3: 2026-11-21, rate limiting

Environment: same as Run 2 (no FastAPI, SQLAlchemy, Alembic, httpx or ruff).

Command: `python -m pytest tests backend/tests -rs`

Result: **249 passed, 2 skipped** in 1.75s. Added 38 tests since Run 2: 33 rate limiting and client address tests, 5 compile checks for new files.

Command: `python scripts/check_project_rules.py .`

Result: `Scanned 99 files, found 0 violations.` An earlier run in the same session reported 1 violation (a test file of 315 lines, limit 300). It was fixed by splitting the file.

Not run: the 15 integration tests (3 of them cover the rate limiting routes), and everything listed under Run 2.

## Run 4: 2026-11-22, first execution in a real environment (GitHub Actions)

Environment: GitHub Actions `ubuntu-latest`, Python 3.12.16, full dependency set from `pip install -e ".[dev]"`, PostgreSQL 16 service container for one job.
Commit under test: `b3306cd` on `sp-01/architect-foundation`. CI run id for that commit: 6 jobs, all `success`. This sandbox still cannot install FastAPI or SQLAlchemy, so these results come from CI, read with the GitHub REST API (job ids 137167288618 to 137167288802).

| Job | Result (copied from the job log) |
|---|---|
| tests (`SITEPAY_REQUIRE_FULL_STACK=1`, a missing package fails instead of skipping) | `264 passed, 1 warning in 4.27s`, 0 skipped. This includes all 15 integration tests. |
| lint (`ruff check .`, ruff 0.16.x) | passed |
| rules (`scripts/check_project_rules.py .`) | passed |
| smoke (`scripts/smoke_test_backend.py`) | real uvicorn server on a SQLite file: 14 checks passed (health, readiness, security headers, register 201, duplicate 409, invalid email 422, login, `/auth/me`, no token 401, **restart then login works**, 3 wrong passwords then 429 with Retry-After, lock holds for the right password) |
| migrations (sqlite) | `upgrade head`, audit log refuses UPDATE, audit log refuses DELETE, `downgrade base` removes all tables, second `upgrade head` works |
| migrations (postgresql 16) | the same 5 checks, all passed, so the PostgreSQL trigger SQL has now executed |

The 1 warning is `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` It comes from the pinned test client, not from our code. Not acted on.

Defects found by execution: none in application code. The only failures were in my own tooling: (1) ruff reported 147 findings on `38b40f2`, which stopped the old single-job CI before the tests ran (fixed in `53b5a18`: ruff FastAPI config, line length, typing, import order); (2) `scripts/check_migrations.py` could not import `app` (fixed in `b3306cd`). Because no application defect appeared, no application regression test was added. The new scripts and the strict mode are themselves the regression guard.

Local sandbox, same commit: `python -m pytest tests backend/tests` gives 249 passed and 15 skipped (the integration tests skip without FastAPI). Rule checker: 101 files, 0 violations. `ruff check .`: all checks passed (ruff is installed here as a binary).

Not run: Docker Compose, concurrent requests, more than one server process, load, the roadmap's independent review.
