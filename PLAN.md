# Story Time — Development Plan

> **Status key**: `[ ]` pending, `[x]` completed, `[~]` in progress. Completed milestones are archived in `docs/previous-milestones.md`.
> **Agent instructions**: See `AGENTS.md`.


## Backlog
Tasks that don't belong to a milestone yet. Assign to a milestone when ready to work on them.
- [ ] Brainstorm a new project name ("StoryTime" is very common). Candidates: Write-a-story, typerLuck, interactiveTyper, QuickTypeFunTimes, Good Type Good Story.
- [ ] Auto-pause: 5 seconds of inactivity pauses the speed capture (doesn't affect metrics). Button and/or keyboard shortcut for manual pause too. Needed for continuous mode.


## Bugs
- [ ] scoring mode default button shows "(splits)" when it should show "adaptive"
- [ ] scoring mode adaptive shouldn't also have "(splits)" in the name
- [ ] scoring mode clicking on default button to set to adaptive doesn't change the settings from fixed thresholds to the adaptive std-dev settings like when we manually click the dropdown.


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
- [x] Store rolling split history (not per story/session)
- [x] flush the split history
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


