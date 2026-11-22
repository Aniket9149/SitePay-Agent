# SP-01 Recovery Checkpoint

Written 2026-11-20. Read this first when resuming.

## State in one paragraph

Phase 0 and Phase 1 are written (101 files, plus login and registration rate limiting). On 2026-11-22 the code ran for the first time in GitHub Actions: 264 tests pass including all 15 integration tests, the real server smoke test passes, and the migration runs up and down on SQLite and PostgreSQL 16. Remote head `b3306cd` on `sp-01/architect-foundation`. Scope is frozen: nothing new has been added.

## Resume here, in this order

1. **Keep pushing** to `sp-01/architect-foundation` only (never `main`, never force). Read CI results with `gh api repos/Aniket9149/SitePay-Agent/actions/runs`.
2. Remaining Phase 1 gaps: concurrency and multi-process behaviour, a shared rate limit store, Docker Compose run, independent review.
3. Only when the owner lifts the scope freeze: adopt the paging envelope in list routes, organisation invitations, password reset behind its flag.

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
ruff check .
python scripts/check_migrations.py   # needs DATABASE_URL
python scripts/smoke_test_backend.py
```

## Open questions for the owner

Who may approve claims in a small company (default owner, manager, engineer)? Which pilot customers? Gate evidence. Repository creation or access.

## Artifacts

Checkpoint ZIPs are in `/home/claude/checkpoints/` (outside the project folder).
