# Architecture

Source: Roadmap Version 2.0, Part 5.

**Freeze status: DRAFT, not frozen.** The architecture freezes when the Phase 0 exit check passes, which needs the Product Validation Gate. After the freeze it changes only through an approved change request.

## Layers

| Layer | Responsibility |
|-------|----------------|
| 1 Capture | Mobile-first Progressive Web App for photos, voice notes and documents. Saves offline, syncs later. |
| 2 Ingestion | Image resizing and orientation, speech to text, PDF and spreadsheet parsing, drawing parsing, Optical Character Recognition for bills. |
| 3 Understanding | Vision language model for photos and drawings, language model for voice transcripts, document extractors for bills and the Bill of Quantities. |
| 4 Measurement and comparison | Deterministic code calculates quantities, compares planned and actual work, checks duplicates and mismatches. |
| 5 Rules engine | Country and client rules load from configuration files. A new country needs a new rule pack, not new core code. |
| 6 Agent orchestrator | Planner chooses the next step, calls approved tools, enforces guardrails, decides when to ask a person. |
| 7 Documents | Progress reports, measurement sheets, payment claims, issue registers as PDF and Excel. |
| 8 Workflow and approval | Draft, review, approve, submit and track, with an audit record at every step. |
| 9 Storage | PostgreSQL for structured data, object storage for files, a job queue for long tasks. |

Cross-cutting modules: financial calculation engine (isolated), contract and variation layer, evidence conflict resolution, synchronisation layer, evaluation and release gate.

## Technology

| Area | Choice |
|------|--------|
| Backend | Python 3.12 or later with FastAPI |
| Database | PostgreSQL, SQLite for local development |
| Frontend | React with TypeScript, mobile-first Progressive Web App with offline support |
| AI models | Claude API for vision and text, a multilingual speech-to-text model |
| Documents | HTML templates to PDF, openpyxl for Excel |
| Job queue | Database-backed first, Redis with workers when load grows |
| File storage | S3-compatible object storage |
| Deployment | Docker containers on a small cloud server |
| Testing | pytest, golden evaluation set, Vitest, Playwright |

## Data flow (summary)

Evidence arrives, ingestion cleans and fingerprints it, the agent extracts facts with confidence and source links, code calculates quantities, comparison and conflict detection raise issues, a person verifies, the financial engine produces every figure with a trace, a claim is drafted, the approval chain runs, the final document is hashed and locked, and the claim enters the payment lifecycle. The full 13 step flow is in the roadmap, Part 17.

## Hard boundaries

- The agent cannot write directly to the database. It acts only through registered tools.
- The agent never calculates money. The financial engine does, with exact decimals.
- Conflicts are never resolved automatically.
- Uploaded text is data, never instructions.
- Every query is filtered by organisation (tenant separation).

## Environment note

The development sandbox used so far has no FastAPI, SQLAlchemy or Alembic installed and cannot install packages. See decision D-003. This does not change the architecture.
