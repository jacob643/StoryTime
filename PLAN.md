# Story Time — Development Plan

> **Status key**: `[ ]` pending, `[x]` completed, `[~]` in progress. Completed milestones are archived in `previous-milestones.md`.
> **Agent instructions**: See `AGENTS.md`.

---

## Milestone 4: Ship Ready

Goal: Friends and family can download and run the game with zero Python knowledge.

### Epic 4.1: PyInstaller Packaging

- [x] **4.1.1** Create `backend/_version.py` — single source of truth: `__version__ = "0.1.0"`. Import in `main.py` for the banner string. All version references (CLI, pyproject.toml, builds) read from this file.
- [x] **4.1.2** Create `pyproject.toml` with:
      - `[build-system]` requires setuptools + wheel
      - `[project]` name=storytime, version hardcoded as `"0.1.0"` (kept in sync with `_version.py` manually), requires-python>=3.10
      - `[project.dependencies]` — runtime only: fastapi, uvicorn[standard], httpx, pydantic, pydantic-settings
      - `[project.optional-dependencies] dev` — pytest, pytest-playwright
      - `[project.scripts]` — `storytime = backend.main:main`
      - `[tool.setuptools.packages.find]` — include backend/
- [x] **4.1.3** Add `--version` and `--no-reload` CLI flags — in `main()`, add `argparse` to handle `--version` (print version and exit) and `--no-reload` (disable uvicorn reload for production). Auto-detect PyInstaller via `getattr(sys, 'frozen', False)` and force `reload=False`.
- [x] **4.1.4** Update `.gitignore` — remove `*.spec` from the ignore list so the spec file is tracked in Git.
- [x] **4.1.5** Create `storytime.spec` at the repo root — one-file mode, bundle `frontend/` directory, include hidden imports. `console=True`, target name `StoryTime`. Update `main.py` to use `sys._MEIPASS` for frozen mode static files.
- [x] **4.1.6** Create `scripts/build.py` — unified build script that reads version from `_version.py`, installs PyInstaller if missing, parses `--clean` and `--skip-smoke` flags, runs `pyinstaller storytime.spec`, prints output binary path and size.
- [x] **4.1.7** Create `scripts/smoke_test.py` — standalone script that takes a binary path (or auto-discovers in `dist/`), launches it as a subprocess, polls `GET /` every 0.5s for up to 15s until 200, kills the process, exits code 0 on success / 1 on failure.
- [x] **4.1.8** Create `scripts/build.bat` and `scripts/build.sh` — wrappers that call `python scripts/build.py`. One-command entry point.
- [x] **4.1.9** Add `.github/workflows/build.yml` — triggered on push/PR to main, matrix `[windows-latest, ubuntu-latest]`, Python 3.12, `pip install . && pip install pyinstaller`, `python scripts/build.py --skip-smoke`, upload `dist/` as artifact.

### Epic 4.2: Startup & Onboarding

- [x] **4.2.1** Add `GET /api/health` endpoint — returns `{ first_visit: bool, ollama_running: bool }`. Checks if `~/.storytime/config.json` exists (`first_visit`), probes the configured provider via a lightweight HTTP call (`ollama_running`). Add a test that the endpoint returns correct booleans for each combination (config exists vs not, provider responds vs timeout/refused).
- [x] **4.2.2** Wire startup messages in frontend — in `reset()` or `DOMContentLoaded`, call `GET /api/health` and set the message box based on the two booleans. Define 3 message fragments as constants:
      ```js
      const MSG_WELCOME = "Welcome to Story Time! Type each paragraph to drive the story forward. Faster typing leads to brighter outcomes.";
      const MSG_OLLAMA_DOWN = "Ollama is not running. Open Setup to install or start a model.";
      const MSG_PROMPT_READY = "Enter a story prompt and send.";
      ```
      Compose them into the message box with `\n\n` separators:
      | State | `first_visit` | `ollama_running` | Message |
      |---|---|---|---|
      | 1 | true | false | `MSG_WELCOME + "\n\n" + MSG_OLLAMA_DOWN` (`.neutral` class) |
      | 2 | true | true | `MSG_WELCOME + "\n\n" + MSG_PROMPT_READY` (`.neutral` class) |
      | 3 | false | false | `MSG_OLLAMA_DOWN` (`.error` class) |
      | 4 | false | true | `MSG_PROMPT_READY` (`.neutral` class) |
      Add a Playwright test that asserts the correct message appears for each state.
- [x] **4.2.3** Auto-open browser on startup — after Uvicorn binds, open `http://127.0.0.1:8000` in the default browser via `webbrowser.open`. On build failure (e.g., port in use), print the URL to the terminal and skip browser open. The terminal output is only for debugging, never for user instructions.
- [x] **4.2.4** Handle Ollama going down mid-game — if `POST /api/generate` gets a connection refused / timeout from the provider, return `503` with a structured error. Frontend already shows "Start Ollama" with retry button (3.5.1); verify this flow works end-to-end in a Playwright test.
- [x] **4.2.5** Add `scripts/run.sh` and `scripts/run.bat` — production launchers that run the PyInstaller binary (or fall back to `python -m backend.main` if the binary is not found), with a descriptive terminal title

### Epic 4.3: Release Infrastructure

- [ ] **4.3.1** Add `.github/workflows/release.yml` — triggered on tag push `v*.*.*`, builds all platforms via `build.yml` (reuse as a reusable workflow or composite action), then creates a GitHub Release with the build artifacts attached. Include release notes auto-generated from commits since the last tag.
- [ ] **4.3.2** Create `CHANGELOG.md` — keep a manual changelog with sections per version (Unreleased / x.y.z), categorized as Added, Changed, Fixed, Removed. Populate initial entries for v0.1.0 from completed Milestones 1-3.
- [ ] **4.3.3** Create `CONTRIBUTING.md` — development setup guide (clone, venv, dependencies, running tests), code conventions, PR workflow, link to docs/. Keep it short.
- [ ] **4.3.4** Add per-platform download badges to `README.md` — shields.io badges that link to the latest GitHub Release. Badges for Windows, macOS (Intel/ARM), Linux.
- [ ] **4.3.5** Add `scripts/version.py` — CLI tool to bump the version across all files (`_version.py`, `CHANGELOG.md` new section, etc.). `python scripts/version.py bump 0.2.0` reads current version, rewrites files, and prints the diff.

### Epic 4.4: Model Selection

- [x] **4.4.1** Backend model setting plumbing — add `ollama_model` field to `GameSettings`, `SettingsResponse`/`SettingsPatch`, update `registry.active_model` to use it for Ollama provider.
- [x] **4.4.2** Add thinking-tag stripping to `prompt_engine.py` (`strip_thinking`) and apply in `generate.py` route so thinking models produce clean story text.
- [x] **4.4.3** Frontend model selector — add `<select>` (populated from `/api/models`) + refresh button + default button in LLM Settings section; text-input fallback when model list unreachable; wire `ollama_model` in `loadSettings`/`collectSettings`.
- [x] **4.4.4** Update existing tests and add new tests for model selection and thinking-tag stripping.

---

## Milestone 5: Juice

Goal: Add sound effects and animations to make the game feel polished and responsive. Details TBD.
