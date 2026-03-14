# Browser viz: automated tests and debugging

Automated tests use **Playwright** to drive the browser, run the viz (load page, click Run, wait for stream), and write **artifacts** (screenshots, console log) to a fixed directory so you or Cursor can inspect them when debugging.

## Setup

```bash
pip install -r requirements-browser-test.txt
playwright install chromium
```

## Run tests

From repo root:

```bash
pytest tests/test_browser_viz.py -v
```

The test will:

1. Start `viz_server` on a free port (or use `VIZ_SERVER_PORT` if set).
2. Open Chromium (headless), go to the viz page.
3. Wait for the canvas, take **screenshot_after_load.png**.
4. Click **Run**, wait until status shows "Done" or "points", take **screenshot_after_run.png** and **screenshot_canvas_after_run.png** (canvas only).
5. Collect all console messages and write **console.log**.
6. Assert there are no console errors.
7. Assert the canvas has at least 500 non-background pixels (grid + points visible), so we can debug "does the viz show anything?" separately from your local browser.

Artifacts are written to:

```
.browser-test-artifacts/
  screenshot_after_load.png      # Page right after load (grid visible)
  screenshot_after_run.png       # After Run, trajectory visible
  screenshot_canvas_after_run.png # Canvas only (used for pixel assertion)
  console.log                    # All [log]/[error]/[warn] messages
  # On failure only:
  screenshot_on_failure.png   # Page at moment of failure
  failure-trace.zip           # Playwright trace (playwright show-trace failure-trace.zip)
```

## Using artifacts for debugging

- **Cursor**: Open `.browser-test-artifacts/` in the file tree and click the screenshots or `console.log` to see what the browser saw and what it logged. Use this after a failing test or to confirm the viz looks correct.
- **Headed run**: To watch the browser while the test runs:
  ```bash
  pytest tests/test_browser_viz.py -v --headed
  ```
  (Requires Playwright’s `--headed` support; you may need to pass it via `PLAYWRIGHT_HEADED=1` or a pytest option if your pytest-playwright setup supports it. Otherwise run the server manually and use `VIZ_SERVER_PORT=8000` with a server you started in another terminal.)
- **Existing server**: If the viz is already running (e.g. `uvicorn viz_server:app --port 8000`):
  ```bash
  VIZ_SERVER_PORT=8000 pytest tests/test_browser_viz.py -v
  ```

## Adding more checks

In `tests/test_browser_viz.py` you can:

- Take more screenshots (e.g. after toggling Layer river).
- Use `page.locator(...).screenshot(path=...)` for element-only screenshots.
- Assert on DOM text, canvas size, or WebSocket message count.
- Record a trace or video (see Playwright docs) and save under `.browser-test-artifacts/` for later inspection.
