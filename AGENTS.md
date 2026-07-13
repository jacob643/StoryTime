# Agent guidance

Instructions and conventions for AI agents working on this codebase.

## Instructions

- After each task, mark it `[x]` in `PLAN.md` and update affected docs in `docs/`.
- When a milestone is fully completed, move it to `docs/previous-milestones.md`.
- Always add or update corresponding tests (pytest for backend, Playwright for frontend). Keep existing tests passing.
- Commit after each single task — never batch multiple tasks into one commit.
- Status key in `PLAN.md`: `[ ]` pending, `[x]` completed, `[~]` in progress.
- Update `CHANGELOG.md` under `## [Unreleased]` during development with only the changes you consider noteworthy. You decide what's important — not everything needs an entry.

## Conventions

- **Scoring**: adaptive mode uses z-score with `σ/√N`. n=1 first paragraph forced tier 2.
- **Settings defaults**: mirrored in JS `SETTINGS_DEFAULTS` and `DEFAULT_FIXED_THRESHOLDS_CPM`. Backend is SSOT.
- **CPM vs WPM**: backend always stores CPM. `cpmToDisplay`/`displayToCpm` in JS. `5*WPM = CPM`.
- **Testing**: `pytest` for backend, `Playwright` for frontend smoke tests.
- **Version**: single source in `backend/_version.py`. `pyproject.toml` synced manually.
