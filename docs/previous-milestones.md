# Previous Milestones

## Milestone 1: Hello World Infrastructure

Goal: A minimal end-to-end pipeline — FastAPI backend serves a static page, connects to Ollama, and returns LLM-generated text to the browser. No typing game logic yet, just proving the chain works.

### Epic 1.1: FastAPI Static Server
- [x] **1.1.1** Create `backend/` project skeleton — `main.py` (FastAPI app + static mount), `config.py` (Pydantic settings), `requirements.txt`, and entry point with Uvicorn launcher + auto-open browser
- [x] **1.1.2** Set up `backend/tests/` with pytest + FastAPI TestClient; add a test that the server starts and `GET /` returns the frontend page successfully

### Epic 1.2: Basic Ollama Connection
- [x] **1.2.1** Create `backend/providers/ollama.py` with a basic OllamaProvider class (generate + is_available) and `backend/routes/generate.py` exposing `POST /api/generate`
- [x] **1.2.2** Write mocked unit tests for OllamaProvider (using httpx mock) — test generate returns expected text, is_available returns true/false based on HTTP status

### Epic 1.3: Simple "Send Prompt → Get Response" Page
- [x] **1.3.1** Build minimal frontend page — an input field, submit button, and response area, with JS `fetch` to `POST /api/generate` and display the result
- [x] **1.3.2** Add Playwright smoke test (`pip install pytest-playwright && playwright install chromium`) that opens the page, types a prompt, clicks submit, and verifies no console errors or network failures
- [x] **1.3.3** Fix `GET /favicon.ico` 404 — add a small SVG favicon to `frontend/` and reference it in `index.html`

> **Note**: Each prompt currently starts a new conversation — no story history is passed to the LLM. Session management and context threading are the first tasks in M2.

---

## Milestone 2: Working Game Loop

Goal: The game runs end-to-end — typing speed drives the story via the 5-tier prompt system.

### Epic 2.1: Game Session & Prompt Engine

- [x] **2.1.1** Create `backend/session.py` — `GameSession` and `ParagraphRecord` dataclasses, in-memory dict store indexed by `session_id` (UUID), with create/get/append methods
- [x] **2.1.2** Create `backend/prompt_engine.py` — `build_prompt()` that takes the initial prompt, story history (list of paragraph texts), and an outcome tier (0–4), and assembles a prompt string using the 5-tier templates (docs expect user/assistant formatting or plain text; LLM agent should pick based on `docs/technical-design/`)
- [x] **2.1.3** Create `backend/game_logic.py` — `compute_outcome_tier(speed_cpm) -> int` mapping CPM thresholds to 5 tiers (very negative → very positive), with configurable threshold constants
- [x] **2.1.4** Add session context to `POST /api/generate` — accept optional `session_id`/`speed_cpm` fields; auto-create session if new; on subsequent calls append previous paragraph to story history before calling LLM

### Epic 2.2: Frontend Typing Game

- [x] **2.2.1** Rewrite frontend typing engine — on paragraph completion, send `{session_id, speed_cpm}` to `POST /api/generate`, receive next paragraph, display it as the text to type; remove random string generation
- [x] **2.2.2** Wire initial prompt flow — on "Send" or page load, call `/api/generate` to get the first story paragraph and display it in `#textDisplay`; integrate the typing box/character highlighting/timer/CPM-WPM display with the new API-driven flow
- [x] **2.2.3** Add story history sidebar — after each completed paragraph, append the typed text, time, and speed to the `#history` sidebar

### Epic 2.3: End-to-End Game Flow

- [x] **2.3.1** Wire the full loop — initial prompt → first paragraph appears → user types it → speed_cpm sent → backend computes outcome tier → LLM returns next paragraph → user types again; verify with a full Playwright integration test that mocks the LLM and asserts the typing flow works
- [x] **2.3.2** Add restart flow — clicking "Restart" sends a new initial prompt, clears the session history on both frontend and backend, and fetches a fresh first paragraph

---

## Milestone 3: Polished User Experience

Goal: Adaptive speed scoring, customizable game parameters, settings UI, dev tools, and robust error handling.

### Epic 3.1: Provider System
- [x] **3.1.1** Add custom OpenAI-compatible endpoint provider alongside Ollama
- [x] **3.1.2** Add `GET /api/models` endpoint that discovers models from active providers
- [x] **3.1.3** Build provider registry with fallback logic

### Epic 3.2: Adaptive Speed Scoring
- [x] **3.2.1** Create `ScoringParams` dataclass + `compute_speed_stats()` + `split_text()` in `game_logic.py` — 50-char target split, rolling window of 20 split-speeds, symmetric ±1.5σ/±0.5σ tiers
- [x] **3.2.2** Add `rolling_splits` + `initial_avg_cpm` + `scoring_params` to `GameSession`; update `ParagraphRecord` to include `split_speeds`
- [x] **3.2.3** First-paragraph baseline logic — `ceil(N/2)` splits seed rolling window, `floor(N/2)` split speeds averaged and scored; default avg=300 CPM, σ=10 when no prior data
- [x] **3.2.4** Refactor `POST /api/generate` to accept `split_speeds`, compute outcome tier from rolling stats vs fixed fallback, push splits into rolling window (max 20)
- [x] **3.2.5** Frontend: compute per-split speeds at 50-char boundaries, emit `split_speeds[]` alongside `speed_cpm` on paragraph completion
- [x] **3.2.6** Tests: unit tests for split algorithm, compute_speed_stats, compute_outcome_tier adaptive, baseline edge cases; integration test for full split-based flow; Playwright test for split submission

### Epic 3.3: Game Settings API & Frontend Panel
- [x] **3.3.1** Create `GET/POST /api/settings` — persist/load settings from `~/.storytime/config.json`
- [x] **3.3.2** Expose all game parameters via settings API: tier prompt templates (outcome directions), scoring mode (fixed vs adaptive), stddev multipliers, fixed threshold values, paragraph length
- [x] **3.3.3** Build settings panel in frontend with toggles/sliders for all exposed parameters; store in a collapsible sidebar section

### Epic 3.4: Dev Tools
- [x] **3.4.1** Add `/simulate <CPM> [deviation]` command (prompt box + `window.simulate()` console function) — starts a real game session with split speeds faked at the given CPM (± deviation), for testing adaptive scoring
- [x] **3.4.2** Add dev-only feature flag (`config.dev_mode`) to gate simulation commands and test UI elements in future releases

### Epic 3.5: Error Handling & Resilience
- [x] **3.5.1** Graceful degradation when Ollama is down — frontend shows "Start Ollama" instruction with link; retry button
- [x] **3.5.2** Add retry logic for LLM calls (1 retry on timeout, exponential backoff)
- [x] **3.5.3** Validate LLM response (non-empty, reasonable length); fallback to cached neutral response if LLM returns garbage

### Epic 3.6: UI & UX Polishing
- [x] **3.6.1** Simulate appends to session history — `/api/simulate` stores the simulated paragraph + split speeds + outcome tier in the session so it appears in the history panel alongside real paragraphs
- [x] **3.6.2** Reorganize layout: keep `#history` for compact stats (cropped to ~20 chars, WPM, split speeds) but move it to the right side; create a new left panel that simply shows the last completed paragraph in full for story context
- [x] **3.6.3** History entries display split speeds — appended as vector `[334.2, 342.7, 200]` after the meta line in each history entry
- [x] **3.6.4** Extensive backend request/response logging — log every API request (method, path, params), every LLM request/response payload, every paragraph split boundary + split speed, every outcome tier computation (inputs, intermediate values, result); gated behind DEBUG level via `backend/logger.py`
- [x] **3.6.5** Vertical tier chart on the right side of the game area (a `<div>` inside `#history`), showing:
  - Five labeled tiers from "Very Positive" at top to "Very Negative" at bottom
  - Active tier highlighted with color (blue, green, gray, orange, red)
  - Updates per paragraph via `updateTierChart(data.outcome_tier)`
- [x] **3.6.6** Remove `min_data` / "Min data points" from settings, frontend, backend, and docs — it has no effect in the main game flow
- [x] **3.6.7** Change the initial prompt wrapper to use character count instead of "5 sentences": both `build_first_paragraph_prompt` and `build_prompt` accept `max_chars` parameter (default 200), computed as `target_split_size * 4` from settings in route handlers
- [x] **3.6.8** Write every completed paragraph to `writtenStories/<session_id>.txt` — appended on each `session_store.append_paragraph()` with paragraph number, timestamp, speed, tier, split speeds, and full text
- [x] **3.6.9** Simulate shouldn't restart the story — `sendSimulate()` auto-advances by filling the input box and calling `fetchNextParagraph()` directly with fake split speeds from `computeSplitSpeeds()`. On first call with no story, it auto-fills a default prompt, POSTs to `/api/restart`, and re-enters itself on response to trigger the auto-advance.
- [x] **3.6.10** Split-level outcome scoring — changed to σ/√N rescaling (Proposal C): paragraph-average CPM is scored against rolling stats using `effective_stddev = rolling_stddev / sqrt(N)`. Longer paragraphs have tighter effective stddev, making the same deviation more significant — mathematically principled via standard error of the mean.
- [x] **3.6.11** Written story files use slug filename — `writtenStories/<slug>_<session_id[:8]>.txt` where slug is the initial prompt lowercased, non-alphanumeric stripped, whitespace replaced with underscores, truncated to 50 chars. Empty paragraphs are skipped entirely (no file created for blank text).
- [x] **3.6.12** Clean up test-generated written stories — `test_routes_generate.py` and `test_routes_simulate.py` write real files into `writtenStories/` because their `client()` fixtures don't redirect `Path.cwd()` to a temp directory. The session unit tests (`test_session.py`) already do this correctly with `monkeypatch.setattr(Path, "cwd", lambda: tmp_path)`. Fix: add `monkeypatch` + `tmp_path` to the `client()` fixtures in both route test files, monkeypatching `Path.cwd` to `tmp_path`. After the fix, delete accumulated test artifacts from `writtenStories/` (126 files as of last check). No production code changes. Existing tests continue to pass since mocked LLM responses don't depend on real file paths.
- [x] **3.6.13** Sanitize non-typeable characters from LLM output — LLMs frequently emit accented chars (é, ü, ñ), ligatures (œ, Æ), smart quotes ("", ''), em-dashes (—), and control chars that users can't type on a US keyboard, making it impossible to match the displayed text. Fix:
  - `backend/prompt_engine.py`: add `sanitize_text(text: str) -> str` that normalizes non-ASCII chars using `unicodedata.normalize('NFKD')` to decompose accented chars, then strips combining marks. Apply an explicit replacement dict for remaining cases (œ→oe, Æ→AE, ß→ss, smart quotes→straight, dashes→hyphen, bullets→asterisk). Strip any remaining non-ASCII char not in the replacement dict. Keep: ASCII printable (0x20-0x7E), \n, \t.
  - `backend/routes/generate.py`: apply `sanitize_text()` after `parse_llm_response()` on lines 76 and 148.
  - `backend/routes/restart.py`: apply `sanitize_text()` after `parse_llm_response()` on line 38.
  - `backend/routes/simulate.py`: apply `sanitize_text()` after `parse_llm_response()` on line 81.
  - `backend/tests/test_prompt_engine.py`: add tests — accented→ascii, smart quotes→straight, em-dash→hyphen, control chars stripped, valid ASCII unchanged, idempotent.
  - `frontend/script.js` (optional): add `oninput` handler on `#inputBox` that strips non-whitelisted chars the user pastes, using regex `[^a-zA-Z0-9 .,!?'"();:\[\]{}@#$%^&*_\-+=/\\|`~<>'"'"'\n\t]`. The backend fix is primary.
- [x] **3.6.20** Convert Setup link to button with emoji + distinct background for both top-bar buttons — change `<a id="setupLink">` to `<button id="setupLink">` with a book emoji (📖). Style both `#topBar` buttons with a shared class or selector so they have a distinct `background-color` (e.g. `--bg-btn-topbar`) that differs from the container background. Affects `frontend/index.html` (replace `<a>` with `<button>`) and `frontend/style.css` (new button styles).
- [x] **3.6.21** Add `.neutral` message class and wire states — add CSS class `.neutral` for the message box (`border-color: #757575; background: #f5f5f5;` with dark-mode variants). Wire into JS: after paragraph completion in `fetchNextParagraph()`, set message to `"paragraph over! take a breather"` with `.neutral` class. On `inputBox` `input` event, if the message shows the breather text, switch to `"Typing away..."` with `.success` class. Tracks typing state via a flag `paragraphJustCompleted`.
- [x] **3.6.22** Page-load and reset message — change `reset()` from `"Enter a story prompt and click Send."` to `"Enter a story prompt and send"` and set `className = 'neutral'`. Affects `frontend/script.js` line 117-118.
- [x] **3.6.23** Story-start message flow — in `sendPrompt()`, change `"Starting story..."` to use `neutral` class. After successful restart, change message from `"Story started — type the paragraph above."` to `"Story ready, start typing the first paragraph."` with `neutral` class. When user types first character in `inputBox`, switch to `"Typing away..."` with `success` class (reuses the same input listener from 3.6.21).
- [x] **3.6.14** Reorder settings panel sections — move "Speed Display" to be directly after "Appearance", move "Word Count" to be directly after "Speed Display". Affects `frontend/index.html` (reorder `<section>` elements inside `#settingsPanel`).
- [x] **3.6.15** Collapse settings panel on save/reset — after save or reset-to-defaults succeeds, add `collapsed` class to `#settingsPanel` so it closes automatically. The message box is outside the panel, so this lets the user see the confirmation message without the settings panel blocking it. Affects `frontend/script.js` (add `settingsPanel.classList.add('collapsed')` in both the save and reset click handlers after success).
- [x] **3.6.16** Anchored buttons at bottom of settings panel — wrap all settings `<section>` elements in a scrollable div (`#settingsSections`) that takes 80% of `#settingsPanel` height, and keep `.settings-actions` outside that wrapper so the Save/Reset buttons are always visible at the bottom without scrolling. The `#settingsPanel` itself should use `display: flex; flex-direction: column;` with the scrollable div having `flex: 1; overflow-y: auto; min-height: 0;`. Affects `frontend/index.html` (add wrapper div) and `frontend/style.css` (flex layout, 80% scrollable area).
- [x] **3.6.17** Settings toggle + Setup link side-by-side at top — currently `#settingsToggle` and `#setupLink` are block elements stacked vertically inside `.container`. Wrap them in a horizontal flex container (`#topBar`) placed before the initial prompt container, so they appear side-by-side at the top of the page. Remove `align-self: flex-start` from `#settingsToggle` and `margin-left` from `#setupLink`; instead use `gap` on the flex container. Affects `frontend/index.html` (add wrapper, move elements above `#initialPromptContainer`) and `frontend/style.css` (new `#topBar` styles).
- [x] **3.6.18** Horizontal initial prompt container with button on left — wrap `#initialPrompt` and `#restartButton` in a new `#initialPromptContainer` (horizontal flex). The Send button should be on the left (CSS order), the `#initialPrompt` input fills remaining space with `flex: 1`. The container should NOT grow vertically (`flex-grow: 0; flex-shrink: 0;`). If there's already a `.container` parent, use `flex: 0 0 auto` on this child. Affects `frontend/index.html` (restructure, add container) and `frontend/style.css` (horizontal flex, no grow).
- [x] **3.6.19** textDisplay in a vertically-expanding container — wrap `#textDisplay` in a new `#textDisplayContainer` that uses `flex: 1; min-height: 0; overflow-y: auto;` to take as much vertical space as possible between `#message` and `#inputBox`. The `#textDisplay` itself should fill that container (`height: 100%`). Affects `frontend/index.html` (add wrapper) and `frontend/style.css` (flex-grow container).
- [x] **3.6.24** Diversify continuation prompts with settings UI — replace the single `OUTCOME_DIRECTIONS` string per tier with 10 alternative phrasings per tier. `build_prompt` picks a random entry from the list. Settings UI uses a dropdown to select tier, then shows editable phrasing inputs with minus buttons to delete (min 1), plus an empty input that spawns a new row when typed in. `collectSettings()` returns `dict[str, list[str]]`. API handles both old format (single string → single-element list) and new format for backward compat. Phrasings per tier (8 approved + 2 extras each).
- [x] **3.6.25** Auto-scroll text display — in `fetchNextParagraph()` and `sendPrompt()`, after setting `textDisplay.innerText`, check if `#textDisplayContainer` is within 100px of bottom before calling `scrollTop = scrollHeight`. Prevents stealing scroll from users reading earlier text.
- [x] **3.6.26** Reset simulatedCpm after one simulate shot — in `sendSimulate()`, `await fetchNextParagraph(...)` then immediately set `simulatedCpm = null` and `simulatedDeviation = 0`. The simulate generates one paragraph with fake split speeds, then the next `CheckFinishedSentence` → `computeSplitSpeeds()` uses real timestamps. No backend changes.
- [x] **3.6.27** Collapse newlines to space in parse_llm_response — add `import re`, then `raw = re.sub(r'\n+', ' ', raw)` as the last step in `parse_llm_response` before `return raw`. Any number of consecutive newlines becomes a single space. No period-space or double-space normalization.
- [x] **3.6.28** Regression test for double floor fix — add test that sets rolling=[500]*24, split_speeds=[505]*14, verifies `compute_speed_stats`→σ/√N→`compute_outcome_tier` returns tier=4. Already fixed in 3723a42.
- [x] **3.6.29** Settings already persist via `~/.storytime/config.json` — no changes needed.
- [x] **3.6.30** Reverse history order with scroll-to-top animation — history panel shows newest entry at the top. Automatically scroll to top when a new entry appears. Add a subtle animation (e.g. fade-in or slide-in) on the newest entry so it's visually distinct.
- [x] **3.6.31** Clear input resets paragraph progress — erasing the input box resets ongoing paragraph progress and split speeds so the user can retry the same paragraph for a better score. Add a retry button under "start a new story" on the right of the message div; disabled (greyed) when input is empty, enabled otherwise.
- [x] **3.6.32** Retry button styling — match the appearance of the Settings/Setup topbar buttons (same background, border, font size) when enabled. Keep the disabled (greyed) state as-is.
- [x] **3.6.33** Retry button positioning — place the retry button to the right of the message box in a horizontal flex row, not below/over it.
- [x] **3.6.34** Move settings panel above initial prompt container — reorder the DOM so `#settingsPanel` appears before `#initialPromptContainer` (still collapsible).
- [x] **3.6.35** Hide irrelevant scoring sections — when scoring mode is "adaptive", hide the "Fixed Thresholds" section. When "fixed", hide the "Adaptive Params" section. Use JS to toggle visibility on mode change and on load.
- [x] **3.6.36** Simplify fixed thresholds to 4 boundary inputs — show only 4 inputs for the CPM boundaries between tiers (tier1 low=tier0 high, tier2 low=tier1 high, etc.) instead of 10 low/high pairs. Match the tier chart concept.
- [x] **3.6.37** Reverse tier order in settings sections — in both "Adaptive Params" (σ tier 4, 3, 2, 1, 0) and "Fixed Thresholds" (boundaries between 4→3, 3→2, 2→1, 1→0), order tiers descending.
- [x] **3.6.38** Remove default avg CPM from settings — always use 300 internally. Remove the `default_avg_cpm` field from the settings UI, API, and `GameSettings` dataclass; keep a module-level constant in `game_logic.py` if still referenced.

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
- [x] **4.2.2** Wire startup messages in frontend — in `reset()` or `DOMContentLoaded`, call `GET /api/health` and set the message box based on the two booleans. Define 3 message fragments as constants and compose them into the message box.
- [x] **4.2.3** Auto-open browser on startup — after Uvicorn binds, open `http://127.0.0.1:8000` in the default browser via `webbrowser.open`. On build failure (e.g., port in use), print the URL to the terminal and skip browser open.
- [x] **4.2.4** Handle Ollama going down mid-game — if `POST /api/generate` gets a connection refused / timeout from the provider, return `503` with a structured error. Frontend already shows "Start Ollama" with retry button; verify this flow works end-to-end in a Playwright test.
- [x] **4.2.5** Add `scripts/run.sh` and `scripts/run.bat` — production launchers that run the PyInstaller binary (or fall back to `python -m backend.main` if the binary is not found), with a descriptive terminal title.

### Epic 4.3: Release Infrastructure

- [x] **4.3.1** Add `.github/workflows/release.yml` — triggered on tag push `v*.*.*`, builds all platforms, creates a GitHub Release with build artifacts and auto-generated release notes.
- [x] **4.3.2** Create `CHANGELOG.md` — manual changelog with v0.1.0 entries for all completed work.
- [x] **4.3.3** Create `CONTRIBUTING.md` — development setup, test commands, code conventions, PR workflow.
- [x] **4.3.4** Add per-platform download badges to `README.md` — shields.io badges for Windows, Linux, linked to latest release.
- [x] **4.3.5** Add `scripts/version.py` — `python scripts/version.py bump 0.2.0` rewrites `_version.py`, `pyproject.toml`, `CHANGELOG.md` and prints diff.

### Epic 4.4: Model Selection

- [x] **4.4.1** Backend model setting plumbing — add `ollama_model` field to `GameSettings`, `SettingsResponse`/`SettingsPatch`, update `registry.active_model` to use it for Ollama provider.
- [x] **4.4.2** Add thinking-tag stripping to `prompt_engine.py` (`strip_thinking`) and apply in `generate.py` route so thinking models produce clean story text.
- [x] **4.4.3** Frontend model selector — add `<select>` (populated from `/api/models`) + refresh button + default button in LLM Settings section; text-input fallback when model list unreachable; wire `ollama_model` in `loadSettings`/`collectSettings`.
- [x] **4.4.4** Update existing tests and add new tests for model selection and thinking-tag stripping.

### Epic 4.5: Community Buttons

- [x] **4.5.1** Add Bug Report (🐛, dark red tint) and Support the Dev (❤️, gold tint) buttons to topBar with styled CSS classes and URL constants in script.js.

---

## Milestone 6: Continuous Mode

Goal: Eliminate paragraph-by-paragraph pauses by pre-fetching the next half while the player finishes the current one. Redesign split tracking from per-paragraph to per-split (length-weighted CPM, rolling character window instead of split count window).

### 6.0 — Design clarification & split overhaul
- [x] Research and document the full continuous mode spec (AGENTS.md): half-paragraph overlap, Split dataclass, rolling char window, weighted stddev, outcome timing, first/last/restart/retry edge cases.
- [x] Clean up network messages: removed `speed_cpm` from `GenerateRequest`, removed `time_taken_ms`/`accuracy` usage (hardcoded to 0/1.0).
- [x] `Split` dataclass `(speed_cpm, char_count)` replacing flat `float` lists everywhere.
- [x] `RollingWindow` with `deque[Split]` + running `total_chars` capped at 2500 chars.
- [x] `compute_speed_stats` uses character-weighted mean and variance.
- [x] `compute_weighted_avg` helper added.

### 6.1 — Continuous mode frontend
- [x] `GameSettings.continuous_mode: bool` + checkbox `#optContinuousMode` in Word Count section.
- [x] Continuous mode state variables: `consumedChars`, `splitList`, `pendingText`, `fetchSent`, `fetchPending`.
- [x] `updateSplitTimestamps()`: consume at split boundaries, compute CPM, trim input, update display.
- [x] 75% fetch trigger (by split index, not char count).
- [x] `fetchNextParagraph()`: generates next paragraph, creates history entry, stores fetched text.
- [x] `advanceParagraph()`: swaps fetched text into current, resets continuous state.
- [x] `updateTextDisplay()`: offsets by `consumedChars`, shows fetched text in gray (permanent DOM spans).
- [x] `CheckFinishedSentence()`: early-return in continuous mode (first paragraph still completes normally).
- [x] `retryParagraph()` / `reset()`: clear continuous state.
- [x] Smooth scroll: `scroll-behavior: smooth` on `#textDisplayContainer`.

---

## Milestone 7: Unified Split-Consumption Mode

Goal: Merge paragraph mode and continuous mode into a single code path driven entirely by `fetchTriggerPct` (100% = no overlap, <100% = overlap). Remove all `if (continuousMode)` branches, dead flags, and the old per-char paragraph-completion logic.

### 7.0 — Validate continuous mode at 100%
Set `fetchTriggerPct = 100` and test all scenarios. Identified and fixed: computeSplits early return for short text, message flow gaps, duplicate RPCs. Deemed complete.
- [x] Start a new story → verify typing consumes at split boundaries
- [x] Reach the last split → verify fetch fires, input clears, loading message shows
- [x] Wait for response → verify new paragraph appears, input focused, message reads ready
- [x] Type the next paragraph → verify accumulation in `#completedText`
- [x] Retry → verify it resets to the current paragraph
- [x] Backspace → verify CPM timing is correct
- [x] Error on a split → verify it blocks consumption and shows red
- [x] Simulate → verify it works at 100%
- [x] Verify no duplicate RPCs fire
- [x] Fix computeSplits early return (text.length <= 50 bypassed trigger boundary logic)
- [x] Fix message flow: swap branch now shows "Paragraph ready — take a breather", first keystroke flips to "Typing away..."

### 7.1 — Remove paragraph mode, unify all paths
Remove all `if (continuousMode)` branches: assume continuous mode is always on. Eliminate dead code from old paragraph mode.
- [x] Remove `continuousMode` variable — replace all `if (continuousMode)` branches with unconditional code
- [x] Remove `continuous_mode` from `GameSettings`, `SettingsResponse`, `SettingsPatch`, frontend setting load/save/collect, HTML checkbox
- [x] Unify split tracking: `updateSplitTimestamps()` always calls the continuous version
- [x] Remove old per-char `updateSplitTimestamps` (the non-continuous version)
- [x] Remove `CheckFinishedSentence()` — split consumption handles completion
- [x] Remove `paragraphJustCompleted` flag entirely
- [x] Unify `advanceParagraph()` — single path without `if (continuousMode)` branch
- [x] Unify `updateTextDisplay()` — always use permanent DOM spans, remove innerHTML rebuild path
- [x] Unify `retryParagraph()` — single path, no `if (continuousMode)` branch
- [x] Unify `fetchNextParagraph()` — old dead function deleted
- [x] Unify input handler — remove `CheckFinishedSentence()` call, remove `paragraphJustCompleted` branches
- [x] Remove `resetSplitTracking()` — dead once paragraph mode is gone
- [x] Unify `sendSimulate()` — single path without `if (continuousMode)` branch
- [x] Remove `CalculateSpeed()`, `GetTimeTakenDisplay()`, `GetSpeedDisplay()` — dead once paragraph mode is gone
- [x] 207 tests pass (202 backend + 5 Playwright)

### 7.2 — Rename "prefetch" to "fetch"
After unification, "prefetch" is a misnomer — it's just fetching the next paragraph, whether triggered at 100% or <100%. Rename all identifiers.
- [x] Rename `sendPrefetch()` → `fetchNextParagraph()`
- [x] Rename `prefetchedText` → `pendingText`
- [x] Rename `prefetchSent` → `fetchSent`
- [x] Rename `prefetchPending` → `fetchPending`
- [x] Rename `prefetchTriggerIndex` → `fetchTriggerIndex`
- [x] Rename `prefetchTriggerPct` → `fetchTriggerPct`
- [x] Rename `#prefetchSpan` → `#pendingSpan`
- [x] Rename `#optPrefetchPct` → `#optFetchPct`
- [x] Rename `prefetch_trigger_pct` → `fetch_trigger_pct` in backend Settings API
- [x] Update HTML label: "Prefetch trigger (%)" → "Fetch trigger (%)"
- [x] Update all documentation (PLAN.md, AGENTS.md)

### 7.3 — Clean up dead code and update tests
- [x] Remove dead functions: `resetSplitTracking()`, `CheckFinishedSentence()`, old `fetchNextParagraph`
- [x] Remove dead flags: `paragraphJustCompleted`, `continuousMode`
- [x] Remove old display code (innerHTML path), unused `displayedText` variable
- [x] Remove `#optContinuousMode` checkbox from HTML
- [x] Update fetch trigger label in settings to reflect unified behavior
- [x] Remove `continuous_mode` from backend `GameSettings`, `SettingsResponse`, `SettingsPatch`
- [x] Update Playwright test for continuous mode (includes + not ===, add fetch_trigger_pct to mock)
- [x] 207 tests pass
