# Story Time — Development Plan

> **Status key**: `[ ]` pending, `[x]` completed, `[~]` in progress. Completed milestones are archived in `docs/previous-milestones.md`.
> **Agent instructions**: See `AGENTS.md`.


## Backlog
Tasks that don't belong to a milestone yet. Assign to a milestone when ready to work on them.
- [ ] Brainstorm a new project name ("StoryTime" is very common). Candidates: Write-a-story, typerLuck, interactiveTyper, QuickTypeFunTimes, Good Type Good Story.


## Bugs

- [x] Split CPM uses character count, not character intervals. `updateSplitTimestamps()` computes `cpm = splitChars / minutes`, but the elapsed time spans `splitChars - 1` inter-key intervals on the first split of a paragraph (first keystroke → boundary keystroke), and each pause gap removes another measurable interval, while the formula always counts `splitChars`. This inflates speed by C/(C−1) (~2% at 50 chars) on each paragraph's first split, and more once pause exclusion lands. No compensation exists in the backend — `compute_speed_stats`/`compute_weighted_avg` in `game_logic.py` use `speed_cpm` as-is. Fix: measure intervals — `cpm = (splitChars - (freshStart ? 1 : 0) - pauseGapCount) / activeMinutes` — while keeping `char_count` = real chars (rate-only correction). Confirm behavior for: first split in non-continuous mode (fetch_trigger_pct=100), subsequent paragraphs, first split in continuous mode, split junction in continuous mode (carried-over timestamp after fetch), single-split paragraphs, mid-paragraph input-clear / retry resets, and pause handling (auto-idle ≥5s + manual).

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
- [ ] Game title in the topbar as a link to `/` (acts as a refresh button)
- [ ] Design a game logo (SVG)
- [ ] Redesign the favicon (SVG)

### 5.5 — Bug fixes
- [x] LLM model setting: default value updated to "llama3.2:latest" so the dropdown doesn't go blank when Ollama is running
- [x] Starting a new story now clears the story context pane

### 5.6 — Settings UX improvements
- [x] Word count preview: show a Lorem Ipsum sample that updates live as the word count slider/input changes


