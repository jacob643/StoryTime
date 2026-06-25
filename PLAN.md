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
- [ ] LLM model setting: when starting with no Ollama and clicking the default button, two input boxes appear at once

### 5.6 — Settings UX improvements
- [ ] Word count preview: show a Lorem Ipsum sample that updates live as the word count slider/input changes

## Milestone 6: Continuous Mode

Goal: Eliminate paragraph-by-paragraph pauses by pre-fetching the next half while the player finishes the current one. Redesign split tracking from per-paragraph to per-split (length-weighted CPM, rolling character window instead of split count window).

### 6.0 — Design clarification
- [ ] Research and document the full continuous mode spec: half-paragraph overlap, split representation (CPM + char length), rolling char window, how stddev is length-weighted, when outcomes are computed, how the UI transitions between halves, and edge cases (first half, last half, restart, retry)
