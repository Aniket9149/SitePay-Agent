# SP-01 Execution Log

Chronological, facts only.

## Session 2: 2026-11-20

1. Inspected Git state. No `.git` folder, no remote, no commits. All work existed only in the workspace.
2. Counted files by modification time: 78 at that point (26 from Phase 0, 52 new in Phase 1, `pyproject.toml` the only Phase 0 file edited).
3. Tried GitHub access with push permission for `Aniket9149/SitePay-Agent`: refused as not found or no access. Listed accessible repositories: `aniket_24`, `Aniket_249`, `Aniket9149`. Did not push to any of them.
4. Built a safety ZIP of 78 files before further work: `checkpoints/sitepay-agent_checkpoint_1_safety.zip`.
5. Added `app/contracts/` (entity references and ownership, review states, audit actions, quantities and money, paging) with 53 tests, all passing.
6. Wired audit action validation into `record_audit_event`. Verified by source scan only, because that code needs SQLAlchemy.
7. Re-extracted the roadmap text and compared the Phase 1 file list. Found the four Phase 1 documents missing and wrote them (05, 08, 09, 26).
8. Full run: 211 passed, 2 skipped modules. Rule checker: 0 violations.
9. Updated trackers, decision log, risk register, changelog. Initialised a local Git repository and committed on `sp-01/architect-foundation`.
10. Built the final checkpoint ZIP.
11. Later on 2026-11-20: repository access was granted. The remote was empty. Pushed branch `sp-01/architect-foundation` (no force, not `main`) and verified `ef4f5d3` on GitHub.

Not done: any run of database or web code, any push to GitHub, any integration with other workstreams, lint.

## Session 3: 2026-11-21

1. Rechecked GitHub before pushing. `git ls-remote`, the branches list and the commits list all showed `ef4f5d3` as the head of `sp-01/architect-foundation`, equal to the local head. The two original commits were already on GitHub from the push on 2026-11-20, so there was nothing to re-push.
2. Built login and registration rate limiting: `AttemptTracker`, `LoginThrottle`, `RegistrationThrottle`, client address extraction, `RateLimitedError` (429 with Retry-After), four new settings, wiring in the app, dependencies and auth routes.
3. Wrote 33 unit tests with a fake clock and 3 integration tests. A first run found a mistake in one of my tests (wrong arithmetic for the address limit), fixed in the test. The code was correct.
4. Rule checker found a test file over 300 lines. Split it into two files.
5. Full run: 249 passed, 2 skipped modules (15 integration tests). Rule checker: 0 violations on 99 files.
6. Updated the security document, risk register, trackers, checkpoint and test records.
