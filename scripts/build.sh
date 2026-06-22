#!/usr/bin/env bash
# Build launcher for Unix — calls scripts/build.py
set -euo pipefail
cd "$(dirname "$0")"
python build.py "$@"
