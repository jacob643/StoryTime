# Backend Design

## Technology Stack

| Component | Library | Purpose |
|---|---|---|
| Framework | FastAPI | Async web server with automatic OpenAPI docs |
| ASGI server | Uvicorn | Production-grade async server |
| HTTP client | httpx | Async HTTP calls to Ollama/custom APIs |
| Settings | Pydantic Settings | Environment + file-based configuration |
| Static files | FastAPI StaticFiles | Serve HTML/CSS/JS from the backend |
| Packaging | PyInstaller | Bundle Python + dependencies into single executable |

## Project Structure

```
backend/
  main.py                  # FastAPI app entry, CORS, static mount
  config.py                # Pydantic settings (env vars, config file)
  session.py               # Game session management (story history, state)
  game_logic.py            # Speed-to-outcome mapping, accuracy calc
  prompt_engine.py         # Prompt template selection, context assembly
  providers/
    __init__.py            # Provider base class / protocol
    ollama.py              # Ollama-specific provider
    openai_compat.py       # OpenAI-compatible provider
  routes/
    __init__.py
    chat.py                # POST /api/chat
    models.py              # GET /api/models
    settings.py            # GET/POST /api/settings
    history.py             # GET /api/history
  static/
    index.html             # Main HTML page
    style.css
    script.js
  templates/               # (optional) Jinja2 templates if needed
```

## Routes Reference

### `GET /api/models` — Discover available models

**Logic:**
1. If Ollama provider is active, call `ollama list` API (`GET http://localhost:11434/api/tags`)
2. Parse model names from response
3. If custom endpoint is configured, do a lightweight health check
4. Return combined list with provider tags

**Response:**
```json
{
  "providers": [
    {
      "id": "ollama",
      "name": "Ollama (Local)",
      "models": ["llama3.2:3b", "mistral:7b", "dolphin-llama3:latest"],
      "default": "llama3.2:3b",
      "status": "available"
    },
    {
      "id": "custom",
      "name": "Custom Endpoint",
      "models": ["gpt-4o-mini", "claude-3-haiku"],
      "default": null,
      "status": "available"
    }
  ]
}
```

### `POST /api/generate` — Story generation (current endpoint)

**Request:**
```json
{
  "prompt": "the paragraph the user just typed",
  "model": "llama3.2:3b",
  "session_id": "uuid-or-null",
  "speed_cpm": 95.2,
  "split_speeds": [88.0, 92.5, 101.3, 97.8]
}
```

**Processing (subsequent call with session_id):**
1. Look up session, extract `rolling_splits` + `scoring_params`
2. First paragraph (no splits yet):
   - With N split_speeds, `baseline_count = ceil(N/2)`
   - Compute avg of first `baseline_count` speeds; σ = max(real_σ, min_stddev)
   - Average remaining `floor(N/2)` speeds → whole-paragraph CPM
   - `tier = compute_outcome_tier(evaluated_avg, avg=baseline_avg, stddev=baseline_σ, params=...)`
3. Subsequent paragraphs (rolling window has data):
   - Compute avg + σ from rolling window
   - Average all split_speeds → whole-paragraph CPM
   - `tier = compute_outcome_tier(whole_paragraph_cpm, avg=..., stddev=..., params=...)`
4. Append ParagraphRecord (includes split_speeds) to session history
5. Push split_speeds into rolling window, drop oldest if > 20
6. Assemble prompt with outcome tier, call LLM
7. Return next paragraph + metadata

**Response:**
```json
{
  "response": "The dragon circled overhead...",
  "session_id": "uuid",
  "outcome_tier": 3,
  "outcome_label": "positive"
}
```

### `POST /api/chat` — Main game loop endpoint (future)

**Request:**
```json
{
  "typed_text": "The warrior stepped into the dark forest...",
  "target_text": "...",
  "time_taken_ms": 12300,
  "speed_cpm": 95.2,
  "accuracy": 98.5
}
```

**Processing:**
1. Validate input matches target (integrity check)
2. Calculate outcome tier from `speed_cpm` (see game_logic)
3. Assemble prompt: story history + outcome tier + follow-up instruction
4. Call LLM provider (with timeout, retry logic)
5. Validate response (non-empty, reasonable length, no hallucinated formatting)
6. Append to story history
7. Return next paragraph + metadata

**Response:**
```json
{
  "next_paragraph": "Branches clawed at his face...",
  "outcome_tier": 3,
  "outcome_label": "positive",
  "history": [
    {"text": "...", "speed": 95, "outcome": "positive"},
    {"text": "...", "speed": 72, "outcome": "neutral"}
  ],
  "session_stats": {
    "avg_speed": 83.6,
    "paragraphs_completed": 5
  }
}
```

### `POST /api/restart` — Reset the story

**Request:**
```json
{
  "initial_prompt": "Write the first paragraph of an adventure story..."
}
```

**Processing:**
1. Clear story history in session
2. Send initial_prompt directly to LLM (no speed mapping)
3. Return first paragraph for typing display

### `GET /api/history` — Fetch full history

Returns complete story log with all metadata for the sidebar.

### `POST /api/settings` — Update backend settings

**Request:**
```json
{
  "provider": "ollama",
  "model": "llama3.2:3b",
  "custom_endpoint": "",
  "api_key": "",
  "paragraph_length": 20
}
```

Persisted to a JSON file (`~/.storytime/config.json`) for reuse across sessions.

## Game Logic (`game_logic.py`)

### Fixed Thresholds (Fallback)

Used when fewer than 3 splits of data exist in the rolling window.

```python
FIXED_THRESHOLDS = [
    (0, 30),       # Tier 0: Very Negative (very slow)
    (30, 50),      # Tier 1: Negative (slow)
    (50, 75),      # Tier 2: Neutral (average)
    (75, 100),     # Tier 3: Positive (fast)
    (100, float("inf"))  # Tier 4: Very Positive (very fast)
]
```

### Split-Based Adaptive Scoring (Primary)

Each paragraph is divided into **splits** of ~50 characters (configurable target size) with a minimum of 30 characters. Splits let us gather multiple speed data points per paragraph for faster baseline convergence.

**Split algorithm (target=50, min=30):**
```python
splits = []
pos = 0
while len(text) - pos >= 80:    # need room for target + min
    splits.append(text[pos:pos+50])
    pos += 50
remaining = len(text) - pos
if remaining >= 30:
    splits.append(text[pos:])
else:
    splits[-1] += text[pos:]    # merge into previous split
```

**Rolling window:** Last 20 split-speeds stored per session. Stats computed from scratch each time (O(20) = trivial).

**First paragraph baseline logic:**
With `N` splits on the first paragraph, the first `ceil(N/2)` splits seed the baseline. The remaining `floor(N/2)` are averaged into a single whole-paragraph speed and scored.

| N | Baseline (seed rolling window) | Evaluated | Outcome |
|---|---|---|---|
| 1 | Default avg=300 CPM, σ=10 | That 1 split | Scored against defaults |
| 2 | Split 1 (avg=s1, σ=10) | Split 2 | Scored against [s1, 10] |
| 3 | Splits 1–2 | Split 3 | Scored against those 2 |
| 4 | Splits 1–2 | Splits 3–4 averaged | Scored against those 2 |

After the first paragraph, all splits go into the rolling window and whole-paragraph speed is scored against `avg ± σ` of the window.

**`ScoringParams` dataclass:**
```python
@dataclass
class ScoringParams:
    mode: str = "split"
    min_data: int = 3
    min_stddev_cpm: float = 10.0
    tier_0_max_sigma: float = -1.5
    tier_1_max_sigma: float = -0.5
    tier_2_max_sigma: float =  0.5
    tier_3_max_sigma: float =  1.5
```

**Tier assignment (symmetric):**
| Tier | Label | Condition |
|---|---|---|
| 0 | Very Negative | speed < avg - 1.5σ |
| 1 | Negative | avg - 1.5σ ≤ speed < avg - 0.5σ |
| 2 | Neutral | avg - 0.5σ ≤ speed ≤ avg + 0.5σ |
| 3 | Positive | avg + 0.5σ < speed ≤ avg + 1.5σ |
| 4 | Very Positive | speed > avg + 1.5σ |

**Edge cases:**
- stddev below `min_stddev_cpm` (10) is floored to it
- < 3 splits in rolling window → fall back to fixed thresholds
- Negative speed_cpm → Tier 0

### Prompt Selection

The existing prompts from `script.js` map directly to these tiers:

| Tier | Label | Prompt Direction |
|---|---|---|
| 0 | Very Negative | "even worse situation, no clear way out" |
| 1 | Negative | "significant setback, more difficult" |
| 2 | Neutral | "minor challenge but continue" |
| 3 | Positive | "small success that aids the journey" |
| 4 | Very Positive | "greatly improves situation, significant advance" |

### Prompt Assembly (`prompt_engine.py`)

```python
def build_prompt(history: list, outcome_tier: int, initial_context: str) -> str:
    """
    Build a complete prompt for the LLM.

    Structure:
    1. System context (story premise, output format rules)
    2. Story history (previous paragraphs)
    3. Outcome direction (the tier-based instruction)
    4. Output constraint ("Write only a single paragraph, nothing else")
    """

def parse_llm_response(raw: str) -> str:
    """
    Clean up LLM output:
    - Strip quotes if present
    - Remove "Here's the next paragraph:" prefixes
    - Ensure it ends with sentence-ending punctuation
    - Truncate to max paragraph length if needed
    """
```

## Session Management

A lightweight in-memory session store (dict keyed by session ID). Each session holds:

```python
@dataclass
class GameSession:
    id: str                    # UUID
    created_at: datetime
    history: list[ParagraphRecord]
    initial_prompt: str
    rolling_splits: list[float]    # up to 20 split CPM values
    initial_avg_cpm: float = 300.0
    scoring_params: ScoringParams

@dataclass
class ParagraphRecord:
    text: str                   # The paragraph text
    speed_cpm: float            # Whole-paragraph CPM (mean of splits)
    time_taken_ms: int
    accuracy: float
    outcome_tier: int
    split_speeds: list[float]   # Individual split CPM values
```

For a single-user local app, a simple global session is sufficient. For multi-session support (future), a dict with timestamp-based cleanup works. The rolling window stats can be persisted alongside session history in 3.3.

## Configuration (`config.py`)

```python
class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    ollama_host: str = "http://127.0.0.1:11434"
    default_model: str = ""
    custom_endpoint: str = ""
    api_key: str = ""
    config_path: str = "~/.storytime/config.json"
    paragraph_length: int = 20
    log_level: str = "info"
```

Loaded from:
1. Environment variables (for packaging)
2. Config file at `~/.storytime/config.json`
3. Command-line arguments (for development)

## Error Handling & Resilience

| Failure Mode | Strategy |
|---|---|
| Ollama not running | Return `503` with `{"error": "ollama_unavailable", "message": "..."}`; frontend shows "Start Ollama" instruction |
| LLM generation timeout | 30s timeout on LLM call, retry once, then fail gracefully |
| LLM returns empty/garbage | Validate response; if invalid, retry with stronger constraints |
| Network error to custom API | Return error details to frontend for display |
| Invalid typed text submission | Reject with 400; this should not happen in normal flow |
