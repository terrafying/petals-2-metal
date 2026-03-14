"""
Browser tests for the LLM State Viz. Uses Playwright to drive the app, capture
screenshots and console logs, and write them to .browser-test-artifacts/ for
debugging (e.g. Cursor can open the screenshots and log file).

Asserts that the viz actually draws something (canvas has non-background pixels)
so we can debug "does the visualization show anything?" separately from a
specific browser.

Run:
  pip install -r requirements-browser-test.txt
  playwright install chromium
  pytest tests/test_browser_viz.py -v

Optional: run against an already-running server:
  VIZ_SERVER_PORT=8000 pytest tests/test_browser_viz.py -v

Artifacts: .browser-test-artifacts/
  - screenshot_after_load.png
  - screenshot_after_run.png
  - screenshot_canvas_after_run.png   (canvas only, for pixel assertion)
  - console.log
"""
from pathlib import Path

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import sync_playwright


# Scene background from viz.js (THREE.Color 0x0d0d0f)
VIZ_BACKGROUND_RGB = (13, 13, 15)


def _count_non_background_pixels(image_path: Path, background_rgb=VIZ_BACKGROUND_RGB, tolerance: int = 8) -> int:
    """Count pixels that differ from the viz background (grid/points are visible)."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("PIL/Pillow required for canvas pixel assertion")
    img = Image.open(image_path).convert("RGB")
    pixels = img.load()
    w, h = img.size
    count = 0
    r0, g0, b0 = background_rgb
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            if abs(r - r0) > tolerance or abs(g - g0) > tolerance or abs(b - b0) > tolerance:
                count += 1
    return count


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
            # Use fewer tokens so stream finishes quickly; then click Run
            max_tokens_el = page.locator("#max-tokens")
            if max_tokens_el.count() > 0:
                max_tokens_el.fill("24")
            page.click("button.primary")
            page.wait_for_function(
                "() => document.getElementById('status').textContent.includes('Done') || document.getElementById('status').textContent.includes('points')",
                timeout=20000,
            )
            page.screenshot(path=artifact_path("screenshot_after_run.png"))
            canvas_shot = artifact_path("screenshot_canvas_after_run.png")
            page.locator("#canvas-container").screenshot(path=canvas_shot)
        except Exception:
            page.screenshot(path=artifact_path("screenshot_on_failure.png"))
            context.tracing.stop(path=artifact_path("failure-trace.zip"))
            raise
        context.tracing.stop()
        browser.close()
    (Path(browser_artifact_dir) / "console.log").write_text("\n".join(console_log))
    errors = [l for l in console_log if l.startswith("[error]")]
    assert not errors, f"Console errors:\n" + "\n".join(errors)

    canvas_path = Path(browser_artifact_dir) / "screenshot_canvas_after_run.png"
    non_bg = _count_non_background_pixels(canvas_path)
    assert non_bg >= 500, (
        f"Viz did not draw enough content: {non_bg} non-background pixels (expected >= 500). "
        f"Inspect {canvas_path} and failure artifacts."
    )
