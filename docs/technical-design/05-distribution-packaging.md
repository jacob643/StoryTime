# Distribution & Packaging

## Distribution Strategy

The project should support an **incremental distribution path** — usable in development with minimal friction, shareable with friends as a single file, and eventually releasable as a polished installer.

```
Phase 1                  Phase 2                   Phase 3
Dev (python app.py)  →   Friend-ready          →   Public release
                         (PyInstaller)             (Installer + auto-update)
                         Windows / macOS / Linux
```

## Phase 1: Development Setup

### Requirements
- Python 3.10+
- Ollama installed separately

### Running in Development

```bash
# Clone the repo
git clone <repo>
cd story-time

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m backend.main
# Opens at http://127.0.0.1:8000
```

### `requirements.txt`

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
httpx>=0.27.0
pydantic-settings>=2.0.0
```

That's it for core dependencies. No frameworks, no build tools.

### Startup Script (replacing `.bat`)

A Python entry point that:
1. Prints startup banner
2. Launches Uvicorn
3. Optionally opens browser

```python
# main.py (entry point)
import uvicorn
import webbrowser

def main():
    print("╔══════════════════════════════════╗")
    print("║      Story Time v0.1.0           ║")
    print("║  http://127.0.0.1:8000           ║")
    print("╚══════════════════════════════════╝")

    webbrowser.open("http://127.0.0.1:8000")  # auto-open
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()
```

## Phase 2: PyInstaller Packaging (Cross-Platform)

### Goal
Create a native binary for **each platform** that includes Python, all dependencies, and the static frontend files. The user double-clicks and it works (assuming Ollama is installed).

PyInstaller is **fully cross-platform** — it builds a native executable for the OS it runs on. The same Python codebase produces a Windows `.exe`, a macOS `.app`, and a Linux binary with no code changes.

### Build Process

```bash
pip install pyinstaller
pyinstaller --onefile --name "StoryTime" --add-data "backend/static;static" backend/main.py
```

### `storytime.spec` (PyInstaller config)

```python
# storytime.spec
a = Analysis(
    ['backend/main.py'],
    pathex=[],
    binaries=[],
    datas=[('backend/static', 'static')],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.protocols'],
    hookspath=[],
    runtime_hooks=[],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='StoryTime',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # set to False for GUI mode if desired
)
```

### Building for Each Platform

You must build **on** the target platform — PyInstaller cannot cross-compile.

| Platform | Build machine | Output | Download name |
|---|---|---|---|
| Windows | Windows | `StoryTime.exe` (~10-15 MB) | `StoryTime-windows-x64.exe` |
| macOS (Intel) | macOS Intel | `StoryTime.app` | `StoryTime-macos-x64.dmg` |
| macOS (Apple Silicon) | macOS ARM | `StoryTime.app` | `StoryTime-macos-arm64.dmg` |
| Linux | Linux | `StoryTime` binary | `StoryTime-linux-x64` |

### CI Builds (Public Release)

For a public release, use **GitHub Actions** to build all platforms automatically on every tag:

```yaml
# .github/workflows/build.yml
jobs:
  build:
    strategy:
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pyinstaller -r requirements.txt
      - run: pyinstaller --onefile --name "StoryTime" backend/main.py
      - uses: actions/upload-artifact@v4
        with:
          name: storytime-${{ matrix.os }}
          path: dist/StoryTime*
```

Each build produces the correct native binary for its platform with the same Python codebase.

### What the User Sees (Per Platform)

| Platform | Download | How to Run |
|---|---|---|
| Windows | `StoryTime-windows-x64.exe` | Double-click the `.exe` |
| macOS | `StoryTime-macos-x64.dmg` or `StoryTime-macos-arm64.dmg` | Open the `.dmg`, drag to Applications, double-click |
| Linux | `StoryTime-linux-x64` | `chmod +x` and run from terminal, or double-click in file manager |

In all cases:
1. A terminal window opens with the server banner
2. Browser opens automatically to `http://127.0.0.1:8000`
3. **Requirement**: Ollama must be installed separately (include a check on startup)

### Ollama Dependency Note

Since Ollama must be installed separately, the startup flow should detect this:

```
App starts
  │
  ├──> Check if Ollama is reachable
  │     ├── Yes → proceed normally
  │     └── No  → show dialog:
  │                  "Ollama is not running.
  │                   Install from https://ollama.com/download
  │                   Then run: ollama serve
  │                   Or configure a custom endpoint in settings."
  │
  └──> Open browser to localhost:8000
```

## Phase 3: Public Release

### Installer Options

| Tool | Pros | Cons |
|---|---|---|
| **NSIS** (Windows) | Free, widely used, small installers | Windows only, script-based |
| **Inno Setup** | GUI-based setup, handles dependencies | Windows only |
| **WiX Toolset** | Professional MSI installers | Steep learning curve |
| **Squirrel** | Auto-update built in | .NET dependency |
| **GitHub Releases** (manual) | Simple zip download | No installer, no auto-update |

**Recommendation**: Start with GitHub Releases + PyInstaller binary. Add an installer (NSIS or Inno Setup) when the user base grows.

### Auto-Update

For a native-like experience, consider:

1. **GitHub Releases API** — check latest version on startup
2. **In-app update prompt** — "Version X.Y.Z available. Download?"
3. **Manual download** — simplest, user replaces old binary

## Future: Tauri Wrapper

If a fully native desktop app becomes desirable:

```
[Current]                         [Future]
Python FastAPI        →           Tauri (Rust) shell
Serves UI + LLM API              Embeds webview
PyInstaller .exe                  Bundles Python sidecar
                                  OR rewrites backend in Rust
```

### Tauri Approach A: Sidecar (recommended)

```
Tauri App
  ├── Webview (HTML/CSS/JS UI)
  ├── Python sidecar (FastAPI backend, bundled via PyInstaller)
  └── System tray icon
```

The Tauri shell:
- Launches the Python sidecar on startup
- Spawns a webview pointed at `http://127.0.0.1:8000`
- Provides system tray with "Show/Hide" and "Quit"
- Kills sidecar on exit
- Adds auto-update via Tauri updater

### Tauri Approach B: Rust Native

Rewrite the backend in Rust:
- **axum** for HTTP server
- **reqwest** for LLM API calls
- **serde** for JSON
- **tray-icon** for system tray

This eliminates the Python dependency entirely and produces a single ~5 MB binary. However, it's significantly more work.

## Comparison Summary

| Approach | Bundle Size | Python Req | Dev Speed | User Experience |
|---|---|---|---|---|
| Dev script (phase 1) | N/A | Yes | Instant | CLI + browser |
| PyInstaller (phase 2) | 10-15 MB | No | Fast | Double-click + browser |
| Tauri sidecar | 15-25 MB | No (bundled) | Moderate | Native window |
| Tauri native Rust | ~5 MB | No | Slow | Native window |

## Recommended Roadmap

```
Phase 1: Python dev server + browser UI
    └── Do this first, it's the fastest path to a working game

Phase 2: PyInstaller build for friends
    └── Native binary per platform (Windows/macOS/Linux), they just need Ollama

Phase 3 (optional): Tauri sidecar
    └── Polished native app with auto-update
    └── Only if demand justifies it
```
