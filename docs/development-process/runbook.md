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

**`/simulate <CPM>`** — Type into the prompt box (instead of a story prompt) to simulate typing at a given speed. The backend computes the outcome tier using the current session's rolling stats (or fixed thresholds if none exist), generates a matching story paragraph, and displays it as a read-only preview. The session history and rolling stats are **not** modified.

- Example: `/simulate 85` — generates the next paragraph as if typed at 85 CPM
- Example: `/simulate 300` — generates the next paragraph as if typed at 300 CPM (likely tier 4)
- Works with or without an active session (passes `session_id` if one exists)
- Result is shown in orange with a `[SIMULATION]` label; the typing game state is untouched

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
