# Story Time — Development Plan

> **Status key**: `[ ]` pending, `[x]` completed, `[~]` in progress. Completed milestones are archived in `docs/previous-milestones.md`.
> **Agent instructions**: See `AGENTS.md`.


## Backlog
Tasks that don't belong to a milestone yet. Assign to a milestone when ready to work on them.
- [ ] Brainstorm a new project name ("StoryTime" is very common). Candidates: Write-a-story, typerLuck, interactiveTyper, QuickTypeFunTimes, Good Type Good Story.


## Bugs

- [x] Split CPM uses character count, not character intervals. `updateSplitTimestamps()` computes `cpm = splitChars / minutes`, but the elapsed time spans `splitChars - 1` inter-key intervals on the first split of a paragraph (first keystroke → boundary keystroke), and each pause gap removes another measurable interval, while the formula always counts `splitChars`. This inflates speed by C/(C−1) (~2% at 50 chars) on each paragraph's first split, and more once pause exclusion lands. No compensation exists in the backend — `compute_speed_stats`/`compute_weighted_avg` in `game_logic.py` use `speed_cpm` as-is. Fix: measure intervals — `cpm = (splitChars - (freshStart ? 1 : 0) - pauseGapCount) / activeMinutes` — while keeping `char_count` = real chars (rate-only correction). Confirm behavior for: first split in non-continuous mode (fetch_trigger_pct=100), subsequent paragraphs, first split in continuous mode, split junction in continuous mode (carried-over timestamp after fetch), single-split paragraphs, mid-paragraph input-clear / retry resets, and pause handling (auto-idle ≥5s + manual).
- [x] Fetch trigger (%) was only bounded by HTML `min`/`max` attributes, so values outside 10–100 could be typed, saved, and loaded. Now the UI clamps saved/loaded values, the settings API rejects out-of-range values with 422, and legacy config values are clamped on load.

## Milestone 5: Juice & User Profiles

Goal: Add sound effects, animations, and per-user split tracking to make the game feel polished and personal.

### 5.1 — Sound effects
- [ ] Typewriter click sound per character typed (low-volume, mechanical key press)
- [ ] Paragraph-completion jingle that varies by tier (tier 5/4 = epic fanfare, tier 3 = neutral chime, tier 2-0 = failure tone)
- [ ] Settings: master enable/disable toggle, volume slider, separate toggle for per-character sounds vs completion sounds

### 5.2 — Animations
- [ ] Paragraph-completion animation varying by tier (screen flash, text glow, confetti for high tiers; shake/dim for low tiers)
- [ ] Settings: enable/disable animations, optional intensity preference
- [ ] Animate tier chart transitions so repeated tiers are distinguishable (no sudden jumps — e.g. slide/fade between states)

### 5.3 — Split history
- [x] Store rolling split history (not per story/session)
- [x] Flush the split history

### 5.4 — Branding & UI polish
- [x] Text viewer renders each paragraph as its own block with vertical spacing instead of one continuous run of text.
- [x] Removed the artificial leading space prepended to fetched paragraphs; paragraph separation is visual only.
- [x] Leading whitespace typed at the start of a paragraph is ignored while typing.
- [x] Removed the "Story Context" left pane; the text viewer now provides story context and the typing area expands into the freed space.
- [ ] Game title in the topbar as a link to `/` (acts as a refresh button)
- [ ] Design a game logo (SVG)
- [ ] Redesign the favicon (SVG)

### 5.5 — Bug fixes
- [x] LLM model setting: default value updated to "llama3.2:latest" so the dropdown doesn't go blank when Ollama is running
- [x] Starting a new story now clears the story context pane

### 5.6 — Settings UX improvements
- [x] Word count preview: show a Lorem Ipsum sample that updates live as the word count slider/input changes

### 5.7 — Custom prompt templates

Goal: let players replace the opening and continuation prompt wrappers so the generated story can follow any structure, not just the default interactive-story framing. Full design: [`docs/technical-design/07-prompt-templates.md`](docs/technical-design/07-prompt-templates.md).

- [ ] **5.7.1** Add template defaults and rendering to `backend/prompt_engine.py`: `DEFAULT_INITIAL_PROMPT_TEMPLATE`, `DEFAULT_CONTINUATION_PROMPT_TEMPLATE`, `render_prompt_template()` (replace known `{premise}`, `{history}`, `{direction}`, `{tier}`, `{max_words}` only; preserve unknown tokens verbatim; blank template falls back to default), and optional `template=` args on both prompt builders. Add unit tests for default parity, custom templates, unknown-token preservation, and blank fallback.
- [ ] **5.7.2** Persist both templates through settings: add `initial_prompt_template` and `continuation_prompt_template` to `GameSettings`, normalize non-string/blank values on load, and add both fields to `SettingsResponse` / `SettingsPatch` (max 8000 chars). Add tests for defaults, save/load roundtrip, and legacy configs missing the fields.
- [ ] **5.7.3** Add `POST /api/settings/preview` returning the fully rendered prompt for either template kind using the production renderer and sample premise/history/direction/tier/word count. Add API tests for opening, continuation, and preserved unknown tokens.
- [ ] **5.7.4** Wire stored templates into `routes/generate.py` (opening + continuation), `routes/restart.py` (opening), and both `routes/simulate.py` branches (continuation). Add route tests asserting the custom template text reaches the provider.
- [ ] **5.7.5** Add the frontend settings section: two textareas, placeholder legends, per-template "Restore default" buttons, mirrored defaults in `SETTINGS_DEFAULTS`, `loadSettings()` / `collectSettings()` wiring, length-only client validation, and API error-detail surfacing. Add Playwright coverage for loading, saving, and resetting both templates.
- [ ] **5.7.6** Add live previews under each textarea using debounced `POST /api/settings/preview` (refresh when `paragraph_word_count` changes) so the user sees the exact LLM-facing text, including literal unknown placeholders. Add Playwright coverage for live updates and token preservation.
- [ ] **5.7.7** Update `docs/technical-design/03-backend-design.md`, `docs/technical-design/02-frontend-design.md`, `docs/development-process/runbook.md`, and `CHANGELOG.md`; run the full backend and frontend suites.


