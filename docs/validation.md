# Current-instance validation

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
