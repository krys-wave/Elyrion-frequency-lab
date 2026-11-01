#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if command -v uv >/dev/null 2>&1; then
  test -d .venv || uv venv --python python3 .venv
  uv pip sync --python .venv/bin/python requirements.lock
  uv pip install --python .venv/bin/python --no-deps -e .
else
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.lock
  .venv/bin/python -m pip install --no-deps -e .
fi
cd ui
npm ci --no-audit --no-fund
npm run build
