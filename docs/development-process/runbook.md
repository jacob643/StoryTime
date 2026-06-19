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
