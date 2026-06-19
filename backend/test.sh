#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/Scripts/activate
exec python -m pytest backend/tests/ "$@"
