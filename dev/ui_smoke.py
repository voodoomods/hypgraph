"""Smoke-check the HypGraph UI in headless Chrome: every view × every profile fixture × both themes.

    python dev/ui_smoke.py                    # Chrome found on PATH or in the usual places; exit 1 on any failure
    python dev/ui_smoke.py --shots out/       # also save a 1440×900 screenshot of each
    python dev/ui_smoke.py --chrome PATH

Each page (dev/ui-fixtures/view.html?bundle=<profile>&theme=<t>#view=<v>) must finish rendering (the app sets
data-hg-ready="1" and data-hg-view="<v>") with no script error (data-hg-error unset), and show the view's heading.
Serves the repo root on a free local port; reads nothing from the network."""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = sorted(p.name.split(".")[0] for p in (ROOT / "dev" / "ui-fixtures").glob("*.bundle.json"))
VIEWS = ["overview", "live", "pipeline", "graph", "evidence", "orders", "audit", "report"]
HEADINGS = {"overview": None, "live": "Live", "pipeline": "Pipeline", "graph": "Graph", "evidence": "Evidence",
            "orders": "Work orders", "audit": "Audit log", "report": None}


def chrome_path(given: str = "") -> str:
    for c in [given, os.environ.get("CHROME", ""), "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        if c and (shutil.which(c) or Path(c).exists()):
            return shutil.which(c) or c
    raise SystemExit("no Chrome / Chromium found (pass --chrome or set CHROME)")


def serve() -> tuple[http.server.ThreadingHTTPServer, int]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a: object) -> None:
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def run(chrome: str, url: str, *, shot: Path | None = None) -> str:
    base = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", "--window-size=1440,900",
            "--virtual-time-budget=6000", "--run-all-compositor-stages-before-draw"]
    if shot:
        subprocess.run(base + [f"--screenshot={shot}", url], capture_output=True, timeout=90, check=False)
    out = subprocess.run(base + ["--dump-dom", url], capture_output=True, timeout=90, check=False, text=True,
                         encoding="utf-8", errors="replace")
    return out.stdout


def check(dom: str, view: str, el: str = "app", telemetry: bool = False) -> str:
    m = re.search(rf'<div id="{el}"([^>]*)>', dom)
    if not m:
        return f"no #{el} element in the page"
    attrs = m.group(1)
    err = re.search(r'data-hg-error="([^"]*)"', attrs)
    if err:
        return f"script error: {err.group(1)}"
    if 'data-hg-ready="1"' not in attrs:
        return "never finished rendering"
    if f'data-hg-view="{view}"' not in attrs:
        return f"rendered {re.search(r'data-hg-view=\"([^\"]*)\"', attrs).group(1) if 'data-hg-view' in attrs else 'nothing'}, not {view}"
    want = HEADINGS[view]
    h1 = re.search(r"<h1>(.*?)</h1>", dom, re.S)
    if not h1 or (want and want not in h1.group(1)):
        return f"heading {h1.group(1) if h1 else 'missing'!r}, wanted {want!r}"
    if view == "graph" and "<canvas" not in dom:
        return "the graph drew nothing"
    if view == "live" and telemetry and ('class="trace"' not in dom or "telemetry · " not in dom):
        return "the run's telemetry isn't shown (no trace or telemetry pill)"
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chrome", default="")
    ap.add_argument("--shots", default="")
    ap.add_argument("--themes", default="light,dark")
    args = ap.parse_args()
    chrome = chrome_path(args.chrome)
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    srv, port = serve()
    bad = 0
    try:
        for fx in FIXTURES:
            for theme in args.themes.split(","):
                for v in VIEWS:
                    url = f"http://127.0.0.1:{port}/dev/ui-fixtures/view.html?bundle={fx}&theme={theme}#view={v}"
                    shot = (shots / f"{fx}-{theme}-{v}.png") if shots else None
                    has_tel = (ROOT / "dev" / "ui-fixtures" / f"{fx}.telemetry.jsonl").exists()
                    why = check(run(chrome, url, shot=shot), v, telemetry=has_tel)
                    bad += bool(why)
                    print(f"{'FAIL' if why else 'ok  '} {fx:13} {theme:5} {v:9} {why}", flush=True)
        # a page written for the Atlas (atlas.css + atlas.js + HypAtlas.mount, dark host tokens) keeps working
        url = f"http://127.0.0.1:{port}/dev/ui-fixtures/atlas-compat.html#view=pipeline"
        why = check(run(chrome, url, shot=(shots / "atlas-compat.png") if shots else None), "pipeline", "page-atlas")
        bad += bool(why)
        print(f"{'FAIL' if why else 'ok  '} atlas-compat  dark  pipeline  {why}", flush=True)
    finally:
        srv.shutdown()
    n = len(FIXTURES) * len(args.themes.split(",")) * len(VIEWS) + 1
    print(f"\n{n - bad} of {n} pages render")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
