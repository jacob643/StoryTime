# Story Time — Development Plan

> **Agent instructions**: When you complete a task, mark it `[x]` and update any affected documentation in `docs/`. Do not modify this file's structure or remove completed milestones — only check boxes and add new tasks. Cross-reference all work against `docs/technical-design/` to ensure consistency with the architecture decisions. **When implementing a task, always add or update the corresponding tests** (pytest for backend, Playwright for frontend). Keep existing tests passing.
>
> **Status key**: `[ ]` pending, `[x]` completed, `[~]` in progress

## Milestone 1: Hello World Infrastructure

Goal: A minimal end-to-end pipeline — FastAPI backend serves a static page, connects to Ollama, and returns LLM-generated text to the browser. No typing game logic yet, just proving the chain works.

### Epic 1.1: FastAPI Static Server
- [ ] Task: Create `backend/` project skeleton — `main.py` (FastAPI app + static mount), `config.py` (Pydantic settings), `requirements.txt`, and entry point with Uvicorn launcher + auto-open browser
- [ ] Task: Set up `backend/tests/` with pytest + FastAPI TestClient; add a test that the server starts and `GET /` returns the frontend page successfully

### Epic 1.2: Basic Ollama Connection
- [ ] Task: Create `backend/providers/ollama.py` with a basic OllamaProvider class (generate + is_available) and `backend/routes/generate.py` exposing `POST /api/generate`
- [ ] Task: Write mocked unit tests for OllamaProvider (using httpx mock) — test generate returns expected text, is_available returns true/false based on HTTP status

### Epic 1.3: Simple "Send Prompt → Get Response" Page
- [ ] Task: Build minimal frontend page — an input field, submit button, and response area, with JS `fetch` to `POST /api/generate` and display the result
- [ ] Task: Add Playwright smoke test (`pip install pytest-playwright && playwright install chromium`) that opens the page, types a prompt, clicks submit, and verifies no console errors or network failures

---

## Milestone 2: Working Game Loop

Goal: The game runs end-to-end — typing speed drives the story via the 5-tier prompt system.

### Epic 2.1: Game Session & Prompt Engine
- Session management, story history, speed-to-outcome mapping, prompt templates

### Epic 2.2: Frontend Typing Game
- Adapt existing typing UI (character highlighting, timer, CPM/WPM) to use backend API

### Epic 2.3: End-to-End Game Flow
- Wire typing completion → speed calculation → outcome tier → LLM call → next paragraph display

---

## Milestone 3: Polished User Experience

Goal: Model discovery, settings persistence, error handling, and a clean UI for configuring the LLM provider.

### Epic 3.1: Provider System
- Ollama auto-discovery, custom endpoint support, provider registry

### Epic 3.2: Settings UI
- Model selector, custom endpoint config, paragraph length, CPM/WPM toggle persisted

### Epic 3.3: Error Handling & Resilience
- Graceful degradation when Ollama is down, timeouts, retries, user-facing error messages

### Epic 3.4: Story History & Session UX
- History sidebar wire-up, session persistence, restart flow

---

## Milestone 4: Ship Ready

Goal: Friends and family can download and run the game with zero Python knowledge.

### Epic 4.1: PyInstaller Packaging
- Cross-platform build scripts, GitHub Actions CI

### Epic 4.2: Startup & Onboarding
- Ollama detection on startup, auto-open browser, first-run experience

### Epic 4.3: Release Infrastructure
- GitHub Releases, per-platform downloads, contributor docs
