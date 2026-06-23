#!/usr/bin/env bash
# Story Time launcher — tries PyInstaller binary first, falls back to python -m backend.main

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$PROJECT_DIR/dist/StoryTime/StoryTime" ]; then
    exec "$PROJECT_DIR/dist/StoryTime/StoryTime"
fi

if [ -f "$PROJECT_DIR/dist/StoryTime" ]; then
    exec "$PROJECT_DIR/dist/StoryTime"
fi

echo "[storytime] PyInstaller binary not found, starting via python..."
cd "$PROJECT_DIR"
python -m backend.main
