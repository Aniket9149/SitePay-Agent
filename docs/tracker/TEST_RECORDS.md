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
