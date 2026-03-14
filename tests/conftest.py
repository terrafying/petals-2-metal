"""
Pytest fixtures. Browser viz tests use viz_server_url and browser_artifact_dir.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO_ROOT / ".browser-test-artifacts"
VIZ_SERVER_PORT_ENV = "VIZ_SERVER_PORT"


def _find_free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def viz_server_url():
    """Start viz_server if not already running; return base URL."""
    port = os.environ.get(VIZ_SERVER_PORT_ENV)
    if port:
        url = f"http://127.0.0.1:{int(port)}"
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=2)
            return url
        except Exception:
            pytest.skip(f"VIZ_SERVER_PORT={port} set but server not reachable at {url}")
    port = _find_free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "viz_server:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(30):
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        proc.kill()
        proc.wait()
        pytest.skip("viz_server did not start in time")
    yield url
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def browser_artifact_dir():
    """Directory for screenshots and logs; Cursor can open these for debugging."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACT_DIR
