# Current-instance validation

## Monterey-compatible local setup milestone

The current lockfile targets **Python 3.12.x / Node 22.x** and macOS 12+, including the user's Monterey 12.7.6. Cloud execution uses Python 3.12.14, Node 22.23.4, and npm 10.9.9.

| Current check | Result |
| --- | --- |
| Python test suite with the revised lockfile | **17 passed** in 10.28 seconds; includes five runtime-version guard cases |
| Full installation / Node 22 TypeScript + Vite build | Passed |
| Clean installation without `.venv` or `node_modules`, in a path containing spaces | Passed |
| Repeat installation in that clean copy | Passed; existing `data/` file preserved |
| Dependency consistency (`pip check`) | Passed |
| Complete lockfile binary-only download for CPython 3.12 / macOS 12 / arm64 | **35 wheels downloaded** |
| Complete lockfile binary-only download for CPython 3.12 / macOS 12 / x86_64 | **35 wheels downloaded** |
| Existing browser smoke workflow with the revised backend | Passed: live simulation, start/stop, events, acoustic response, room comparison and archive reopening |
| Browser errors / external requests | None / none |
| Duplicate server startup | Rejected with an actionable port-8765 message |
| Full process restart using `scripts/start.sh` | Both completed runs retained; archived FM reopened with status ready |

The current Python tests emit one upstream Starlette typing-alias deprecation warning from the installed AnyIO version. The suite completes successfully. The unchanged signal engine, schema, serial gateway, acquisition code and existing UI controls are exercised with the new pins. This cloud host runs Linux: Mac wheels and Node's declared deployment targets were verified, but native execution on the Mac remains the local acceptance step in [macos.md](macos.md).

## Original cloud validation record

Validated on Linux with Python 3.12.14, Node.js 24.19.0, npm 11.9.0, and the pinned dependency files. These results describe this prepared machine; a fresh published environment has not been independently restored and tested.

| Check | Result |
| --- | --- |
| `bash scripts/install.sh` with configured uv cache | Passed; pinned Python sync, editable installation, `npm ci`, TypeScript and Vite build |
| `.venv/bin/python -m pytest -q` | 12 passed in 12.32 seconds |
| Final `npm run build` | Passed; TypeScript compilation and local static bundle |
| `bash scripts/start.sh` | Passed; loopback HTTP service and persisted archive after restart |
| Chromium live simulation | Passed; connected acquisition, qualifying FM, Room A and Room B |
| Browser event / stop / save controls | Passed |
| Browser acoustic perturbation | Passed; stored pre/during/post response marked ready; physical output unverified |
| Browser comparison | Passed; latest simulation room similarity 0.63015, below the test's 0.8 discrimination threshold |
| Browser archive reopening | Passed |
| Browser JavaScript errors | None |
| Frontend external runtime requests | None; non-loopback requests were blocked by the browser test |
| Existing records after process restart | Preserved in the separate smoke-test data directory |
| Firmware compilation / flashing | Not run |
| Physical sensors / speaker / USB board | Not available; physical acceptance unverified |

The Python suite emits one upstream Starlette warning about future migration of its test-client transport from `httpx` to `httpx2`; it does not affect the passing tests. The test suite exercises the current installed transport.

The API test covers persistence through complete application lifespan restarts, and the service was also stopped and restarted through the documented shell script. Browser smoke runs use `LAB_DATA_DIR=/tmp/elyrion-smoke-data`, separate from the default experiment data directory. The current browser smoke records are synthetic.

## Repeat the browser check

With Playwright and Chromium installed separately, start the app and run from the repository root:

```sh
PLAYWRIGHT_MODULE=/path/to/playwright CHROMIUM_PATH=/path/to/chromium node tests/browser_smoke.cjs
```

The script creates two simulated runs, adds an event, generates a synthetic perturbation, validates the numerical response and comparison, opens the archive, rejects external page requests, and writes the screenshots below. It needs approximately 30 seconds and an idle server. It exercises browser audio scheduling, not speaker audibility or physical acoustic calibration.

- [Dashboard screenshot](dashboard.png)
- [Room comparison screenshot](comparison.png)

## Saved configuration and remaining work

`install_script` and `start_skill` were saved to the environment configuration draft. They preserve repository isolation and specify installation, startup, local readiness checks, storage, test commands, and hardware limitations. Saving the draft did not publish an environment snapshot. Review and save these changes in environment settings, then publish when desired.

Source files remain local and uncommitted in the originally empty `krys-wave/Elyrion-frequency-lab` checkout. Nothing was pushed, deployed, or connected to production. Hardware work is listed in [hardware.md](hardware.md); scientific interpretation limits are in [methods.md](methods.md).
