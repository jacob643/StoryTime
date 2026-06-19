# Story Time — Development Plan

> **Agent instructions**: When you complete a task, mark it `[x]` and update any affected documentation in `docs/`. Do not modify this file's structure or remove completed milestones — only check boxes and add new tasks. Cross-reference all work against `docs/technical-design/` and `docs/development-process/` to ensure consistency with the architecture decisions and runbook. **When implementing a task, always add or update the corresponding tests** (pytest for backend, Playwright for frontend). Keep existing tests passing.
>
> **Status key**: `[ ]` pending, `[x]` completed, `[~]` in progress

## Milestone 1: Hello World Infrastructure

Goal: A minimal end-to-end pipeline — FastAPI backend serves a static page, connects to Ollama, and returns LLM-generated text to the browser. No typing game logic yet, just proving the chain works.

### Epic 1.1: FastAPI Static Server
- [x] **1.1.1** Create `backend/` project skeleton — `main.py` (FastAPI app + static mount), `config.py` (Pydantic settings), `requirements.txt`, and entry point with Uvicorn launcher + auto-open browser
- [x] **1.1.2** Set up `backend/tests/` with pytest + FastAPI TestClient; add a test that the server starts and `GET /` returns the frontend page successfully

### Epic 1.2: Basic Ollama Connection
- [x] **1.2.1** Create `backend/providers/ollama.py` with a basic OllamaProvider class (generate + is_available) and `backend/routes/generate.py` exposing `POST /api/generate`
- [x] **1.2.2** Write mocked unit tests for OllamaProvider (using httpx mock) — test generate returns expected text, is_available returns true/false based on HTTP status

### Epic 1.3: Simple "Send Prompt → Get Response" Page
- [x] **1.3.1** Build minimal frontend page — an input field, submit button, and response area, with JS `fetch` to `POST /api/generate` and display the result
- [x] **1.3.2** Add Playwright smoke test (`pip install pytest-playwright && playwright install chromium`) that opens the page, types a prompt, clicks submit, and verifies no console errors or network failures
- [x] **1.3.3** Fix `GET /favicon.ico` 404 — add a small SVG favicon to `frontend/` and reference it in `index.html`

> **Note**: Each prompt currently starts a new conversation — no story history is passed to the LLM. Session management and context threading are the first tasks in M2.

---

## Milestone 2: Working Game Loop

Goal: The game runs end-to-end — typing speed drives the story via the 5-tier prompt system.

### Epic 2.1: Game Session & Prompt Engine

- [x] **2.1.1** Create `backend/session.py` — `GameSession` and `ParagraphRecord` dataclasses, in-memory dict store indexed by `session_id` (UUID), with create/get/append methods
- [x] **2.1.2** Create `backend/prompt_engine.py` — `build_prompt()` that takes the initial prompt, story history (list of paragraph texts), and an outcome tier (0–4), and assembles a prompt string using the 5-tier templates (docs expect user/assistant formatting or plain text; LLM agent should pick based on `docs/technical-design/`)
- [x] **2.1.3** Create `backend/game_logic.py` — `compute_outcome_tier(speed_cpm) -> int` mapping CPM thresholds to 5 tiers (very negative → very positive), with configurable threshold constants
- [x] **2.1.4** Add session context to `POST /api/generate` — accept optional `session_id`/`speed_cpm` fields; auto-create session if new; on subsequent calls append previous paragraph to story history before calling LLM

### Epic 2.2: Frontend Typing Game

- [x] **2.2.1** Rewrite frontend typing engine — on paragraph completion, send `{session_id, speed_cpm}` to `POST /api/generate`, receive next paragraph, display it as the text to type; remove random string generation
- [x] **2.2.2** Wire initial prompt flow — on "Send" or page load, call `/api/generate` to get the first story paragraph and display it in `#textDisplay`; integrate the typing box/character highlighting/timer/CPM-WPM display with the new API-driven flow
- [x] **2.2.3** Add story history sidebar — after each completed paragraph, append the typed text, time, and speed to the `#history` sidebar

### Epic 2.3: End-to-End Game Flow

- [x] **2.3.1** Wire the full loop — initial prompt → first paragraph appears → user types it → speed_cpm sent → backend computes outcome tier → LLM returns next paragraph → user types again; verify with a full Playwright integration test that mocks the LLM and asserts the typing flow works
- [x] **2.3.2** Add restart flow — clicking "Restart" sends a new initial prompt, clears the session history on both frontend and backend, and fetches a fresh first paragraph

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
