---
date: 2025-03-14
topic: viz-browser-testing
---

# Viz browser testing (Playwright)

## What We're Building

Automated browser tests for the LLM State Viz so we can (1) get to the root cause of "nothing showing in the browser" and (2) avoid regressions. Tests use Playwright (Python), run against `viz_server` (started by fixture or `VIZ_SERVER_PORT`). Success means: page loads, no JS errors, and something visible (canvas present; optional: after Run, trajectory/status). Structure is CI-ready (configurable server URL) but runs locally for now.

## Why This Approach

- **Minimal pytest + Playwright**: Fits existing pytest/conftest; one test loads `/`, waits for `#canvas-container canvas`, clicks Run, waits for status "Done"/"points", captures screenshots and console log, asserts no console errors.
- **Failure artifacts**: Trace and screenshot on failure so when the test fails (e.g. blank screen) we get a trace and screenshot in `.browser-test-artifacts/` for debugging.
- **No second test runner**: Stay with Python/Playwright rather than adding Node-based Playwright.

## Key Decisions

- **At least (a)**: Assert page loads, no JS errors, canvas exists (and in current test, Run → stream completes). Can add stricter checks (e.g. WebSocket, pixel checks) later.
- **Local first, CI-ready**: Fixture starts server on a free port; `VIZ_SERVER_PORT` lets CI (or manual run) use an existing server.
- **Artifacts in `.browser-test-artifacts/`**: Screenshots, console.log, and on failure trace + failure screenshot so Cursor or dev can inspect.

## Open Questions

- None for initial implementation. Add trace/screenshot-on-failure and keep existing test flow.

## Next Steps

- Implement trace + screenshot on failure in `tests/test_browser_viz.py`.
- Run test; use failure artifacts to debug current "nothing in browser" if it still fails.
