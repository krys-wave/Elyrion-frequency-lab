#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  printf 'Run bash scripts/install.sh first. See docs/macos.md.\n' >&2
  exit 1
fi
.venv/bin/python scripts/check_runtime.py --startup
printf '\nOpen http://127.0.0.1:8765 in your browser. Simulation is the default input.\n'
printf 'Keep this Terminal open. Press Control+C to save an active run and stop.\n\n'
exec .venv/bin/python -m uvicorn lab.app:app --host 127.0.0.1 --port 8765
