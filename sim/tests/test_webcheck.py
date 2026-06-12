"""Guard: the browser code must actually BOOT, not just pass `node --check`.
A runtime ReferenceError (e.g. an orphaned constant) blanks the page but is
invisible to syntax checks and the Python suite — tools/webcheck.js loads
world.js and game.js in a stubbed DOM and exercises their boot paths."""
import shutil
import subprocess

import pytest

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(
    __import__("os").path.dirname(__import__("os").path.abspath(__file__))))


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_browser_pages_boot():
    r = subprocess.run(["node", "tools/webcheck.js"], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, f"web page failed to boot:\n{r.stdout}{r.stderr}"
