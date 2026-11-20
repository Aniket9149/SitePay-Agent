# Decision Log

Every major decision, the options considered, and the reason. Newest at the bottom. Renaming any roadmap file needs an entry here first.

## D-001 (2026-11-19): Owner tag forms per language

- Context: Rule B1 says the first line is exactly `#Owner::ANIKET::ANHOTRA = MR.Panda`, and that non-hash languages use their own comment syntax with the same text.
- Decision: Python, shell and YAML use the bare form. TypeScript and JavaScript use `// ` plus the tag. CSS uses `/* ` plus the tag plus ` */`. Shell scripts carry no shebang line so the tag can stay on line 1. They are run with `bash script.sh`.
- Enforced by: `scripts/check_project_rules.py`.

## D-002 (2026-11-19): Tracked exception to rule A5 (phase gate)

- Context: Phase 0 exit needs the Product Validation Gate, which needs real interviews and documents that only the owner can collect. Waiting would stop all technical work.
- Decision: Technical foundation work may proceed while the gate is open. Scope is not expanded, scope freeze and architecture freeze stay pending, and the gate stays marked NOT PASSED. Owner: Aniket Anhotra. Review: when the gate evidence is complete.
- Risk accepted: foundation code may need rework if interviews change the scope. Mitigated by keeping Phase 1 to generic foundation (users, organisations, projects, audit).

## D-003 (2026-11-19): Sandbox has no FastAPI, SQLAlchemy or Alembic

- Context: The build sandbox has Python 3.13, pytest, pydantic, PyJWT, PyYAML, openpyxl, Jinja2, reportlab, uvicorn and starlette. It does not have FastAPI, SQLAlchemy, Alembic, httpx, ruff or an argon2 or bcrypt library, and package installs are blocked.
- Decision: Do not swap the architecture to fit the sandbox. Phase 0 is built and tested here. Phase 1 server code is not written as "done" until it can be run. Options are recorded in the tracker: allow package installs, or run the tests on the owner's machine.
- Python version: roadmap says 3.12. The sandbox has 3.13. `requires-python` is set to `>=3.12`.

## D-004 (2026-11-19): Proprietary license as placeholder

- Decision: `LICENSE` is "all rights reserved" for the owner. This is a safe default for a commercial product. The owner may replace it.

## D-005 (2026-11-19): Extra files added beyond the roadmap list

- `tests/unit/test_check_project_rules.py`: tests for the rule checker (rule B8, tests with every feature).
- `tests/unit/test_rules_copy_in_sync.py`: keeps `docs/03_rules.md` identical to `PROJECT_RULES.md`.
- `docs/tracker/DEVELOPMENT_TRACKER.md`, `IMPLEMENTATION_LOG.md`, `TEST_RECORDS.md`: required by the project brief for tracking implemented, tested and verified status.
- Reason: the roadmap file list does not include these but the rules and the brief require them.

## D-006 (2026-11-19): Length rule applies to code files only

- Rule B4 says a file stays under 300 lines. The checker applies this to code files (python, shell, yaml, typescript, javascript, css). Documents and data files are exempt. The em dash rule applies to all text files.

## D-007 (2026-11-20): GitHub repository not accessible, nothing pushed

- Evidence: `add_repo` for `Aniket9149/SitePay-Agent` with push access answered not found or no access. The repository list for the authorised account holds `aniket_24`, `Aniket_249` and `Aniket9149` only. The `gh` token in the shell is invalid.
- Decision: do not push to any other repository. Keep a local Git repository on branch `sp-01/architect-foundation`, make checkpoint ZIPs, and provide upload steps in `docs/GIT_UPLOAD_INSTRUCTIONS.md`. Never push to `main`, never force push.
- Open: the owner creates the repository or grants access.

## D-008 (2026-11-20): Shared contracts live in `backend/app/contracts/`

- Context: six workstreams build one product and need common conventions. SP-01 owns the shared foundation.
- Decision: a small framework-free package holds record ownership, typed references, review states, audit action namespaces, quantity and money shapes and paging. Other workstreams import it and change it only through a change request.
- Not decided: who may approve claims in a small company. `DECIDING_ROLES` is a default (owner, manager, engineer) pending the owner.
- Also added beyond the roadmap list: `app/security/`, `database_triggers.py`, `refresh_token_model.py`, `organization_schema.py`, extra tests.

## D-009 (2026-11-20): Audit actions are validated before they are written

- Decision: `record_audit_event` refuses an action that is not `namespace.verb` or whose namespace is unregistered. This stops typos from entering a permanent log.
- Verified by a source scan of every action string in the services. The writer itself has not been run.

## D-010 (2026-11-20): Phase 1 documents written from the code as built

- `05_data_model`, `08_security_privacy`, `09_testing_plan` and `26_environments_and_release_process` list known gaps and unrun parts openly. No thresholds were invented.
