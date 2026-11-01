"""Offline preflight for the supported Mac/Linux development runtime."""
import argparse
import importlib
import platform
from pathlib import Path
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def check_python(version):
    if tuple(version[:2]) != (3, 12):
        raise ValueError("Python 3.12.x is required for the pinned Mac wheels. Install Python 3.12; rename an older .venv before rerunning setup. Keep data/ intact.")


def check_node(version):
    if version.strip().lstrip("v").split(".")[0] != "22":
        raise ValueError("Node.js 22.x LTS is required. Install the macOS .pkg linked in docs/macos.md; open a new Terminal afterward.")


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--tools-only", action="store_true")
    mode.add_argument("--installed", action="store_true")
    mode.add_argument("--startup", action="store_true")
    args = parser.parse_args()
    try:
        check_python(sys.version_info)
        print(f"Python {platform.python_version()} · {sys.executable}")
        print(f"Platform {platform.system()} {platform.release()} · {platform.machine()}")
        if platform.system() == "Darwin":
            mac = platform.mac_ver()[0]
            if not mac or tuple(map(int, mac.split(".")[:2])) < (12, 0):
                raise ValueError("macOS 12 Monterey or newer is required by the pinned storage/scientific wheels.")
            print(f"macOS {mac}")
        if args.tools_only:
            if not shutil.which("node") or not shutil.which("npm"):
                raise ValueError("Install Node.js 22.x with npm. See docs/macos.md.")
            node = subprocess.check_output(["node", "--version"], text=True).strip()
            check_node(node)
            npm = subprocess.check_output(["npm", "--version"], text=True).strip()
            print(f"Node {node} · npm {npm}")
            return 0
        for name in ("fastapi", "uvicorn", "numpy", "scipy", "pandas", "duckdb", "pyarrow", "serial", "websockets"):
            module = importlib.import_module(name)
            print(f"{name}: {getattr(module, '__version__', getattr(module, 'VERSION', 'installed'))}")
        if not (ROOT / "ui/dist/index.html").is_file() or not list((ROOT / "ui/dist/assets").glob("*.js")):
            raise ValueError("Dashboard build missing. Run bash scripts/install.sh.")
        if args.startup:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    probe.bind(("127.0.0.1", 8765))
                except OSError as error:
                    raise ValueError("Port 8765 is already in use. If Frequency Lab is running, open http://127.0.0.1:8765; otherwise stop that process and retry.") from error
        print("Preflight passed. Data stays in this checkout's data/ directory (or LAB_DATA_DIR).")
        return 0
    except (ValueError, ImportError, OSError, subprocess.CalledProcessError) as error:
        print(f"\nFrequency Lab setup: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
