"""Smoke-check the HypGraph UI in headless Chrome: every view × every profile fixture × both themes.

    python dev/ui_smoke.py                    # Chrome found on PATH or in the usual places; exit 1 on any failure
    python dev/ui_smoke.py --shots out/       # also save a 1440×900 screenshot of each
    python dev/ui_smoke.py --chrome PATH

Each page (dev/ui-fixtures/view.html?bundle=<profile>&theme=<t>#view=<v>) must finish rendering (the app sets
data-hg-ready="1" and data-hg-view="<v>") with no script error (data-hg-error unset), and show the view's heading.
Then the website's pages that run the app (site/, built by dev/build_site.py): each profile's live example must open
replaying, with its hash chain verified in the browser and its telemetry shown as not hash-chained; the home page's
embed, the explorer, the /atlas/ forward and the examples gallery must render.
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


EXAMPLES = ["scientific", "software", "trading", "knowledge", "optimization"]
# views of what an engine derived (standing, stages, orders, the report): a bundle's must say they are as exported
EXPORTED = {"overview", "pipeline", "evidence", "orders", "report"}
# site page, the view it must open on ("" = no app on the page), text the page must contain
SITE_PAGES = ([(f"examples/{k}/", "live", ["Replaying", "not hash-chained", 'aria-current="page"']) for k in EXAMPLES]
              + [("", "live", ["chain verified", "Replaying", "data-open-claim", 'class="card ref"', "0 errors"]),
                 ("explore/", "overview", []), ("atlas/", "overview", []),
                 ("examples/", "", ['class="excard"'] * 1 + [f'href="{k}/"' for k in EXAMPLES])])


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
    m = (re.search(r'<div data-hypgraph(?:="")?([^>]*)>', dom) if el == "[data-hypgraph]"
         else re.search(rf'<div id="{el}"([^>]*)>', dom))
    if not m:
        return f"no {el} element in the page"
    attrs = m.group(1)
    err = re.search(r'data-hg-error="([^"]*)"', attrs)
    if err:
        return f"script error: {err.group(1)}"
    if 'data-hg-ready="1"' not in attrs:
        return "never finished rendering"
    if f'data-hg-view="{view}"' not in attrs:
        return f"rendered {re.search(r'data-hg-view=\"([^\"]*)\"', attrs).group(1) if 'data-hg-view' in attrs else 'nothing'}, not {view}"
    want = HEADINGS[view]
    h1 = re.compile(r"<h1>(.*?)</h1>", re.S).search(dom, m.end())        # the app's own heading, not the page's
    if not h1 or (want and want not in h1.group(1)):
        return f"heading {h1.group(1) if h1 else 'missing'!r}, wanted {want!r}"
    if view == "graph" and "<canvas" not in dom:
        return "the graph drew nothing"
    if view == "live" and telemetry and ('class="trace"' not in dom or "telemetry · " not in dom):
        return "the run's telemetry isn't shown (no trace or telemetry pill)"
    if view in EXPORTED and "⛓ verified" in dom and "data-exported" not in dom and 'class="note warn"' not in dom             and "has no workflow profile" not in dom:                # nothing derived on the page
        return "a bundle's derived view is shown without saying it is as exported, not verified"
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
        site = 0
        if (ROOT / "site" / "examples" / "index.html").exists():
            for page, view, extra in SITE_PAGES:
                url = f"http://127.0.0.1:{port}/site/{page}"
                shot = (shots / ("site-" + (page.strip("/").replace("/", "-") or "home") + ".png")) if shots else None
                dom = run(chrome, url, shot=shot)
                why = (check(dom, view, "app" if page == "" else "[data-hypgraph]", telemetry=page.startswith("examples/"))
                       if view else "")
                why = why or next((f"missing {x!r}" for x in extra if x not in dom), "")
                if view and not why and "⛓ verified" not in dom:
                    why = "the hash chain wasn't verified in the browser"
                bad += bool(why)
                site += 1
                print(f"{'FAIL' if why else 'ok  '} site/{page:24} {view or 'page':9} {why}", flush=True)
    finally:
        srv.shutdown()
    n = len(FIXTURES) * len(args.themes.split(",")) * len(VIEWS) + 1 + site
    print(f"\n{n - bad} of {n} pages render")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
