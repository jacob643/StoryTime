# Release Guide

## Overview

A release produces a standalone binary for a platform — no Python or pip required. The version lives in two files that must be kept in sync.

---

## Step-by-step

### 1. Update the version

Edit both of these to the *new* version:

| File | Field |
|------|-------|
| `backend/_version.py` | `__version__ = "0.2.0"` |
| `pyproject.toml` | `version = "0.2.0"` |

### 2. Update the changelog

Open `CHANGELOG.md` and add an entry under the new version with any relevant changes (Added, Changed, Fixed).

### 3. Commit and tag

```bash
git add backend/_version.py pyproject.toml CHANGELOG.md PLAN.md
git commit -m "release v0.2.0"
git tag v0.2.0
git push origin v0.2.0
```

### 4. Let CI build

Pushing the tag triggers `.github/workflows/build.yml`. After the jobs finish, download the artifacts from the Action run.

### 5. Create a GitHub Release

1. Go to **Releases → Draft a new release**
2. Select the tag (`v0.2.0`)
3. Auto-generate release notes or write them manually
4. Attach the binaries from the CI artifacts
5. Publish

---

## Local build (optional)

```bash
# Full build with smoke test
python scripts/build.py --clean

# Build only, no smoke test
python scripts/build.py --clean --skip-smoke

# Windows wrapper
scripts\build.bat --clean
```

Output goes to `dist/`. Run the smoke test separately:

```bash
python scripts/smoke_test.py dist/StoryTime.exe
```

---

## Project layout

```
storytime.spec           PyInstaller config (one-file, bundles frontend/)
scripts/
  build.py               Orchestrator — runs PyInstaller, prints output, optional smoke test
  smoke_test.py          Launches binary on free port, polls GET /, exits 0/1
  build.bat / build.sh   One-command wrappers
  run.bat / run.sh       Production launchers (binary first, python fallback)
.github/workflows/
  build.yml              CI — builds on push/PR to main, uploads artifact
```
