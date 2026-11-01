"""Dev: photograph the website for the README, light and dark, into site/assets/readme/ (served at hypgraph.com).

    pip install playwright pillow && playwright install chromium     # dev only; the package never needs them
    python dev/build_site.py && python dev/readme_shots.py [--record BUNDLE]

The README is also the PyPI page, so it links the pictures by absolute hypgraph.com URL: they show there once the
site is deployed. Serves site/ on a free local port; reads nothing from the network.

    record-<theme>.png      the Graph view of a large real record (--record: a bundle exported with `hypgraph
                            export`; only the graph's node codes are photographed, never its titles or text, and
                            the bundle itself is not published). Without --record the existing pictures are kept.
    linked-<theme>.png      three records joined by pinned references (examples/linked/, Graph view)
    refusals-<theme>.png    overclaims the engine refused, each with its code and the accepted rewrite (home page)
"""
from __future__ import annotations

import argparse
import functools
import http.server
import io
import shutil
import tempfile
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
    ("record", "_record/#view=graph", "#hg-graph", (1500, 1250)),
    ("linked", "examples/linked/#view=graph", "#hg-graph", (1600, 1000)),
    ("refusals", "", "#refusals", (1400, 1000)),
]


class Quiet(http.server.SimpleHTTPRequestHandler):
    record_dir: Path | None = None       # served at /_record/: the explorer page opened on the --record bundle

    def translate_path(self, path):
        if self.record_dir and path.startswith("/_record/"):
            return str(self.record_dir / path[len("/_record/"):].split("?")[0].split("#")[0] or "index.html")
        return super().translate_path(path)

    def log_message(self, *a):
        pass


def record_page(bundle: Path, into: Path) -> None:
    """The explorer page (site/explore/) opened on a local bundle, so its paths still resolve against site/."""
    page = (SITE / "explore" / "index.html").read_text(encoding="utf-8")
    mount = '<div data-hypgraph data-main="on" data-hash="on"'
    if page.count(mount) != 1:
        raise SystemExit("site/explore/index.html: the app mount moved; update record_page")
    (into / "index.html").write_text(page.replace(mount, mount + ' data-bundle="record.bundle.json"'), encoding="utf-8")
    shutil.copyfile(bundle, into / "record.bundle.json")


def save(png: bytes, path: Path) -> None:
    """Scale to WIDTH and write a palette PNG when it stays faithful (flat UI colours), else an optimized RGB one."""
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if im.width > WIDTH:
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.Resampling.LANCZOS)
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--record", type=Path, help="a bundle (.json) to photograph as record-<theme>.png")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.TemporaryDirectory()
    if args.record:
        record_page(args.record, Path(tmp.name))
        Quiet.record_dir = Path(tmp.name)
    shots = [s for s in SHOTS if s[0] != "record" or args.record]
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, page, sel, (w, h) in shots:
                for theme in ("light", "dark"):
                    path, _, frag = page.partition("#")
                    pg = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
                    errors: list[str] = []
                    pg.on("pageerror", lambda e: errors.append(str(e)))
                    pg.goto(f"{base}{path}?theme={theme}" + (f"#{frag}" if frag else ""), wait_until="networkidle")
                    pg.wait_for_timeout(9000)        # the graph layout settles and linked records load
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
        tmp.cleanup()


if __name__ == "__main__":
    main()
