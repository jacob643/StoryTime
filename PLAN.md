# Story Time — Development Plan

> **Agent instructions**: When you complete a task, mark it `[x]` and update any affected documentation in `docs/`. When a milestone is fully completed, move it to `previous-milestones.md` to keep this file lean. Cross-reference all work against `docs/technical-design/` and `docs/development-process/` to ensure consistency with the architecture decisions and runbook. **When implementing a task, always add or update the corresponding tests** (pytest for backend, Playwright for frontend). Keep existing tests passing. **Commit after each single task** (e.g., after 3.4.1, then 3.4.2) — never batch multiple tasks into one commit.
>
> **Status key**: `[ ]` pending, `[x]` completed, `[~]` in progress. Completed milestones are archived in `previous-milestones.md`.

## Milestone 3: Polished User Experience

Goal: Adaptive speed scoring, customizable game parameters, settings UI, dev tools, and robust error handling.

### Epic 3.1: Provider System
- [x] **3.1.1** Add custom OpenAI-compatible endpoint provider alongside Ollama
- [x] **3.1.2** Add `GET /api/models` endpoint that discovers models from active providers
- [x] **3.1.3** Build provider registry with fallback logic

### Epic 3.2: Adaptive Speed Scoring
- [x] **3.2.1** Create `ScoringParams` dataclass + `compute_speed_stats()` + `split_text()` in `game_logic.py` — 50-char target split, 30-char minimum, rolling window of 20 split-speeds, symmetric ±1.5σ/±0.5σ tiers
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

---

## Milestone 4: Ship Ready

Goal: Friends and family can download and run the game with zero Python knowledge.

### Epic 4.1: PyInstaller Packaging
- Cross-platform build scripts, GitHub Actions CI

### Epic 4.2: Startup & Onboarding
- Ollama detection on startup, auto-open browser, first-run experience

### Epic 4.3: Release Infrastructure
- GitHub Releases, per-platform downloads, contributor docs
