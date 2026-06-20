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
- [x] **3.6.10** Split-level outcome scoring — `_compute_first_paragraph_tier` and `_compute_subsequent_tier` now score each split individually against rolling stats and return `min()` of all split tiers. This favors consistency: one slow split drags the whole paragraph down.
- [x] **3.6.11** Written story files use slug filename — `writtenStories/<slug>_<session_id[:8]>.txt` where slug is the initial prompt lowercased, non-alphanumeric stripped, whitespace replaced with underscores, truncated to 50 chars. Empty paragraphs are skipped entirely (no file created for blank text).
- [ ] **3.6.12** Clean up test-generated written stories — running the test suite leaves behind `writtenStories/*.txt` files (untitled slugs, generic one-paragraph stories). Find a way to prevent or clean these up so the directory stays clean during development.

---

## Milestone 4: Ship Ready

Goal: Friends and family can download and run the game with zero Python knowledge.

### Epic 4.1: PyInstaller Packaging
- Cross-platform build scripts, GitHub Actions CI

### Epic 4.2: Startup & Onboarding
- Ollama detection on startup, auto-open browser, first-run experience

### Epic 4.3: Release Infrastructure
- GitHub Releases, per-platform downloads, contributor docs
