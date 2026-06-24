# Contributing

Thanks for your interest in Story Time!

## Development Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/jacob643/StoryTime.git
   cd StoryTime
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -e ".[dev]"
   ```

3. Start the dev server:
   ```bash
   python -m backend.main
   ```

4. Open http://127.0.0.1:8000 in your browser.

## Running Tests

```bash
pytest backend/tests/
```

Frontend smoke tests require Playwright:
```bash
playwright install
pytest backend/tests/test_frontend_smoke.py
```

## Code Conventions

- **Python**: black formatting, type hints, fastapi routes in `backend/routes/`.
- **JavaScript**: ES6, no build step, single `frontend/script.js`.
- **CSS**: CSS custom properties for theming (light/dark mode).
- **Commits**: one task per commit, descriptive message. See `AGENTS.md` for the full workflow.

## Pull Request Process

1. Open an issue first to discuss the change you'd like to make.
2. Create a branch from `main`.
3. Make your changes, add tests, ensure all tests pass.
4. Open a pull request with a clear description of what and why.
