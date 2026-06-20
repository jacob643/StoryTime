# Frontend Design

## Overview

The frontend is a single-page web application served by the FastAPI backend. It communicates with the backend via the Fetch API. No build step, no bundler — vanilla HTML, CSS, and JavaScript.

## Page Layout

```
+------------------------------------------------------------+
|  #history (left sidebar)    |    #main-content (center)     |
|                              |                              |
|  +------------------------+ |  +--------------------------+ |
|  | History Item 1         | |  | Settings Bar             | |
|  |   Text: ...            | |  |  [CPM/WPM] [Chars: 20]  | |
|  |   Time: 12.3s          | |  |  [Possible Characters]   | |
|  |   Speed: 95 CPM        | |  |                          | |
|  +------------------------+ |  | Initial Prompt Input      | |
|  +------------------------+ |  | [Restart Button]          | |
|  | History Item 2         | |  +--------------------------+ |
|  |   ...                  | |  +--------------------------+ |
|  +------------------------+ |  | Story Text Display        | |
|  +------------------------+ |  |  (current paragraph)      | |
|  | History Item 3         | |  +--------------------------+ |
|  |   ...                  | |  +--------------------------+ |
|  +------------------------+ |  | Typing Input Box          | |
|                              |  |  [text input field]      | |
|                              |  +--------------------------+ |
|                              |  +--------------------------+ |
|                              |  | Stats                    | |
|                              |  |  Time: ...  Speed: ...   | |
|                              |  |  Message: ...            | |
|                              |  +--------------------------+ |
+------------------------------------------------------------+
```

## Component Breakdown

### 1. Settings Bar
- **CPM/WPM toggle** — radio group, changes speed display unit
- **Target paragraph length** — slider/number input for approximate character count
- **Possible characters** — textarea defining the character set (relevant if using randomized fallback; less relevant with LLM, but kept for future prompt constraints)
- **LLM Model selector** — dropdown populated from `GET /api/models`
- **Custom endpoint field** — optional URL + API key for non-Ollama backends

### 2. Story Controls
- **Initial prompt** — text input for the opening story prompt
- **Restart button** — clears history, sends initial prompt to LLM, resets game
- **Status indicator** — shows "Generating...", "Ready", "Error" states

### 3. Typing Area
- **Text display** — shows the current paragraph with character-by-character highlighting (green correct, red incorrect, untyped neutral)
- **Input box** — single-line or multi-line text input for typing
- **Auto-advance** — when input matches the target text exactly, the paragraph is submitted automatically

### 4. History Sidebar
- Scrollable list of completed paragraphs with metadata:
  - Full paragraph text
  - Time taken to type
  - Typing speed (CPM/WPM)
  - Outcome tier (visual badge: terrible/great etc.)
- Auto-scrolls to latest entry

### 5. Stats Display
- **Live stats** during typing:
  - Current speed (updating in real-time)
  - Running average speed for the session
- **Post-paragraph stats**:
  - Time taken
  - Speed
  - Accuracy percentage (correct keystrokes / total characters)

## State Management

### Frontend State (in-memory JS object)

```javascript
const state = {
  currentParagraph: "",        // the text the player must type
  storyHistory: [],           // { text, timeTaken, speed, outcome }
  startTime: null,            // timestamp when typing began
  isGenerating: false,        // true while waiting for LLM
  settings: {
    speedUnit: "cpm",         // "cpm" | "wpm"
    targetLength: 20,
    modelName: "",
    customEndpoint: "",
    apiKey: ""
  },
  gamePhase: "idle"           // "idle" | "typing" | "generating" | "finished"
};
```

### Backend State (server-side session)
The server maintains:
- Story history (list of `{ prompt, response, speed, outcome }`)
- Current session configuration
- This allows page refreshes without losing progress (future: session persistence)

## API Communication

### Endpoints consumed by the frontend:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/models` | Fetch available models from Ollama + custom config |
| `POST` | `/api/chat` | Submit typed paragraph, get next paragraph |
| `POST` | `/api/restart` | Reset story with initial prompt |
| `GET` | `/api/history` | Get full story history |
| `POST` | `/api/settings` | Update backend settings (model, endpoint) |

### POST /api/chat — Request

```json
{
  "typed_text": "The warrior stepped into the dark forest...",
  "target_text": "The warrior stepped into the dark forest...",
  "time_taken_ms": 12300,
  "speed_cpm": 95.2,
  "accuracy": 98.5
}
```

### POST /api/chat — Response

```json
{
  "next_paragraph": "Branches clawed at his face as he pushed deeper...",
  "outcome_tier": 3,
  "outcome_label": "positive",
  "history": [...]
}
```

## Typing Engine (from existing code)

The existing character-matching logic is solid and should be preserved:

1. **On each keystroke**: compare `input.value[i]` to `targetText[i]`
2. **Render**:
   - Match → green background
   - Mismatch → red background
   - Not yet typed → no background
3. **On complete match**: trigger submission
4. **Timer**: starts on first keystroke, stops on completion

### Enhancements to consider:
- **Accuracy tracking** — count total keystrokes vs correct keystrokes
- **Real-time WPM/CPM** — update speed display during typing
- **Backspace handling** — currently raw comparison; should track forward progress rather than punishing corrections
- **Multi-line support** — paragraphs can be long; textarea input or scrollable display

## Settings Panel (new)

A collapsible settings panel to replace/adjust the existing settings bar:

```
+-- Settings --------------------------------+
|                                             |
|  LLM Provider: [Ollama ▼]                  |
|  Model: [llama3.2:3b        ▼]  (Refresh) |
|  Custom Endpoint: [http://... :11434]      |
|  API Key: [·······················]        |
|                                             |
|  Speed Display: (●) CPM  ( ) WPM          |
|  Paragraph Length: [20] chars             |
|                                             |
|  [Save] [Test Connection]                  |
+---------------------------------------------+
```

## Error States

| State | UI Reaction |
|---|---|
| LLM unavailable | Show "Check Ollama" banner, disable start, show connection test button |
| Generation timeout | Show "Generation took too long" toast, offer retry |
| Typing submission failed | Retry with backoff, show error if persistent |
| Empty model list | Show manual endpoint input, link to Ollama install guide |
