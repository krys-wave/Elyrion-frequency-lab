#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PWD/.cache/pip}"
export PIP_DISABLE_PIP_VERSION_CHECK=1
export npm_config_cache="${npm_config_cache:-$PWD/.cache/npm}"
fail() { printf '\nSetup stopped: %s\n' "$*" >&2; exit 1; }
# Same pip/venv path on Mac and Linux; optional uv installs do not change setup.
if [[ -d .venv ]]; then
  [[ -x .venv/bin/python ]] || fail "Existing .venv is incomplete. Rename it before installing again; keep data/ intact."
  lab_python=.venv/bin/python
elif [[ -n "${LAB_PYTHON:-}" ]]; then
  lab_python="$LAB_PYTHON"
elif command -v python3.12 >/dev/null 2>&1; then
  lab_python=python3.12
elif [[ -x /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 ]]; then
  lab_python=/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12
elif command -v python3 >/dev/null 2>&1; then
  lab_python=python3
else
  fail "Install Python 3.12 from python.org. See docs/macos.md."
fi
"$lab_python" scripts/check_runtime.py --tools-only
if [[ ! -d .venv ]]; then "$lab_python" -m venv .venv; fi
.venv/bin/python -m ensurepip --upgrade
.venv/bin/python -m pip install --only-binary=:all: -r requirements-bootstrap.lock
.venv/bin/python -m pip install --only-binary=:all: -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m pip check
(cd ui && npm ci --no-audit --no-fund && npm run build)
.venv/bin/python scripts/check_runtime.py --installed
printf '\nFrequency Lab installed. Start with: bash scripts/start.sh\n'
