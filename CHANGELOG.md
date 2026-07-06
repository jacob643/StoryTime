# Changelog

All notable changes to this project will be documented in this file.


## [Unreleased]
### Added
- Continuous mode: prefetch next paragraph at 75% typing progress, smooth-scrolling text display, split consumption at boundaries without interrupting typing.
- Continuous mode checkbox in settings (Word Count section).
- `isContinuousMode()` helper, `updateSplitTimestampsContinuous()`, `sendPrefetch()`, `advanceParagraph()` in frontend.
- `consumedChars`, `splitList`, `prefetchedText`, `prefetchSent`, `prefetchPending` state variables for continuous mode.
- Prefetched text shown in gray below current paragraph text.
- `scroll-behavior: smooth` on text display container.
- Automatic retry-button enable in continuous mode.
### Changed
### Deprecated
### Removed
- `min_split_size` setting / `MIN_SPLIT_SIZE` constant — backend handles variable-sized splits, no minimum required.
### Fixed
- Backend tests pass (203) with Split dataclass and rolling window.
### Security

## [0.2.2] - 2026-06-26

### Added
- word count preview tooltip with live Lorem Ipsum (shows on input, hides after 3s or on blur).
### Changed
### Deprecated
### Removed
### Fixed
- default model changed to "llama3.2:latest" so dropdown doesn't go blank on default click.
- new story now clears the story context pane.

## [0.2.1] - 2026-06-24

- Fix release flow.

## [0.2.0] - 2025-06-24

### Added
- macOS build support in CI (GitHub Actions matrix now includes `macos-latest`).

### Changed
- Story context left panel now appends all completed paragraphs instead of replacing the last one.
- History items redesigned to multi-line labeled format (tier label, speed + time, split progression).
- History shows speed delta (↑/↓) vs previous paragraph for paragraph 2 onward.
- Min stddev label clarified: "per split" instead of "per 50-char split".
- Changelog, contributing guide, and release infrastructure documented.

### Removed
- Split direction label ("increasing"/"decreasing") from history — arrows in the split chain already convey progression.

## [0.1.0] - 2025-06-24

### Added
- Initial release: interactive typing game powered by local LLMs.
- First paragraph generation from a user prompt via Ollama or OpenAI‑compatible providers.
- Paragraph typing with split‑based speed tracking (adaptive z‑score or fixed threshold scoring).
- 5 outcome tiers (very negative → very positive) with customizable prompt directions per tier.
- Provider system: Ollama (default), custom OpenAI‑compatible endpoint, mock LLM for development.
- Settings panel with live preview, reset to defaults, per‑field default‑value buttons.
- WPM/CPM display toggle, dark mode, retry paragraph button.
- Tier prompt editor (add/remove phrasing entries inline).
- Temperature, top_k, and top_p sampling controls.
- Story simulation endpoint (`simulate(cpm, deviation)`) for testing.
- Session history with rolling split window (max 50).
- Automatic config creation on first launch.
- Startup health check with contextual messages (first visit, Ollama status).
- Auto‑open browser 1.5s after server starts.
- Getting started guide.
- Technical design documentation (paragraph scoring, backend design, distribution/packaging).
- PyInstaller binary packaging (one‑file, bundles frontend).
- Build pipeline: `scripts/build.py`, `scripts/smoke_test.py`, `build.bat`/`build.sh`.
- CI: GitHub Actions workflow for Ubuntu and Windows builds.
- Production launchers (`scripts/run.sh`, `scripts/run.bat`) with python fallback.
- Dev launchers (`backend/run.sh`, `backend/run.bat`).
- Debug logging with `--verbose`/`-v` flag.
- Model selection: dropdown of installed Ollama models with text‑input fallback and refresh button.
- Thinking‑tag stripping (`<thinking>`, `[thinking]`, etc.) for compatibility with reasoning models.
- Ignore case setting for case‑insensitive typing.
- Cascading failure highlighting: all characters after the first mistake show red.
- Bug Report (🐞) and Support the Dev (❤️) buttons in top bar.
