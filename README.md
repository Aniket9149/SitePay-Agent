# SitePay Agent

An evidence-based AI agent that connects the construction site to the payment office.

It reads site photos, voice notes, drawings, bills and project documents, compares actual work with planned work, flags missing or inconsistent information, and prepares progress reports and payment claim drafts. A qualified human always gives final approval.

Owner: Aniket Anhotra (MR.Panda). Master plan: Roadmap Version 2.0 with Implementation Addendum.

## Current status

Phase 0 and Phase 1 are written. Pure logic is tested (211 tests pass). The database and web code has not been run yet, because the build environment lacks FastAPI and SQLAlchemy. The honest, always-current status of every file and phase is in
[`docs/tracker/DEVELOPMENT_TRACKER.md`](docs/tracker/DEVELOPMENT_TRACKER.md).

The Product Validation Gate has **not** passed. It needs real interviews and documents that only the owner can collect. See [`docs/21_product_validation_gate.md`](docs/21_product_validation_gate.md).

## Read first

1. [`PROJECT_RULES.md`](PROJECT_RULES.md): the mandatory rules.
2. [`docs/04_architecture.md`](docs/04_architecture.md): layers and technology.
3. [`docs/12_decision_log.md`](docs/12_decision_log.md): why things are the way they are.

## Run the checks

```
python -m pytest tests          # tests that exist today
python scripts/check_project_rules.py .   # owner tag, em dash, file length
```

Or use `make test` and `make check-rules`.

## Technology (planned)

Python 3.12 with FastAPI, PostgreSQL, React with TypeScript as a mobile-first Progressive Web App, the Claude API for vision and text understanding, and Docker for deployment. See the architecture document for details.

## Environment variables

Copy `.env.example` to `.env` and fill in real values. Never commit `.env`.
