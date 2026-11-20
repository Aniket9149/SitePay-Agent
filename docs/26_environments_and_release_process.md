# Environments and Release Process

Source: roadmap Phase 1 and the change control rules (section H). This describes the intended process.
**No staging or production environment exists yet, and no deployment automation exists.** Only local development
(Docker Compose) and the continuous integration workflow are written, and neither has been run.

## Environments

| | Development | Staging | Production |
|---|---|---|---|
| Purpose | Building and trying things | Rehearse a release with realistic settings | Real customers |
| Database | SQLite allowed, or PostgreSQL through Compose | PostgreSQL only | PostgreSQL only |
| `APPLICATION_ENVIRONMENT` | development | staging | production |
| API docs page | On | On | Off |
| Secrets | Local `.env`, never committed | Environment of the host | Environment of the host, rotated |
| Data | Test data only | Test data only, never a copy of real customer data | Real |
| Feature flags | Any | Same as the release candidate | Only finished features |

The application itself enforces the database rule: staging and production refuse a SQLite url at start.

## Release flow

1. Work on a branch. SP-01 uses `sp-01/<topic>`. Never commit directly to `main`.
2. Open a pull request. The template checklist is filled in honestly, including what was run and what was not.
3. Continuous integration must pass: rule checker, lint, tests with zero skipped.
4. A significant change needs an approved change request (`docs/17_change_control.md`) before it is merged.
5. Merge to `main` after review.
6. Deploy to staging. Take a database backup first. Run `alembic upgrade head`. Check `/health/ready`. Walk through register, login, create project.
7. Deploy to production the same way, with the same backup first.
8. Watch the logs and `/health/ready` after release.

## Rollback

- Application: redeploy the previous version.
- Database: every migration has a `downgrade`. Prefer restoring the pre-release backup if data was changed.
- A feature that misbehaves can be switched off with `FEATURE_FLAGS` without a redeploy.
- Rollback steps are written in each change request, as required.

## Not built yet

Deployment scripts, backup and restore scripts and the restore drill (Phase 9), staging infrastructure, and the AI regression gate
(Phase 3). Until the backup restore has been proven, a backup must not be treated as reliable.
