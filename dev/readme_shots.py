"""Dev: photograph the website for the README, light and dark, into site/assets/readme/ (served at hypgraph.com).

    pip install playwright pillow && playwright install chromium     # dev only; the package never needs them
    python dev/build_site.py && python dev/readme_shots.py

The README is also the PyPI page, so it links the pictures by absolute hypgraph.com URL: they show there once the
site is deployed. Serves site/ on a free local port; reads nothing from the network.

    linked-<theme>.png      three records joined by pinned references (examples/linked/, Graph view)
    refusals-<theme>.png    overclaims the engine refused, each with its code and the accepted rewrite (home page)
    standing-<theme>.png    the Broad Street record with a claim's standing open (explore/, Graph view, node CL1)
"""
from __future__ import annotations

import functools
import http.server
import io
import threading
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE, OUT = ROOT / "site", ROOT / "site" / "assets" / "readme"
WIDTH = 1760                     # 2x GitHub's README column, so text stays sharp on high-density screens
PAD = 20                         # CSS px around an element shot

# name, page, element to photograph, viewport
SHOTS = [
    ("linked", "examples/linked/#view=graph", "#hg-graph", (1600, 1000)),
    ("refusals", "", "#refusals", (1400, 1000)),
    ("standing", "explore/#view=graph&node=CL1", None, (1600, 1000)),
]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def save(png: bytes, path: Path) -> None:
    """Scale to WIDTH and write a palette PNG when it stays faithful (flat UI colours), else an optimized RGB one."""
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if im.width > WIDTH:
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.Resampling.LANCZOS)
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, page, sel, (w, h) in SHOTS:
                for theme in ("light", "dark"):
                    path, _, frag = page.partition("#")
                    pg = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
                    errors: list[str] = []
                    pg.on("pageerror", lambda e: errors.append(str(e)))
                    pg.goto(f"{base}{path}?theme={theme}" + (f"#{frag}" if frag else ""), wait_until="networkidle")
                    pg.wait_for_timeout(6000)        # the graph layout settles and linked records load
                    if errors:
                        raise SystemExit(f"{name} ({theme}): {errors[0]}")
                    clip = None
                    if sel:
                        el = pg.query_selector(sel)
                        if el is None:
                            raise SystemExit(f"{name} ({theme}): no {sel} on {page or 'the home page'}")
                        b = el.bounding_box()            # a margin, so card borders don't touch the picture's edge
                        clip = {"x": b["x"] - PAD, "y": b["y"] - PAD, "width": b["width"] + 2 * PAD,
                                "height": b["height"] + 2 * PAD}
                    out = OUT / f"{name}-{theme}.png"
                    save(pg.screenshot(clip=clip, full_page=bool(clip)), out)
                    print(f"{out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB")
                    pg.close()
            browser.close()
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
