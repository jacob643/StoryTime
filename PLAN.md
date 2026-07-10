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
- [x] Continuous mode state variables: `consumedChars`, `splitList`, `prefetchedText`, `prefetchSent`, `prefetchPending`.
- [x] `updateSplitTimestampsContinuous()`: consume at split boundaries, compute CPM, trim input, update display.
- [x] 75% prefetch trigger (by char count `consumedChars + inputBox.value.length`).
- [x] `sendPrefetch()`: generates next paragraph, creates history entry, stores prefetched text.
- [x] `advanceParagraph()`: swaps prefetched text into current, resets continuous state.
- [x] `updateTextDisplay()`: offsets by `consumedChars`, shows prefetched text in gray.
- [x] `CheckFinishedSentence()`: early-return in continuous mode (first paragraph still completes normally).
- [x] `retryParagraph()` / `reset()`: clear continuous state.
- [x] Smooth scroll: `scroll-behavior: smooth` on `#textDisplayContainer`.

## Milestone 7: Unified Split-Consumption Mode

Goal: Merge paragraph mode and continuous mode into a single code path driven entirely by `prefetchTriggerPct` (100% = no overlap, <100% = overlap). Remove all `if (continuousMode)` branches, dead flags, and the old per-char paragraph-completion logic.

### 7.0 — Validate continuous mode at 100%

Set `prefetchTriggerPct = 100` and manually test all scenarios. Identify behavioral gaps before removing paragraph mode.

- [ ] Start a new story → verify typing consumes at split boundaries
- [ ] Reach the last split → verify prefetch fires, input clears, loading message shows
- [ ] Wait for response → verify new paragraph appears, input focused, message reads ready
- [ ] Type the next paragraph → verify accumulation in `#completedText`
- [ ] Retry → verify it resets to the current paragraph
- [ ] Backspace → verify CPM timing is correct
- [ ] Error on a split → verify it blocks consumption and shows red
- [ ] Simulate → verify it works at 100%
- [ ] Verify no duplicate RPCs fire
- [ ] **TBD:** Input behavior during prefetch load (cleared+blocked vs allow typing ahead) — decide after testing.
- [ ] Fix any issues found during testing

### 7.1 — Remove paragraph mode, unify all paths

- [ ] Remove `continuousMode` variable — `prefetchTriggerPct` is the single control; replace all `if (continuousMode)` branches with unconditional code
- [ ] Remove `continuous_mode` from `GameSettings`, `SettingsResponse`, `SettingsPatch`, frontend setting load/save/collect, HTML checkbox
- [ ] Unify split tracking: `updateSplitTimestamps()` always calls `updateSplitTimestampsContinuous()` (rename it to `updateSplitTimestamps`)
- [ ] Remove old per-char `updateSplitTimestamps` (the non-continuous version)
- [ ] Remove `CheckFinishedSentence()` — split consumption handles completion
- [ ] Remove `paragraphJustCompleted` flag from `reset()`, `advanceParagraph()`, `fetchNextParagraph()`, `retryParagraph()`, input handler
- [ ] Unify `advanceParagraph()` — single path: if waiting for prefetch → clear input + show loading; if prefetch ready → accumulate in `#completedText`, swap text, reset state
- [ ] Unify `updateTextDisplay()` — always use permanent DOM spans, remove `if (continuousMode)` guard
- [ ] Remove `_contDisplayInit` — unconditional first-render init
- [ ] Remove old `innerHTML` rebuild path in `updateTextDisplay()`
- [ ] Unify `retryParagraph()` — single path, no `if (continuousMode)` branch
- [ ] Unify `fetchNextParagraph()` — remove `if (continuousMode)` branch for post-RPC behavior
- [ ] Unify input handler — remove `CheckFinishedSentence()` call, remove `paragraphJustCompleted` branches
- [ ] Remove `resetSplitTracking()` — dead once paragraph mode is gone

### 7.2 — Rename "prefetch" to "fetchNextParagraph"

After the unification, "prefetch" is a misnomer — it's just fetching the next paragraph, whether triggered at 100% or <100%. Rename for clarity:

- [ ] Rename `sendPrefetch()` → `fetchNextParagraph()` (merge with existing `fetchNextParagraph` or rename both)
- [ ] Rename `prefetchedText` → `nextText` or `pendingText`
- [ ] Rename `prefetchSent` → `fetchSent`
- [ ] Rename `prefetchPending` → `fetchPending`
- [ ] Rename `prefetchTriggerIndex` → `triggerBoundaryIndex` or `fetchTriggerIndex`
- [ ] Rename `prefetchTriggerPct` → `triggerPct` or `fetchTriggerPct`
- [ ] Update CSS/HTML `#prefetchSpan` → `#nextParagraphSpan` or keep with new semantic meaning
- [ ] Update `SHOW_PREFETCH` or related CSS classes

### 7.3 — Clean up dead code and settings

- [ ] Remove dead functions: `resetSplitTracking()`, `CheckFinishedSentence()`, old `updateSplitTimestamps()`
- [ ] Remove dead flags: `paragraphJustCompleted`, `_contDisplayInit`, `continuousMode`
- [ ] Remove old display code (innerHTML path)
- [ ] Remove `#optContinuousMode` checkbox from HTML
- [ ] Update prefetch trigger label in settings to reflect unified behavior
- [ ] Remove `continuous_mode` from backend `GameSettings`, `SettingsResponse`, `SettingsPatch`, collectSettings mapping
- [ ] Update tests — remove references to `continuous_mode`, update function names
- [ ] Update `CHANGELOG.md`
