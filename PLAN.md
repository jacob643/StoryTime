# Story Time — Development Plan

> **Status key**: `[ ]` pending, `[x]` completed, `[~]` in progress. Completed milestones are archived in `previous-milestones.md`.
> **Agent instructions**: See `AGENTS.md`.



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

### 5.3 — User profiles
- [ ] Store rolling split history per user (not per story/session)
- [ ] Create new user (name input)
- [ ] Select active user from a list
- [ ] Delete user (with confirmation)
- [ ] Flush split history for current user (without deleting the user)
- [ ] User management UI in settings panel or topbar

### 5.4 — Branding & UI polish
- [ ] Game title in the topbar as a link to `/` (acts as a refresh button)
- [ ] Design a game logo (SVG)
- [ ] Redesign the favicon (SVG)

### 5.5 — Bug fixes
- [x] LLM model setting: default value updated to "llama3.2:latest" so the dropdown doesn't go blank when Ollama is running
- [x] Starting a new story now clears the story context pane

### 5.6 — Settings UX improvements
- [x] Word count preview: show a Lorem Ipsum sample that updates live as the word count slider/input changes

## Milestone 6: Continuous Mode

Goal: Eliminate paragraph-by-paragraph pauses by pre-fetching the next half while the player finishes the current one. Redesign split tracking from per-paragraph to per-split (length-weighted CPM, rolling character window instead of split count window).

### 6.0 — Design clarification & split overhaul
- [x] Research and document the full continuous mode spec (AGENTS.md): half-paragraph overlap, Split dataclass, rolling char window, weighted stddev, outcome timing, first/last/restart/retry edge cases.
- [x] Clean up network messages: removed `speed_cpm` from `GenerateRequest`, removed `time_taken_ms`/`accuracy` usage (hardcoded to 0/1.0).
- [x] `Split` dataclass `(speed_cpm, char_count)` replacing flat `float` lists everywhere.
- [x] `RollingWindow` with `deque[Split]` + running `total_chars` capped at 2500 chars.
- [x] `compute_speed_stats` uses character-weighted mean and variance.
- [x] `compute_weighted_avg` helper added.
- [ ] Brainstorm a new project name ("StoryTime" is very common). Candidates: Write-a-story, typerLuck, interactiveTyper, QuickTypeFunTimes, Good Type Good Story.
- [ ] Auto-pause: 5 seconds of inactivity pauses the speed capture (doesn't affect metrics). Button and/or keyboard shortcut for manual pause too. Needed for continuous mode.

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
