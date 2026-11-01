# ELYRION FREQUENCY LAB / V0.1

A standalone, offline sensor-acquisition and signal-analysis lab. This checkout has no connections to Elyrion/WAV production, W.I., Auth, Founder Presence, Airwallex, Otharis, Supabase, or Netlify. No accounts, cloud database, production secrets, telemetry, or CDN assets are needed.

## Start here

**MacBook Air on macOS Monterey 12.7.6:** follow the [Mac setup guide](docs/macos.md) for the official installers, exact launch commands, and simulator walkthrough.

Supported toolchain: **Python 3.12.x** and **Node.js 22.x LTS** with npm. The scientific dependencies are pinned to prebuilt wheels compatible with Monterey on both Intel and Apple Silicon. Internet access is needed during setup; the built application then operates offline.

```sh
cd /workspace/Elyrion-frequency-lab # or your local checkout
bash scripts/install.sh
bash scripts/start.sh
```

On your own laptop, open `http://127.0.0.1:8765`. The cloud onboarding environment is used for internal validation; it does not provide a dashboard preview. On a Mac, the included **Setup Frequency Lab.command** and **Start Frequency Lab.command** launch the same setup/startup scripts from Finder. Use one server process; do not enable multiple Uvicorn workers against the same DuckDB file.

Windows: `python -m venv .venv`, `.venv\Scripts\python -m pip install -r requirements.lock`, `.venv\Scripts\python -m pip install --no-deps -e .`, then run `npm ci` and `npm run build` in `ui`. From the repository root, run `.venv\Scripts\python -m uvicorn lab.app:app --host 127.0.0.1 --port 8765`. Windows has not been validated in this cloud task.

## First experiment

1. Select **Simulation · synthetic**, **Room A**, and **Full-resolution** storage.
2. Click **New Baseline Run**. Wait at least 8 seconds, then **Stop & save**. Repeat three qualifying baseline runs in the same room and input mode to produce the PI descriptor.
3. Record Room B. Choose **Room A ↔ Room B** to compare the most recent completed qualifying run in each room. Hardware and simulated runs are never mixed for comparison or PI.
4. On another run, wait at least the configured pre-window (default 4 seconds), then **Start Acoustic Perturbation**. Keep recording for the tone duration **and** post-window. Defaults: 4 + 4 + 4 seconds. Shortened/incomplete windows are explicitly marked insufficient.
5. Add event markers or custom notes. **Run archive** reopens measurements, traces, timestamps, FM/PI/D/PA descriptors, summaries, and response records after application restarts.

Tone amplitude is normalized digital amplitude, not speaker SPL. Browser playback goes to the laptop's selected audio output; connect the wired Bose speaker there. Playback and API timestamps are software timestamps, not measured physical acoustic onset. In simulation, the same perturbation also injects synthetic audio directly into the simulated microphone. Real acoustic response requires a connected microphone and verified output path.

The simulator uses a seeded generator, 20 Hz scalar frames and 8 kHz mono audio. Room A has a 1.25 Hz motion component and 160 Hz acoustic baseline; Room B uses 2 Hz and 240 Hz. Stable components, noise, slow environmental drift, a configurable disturbance magnitude, and tones are included. The Python API additionally accepts a `seed`. Changing input mode uses the same validated `Frame` downstream.

## Architecture

```text
ESP32-S3 sensors → USB native CDC / newline JSON ─┐
                                                ├→ validated Frame → deterministic engine
seeded Sensor Node 01 simulator ─────────────────┘                   ↓
                                                         DuckDB + Parquet + WAV
                                                                  ↕
                                                     FastAPI / WebSocket gateway
                                                                  ↕
                                                   React / TypeScript dashboard
```

```text
firmware/sensor-node-01/    PlatformIO target and modular hardware adapter
  include/pins.h           example wiring, must be checked for your board
  include/sensors.h        MMC5983MA / ISM330DHCX / BME280 / I²S adapter
  src/main.cpp             USB frame emission and host clock synchronization
lab/
  schema.py                canonical schema and SI unit labels
  simulator.py             seeded room model and acoustic injection
  serial_gateway.py        bounded newline JSON reader, no synthetic fallback
  engine.py                spectra, relationships, FM, PI, D, PA, comparisons
  storage.py               DuckDB recording, Parquet/WAV/derived exports
  app.py                   acquisition lifecycle, REST, WebSocket and static UI
ui/src/                    dashboard, event/tone controls, comparison, archive
tests/                     numerical, API, persistence and serial contract tests
scripts/                   reproducible install and loopback startup
docs/                      scientific methods, hardware status and UI captures
requirements.lock          pinned Monterey-compatible Python package versions
requirements-compat.txt    native wheel compatibility constraints
requirements-bootstrap.lock pinned installer/build tooling
.python-version / .nvmrc   Python 3.12 / Node 22 reference versions
ui/package-lock.json       pinned frontend dependency tree
data/                      generated locally; ignored by Git
  database/lab.duckdb       runs, frames, events, summaries and responses
  raw/<location>/<run>/     measurements.parquet and normalized audio.wav
  derived/                 FM, PI/PA, responses and summary Parquet
  exports/                 reserved for user-selected exports
```

Set `LAB_DATA_DIR` to an absolute local directory to relocate recordings. DuckDB persists accepted frames immediately; Parquet/WAV and derived files are exported when a run stops. Interrupted runs remain in the archive and are labeled interrupted on restart. Data is never uploaded.

For longer baselines select **Summarized windows**. Five-second FM summaries are retained, with a bounded 200-second analysis buffer at the supported 20 Hz frame rate. Full-resolution frames are retained during perturbations (including the pre-window), user-selected raw intervals, and anomalies scoring above 2 relative to a stored baseline (including four seconds before/after). Without a baseline, automatic anomaly retention is unavailable. Full-resolution mode retains every accepted frame. WAV exports use 16-bit clipped samples; original floating audio samples remain in DuckDB/Parquet. Raw records containing gaps must not be treated as continuous audio; the exported WAV concatenates retained frames. Use their Parquet timestamps to recover interval boundaries. Long full-resolution exports currently materialize the run in memory; summarized storage is recommended for extended monitoring.

## Validation and development

```sh
.venv/bin/python -m pytest -q
cd ui && npm run build
```

Python tests cover runtime-version guards, FFT frequency/amplitude/phase, PSD, phase/coherence, deterministic repeatability, numerical room discrimination, PI prerequisites, synthetic acoustic response, incomplete/timing-invalid data, finite schemas, REST/WebSocket lifecycle, event timestamps, restart persistence, Parquet/WAV export, serial schema transport, and local-origin checks. See [validation](docs/validation.md) for results from this environment.

The compiled UI is served by FastAPI. After editing TypeScript, run `npm run build` and refresh. Backend development may use `.venv/bin/python -m uvicorn lab.app:app --host 127.0.0.1 --port 8765 --reload`. Reload closes and saves the active run; do not use it while collecting an experiment. Dependencies are not fetched at runtime.

The dashboard uses dark panels, blue input traces, gold derived metrics, an acoustic spectrum and spectrogram, room comparison, and a persistent run archive. It labels simulated inputs, uncalibrated audio, insufficient baseline/PI, and preliminary PA explicitly. [Scientific definitions and limitations](docs/methods.md) explain the calculations; [hardware status](docs/hardware.md) separates implemented adapters from unverified physical acceptance.
