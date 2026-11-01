# MacBook Air / macOS Monterey 12.7.6

Frequency Lab runs locally with the existing dashboard and simulator. Setup installs dependencies and builds the dashboard once; startup serves everything from one local FastAPI process at `http://127.0.0.1:8765`. No cloud account, database, sensor, or speaker is required to start simulation.

## 1. Install the supported runtimes

Use **Python 3.12.x** and **Node.js 22.x LTS**. The reference installer versions are Python 3.12.10 and Node 22.23.4; the cloud checks use Python 3.12.14 and the same Node 22.23.4. Keep Python within 3.12 and Node within 22 for this lockfile.

- Python: open [Python 3.12.10](https://www.python.org/downloads/release/python-31210/), choose **macOS 64-bit universal2 installer**, and run the downloaded `.pkg`. It supports both Intel and Apple Silicon. Open **Applications → Python 3.12 → Install Certificates.command** after installation to configure Python's HTTPS certificate trust. Keep certificate verification enabled.
- Node: open the [official Node 22.23.4 release directory](https://nodejs.org/dist/v22.23.4/) and run **node-v22.23.4.pkg**. This installs Node and npm. Node 22's official binaries target macOS 11 or newer, including Monterey.
- Close and reopen Terminal after installing both. Check:

```sh
python3.12 --version
node --version
npm --version
```

Expected: `Python 3.12.x`, `v22.x.x`, and an npm version. The setup script also checks these versions before installing anything. macOS's system Python is left alone. Homebrew is optional; the official `.pkg` path avoids depending on Homebrew support for an older macOS release.

## 2. Get this standalone project

If Git is available:

```sh
mkdir -p ~/Projects
cd ~/Projects
git clone --branch main https://github.com/krys-wave/Elyrion-frequency-lab.git
cd Elyrion-frequency-lab
```

If you already have this checkout, open its directory and use `git pull --ff-only` while the app is stopped. Preserve any local changes before updating.

If Git prompts for Apple developer tools and you prefer not to install them, sign in to GitHub in Safari, open the Frequency Lab repository, choose **Code → Download ZIP**, and extract it in Finder. Open Terminal in that extracted folder, or type `cd ` and drag the folder into Terminal before pressing Return. The project does not need Git or Apple compiler tools to install its prebuilt Python dependencies. A private repository requires your normal GitHub access to clone or download it.

## 3. Install and launch

From the project folder:

```sh
bash scripts/install.sh
bash scripts/start.sh
```

Then open **http://127.0.0.1:8765** in Safari or Chrome. Keep Terminal open while using the lab. Simulation is already the default input.

Finder alternatives: run **Setup Frequency Lab.command** once, then **Start Frequency Lab.command** for subsequent launches. If macOS asks how to open a downloaded script, use its normal **Open With → Terminal** action or run the two `bash` commands above. No application deployment or background system service is installed.

The installer creates a project-local `.venv`, installs pinned bootstrap and application requirements using prebuilt wheels, checks dependency consistency, runs `npm ci`, builds the existing dashboard, and imports the backend dependencies. It is safe to run again. It does not delete recordings, recreate an existing environment, alter global Python packages, or install firmware tools. Node/npm are needed for installation and rebuilding; ordinary startup only uses the prepared Python environment and built UI. Internet access is needed during setup; runtime can operate offline.

## 4. Try the simulator

1. Leave **Input → Simulation · synthetic** selected. Select **Room A** and click **New Baseline Run**.
2. Confirm **ACQUIRING / GATEWAY ONLINE** appears, elapsed time increases, and sensor traces change. Wait at least eight seconds, then **Stop & save**.
3. Record three qualifying Room A baseline runs to populate PI; the following live run displays its D and PA relative to PI. Shorter runs show the existing collection states.
4. Select **Room B**, record at least eight seconds, and stop. Click **Room A ↔ Room B** to inspect the latest completed runs in the selected input mode.
5. During a run, select an event, add a note if desired, and click **Mark event**.
6. For a perturbation, wait at least the pre-window (four seconds by default), click **Start Acoustic Perturbation**, and keep the run active through the tone and post-window. The simulator records synthetic acoustic changes. Browser audio uses your selected laptop output when the browser permits playback from that click.
7. Open **Run archive** and choose a completed run. Stored measurements, graphs, events, descriptors, and responses are available there.
8. Press **Control+C** in Terminal, relaunch with `bash scripts/start.sh`, and confirm the archive is still present.

Default storage is the checkout's `data/` directory. Keep that folder when updating the project. Optional relocation:

```sh
LAB_DATA_DIR="$HOME/Documents/FrequencyLabData" bash scripts/start.sh
```

Use the same directory on later launches. Quit the app before copying its DuckDB files. Existing recordings created by a newer DuckDB version should remain backed up with that original environment; this Monterey lock pins DuckDB 1.2.2. No automatic database downgrade or migration is performed.

## Troubleshooting

| Message | Action |
| --- | --- |
| Python 3.12 required | Install the Python 3.12 `.pkg`. An explicit interpreter can be selected with `LAB_PYTHON=/full/path/to/python3.12 bash scripts/install.sh` when no `.venv` exists. |
| Existing `.venv` uses another Python version | Stop the app, rename `.venv` to `.venv-backup`, then rerun setup. Keep `data/` untouched. |
| Node 22 required | Install Node 22's `.pkg`, reopen Terminal, and run `node --version`. If you already use nvm, run `nvm install` followed by `nvm use` from the project folder. |
| Certificate verification failed | Run Python's **Install Certificates.command** and retry. On managed networks, configure the organization's trusted CA through its supported certificate setup. |
| No matching distribution / wheel | Confirm Python 3.12, macOS 12 or later, and the checked-in lockfile. Setup intentionally uses prebuilt wheels rather than starting a lengthy local scientific-package compilation. Save the exact package/error for diagnosis. |
| Port 8765 is already in use | Open the running lab, or stop it with Control+C in its Terminal before starting another instance. |
| Site can't be reached | Keep the startup Terminal open. Wait for Uvicorn's running message, then open the exact local URL on this Mac. Check the startup message for missing dependencies or a busy port. |
| Audio is silent | Check browser playback permissions, laptop output selection, and volume. Simulator injection remains available independently of audible speaker output. |

For diagnostic checks from the project folder:

```sh
.venv/bin/python scripts/check_runtime.py --installed
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
```

## Compatibility evidence

The selected NumPy 2.2.6, SciPy 1.15.3, pandas 2.2.3, DuckDB 1.2.2, PyArrow 19.0.1 and supporting native packages publish CPython 3.12 wheels with deployment targets at or below macOS 12 for **both arm64 and x86_64**. The complete lockfile is checked with cross-platform binary-only downloads. Node 22's official [platform requirements](https://github.com/nodejs/node/blob/v22.23.4/BUILDING.md#platform-list) list macOS 11+ for both architectures.

These checks establish package availability and declared platform compatibility. Automated application and browser validation runs in Linux using the pinned dependencies and Node 22; this cloud machine cannot execute macOS binaries. The steps above include the local acceptance check on your Mac.
