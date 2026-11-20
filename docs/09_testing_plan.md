# Testing Plan

Source: roadmap Phase 1 and the project rules (B8: no feature is complete without tests).
SP-06 Sentinel owns the wider QA system. This file covers what SP-01 needs for the foundation.

## Test layers

| Layer | Location | Needs | Runs in the current environment |
|---|---|---|---|
| Rule checker tests | `tests/unit/test_check_project_rules.py` and the rules copy test | pytest | Yes |
| Static structure tests | `tests/unit/test_backend_static_structure.py`, `test_infrastructure_files.py` | pytest, PyYAML | Yes |
| Backend unit tests | `backend/tests/unit/` | pytest, pydantic, PyJWT | Yes |
| Backend integration tests | `backend/tests/integration/` | FastAPI, SQLAlchemy, httpx | **No, they skip** |
| AI golden set and regression gate | planned for Phase 3 | n/a | Not built |
| Financial formula tests | planned with the financial engine (SP-05) | n/a | Not built |
| Frontend tests | planned (Vitest, Playwright) | n/a | Not built |

## What static structure tests prove, and what they do not

They prove every backend file compiles, each function has types and a docstring, every model table matches the migration,
pure modules import no framework, and mutating routes commit. They do **not** prove the code runs. Only the integration
tests do that.

## Skipped tests

A skipped test is not a pass. Reports must always show the number skipped. Continuous integration installs every
dependency, so it must show zero skipped. A skip in continuous integration is a failure to investigate.

## Gates today

1. `python scripts/check_project_rules.py .` reports 0 violations.
2. `python -m pytest tests backend/tests` passes with 0 failures. Skips are allowed only in a limited environment.
3. Phase 1 exit check from the roadmap: a new user can register, log in and create a project, and all tests pass in continuous
   integration. **Not yet met**, because the integration tests have never run.

AI evaluation thresholds are set in Phase 3 with the golden set. No threshold is invented here.

## First things to run when dependencies exist

1. Install with `pip install -e ".[dev]"` and run the full suite. Expect the two integration files to run, not skip.
2. Check the savepoint behaviour on SQLite. `flush_or_raise_conflict` and `record_audit_event` use nested transactions.
   SQLite's driver has known savepoint quirks, so the duplicate email and duplicate project tests are the first to watch.
3. Run `alembic upgrade head` then `alembic downgrade base` on SQLite and on PostgreSQL.
4. Run the PostgreSQL audit trigger statements, which have never been executed.
5. Run `ruff check .`, which has not been run on this code.

## How to run

```
python scripts/check_project_rules.py .
python -m pytest tests backend/tests -rs     # -rs lists skipped tests and why
```
