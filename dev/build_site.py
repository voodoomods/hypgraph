"""
Regenerate the website's generated files from the package:

    site/data/broad-street.bundle.json   the demo, as a verifiable bundle
    site/schema/hypgraph-1.json          the vocabulary
    site/app/{hypgraph.js, hypgraph.css, vendor/}   the UI, copied from src/hypgraph/ui
    site/explore/, site/atlas/ (→ explore)  the UI full screen on any bundle
    site/examples/                       one live example per profile, from site/data/examples/ (dev/site_examples.py)
    site/py/                             the engine's source + manifest.json, for the Pyodide playground
    site/spec/index.html                 docs/spec.md as a page
    site/disclaimer/index.html           DISCLAIMER.md as a page
    site/<lang>/…, site/assets/strings.<lang>.js   the main pages in es / fr / de / zh-Hans (dev/site_i18n.py)
    site/sitemap.xml                     every page, with its language alternates
    site/agents.md                       AGENTS.md
    site/SKILL.md, skills/hypgraph/      the agent skill (source: src/hypgraph/skill/SKILL.md)

    python dev/build_site.py
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hypgraph import __version__  # noqa: E402
from hypgraph.demos import broad_street  # noqa: E402
from hypgraph.schema import describe  # noqa: E402

sys.path.insert(0, str(ROOT / "dev"))
import site_i18n  # noqa: E402

SITE = ROOT / "site"
PKG = ROOT / "src" / "hypgraph"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes)")


def md_inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s.replace("\\*", "*")


def markdown(md: str) -> tuple[str, list[tuple[str, str]]]:
    """Just enough Markdown for our docs: headings, paragraphs, fenced code, tables, lists, quotes."""
    out, toc, lines, i = [], [], md.splitlines(), 0
    slug = lambda t: re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")  # noqa: E731
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            buf, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            out.append('<div class="code"><pre>' + html.escape("\n".join(buf)) + "</pre></div>")
            i += 1
            continue
        m = re.match(r"(#{1,3}) (.*)", ln)
        if m:
            level, text = len(m.group(1)), m.group(2)
            if level == 1:
                i += 1
                continue                                     # the page header carries the title
            sid = slug(re.sub(r"`", "", text))
            if level == 2:
                toc.append((sid, re.sub(r"`", "", text)))
            out.append(f'<h{level} id="{sid}">{md_inline(text)}</h{level}>')
            i += 1
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in re.split(r"(?<!\\)\|", lines[i].strip().strip("|"))])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            out.append("<table><thead><tr>" + "".join(f"<th>{md_inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in body)
                       + "</tbody></table>")
            continue
        if re.match(r"\s*([-*]|\d+\.) ", ln):
            ordered = bool(re.match(r"\s*\d+\. ", ln))
            items, i = [], i
            while i < len(lines) and (re.match(r"\s*([-*]|\d+\.) ", lines[i]) or (lines[i].startswith("   ") and items)):
                if re.match(r"\s*([-*]|\d+\.) ", lines[i]):
                    nested = lines[i].startswith("  ")
                    items.append([nested, re.sub(r"^\s*([-*]|\d+\.) ", "", lines[i])])
                else:
                    items[-1][1] += " " + lines[i].strip()
                i += 1
            tag = "ol" if ordered else "ul"
            h, open_sub = [f"<{tag}>"], False
            for nested, text in items:
                if nested and not open_sub:
                    h[-1] = h[-1].removesuffix("</li>")
                    h.append("<ul>")
                    open_sub = True
                elif not nested and open_sub:
                    h.append("</ul></li>")
                    open_sub = False
                h.append(f"<li>{md_inline(text)}</li>")
            if open_sub:
                h.append("</ul></li>")
            out.append("".join(h) + f"</{tag}>")
            continue
        if ln.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> "))
                i += 1
            out.append("<blockquote>" + md_inline(" ".join(buf)) + "</blockquote>")
            continue
        if not ln.strip():
            i += 1
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#{1,3} |```|\||\s*([-*]|\d+\.) |>)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>" + md_inline(" ".join(buf)) + "</p>")
    return "\n".join(out), toc


CURRENT = ' aria-current="page"'


def nav_links(current: str, up: str = "../") -> str:
    return "".join(f'<a href="{h}"{CURRENT if h == current else ""}{c}>{t}</a>'
                   for h, t, c in ((f"{up}agents/", "Agents", ""), (f"{up}engineers/", "Engineers", ""),
                                   (f"{up}examples/", "Examples", ""), (f"{up}never/", "Never", ' class="hide-sm"'),
                                   (f"{up}#workflows", "Workflows", ' class="hide-sm"'),
                                   (f"{up}play/", "Playground", ' class="hide-sm"'), (f"{up}verify/", "Verify", ' class="hide-sm"'),
                                   (f"{up}spec/", "Spec", ' class="hide-sm"'),
                                   ("https://github.com/voodoomods/hypgraph", "GitHub", ' class="hide-sm"')))


FOOTER = """<footer><div class="wrap"><span class="slogan">Don't believe the hype. Test the hyp.</span>
<span>Made by <a href="https://www.linkedin.com/in/nicolas-houghtaling-b68074147">Nicolas Houghtaling</a> · VoodooMods LLC · Code Apache-2.0 · format &amp; docs CC BY 4.0 · <a href="../disclaimer/">Disclaimer</a> · <a href="https://github.com/voodoomods/hypgraph">GitHub</a></span></div></footer>"""


def page(title: str, lede: str, body: str, toc: list[tuple[str, str]], current: str, kicker: str = "hypgraph/1 · draft 1",
         translated_body: bool = True) -> str:
    nav = nav_links(current)
    no = "" if translated_body else ' translate="no"'          # the spec stays English in every language
    toc_html = "".join(f'<a href="#{s}">{html.escape(t)}</a>' for s, t in toc)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — HypGraph</title>
<meta name="description" content="{html.escape(lede)}">
<link rel="icon" href="../assets/hypgraph.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/site.css">
<script>try{{const t=localStorage.getItem('hg-theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="nav"><div class="wrap">
  <a class="brand" href="../"><img src="../assets/hypgraph.svg" alt=""><span>Hyp<b>Graph</b></span></a>
  <nav aria-label="Site">{nav}<button class="iconbtn" data-toggle-theme type="button" aria-label="Toggle light and dark">◐</button></nav>
</div></header>
<main id="main">
<div class="phead"><div class="wrap"><div class="kicker">{html.escape(kicker)}</div><h1>{html.escape(title)}</h1>
<p>{html.escape(lede)}</p></div></div>
<div class="wrap doc"><nav class="toc" aria-label="On this page"{no}>{toc_html}</nav><article class="prose"{no}>
{body}
</article></div>
</main>
{FOOTER}
<script src="../assets/site.js" defer></script>
</body>
</html>
"""


# HypSwarm's five scripted examples, one per @2 profile (the bundles come from dev/site_examples.py)
EXAMPLES = [
    ("scientific", "Scientific", "01-eval-report",
     "Two analysts and a critic test an evaluation claim. The instrument re-runs every value before any review, and "
     "the report is checked against the record."),
    ("software", "Software", "02-software-tests",
     "The tests count only when the instrument runs them. A tester's \u201cpasses\u201d written before that run is "
     "refused, reworked and accepted once the lab run lands."),
    ("trading", "Trading", "03-paper-trading",
     "A backtest on a held-out window, with fees and slippage. A result without costs is refused before it can "
     "become a thesis."),
    ("knowledge", "Knowledge", "04-sourced-brief",
     "Three facts, each a source node and a claim that cites it. A claim with nothing behind it is refused."),
    ("optimization", "Optimization", "05-optimal-with-bound",
     "Objective, feasibility and a gap. An objective with no feasibility check is refused, and \u201coptimal\u201d "
     "needs a bound that meets it."),
]
VENDOR = ("cytoscape.min.js", "layout-base.js", "cose-base.js", "cytoscape-fcose.js")


def app_page(up: str, title: str, desc: str, bar: str, note: str, mount: str) -> str:
    """A full-screen HypGraph page: the site's bar, an optional note, and the app on a bundle (assets/embed.js)."""
    scripts = "".join(f'<script src="{up}app/vendor/{v}"></script>\n' for v in VENDOR)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — HypGraph</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="icon" href="{up}assets/hypgraph.svg" type="image/svg+xml">
<link rel="stylesheet" href="{up}assets/site.css">
<link rel="stylesheet" href="{up}app/hypgraph.css">
<script>try{{document.documentElement.dataset.theme=localStorage.getItem('hg-theme')||'light'}}catch(e){{document.documentElement.dataset.theme='light'}}</script>
</head>
<body class="apppage">
<header class="appbar"><a class="brand" href="{up}"><img src="{up}assets/hypgraph.svg" alt=""><span>Hyp<b>Graph</b></span></a>
{bar}</header>
{note}<div class="appfull">{mount}</div>
{scripts}<script src="{up}app/hypgraph.js"></script>
<script src="{up}assets/site.js"></script>
<script src="{up}assets/embed.js"></script>
</body>
</html>
"""


def _report_name(r: object) -> str:
    return r if isinstance(r, str) else str((r or {}).get("name") or "") if isinstance(r, dict) else ""


def example_stats(path: Path) -> dict:
    b = json.loads(path.read_text(encoding="utf-8"))
    tel = (b.get("telemetry") or {}).get("events") or []
    inv = b["scope"]["inv"]
    d = b["derived"]["by_inv"][inv]
    refused = [t for t in tel if t["kind"] == "tool_end" and not t.get("ok", True) and "refused" in (t.get("error") or "")]
    codes = sorted({c for t in refused for c in re.findall(r"\[([A-Z][A-Z_]+)\]", t.get("error") or "")})
    start = next((t for t in tel if t["kind"] == "run_start"), {})
    end = next((t for t in tel if t["kind"] == "run_end"), {})
    return {"title": b["scope"]["title"], "report": _report_name(((d.get("profile") or {}).get("workflow") or {}).get("report")),
            "events": len(b["events"]), "nodes": len(b["nodes"]), "telemetry": len(tel),
            "calls": sum(1 for t in tel if t["kind"] == "model_end"), "tools": sum(1 for t in tel if t["kind"] == "tool_end"),
            "seats": [s["name"] for s in start.get("seats", [])], "refused": len(refused), "codes": codes,
            "seconds": round(end.get("ts", 0) - start.get("ts", 0)) if end and start else 0,
            "stopped": end.get("stopped", ""), "head": b["head"], "size": path.stat().st_size}


def write_examples() -> None:
    data = SITE / "data" / "examples"
    stats = {k: example_stats(data / f"{k}.bundle.json") for k, *_ in EXAMPLES if (data / f"{k}.bundle.json").is_file()}
    if len(stats) != len(EXAMPLES):
        raise SystemExit("site/data/examples/ is missing bundles: run dev/site_examples.py first")
    for k, label, folder, blurb in EXAMPLES:
        s = stats[k]
        tabs = "".join(f'<a href="../{k2}/"{CURRENT if k2 == k else ""}>{l2}</a>' for k2, l2, *_ in EXAMPLES)
        bar = (f'<a class="crumb" href="../">Examples</a><nav class="tabs" aria-label="Profiles">{tabs}</nav>'
               f'<span class="sp"></span><a class="act" href="../../data/examples/{k}.bundle.json" download>Download bundle</a>'
               f'<a class="act hide-sm" href="../../verify/">Verify it</a>')
        note = (f'<p class="appnote"><b>{html.escape(label)}</b> · HypSwarm example '
                f'<a href="https://github.com/voodoomods/hypswarm/tree/main/examples/{folder}">{folder}</a>, run on its '
                f'scripted models: the answers are computed by the example, each model reply is paced 0.35–1.4 s, and '
                f'token counts are the scripted model\u2019s. The record is exactly what the run wrote; its hash chain '
                f'is re-verified in your browser. The telemetry rides along outside the chain.</p>')
        mount = (f'<div data-hypgraph data-bundle="../../data/examples/{k}.bundle.json" data-hash="on" data-play="on" '
                 f'aria-label="{html.escape(label)} example"></div>')
        write(SITE / "examples" / k / "index.html",
              app_page("../../", f"{label} example", f"{s['title']}: a HypSwarm run under the {label.lower()} profile, "
                       "replayed live — every model and tool call, work order, review and refusal.", bar, note, mount))

    cards = []
    for k, label, folder, blurb in EXAMPLES:
        s = stats[k]
        codes = f'<div class="codes">{" ".join(f"<code>{c}</code>" for c in s["codes"])}</div>' if s["codes"] else ""
        v = lambda x: f"<span data-v>{html.escape(str(x))}</span>"  # noqa: E731 — a figure, not words to translate
        refused = (f'{v(s["refused"])} write{"s" if s["refused"] != 1 else ""} refused, then rewritten' if s["refused"]
                   else "no refusals")
        cards.append(f"""<a class="excard" href="{k}/">
  <div class="who">{html.escape(label)}{f' · <span translate="no">{html.escape(s["report"])}</span>' if s["report"] else ''}</div>
  <h2 translate="no">{html.escape(s["title"])}</h2>
  <p>{html.escape(blurb)}</p>
  <dl><dt>seats</dt><dd translate="no">{html.escape(", ".join(s["seats"]))}</dd>
    <dt>run</dt><dd>{v(s["calls"])} model calls · {v(s["tools"])} tool calls · {v(s["seconds"])} s · {html.escape(s["stopped"])}</dd>
    <dt>record</dt><dd>{v(s["events"])} events · {v(s["nodes"])} nodes · {refused}</dd></dl>{codes}
  <span class="go">Watch it run</span>
</a>""")
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Examples — HypGraph</title>
<meta name="description" content="Five swarms, one per profile — scientific, software, trading, knowledge, optimization — replayed live in HypGraph: every model call, tool call, work order, review and refusal.">
<link rel="icon" href="../assets/hypgraph.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/site.css">
<script>try{{const t=localStorage.getItem('hg-theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="nav"><div class="wrap">
  <a class="brand" href="../"><img src="../assets/hypgraph.svg" alt=""><span>Hyp<b>Graph</b></span></a>
  <nav aria-label="Site">{nav_links("../examples/")}<button class="iconbtn" data-toggle-theme type="button" aria-label="Toggle light and dark">◐</button></nav>
</div></header>
<main id="main">
<div class="phead"><div class="wrap"><div class="kicker">Live examples</div><h1>Watch a swarm work, in each profile</h1>
<p>Each example is a real HypSwarm run on a real record: seats pick up work orders from the record, write results
  and claims through it, get refused when they overclaim, and are reviewed before anything counts. Open one and it
  replays from the first event — model and tool calls in flight, the graph growing, the board settling. Then explore
  its pipeline, graph, evidence and report.</p></div></div>
<div class="wrap"><div class="exgrid">
{chr(10).join(cards)}
</div>
<p class="note">The runs use HypSwarm's scripted models, so they cost nothing and replay the same way every time; run
  any of them with a real model with <code>python run.py --model &lt;id&gt;</code>. Rebuild these pages with
  <code>dev/site_examples.py</code>. Each bundle verifies on its own: <a href="../verify/">verify one</a>.</p>
</div>
</main>
{FOOTER}
<script src="../assets/site.js" defer></script>
</body>
</html>
"""
    write(SITE / "examples" / "index.html", body)


def write_explore() -> None:
    bar = ('<a class="crumb" href="../examples/">Examples</a><span class="sp"></span>'
           '<a class="act" href="../verify/">Verify another bundle</a>')
    mount = '<div data-hypgraph data-main="on" data-hash="on" aria-label="HypGraph"></div>'
    write(SITE / "explore" / "index.html",
          app_page("../", "Explore a record", "Open a HypGraph bundle in your browser: the pipeline, graph, evidence, "
                   "audit log and report, with the hash chain re-verified as it loads.", bar, "", mount))
    # the Atlas became HypGraph: its page forwards to the explorer, keeping ?bundle=, ?from=verify and the fragment
    atlas = SITE / "atlas"
    shutil.rmtree(atlas, ignore_errors=True)
    write(atlas / "index.html", """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HypGraph</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="../explore/">
<script>location.replace('../explore/' + location.search + location.hash);</script>
<noscript><meta http-equiv="refresh" content="0; url=../explore/"></noscript>
</head>
<body><p>The Atlas is now HypGraph: <a href="../explore/">open the explorer</a>.</p></body>
</html>
""")


def main() -> None:
    print(f"hypgraph {__version__} -> site/")
    g, inv, story = broad_street.build()
    b = g.export()
    b["story"] = story
    write(SITE / "data" / "broad-street.bundle.json", json.dumps(b, ensure_ascii=False, separators=(",", ":")))
    write(SITE / "schema" / "hypgraph-1.json", json.dumps(describe(), indent=1, ensure_ascii=False))

    app = SITE / "app"
    for f in ("hypgraph.js", "hypgraph.i18n.js", "hypgraph.css"):
        write(app / f, (PKG / "ui" / f).read_text(encoding="utf-8"))
    shutil.copytree(PKG / "ui" / "vendor", app / "vendor", dirs_exist_ok=True)
    shutil.copy2(PKG / "ui" / "hypgraph.svg", SITE / "assets" / "hypgraph.svg")
    print("  site/app/vendor/, site/assets/hypgraph.svg")
    write_explore()
    write_examples()

    py = SITE / "py"
    shutil.rmtree(py, ignore_errors=True)
    files = []
    for f in sorted(PKG.rglob("*.py")):
        rel = f.relative_to(PKG.parent).as_posix()
        if rel in ("hypgraph/mcp.py", "hypgraph/server.py") or "/ui/" in rel:
            continue
        (py / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, py / rel)
        files.append(rel)
    (py / "hypgraph" / "ui").mkdir(exist_ok=True)
    (py / "hypgraph" / "ui" / "__init__.py").write_text("", encoding="utf-8")
    files.append("hypgraph/ui/__init__.py")
    write(py / "manifest.json", json.dumps({"version": __version__, "files": files}, indent=1))

    body, toc = markdown((ROOT / "docs" / "spec.md").read_text(encoding="utf-8"))
    write(SITE / "spec" / "index.html", page("The record format", "Everything needed to write another "
                                                                   "implementation, a verifier or a viewer of HypGraph "
                                                                   "records.", body, toc, "../spec/", translated_body=False))
    body, toc = markdown((ROOT / "DISCLAIMER.md").read_text(encoding="utf-8").split(chr(10), 1)[1])   # drop the title
    write(SITE / "disclaimer" / "index.html", page("Disclaimer", "What HypGraph promises, and what it does not: "
                                                                 "provided as is, standing derived rather than "
                                                                 "certified, and no advice.", body, toc, "", kicker="Terms"))
    shutil.copy2(ROOT / "AGENTS.md", SITE / "agents.md")
    skill = PKG / "skill" / "SKILL.md"
    shutil.copy2(skill, SITE / "SKILL.md")
    (ROOT / "skills" / "hypgraph").mkdir(parents=True, exist_ok=True)
    shutil.copy2(skill, ROOT / "skills" / "hypgraph" / "SKILL.md")
    print("  site/agents.md, site/SKILL.md, skills/hypgraph/SKILL.md")
    site_i18n.build(write)
    check_paths()


def check_paths() -> None:
    """The site must work at / (hypgraph.com) and under a prefix (<owner>.github.io/hypgraph/): no root-absolute
    href/src in any page (404.html sets its own <base>)."""
    bad = []
    for f in SITE.rglob("*.html"):
        if f.name == "404.html" or "py" in f.relative_to(SITE).parts:
            continue
        bad += [f"{f.relative_to(SITE)}: {m}" for m in re.findall(r'(?:href|src)="/(?!/)[^"]*"', f.read_text(encoding="utf-8"))]
    for f in (SITE / "assets").glob("*.js"):
        bad += [f"{f.relative_to(SITE)}: {m}" for m in re.findall(r"""['"]/(?:data|py|assets|app|atlas)/""", f.read_text(encoding="utf-8"))]
    if bad:
        raise SystemExit("root-absolute paths break the site under a prefix:\n  " + "\n  ".join(bad[:20]))
    print("  paths: all relative")


if __name__ == "__main__":
    main()
