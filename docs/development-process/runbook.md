# Runbook

## Prerequisites

- Python 3.13+ installed
- `backend/requirements.txt` installed (`pip install -r backend/requirements.txt`)

## Available Scripts

All scripts live in `backend/` and should be run from the project root.

| Goal | Bash | Windows Cmd/PowerShell |
|---|---|---|
| Start dev server | `backend/run.sh` | `backend\run.bat` |
| Run tests | `backend/test.sh` | `backend\test.bat` |

Both scripts automatically activate the virtual environment (`.venv/`).

### Passing arguments

Append extra arguments after the script name, e.g.:

```bash
backend/test.sh -v                           # verbose
backend/test.sh -x backend/tests/test_config.py  # run a specific file
```

The server starts at `http://127.0.0.1:8000` and opens the browser automatically.

## Dev Mode

Enable dev tools by setting the environment variable before starting the server:

```bash
# Bash (Linux/macOS/Git Bash)
export STORYTIME_DEV_MODE=true
backend/run.sh

# Windows Cmd
set STORYTIME_DEV_MODE=true
backend\run.bat

# PowerShell
$env:STORYTIME_DEV_MODE="true"
backend\run.bat
```

### Available Dev Tools

**`/simulate <CPM>`** — Type into the prompt box to start a real game session where the paragraph's split speeds are **faked** around the given CPM ± 20 WPM (± 100 CPM, random), never below 1 CPM. This lets you test adaptive scoring without having to type at a specific speed.

- Example: `/simulate 85` — each split speed will be a random value between 1 and 185 CPM
- Example: `/simulate 300` — each split speed will be a random value between 200 and 400 CPM
- The fake split speeds are sent to `/api/generate` just like real ones, so the rolling window and adaptive tier computation work as normal
- The session, history, and rolling stats are **real** — you can play multiple paragraphs and watch the adaptive scoring evolve
- Typing game works normally (type to advance), but the split speeds are always faked while simulate mode is active
- Simulate mode persists until you click Restart or refresh the page

### Mock LLM Mode

Set `STORYTIME_MOCK_LLM=true` to replace the real LLM with canned responses. No Ollama needed — perfect for testing the UI/flow offline.

```bash
# Bash
export STORYTIME_MOCK_LLM=true
export STORYTIME_DEV_MODE=true    # optional, for /simulate
backend/run.sh

# Windows Cmd
set STORYTIME_MOCK_LLM=true
backend\run.bat
```

Each response starts with the outcome tier label (Very negative / Negative / Neutral / Positive / Very positive) followed by a couple of sentences. The backend detects the tier from the prompt's outcome direction and returns the matching canned response. When no tier is detected (e.g., first paragraph), tier 2 (Neutral) is used.

Combine with `STORYTIME_DEV_MODE=true` to also use `/simulate` with mock responses. Type any prompt and click Send — the game will flow through without any Ollama connection.
