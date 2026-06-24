## Story Time v0.2.0 — First Public Release

Story Time is a typing game where your speed and accuracy shape an AI-generated story — powered by local LLMs via Ollama.

### What's Included

- **Interactive typing game** — type each paragraph to drive the story forward
- **5-tier outcome system** — faster typing leads to brighter story outcomes (Very Negative → Very Positive)
- **Adaptive speed scoring** — compares your speed to your own rolling average, with per-split tracking
- **Local LLMs via Ollama** — no API keys, no cloud, runs entirely on your machine
- **Custom OpenAI-compatible endpoint** — use any LLM provider that supports the OpenAI API format
- **Model selection** — dropdown of installed Ollama models with manual entry fallback
- **Full settings panel** — scoring mode, paragraph length, temperature/top_k/top_p, tier prompt customization, dark mode, WPM/CPM display toggle, ignore case, and more
- **Story history** — per-paragraph stats with speed deltas and split progression
- **Retry paragraph** — clear your input to retry the same paragraph for a better score
- **Session persistence** — stories saved to `writtenStories/` as text files
- **Dev simulation** — `/simulate <CPM> [deviation]` for testing without typing

### Downloads

| Platform | Binary |
|---|---|
| Windows | `StoryTime.exe` |
| macOS | `StoryTime` |
| Linux | `StoryTime` |

Grab the binary for your platform from the Assets section below.

### Requirements

- [Ollama](https://ollama.com) with a model pulled (e.g. `ollama pull llama3.2`)
- Windows, macOS, or Linux

### How to Run

1. Install Ollama and pull a model
2. Download and run the binary for your platform
3. Open http://127.0.0.1:8000
4. Enter a story prompt and start typing!

### Full Changelog

See [CHANGELOG.md](https://github.com/jacob643/StoryTime/blob/main/CHANGELOG.md) for the complete history.
