# Agent guidance

Instructions and conventions for AI agents working on this codebase.

## Project overview

Story Time is a typing game where typing speed and accuracy shape an AI-generated story. Users type paragraphs to advance the narrative; faster typing yields brighter outcomes. Stories are generated locally via Ollama.

## Tech stack

- **Backend**: Python 3.10+ / FastAPI / Uvicorn
- **Frontend**: Vanilla HTML/CSS/JS (no framework)
- **LLM**: Local models via Ollama
- **Packaging**: PyInstaller (standalone binaries)
- **CI**: GitHub Actions

## Project structure

```
backend/          Python FastAPI app + tests
frontend/         Static HTML/CSS/JS served by the backend
scripts/          Build, run, and smoke-test helpers
docs/             Design docs, brainstorming, runbook
.github/          CI workflows (build + release)
writtenStories/   Generated story storage (gitignored)
```

## Instructions

- After each task, mark it `[x]` in `PLAN.md` and update affected docs in `docs/`.
- When a milestone is fully completed, move it to `docs/previous-milestones.md`.
- Always add or update corresponding tests (pytest for backend, Playwright for frontend). Keep existing tests passing.
- Commit after each single task — never batch multiple tasks into one commit.
- Status key in `PLAN.md`: `[ ]` pending, `[x]` completed, `[~]` in progress.
- Update `CHANGELOG.md` under `## [Unreleased]` during development with only the changes you consider noteworthy. You decide what's important — not everything needs an entry.

## Docs structure

```
docs/
├── brainstorm.md
├── previous-milestones.md
├── release-guide.md
├── development-process/
│   └── runbook.md
└── technical-design/
    ├── index.md
    ├── 01-architecture-overview.md
    ├── 02-frontend-design.md
    ├── 03-backend-design.md
    ├── 04-llm-provider-system.md
    ├── 05-distribution-packaging.md
    └── 06-paragraph-scoring.md
```

## Conventions

- **Scoring**: adaptive mode uses z-score with `σ/√N`. n=1 first paragraph forced tier 2.
- **Settings defaults**: mirrored in JS `SETTINGS_DEFAULTS` and `DEFAULT_FIXED_THRESHOLDS_CPM`. Backend is SSOT.
- **CPM vs WPM**: backend always stores CPM. `cpmToDisplay`/`displayToCpm` in JS. `5*WPM = CPM`.
- **Testing**: `pytest` for backend, `Playwright` for frontend smoke tests.
- **Version**: single source in `backend/_version.py`. `pyproject.toml` synced manually.

## What NOT to change

- Version bumping is handled by the user through a script. Agents should not modify version numbers.
- Don't batch multiple tasks into one commit.
- Don't commit secrets, API keys, or credentials.
- Never modify `writtenStories/` — user-generated content.
