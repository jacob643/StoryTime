# Changelog

All notable changes to this project will be documented in this file.

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
