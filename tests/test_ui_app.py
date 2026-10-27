"""The HypGraph UI's static contract (docs/ui-plan.md, P2), without a browser: the app and its one-release Atlas shims,
the page `hypgraph serve` shows, and text contrast in both themes (WCAG AA, 4.5:1). dev/ui_smoke.py renders every
view in headless Chrome; CI runs it."""
import re
import shutil
import subprocess

import pytest

from hypgraph.ui import static_dir

UI = static_dir()


def test_the_app_and_its_atlas_shims():
    js = (UI / "hypgraph.js").read_text(encoding="utf-8")
    assert "global.HypGraph = API" in js and "global.HypAtlas = global.HypAtlas || API" in js
    table = re.search(r"const V = \{([^}]*)\}", js).group(1)                     # the eight views, each with its renderer
    assert [k.split(":")[0].strip() for k in table.split(",")] == ["overview", "live", "pipeline", "graph", "evidence",
                                                                   "orders", "audit", "report"]
    assert "async function verifyBundle" in js and "/stream?inv=" in js          # the chain check and the live stream
    assert "addEventListener('telemetry'" in js and "/telemetry?inv=" in js        # the swarm's telemetry, pushed or polled
    shim = (UI / "atlas.js").read_text(encoding="utf-8")
    assert "hypgraph.js" in shim and "document.write" in shim
    assert '@import url("hypgraph.css")' in (UI / "atlas.css").read_text(encoding="utf-8")
    page = (UI / "index.html").read_text(encoding="utf-8")
    assert "<title>HypGraph</title>" in page and "HypGraph.mount" in page and "hypgraph.css" in page and "Atlas" not in page


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_scripts_parse():
    for f in ("hypgraph.js", "atlas.js"):
        out = subprocess.run(["node", "-e", f"new (require('vm').Script)(require('fs').readFileSync({str(UI / f)!r}, 'utf8'))"],
                             capture_output=True, text=True, check=False)
        assert out.returncode == 0, out.stderr


def _tokens(block: str) -> dict:
    found = dict(re.findall(r"--([a-z0-9-]+):\s*var\(--hg-[a-z0-9-]+,\s*(#[0-9a-f]{6})\)", block))
    found.update(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-f]{6})", block))
    return found


def _ratio(a: str, b: str) -> float:
    def lum(h: str) -> float:
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted([lum(a), lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_text_meets_wcag_aa_in_both_themes():
    css = (UI / "hypgraph.css").read_text(encoding="utf-8")
    light = _tokens(css[css.index(".hg {"):css.index('.hg[data-theme="dark"]')])
    dark = _tokens(css[css.index('.hg[data-theme="dark"]'):css.index(".hg, .hg * {")])
    pairs = [(f, b) for f in ("ink", "ink2", "ink3", "accent", "accent-ink") for b in ("bg", "surface", "surface2", "sunken")]
    pairs += [("accent-ink", "accent-soft"), ("ok", "ok-soft"), ("warn", "warn-soft"), ("bad", "bad-soft"),
              ("info", "info-soft"), ("ok", "surface"), ("warn", "surface"), ("bad", "surface")]
    for name, t in (("light", light), ("dark", dark)):
        low = [(f, b, round(_ratio(t[f], t[b]), 2)) for f, b in pairs if _ratio(t[f], t[b]) < 4.5]
        assert not low, f"{name} theme below 4.5:1: {low}"
