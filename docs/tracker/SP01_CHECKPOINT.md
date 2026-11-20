# SP-01 Recovery Checkpoint

Written 2026-11-20. Read this first when resuming.

## State in one paragraph

Phase 0 and Phase 1 are fully written (94 files). 211 tests pass here. The 12 integration tests need FastAPI, SQLAlchemy and httpx
and have never run, so the Phase 1 exit check is **not met**. The work is not on GitHub.

## Resume here, in this order

1. **Get the code safe.** Preferred: owner creates `Aniket9149/SitePay-Agent` and grants the session access, then push branch
   `sp-01/architect-foundation` (never to `main`, never force). Fallback: upload from the ZIP using `docs/GIT_UPLOAD_INSTRUCTIONS.md`.
2. **Run the integration tests** in any environment that can install `pip install -e ".[dev]"`. Fix what they find. Watch the savepoint
   risk listed in `DEVELOPMENT_TRACKER.md`. Then run `alembic upgrade head` and `downgrade base`, and `ruff check .`.
3. **Then continue building** in this order: rate limiting and lockout for login, adopt the paging envelope in the list routes,
   organisation invitations, password reset behind its flag, the `docs/` data and security updates that follow.

## Do NOT repeat

- Do not rewrite the existing files or the shared contracts. Change them through a change request.
- Do not re-do the Phase 0 documents, or the Phase 1 documents 05, 08, 09, 26.
- Do not mark anything tested unless a run is recorded in `TEST_RECORDS.md`. Skipped is not passed.
- Do not invent validation gate evidence, interview notes or other workstreams' code.
- Do not push to `main`, force push, or push to any repository other than the intended one.

## Commands

```
python scripts/check_project_rules.py .
python -m pytest tests backend/tests -rs
```

## Open questions for the owner

Who may approve claims in a small company (default owner, manager, engineer)? Which pilot customers? Gate evidence. Repository creation or access.

## Artifacts

Checkpoint ZIPs are in `/home/claude/checkpoints/` (outside the project folder).
