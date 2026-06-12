"""Cut a STABLE release of the standalone battle prototype.

The dev artifact (prototype_web/shattered_jade_battle.html) is rebuilt on every
change; releases/ holds frozen, known-good editions you can hand anyone. Gate:
the full pytest suite must be green. The version comes from the newest DESIGN.md
changelog entry, stamped into the <title> and a build comment.

    python3 tools/release.py             (from game01_demo/)
    → releases/shattered_jade_v0.24.html  +  releases/latest.html
"""
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.build_standalone import build  # noqa: E402


def design_version():
    with open(os.path.join(ROOT, "DESIGN.md"), encoding="utf-8") as f:
        m = re.search(r"\*\*v(\d+\.\d+) \((\d{4}-\d{2}-\d{2})\)\*\*", f.read())
    if not m:
        raise SystemExit("no changelog version found in DESIGN.md")
    return m.group(1), m.group(2)


def main():
    r = subprocess.run([sys.executable, "-m", "pytest", "sim/tests/", "-q"],
                       cwd=ROOT, capture_output=True, text=True)
    summary = (r.stdout.strip().splitlines() or ["?"])[-1]
    if r.returncode != 0:
        raise SystemExit(f"RELEASE BLOCKED — suite not green:\n{r.stdout}{r.stderr}")

    ver, ver_date = design_version()
    html = build()
    stamp = (f"<!-- Shattered Jade STABLE v{ver} ({ver_date}) — built "
             f"{time.strftime('%Y-%m-%d %H:%M')}, {summary} -->")
    html = html.replace("<title>碎玉 · 战斗原型 — Shattered Jade battle prototype</title>",
                        f"<title>碎玉 v{ver} — Shattered Jade stable</title>\n{stamp}", 1)
    assert stamp in html, "title tag changed — update release.py"

    out_dir = os.path.join(ROOT, "releases")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"shattered_jade_v{ver}.html")
    for path in (out, os.path.join(out_dir, "latest.html")):
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"STABLE v{ver} released ({summary}):\n  {out}\n  {os.path.join(out_dir, 'latest.html')}")


if __name__ == "__main__":
    main()
