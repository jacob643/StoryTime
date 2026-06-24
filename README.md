# Story Time

[![Release](https://img.shields.io/github/v/release/jacob643/StoryTime?label=Download&style=for-the-badge)](https://github.com/jacob643/StoryTime/releases/latest)
[![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows)](https://github.com/jacob643/StoryTime/releases/latest)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://github.com/jacob643/StoryTime/releases/latest)
[![License](https://img.shields.io/github/license/jacob643/StoryTime?style=for-the-badge)](LICENSE)

A typing game where your speed and accuracy shape the story — powered by local LLMs via Ollama.

Type each paragraph to drive the story forward. Faster typing leads to brighter outcomes.

## Quick Start

1. Install [Ollama](https://ollama.com) and pull a model (e.g. `ollama pull llama3.2`).
2. Download the latest binary from [Releases](https://github.com/jacob643/StoryTime/releases/latest) and run it.
3. Open http://127.0.0.1:8000 in your browser.
4. Enter a story prompt and start typing!

See the [Getting Started guide](docs/getting_started.md) for full instructions.

## Building from Source

```bash
pip install -e .
python -m backend.main
```

## License

MIT
