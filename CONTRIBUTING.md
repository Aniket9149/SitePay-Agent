# Contributing

These notes mirror `PROJECT_RULES.md`. If they ever disagree, the rules file wins.

## Before you write code

- Read `PROJECT_RULES.md` and the exit checks of the current phase.
- Check the build order in the roadmap. Do not start a phase before the previous one passes its exit check, unless the decision log records an exception.
- Anything significant (database, agent behaviour, security, financial figures, architecture) needs a change request first. See `docs/17_change_control.md`.

## Writing code

- First line of every code file is the owner tag (the accepted forms are in `PROJECT_RULES.md`).
- Complete code only, full descriptive names, type hints, a two to three line docstring on every function.
- One file, one job, under 300 lines.
- All money and quantity maths goes through the financial calculation engine, with exact decimals.
- No secrets in code. Use environment variables.
- No em dashes in code, comments, documents or interface text.

## Before every commit

1. `python scripts/check_project_rules.py .`
2. `python -m pytest tests backend/tests`
3. Format and lint (ruff) once the tool is available in your environment.
4. Update the tracker and, if a decision was made, the decision log.

## Commit messages

One commit does one thing. The message says what changed and why, in plain words.

## Reporting status

Use the words from `PROJECT_RULES.md`: not started, implemented, tested, verified. Never mark something tested without a recorded test run.
