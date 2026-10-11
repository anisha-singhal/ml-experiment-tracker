#!/usr/bin/env bash
# Run the backend test suite in a throwaway container, so it needs no local
# Python and matches what CI does. Usage: ./scripts/run-tests.sh
set -euo pipefail
cd "$(dirname "$0")/.."

docker run --rm \
  -v "$PWD/backend:/app:ro" \
  -w /app \
  -e DATABASE_URL="sqlite://" \
  python:3.12-slim \
  sh -c "pip install --quiet --no-cache-dir -r requirements-dev.txt && python -m pytest -v -p no:cacheprovider"
