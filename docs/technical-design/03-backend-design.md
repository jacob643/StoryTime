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

### `POST /api/chat` — Main game loop endpoint

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

### Speed-to-Outcome Mapping

```python
# Thresholds in CPM (configurable)
TIERS = [
    (0, 30),       # Tier 0: Very Negative (very slow)
    (30, 50),      # Tier 1: Negative (slow)
    (50, 75),      # Tier 2: Neutral (average)
    (75, 100),     # Tier 3: Positive (fast)
    (100, float("inf"))  # Tier 4: Very Positive (very fast)
]
```

These thresholds should be adjustable. Future enhancement: **adaptive scaling** where thresholds adjust based on the player's historical average speed.

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
    settings: PlayerSettings
    current_outcome_tier: int

@dataclass
class ParagraphRecord:
    text: str                  # The paragraph text
    speed_cpm: float
    time_taken_ms: int
    accuracy: float
    outcome_tier: int
```

For a single-user local app, a simple global session is sufficient. For multi-session support (future), a dict with timestamp-based cleanup works.

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
