#!/usr/bin/env bash
cd "$(dirname "$0")/.."
python -m backend.main "$@"
