# Release Guide

## Overview

A release produces standalone binaries for Windows, macOS, and Linux — no Python or pip required. The release workflow is automated via GitHub Actions: push a tag, CI builds everything and creates a GitHub Release.

---

## Step-by-step

### 1. Bump the version

```bash
python scripts/version.py bump 0.2.0
```

This rewrites `backend/_version.py`, `pyproject.toml`, and adds a new section to `CHANGELOG.md`. Review the diff before committing.

### 2. Commit and tag

```bash
git add -A
git commit -m "release v0.2.0"
git tag v0.2.0
git push origin v0.2.0
```

### 3. CI builds + publishes

Pushing the tag triggers `.github/workflows/release.yml`. It builds on Ubuntu, Windows, and macOS, then creates a GitHub Release with all three binaries attached and auto-generated release notes.

---

## Local build (optional)

```bash
python scripts/build.py --clean
python scripts/smoke_test.py dist/StoryTime  # or StoryTime.exe on Windows
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
  version.py             Bump version across _version.py, pyproject.toml, CHANGELOG.md
.github/workflows/
  build.yml              CI build on push/PR to main
  release.yml            Tag-triggered build + GitHub Release
```
