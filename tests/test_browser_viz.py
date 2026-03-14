"""
Browser tests for the LLM State Viz. Uses Playwright to drive the app, capture
screenshots and console logs, and write them to .browser-test-artifacts/ for
debugging (e.g. Cursor can open the screenshots and log file).

Run:
  pip install -r requirements-browser-test.txt
  playwright install chromium
  pytest tests/test_browser_viz.py -v

Optional: run against an already-running server:
  VIZ_SERVER_PORT=8000 pytest tests/test_browser_viz.py -v

Artifacts: .browser-test-artifacts/
  - screenshot_after_load.png
  - screenshot_after_run.png
  - console.log
"""
from pathlib import Path

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import sync_playwright


@pytest.fixture
def artifact_path(browser_artifact_dir):
    def _path(name):
        p = browser_artifact_dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)
    return _path


def test_viz_loads_and_renders(viz_server_url, browser_artifact_dir, artifact_path):
    """Load the viz page, check canvas exists, capture screenshot and console log.
    On failure, saves failure-trace.zip and screenshot_on_failure.png to artifacts."""
    console_log = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        context.tracing.start(screenshots=True, snapshots=True)
        context.on("console", lambda msg: console_log.append(f"[{msg.type}] {msg.text}"))
        page = context.new_page()
        try:
            page.goto(viz_server_url, wait_until="networkidle", timeout=10000)
        except Exception as e:
            (Path(browser_artifact_dir) / "console.log").write_text(
                "\n".join(console_log) + f"\n\nPage load error: {e}"
            )
            raise
        try:
            # Wait for canvas (Three.js app)
            page.wait_for_selector("#canvas-container canvas", timeout=5000)
            page.screenshot(path=artifact_path("screenshot_after_load.png"))
            # Click Run to trigger stream (mock)
            page.click("button.primary")
            page.wait_for_function(
                "() => document.getElementById('status').textContent.includes('Done') || document.getElementById('status').textContent.includes('points')",
                timeout=15000,
            )
            page.screenshot(path=artifact_path("screenshot_after_run.png"))
        except Exception:
            page.screenshot(path=artifact_path("screenshot_on_failure.png"))
            context.tracing.stop(path=artifact_path("failure-trace.zip"))
            raise
        context.tracing.stop()
        browser.close()
    (Path(browser_artifact_dir) / "console.log").write_text("\n".join(console_log))
    errors = [l for l in console_log if l.startswith("[error]")]
    assert not errors, f"Console errors:\n" + "\n".join(errors)
