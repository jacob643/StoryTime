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

**`/simulate <CPM> [deviation]`** — Type into the prompt box to start a real game session where the paragraph's split speeds are **faked** at the given CPM. With no deviation, every split is exactly the target CPM. With deviation, each split varies randomly within target ± deviation (floored at 1 CPM). This lets you test adaptive scoring without having to type at a specific speed.

- Example: `/simulate 100` — all split speeds are exactly 100 CPM
- Example: `/simulate 100 50` — each split speed varies randomly between 50 and 150 CPM
- Example: `/simulate 300 100` — each split speed varies randomly between 200 and 400 CPM
- The fake split speeds are sent to `/api/generate` just like real ones, so the rolling window and adaptive tier computation work as normal
- The session, history, and rolling stats are **real** — you can play multiple paragraphs and watch the adaptive scoring evolve
- Typing game works normally (type to advance), but the split speeds are always faked while simulate mode is active
- Simulate mode persists until you click Restart or refresh the page

You can also start a simulation from the browser console (F12) at any time:

```js
simulate(100);        // all splits exactly 100 CPM
simulate(300, 50);    // each split 250-350 CPM
simulate(50, 100);    // each split 1-150 CPM (floored at 1)
```

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

## Settings API

`GET /api/settings` returns all current game settings. `POST /api/settings` accepts a partial JSON body to update one or more fields.

| Field | Type | Default | Description |
|---|---|---|---|
| `scoring_mode` | `"split"` \| `"fixed"` | `"split"` | Scoring mode |
| `min_data` | int | 3 | Minimum splits before adaptive scoring activates |
| `min_stddev_cpm` | float | 10.0 | Floor for standard deviation (CPM) |
| `tier_0_max_sigma` | float | -1.5 | Sigma upper bound for tier 0 |
| `tier_1_max_sigma` | float | -0.5 | Sigma upper bound for tier 1 |
| `tier_2_max_sigma` | float | 0.5 | Sigma upper bound for tier 2 |
| `tier_3_max_sigma` | float | 1.5 | Sigma upper bound for tier 3 |
| `fixed_thresholds` | `[[float, float], ...]` | — | Low/high CPM pairs for each tier (fixed mode) |
| `target_split_size` | int | 50 | Target characters per split |
| `min_split_size` | int | 30 | Minimum characters per split |
| `default_avg_cpm` | float | 300.0 | Default average CPM when no prior data |
| `outcome_directions` | `{int: str, ...}` | — | Prompt direction text for each tier (0–4) |

Example:
```bash
# Set scoring to fixed mode with a custom average
curl -X POST http://127.0.0.1:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"scoring_mode": "fixed", "default_avg_cpm": 400}'

# Read current settings
curl http://127.0.0.1:8000/api/settings
```

Settings persist in `~/.storytime/user.cfg` and affect **new sessions only** (existing sessions retain their own `ScoringParams`).

## Settings Panel (Frontend)

Click the **⚙ Settings** toggle button to expand/collapse the settings panel. The panel contains controls for every game parameter:

- **Scoring mode**: dropdown (`split` / `fixed`)
- **Sigma bounds**: number inputs for tier 0–3 max sigma
- **Fixed thresholds**: low/high CPM pairs for each tier (shown when `fixed` mode selected)
- **Split parameters**: target and minimum split sizes
- **Default CPM**: default speed when no prior data
- **Prompt directions**: text inputs for each tier's outcome direction

Click **Save** to persist changes via `POST /api/settings`, or **Reset to Defaults** to restore factory values.

## Provider System

### Provider Selection

The active provider is controlled via settings fields:

| Field | Default | Description |
|---|---|---|
| `provider` | `"ollama"` | Active provider: `"ollama"` or `"custom"` |
| `custom_endpoint` | `""` | Base URL for OpenAI-compatible endpoint (e.g. `https://api.openai.com/v1`) |
| `custom_api_key` | `""` | API key for the custom endpoint |
| `custom_model` | `""` | Model name for the custom endpoint (e.g. `gpt-4o-mini`) |

Set via `POST /api/settings`:
```bash
curl -X POST http://127.0.0.1:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"provider": "custom", "custom_endpoint": "https://api.openai.com/v1", "custom_api_key": "sk-xxx", "custom_model": "gpt-4o"}'
```

### Model Discovery

`GET /api/models` returns available models from all configured providers:

```json
{
  "providers": [
    {
      "provider": "ollama",
      "available": true,
      "models": ["llama3.2:3b", "mistral:7b"]
    },
    {
      "provider": "custom",
      "available": true,
      "models": ["gpt-4", "gpt-4o-mini"]
    }
  ]
}
```

The custom endpoint is only checked if `custom_endpoint` is configured in settings.

### Fallback Behavior

When `provider` is set to `"custom"` but `custom_endpoint` is empty or the endpoint is unreachable, the registry falls back to Ollama. All game routes (`/api/generate`, `/api/restart`, `/api/simulate`) use the `ProviderRegistry` singleton to dispatch LLM calls to the active provider.
