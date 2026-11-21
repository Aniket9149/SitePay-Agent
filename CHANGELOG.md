# Changelog

All notable changes are recorded here. Newest first.

## Unreleased

### Added
- Phase 1 backend core: configuration, error handling, logging, feature flags, models, migration `0001`, authentication with refresh token rotation, role based access, organisations, members, projects, sites, hash chained append-only audit log, health routes, Docker Compose, CI workflow.
- Shared cross-workstream contracts in `backend/app/contracts/` and `docs/interface_contracts/SP01_SHARED_CONTRACTS.md`.
- Phase 1 documents: data model, security and privacy, testing plan, environments and release process.
- SP-01 tracker, execution log and recovery checkpoint.
- Login and registration rate limiting with trusted proxy handling, and a 429 response with Retry-After.
- Phase 0 foundation: project rules, documentation set, change control process, validation gate checklist, development tracker.
- `scripts/check_project_rules.py`: automatic checker for the owner tag, em dashes and the 300 line limit, with 17 tests.
- Test that keeps `docs/03_rules.md` identical to `PROJECT_RULES.md`.
