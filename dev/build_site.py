"""
Regenerate the website's generated files from the package:

    site/data/broad-street.bundle.json   the demo, as a verifiable bundle
    site/schema/hypgraph-1.json          the vocabulary
    site/app/{hypgraph.js, hypgraph.css, vendor/}   the UI, copied from src/hypgraph/ui
    site/explore/, site/atlas/ (→ explore)  the UI full screen on any bundle
    site/examples/                       one live example per profile, from site/data/examples/ (dev/site_examples.py)
    site/results/                        results with a real model, from site/data/results/ (dev/site_results.py)
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
from hypgraph.demos import broad_street, cascade, dispute, linked  # noqa: E402
from hypgraph.schema import describe  # noqa: E402

sys.path.insert(0, str(ROOT / "dev"))
import site_i18n  # noqa: E402

SITE = ROOT / "site"
REPO = "https://github.com/voodoomods/hypgraph"
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


def write_examples(lk: dict, dp: dict, cs: dict) -> None:
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
    v = lambda x: f"<span data-v>{html.escape(str(x))}</span>"  # noqa: E731
    lo = lk["london"]
    cards.append(f"""<a class="excard excard-linked" href="dispute/">
  <div class="who">A disputed answer</div>
  <h2 translate="no">{html.escape(dp["title"])}</h2>
  <p>An honest mistake and a lie about the same question. The record refuses both, the honest party corrects hers,
    the liar says it again, and an independent reviewer checks one claim and fails the other.</p>
  <dl><dt>claims</dt><dd>{v(dp["checked"])} checked · {v(dp["contested"])} contested</dd>
    <dt>record</dt><dd>{v(dp["events"])} events · {v(dp["nodes"])} nodes · {v(dp["refused"])} writes refused</dd></dl>
  <div class="codes"><code>COUNT_CONTRADICTS</code> <code>SOURCE_CONTRADICTS</code></div>
  <span class="go">See who gets called out</span>
</a>""")
    cards.append(f"""<a class="excard excard-linked" href="cascade/#view=graph&amp;focus=S1&amp;lens=impact">
  <div class="who">A withdrawn source</div>
  <h2 translate="no">{html.escape(cs["title"])}</h2>
  <p>A decision rests on a vendor benchmark. The vendor withdraws it. Nobody re-reads the memo: the record finds
    every result, claim and decision computed from it, and leaves the team's own load test standing.</p>
  <dl><dt>at risk</dt><dd>{v(cs["at_risk"])} nodes when the benchmark is withdrawn · {v(cs["standing"])} untouched</dd>
    <dt>record</dt><dd>{v(cs["events"])} events · {v(cs["nodes"])} nodes · decision flagged REVISIT, then superseded</dd></dl>
  <span class="go">See what rested on it</span>
</a>""")
    cards.append(f"""<a class="excard excard-linked" href="linked/">
  <div class="who">Linked records</div>
  <h2 translate="no">{html.escape(lo["title"])}</h2>
  <p>Three records, each with its own chain and board, joined by pinned references. A synthesis pins claims in two
    other records, and one of those pins the third, so the graph draws all three together, each verified on its
    own.</p>
  <dl><dt>records</dt><dd>{v(len(lk))} bundles · {v(sum(s["events"] for s in lk.values()))} events · {v(sum(s["nodes"] for s in lk.values()))} nodes</dd>
    <dt>pins</dt><dd>{v(sum(s["pins"] for s in lk.values()))} pinned references, each checked against the record it names</dd></dl>
  <span class="go">See them together</span>
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
<p class="note">With a real model: <a href="../results/">what the record did with gpt-oss-20b</a>, measured on
  preregistered runs, with the limits.</p>
</div>
</main>
{FOOTER}
<script src="../assets/site.js" defer></script>
</body>
</html>
"""
    write(SITE / "examples" / "index.html", body)


LINKED = [  # (name, page folder under examples/linked/, tab label)
    ("london", "", "London's water"),
    ("broad-street", "broad-street", "Broad Street, 1854"),
    ("east-london-1866", "east-london-1866", "East London, 1866"),
]


def write_linked() -> dict:
    """Three records joined by pinned references (hypgraph.demos.linked), each served as its own page and bundle.
    Each page is given the map from every record URL its pins name to that record's bundle on this site, so the
    Explorer can read and verify them without leaving the site (the pins name hypgraph.com URLs)."""
    data = SITE / "data" / "examples" / "linked"
    stats = {}
    for name, (g, inv) in linked.build().items():
        b = g.export()
        write(data / f"{name}.bundle.json", json.dumps(b, ensure_ascii=False, separators=(",", ":")))
        stats[name] = {"events": len(b["events"]), "nodes": len(b["nodes"]), "pins": len(g.references(inv)),
                       "title": linked.TITLES[name]}
    for name, folder, label in LINKED:
        up = "../../../" if folder else "../../"
        page = SITE / "examples" / "linked" / folder / "index.html" if folder else SITE / "examples" / "linked" / "index.html"
        records = {linked.URLS[k]: f"data/examples/linked/{k}.bundle.json" for k in linked.URLS}   # under the site root
        here = "./" if not folder else "../"
        tabs = "".join(f'<a href="{here}{f2 + "/" if f2 else ""}"{CURRENT if n2 == name else ""}>{html.escape(l2)}</a>'
                       for n2, f2, l2 in LINKED)
        bar = (f'<a class="crumb" href="{up}examples/">Examples</a><nav class="tabs" aria-label="Records">{tabs}</nav>'
               f'<span class="sp"></span><a class="act" href="{up}data/examples/linked/{name}.bundle.json" download>Download bundle</a>'
               f'<a class="act hide-sm" href="{up}verify/">Verify it</a>')
        note = ('<p class="appnote"><b>Linked records</b> · three records, each its own hash chain and board, joined '
                'only by pinned references: a source in one record names a node of another, the version it read and '
                'that version’s hash. Open the graph and every record it pins is drawn beside this one, each read '
                'as its own bundle, verified in your browser, and each pin checked against it; the pins are listed under Sources. A teaching '
                'reconstruction: no figures beyond what the records state.</p>')
        mount = (f'<div data-hypgraph data-bundle="{up}data/examples/linked/{name}.bundle.json" data-hash="on" '
                 f'data-view="graph" data-record="{linked.URLS[name]}" '
                 f"data-records='{html.escape(json.dumps(records), quote=True)}' aria-label='{html.escape(label, quote=True)}'></div>")
        write(page, app_page(up, f"{label} · linked records",
                             "One of three HypGraph records joined by pinned references, "
                             "drawn together and each verified on its own.", bar, note, mount))
    return stats


def write_dispute() -> dict:
    """The disputed-answer demo (hypgraph.demos.dispute), opened on the Evidence view: one claim checked, one
    contested. The note says what the record did and what its conduct log says of each party."""
    g, inv, story = dispute.build()
    b = g.export()
    b["story"] = story
    write(SITE / "data" / "examples" / "dispute.bundle.json", json.dumps(b, ensure_ascii=False, separators=(",", ":")))
    conduct = g.conduct(inv)
    review = [g.get(x["node"])["state"]["review"]["state"] for x in story if x.get("code", "").startswith("CL")]
    bar = ('<a class="crumb" href="../">Examples</a><span class="sp"></span>'
           '<a class="act" href="../../data/examples/dispute.bundle.json" download>Download bundle</a>'
           '<a class="act hide-sm" href="../../verify/">Verify it</a>')
    a, m = conduct["ada"], conduct["mallory"]
    assert a["corrected"] and not a["ends_false"] and m["ends_false"] and not m["corrected"]
    note = ('<p class="appnote"><b>A disputed answer</b> · two parties answer one question from the same road '
            'register. <b>Ada</b> makes an honest mistake: 30 km, when the instrument counts 1 of 4 routes shorter. '
            'The record refuses it (<code>COUNT_CONTRADICTS</code>) and she corrects it to 29 km. <b>Mallory</b> '
            'says the register is in miles, citing the register\u2019s own units note, which says kilometres. The '
            'record refuses it (<code>SOURCE_CONTRADICTS</code>), she says it again, then files it without the note. '
            'An independent reviewer reads both against the register. Nobody labels anyone: the standing below is '
            'derived on read, and so is the conduct log, which says Ada corrected what she was shown and Mallory '
            f'said it again {m["reasserted"]} times, never corrected it, and still says it.</p>')
    mount = ('<div data-hypgraph data-bundle="../../data/examples/dispute.bundle.json" data-hash="on" '
             'data-view="evidence" aria-label="A disputed answer"></div>')
    write(SITE / "examples" / "dispute" / "index.html",
          app_page("../../", "A disputed answer", "An honest mistake and a lie about one question: the HypGraph record "
                   "checks one answer, contests the other, and says which author kept saying it.", bar, note, mount))
    return {"title": dispute.TITLE, "events": len(b["events"]), "nodes": len(b["nodes"]),
            "refused": sum("refused" in x for x in story), "checked": review.count("checked"),
            "contested": review.count("contested")}


RESULTS = ("liar-s400", "mistake-s406", "headlines-s400", "hallucinate-s100", "outdated-s100")


def write_results() -> None:
    """Measured results with a real model (site/results/): four findings, each with its numbers, its limits and a
    link that opens the record behind it in the explorer. The bundles come from dev/site_results.py."""
    data = SITE / "data" / "results"
    missing = [k for k in RESULTS if not (data / f"{k}.bundle.json").is_file()]
    if missing:
        raise SystemExit(f"site/data/results/ is missing {missing}: run dev/site_results.py <showcase dir> first")
    size = {k: len(json.loads((data / f"{k}.bundle.json").read_text(encoding="utf-8"))["events"]) for k in RESULTS}

    log = {k: json.loads((data / f"{k}.refusals.json").read_text(encoding="utf-8")) for k in RESULTS}

    def refusals(k: str) -> str:
        """The record's refusal log for one record, quoted: each refused line, why, and what its author filed instead."""
        rows = "".join(f'<tr><td translate="no">{html.escape(r["statement"])}</td>'
                       f'<td>{"<br>".join(f"<code>{c}</code>" for c in r["codes"] if c != "EVIDENCE_MISSING")}</td>'
                       f'<td translate="no">{html.escape(r["fixed"]) if r["fixed"] else "–"}</td></tr>'
                       for r in log[k]["refused"])
        return ('<table><thead><tr><th>refused</th><th>why</th><th>filed instead</th></tr></thead>'
                f'<tbody>{rows}</tbody></table>')

    def conduct(k: str, who: str) -> str:
        return f'<td translate="no">{html.escape(log[k]["conduct"][who])}</td>'

    def rec(k: str, label: str, view: str = "overview") -> str:
        return (f'<a href="../explore/?bundle=../data/results/{k}.bundle.json#view={view}">{label}</a> '
                f'<small>({size[k]} events · <a href="../data/results/{k}.bundle.json" download>bundle</a>)</small>')

    body = f"""
<p>Each result below comes from a run planned and committed before any model call, with gpt-oss-20b, a 20-billion-parameter
open model, playing every seat on local hardware. Where a person judged the text, they labelled it blind: each line
against its own data, shuffled, before any outcome was seen. Every run is two arms on the same seeds. In
<b>prose</b> the seats just write. In <b>record</b> every statement is filed as a HypGraph claim, bound to the
values it rests on, and refused when it says more than they do. The records open in your browser, and their hash
chains are re-verified as they load. A record shows what was accepted. What it refused is kept in a log beside it,
quoted on this page.</p>

<h2 id="headlines">Say no more than the data</h2>
<p>A writer turns test counts into launch headlines, in a house style that bans fractions and asks for strong words.
50 headlines over 10 campaigns:</p>
<table><thead><tr><th></th><th>first drafts</th><th>published through the record</th></tr></thead><tbody>
<tr><td>false against their own count</td><td>15 of 50</td><td><b>2 of 50</b></td></tr>
<tr><td>true, but claiming beyond the test</td><td>8 of 50</td><td>4 of 50</td></tr>
<tr><td>true</td><td>27 of 50</td><td><b>43 of 50</b></td></tr>
<tr><td>nothing published</td><td>–</td><td>1 of 50</td></tr>
</tbody></table>
<p>One campaign's refusal log, on its counts of 57 of 58 real-world files, 12 of 12 encodings, 3 of 6 large files
and 23 of 24 malformed files. A refused headline came back as a true count (a dash where the log links no rewrite):</p>
{refusals("headlines-s400")}
<p><b>Limits.</b> One false headline got through because a singular collective (“Test Suite Triumphs” on 8
of 9) isn't read as “every suite”. A second (“a majority” on 3 of 6) is refused from the next release.
A true absolute without its count (“zero crashes” on 7 runs) is refused until it says the count. That
slows some true headlines down, but it doesn't make them false.</p>
<p>Open the record: {rec("headlines-s400", "this campaign", "evidence")}.</p>

<h2 id="figures">Made-up figures don't get in</h2>
<p>Two seats answer six questions from a staff handbook. One has every section. The other is missing three and is told
to always give a figure. 10 disputes per condition:</p>
<ul>
<li><b>Prose:</b> the seat that couldn't know gave a figure on all 30 of its missing questions, 26 of them wrong.
Every one reached the reader.</li>
<li><b>Record:</b> it filed a made-up figure 41 times, and the record refused <b>39</b>, because no passage it cited
gave that number. It then wrote “the handbook does not say” on 28 of 30, and <b>2</b> wrong figures were published.</li>
<li><b>Who made it up:</b> a rule with no model (“refused for a figure no cited passage gives, on two or more
questions”) named the seat in <b>8 of 10</b> disputes, every one where it really made a figure up, and named
<b>no honest seat in 50</b>. A model judge reading the transcripts caught all 10, but it also accused an honest
seat in 7 of the 20 disputes that had no one making things up.</li>
</ul>
<p><b>Limits.</b> The record checks numbers against the passages a claim cites. It doesn't catch a wrong figure that a
cited passage really gives. One of the two that got through cited a passage about visitor badges that happens to say
“8 hours”. A control that quotes an older edition of the handbook is accepted, and the rule names no one: it
is right about the seat's honesty and wrong about the figures.</p>
<p>The refusal log of one dispute, where the seat told to always answer filed three figures the handbook it had
doesn't give:</p>
{refusals("hallucinate-s100")}
<p>Open the records: {rec("hallucinate-s100", "the seat told to always answer")}; the contrast,
{rec("outdated-s100", "the older edition")}.</p>

<h2 id="bad-actor">Who keeps saying it after being shown</h2>
<p>Two seats argue about the shortest route in a road register. One is a critic briefed to sell a longer route and
never concede. In a control no one lies, and one seat starts from miscopied notes. A tie-breaker who can't see the
register decides who, if anyone, acted in bad faith. Three runs, 40 disputes each, on fresh problems:</p>
<table><thead><tr><th>a model tie-breaker reads</th><th>right answer, liar disputes (runs 1 / 2 / 3)</th><th>liar named</th><th>honest party named, all 20 disputes</th></tr></thead><tbody>
<tr><td>the transcript</td><td>2 / 2 / 4 of 10</td><td>0 / 0 / 0 of 10</td><td>1 / 0 / 0 of 20</td></tr>
<tr><td>the record</td><td><b>10 / 10 / 10 of 10</b></td><td><b>8 / 8 / 10 of 10</b></td><td>1 / 0 / 0 of 20</td></tr>
</tbody></table>
<p>In runs 1 and 2, none of the critics' false “shortest” claims got into the record. Each refusal is shown to its author, and
the record's conduct log counts what happened next: who said it again after being shown, and who corrected it.
Those are facts, not a verdict. Two lines from run 3:</p>
<table><thead><tr><th>who</th><th>the conduct log</th></tr></thead><tbody>
<tr><td>a critic who never conceded</td>{conduct("liar-s400", "iris")}</tr>
<tr><td>an honest seat that slipped once</td>{conduct("mistake-s406", "uma")}</tr>
</tbody></table>
<p><b>Limits.</b> The record measures conduct, not intent. In run 3 an honest seat said its refused figure once more
after correcting it, then corrected it again. The model tie-breaker read that as a mistake, but a preregistered
rule with no model, which names anyone who repeats a refused figure, named it too. The conduct log tells the two
apart only by how many times a figure was repeated and whether the last word is true, so read the counts, not just whether there was a repeat. When the tie-breaker can see the register, a
model judge re-derives the answer itself, and the record adds little. The record pays off when the reader can't re-check.</p>
<p>Open the records: {rec("liar-s400", "a critic who never conceded")}; the contrast,
{rec("mistake-s406", "the honest relapse")}.</p>

<h2 id="tamper">Edits to the record show</h2>
<p>An attacker with write access to the record's file tries five edits. Plain SQL can't delete a refusal: the tables
are append-only. Rewording a claim after dropping that protection is caught by verification. Deleting refusals, or
rewriting every hash to match, is caught only against a chain head published beforehand, as you would publish it
in a paper or a release. The record is tamper-evident, not tamper-proof: publish the head.</p>
<p>Try it: download {rec("liar-s400", "a record")}, change one character, and drop it on <a href="../verify/">Verify</a>.</p>

<h2 id="method">How these were run</h2>
<ul>
<li>Plans, bars and scorers were committed before the runs. Missed bars are reported as missed (the honest seat
named in run 3).</li>
<li>One model plays every seat, at no cloud cost, so these are what a small open model does. A larger model is
not measured here.</li>
<li>The engine is HypGraph's, unmodified. Where a run found a hole in it, the fix went into the library with a test,
and the run is reported as it was.</li>
</ul>
"""
    toc = [("headlines", "Say no more than the data"), ("figures", "Made-up figures"), ("bad-actor", "Who keeps saying it"),
           ("tamper", "Edits show"), ("method", "How these were run")]
    write(SITE / "results" / "index.html",
          page("Results with a real model", "What the record did when a 20B open model wrote launch copy, answered from a "
               "handbook it only half had, and argued with a paid critic: measured, preregistered, with the limits.",
               body, toc, "", kicker="Measured"))


def write_cascade() -> dict:
    """The withdrawn-benchmark demo (hypgraph.demos.cascade). The page opens the record as it stood the moment the
    benchmark was withdrawn, on the graph with the benchmark's impact in focus; the whole record (re-measurement,
    revised claims, REVISIT, the new decision) is a download and a link to the explorer, opened on the old decision."""
    g0, inv0, story0 = cascade.build(until="withdrawn")
    mid = {n["code"]: n["state"] for n in g0.subgraph(inv0)["nodes"]}
    at_risk = sorted(c for c, st in mid.items() if st.get("at_risk"))
    assert at_risk == ["CL1", "CL2", "D1", "RS1", "RS2"], at_risk
    b0 = g0.export()
    b0["story"] = story0
    write(SITE / "data" / "examples" / "cascade-withdrawn.bundle.json",
          json.dumps(b0, ensure_ascii=False, separators=(",", ":")))
    g, inv, story = cascade.build()
    end = {n["code"]: n["state"] for n in g.subgraph(inv)["nodes"]}
    assert end["D1"].get("basis_changed") and not any(end[c].get("at_risk") for c in ("CL1", "CL2", "D2")), end
    b = g.export()
    b["story"] = story
    write(SITE / "data" / "examples" / "cascade.bundle.json", json.dumps(b, ensure_ascii=False, separators=(",", ":")))
    bar = ('<a class="crumb" href="../">Examples</a><span class="sp"></span>'
           '<a class="act" href="../../explore/?bundle=../data/examples/cascade.bundle.json#view=graph&amp;focus=D1'
           '&amp;lens=why">What happened next</a>'
           '<a class="act hide-sm" href="../../data/examples/cascade.bundle.json" download>Download bundle</a>'
           '<a class="act hide-sm" href="../../verify/">Verify it</a>')
    note = ('<p class="appnote"><b>A withdrawn source</b> · an illustration: the engine, the vendor and the team are '
            'made up. A search team decides to move to a new index engine and retire 4 of its 12 servers. Two of the '
            'three claims behind the decision are computed from the vendor’s benchmark; the third is from the '
            'team’s own load test. Then the vendor withdraws the benchmark: the cache was warm. Nobody re-reads '
            'the memo. This is the record at that moment: it marks <b>at risk</b> every result, claim and decision '
            'computed from the benchmark, derived on read from the links that say what each one rests on, and leaves '
            'the load-test claim standing. <b>What happened next</b> opens the whole record: the team re-measures on '
            'its own corpus, revises both claims, the old decision is flagged <b>REVISIT</b> because the claims it '
            'was based on changed, and the new decision retires 3 servers, not 4.</p>')
    mount = ('<div data-hypgraph data-bundle="../../data/examples/cascade-withdrawn.bundle.json" data-hash="on" '
             'data-view="graph" aria-label="A withdrawn source"></div>')
    write(SITE / "examples" / "cascade" / "index.html",
          app_page("../../", "A withdrawn source", "A vendor withdraws the benchmark a decision rested on: the "
                   "HypGraph record finds every result, claim and decision computed from it.", bar, note, mount))
    return {"title": cascade.TITLE, "events": len(b["events"]), "nodes": len(b["nodes"]), "at_risk": len(at_risk),
            "standing": sum(1 for c in ("CL3", "RS3") if not mid[c].get("at_risk"))}


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
    write_examples(write_linked(), write_dispute(), write_cascade())
    write_results()

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
    body = doc_links(body, "docs")
    write(SITE / "spec" / "index.html", page("The record format", "Everything needed to write another "
                                                                   "implementation, a verifier or a viewer of HypGraph "
                                                                   "records.", body, toc, "../spec/", translated_body=False))
    body, toc = markdown((ROOT / "DISCLAIMER.md").read_text(encoding="utf-8").split(chr(10), 1)[1])   # drop the title
    body = doc_links(body, "")
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
    check_links()


def doc_links(body: str, folder: str) -> str:
    """A page rendered from a Markdown file in the repo keeps that file's relative links ("verification.md" in
    docs/spec.md), which have no page on the site: point each at the file on GitHub. The /spec/ page linked to a
    verification.md that 404ed since 0.4 (found checking the merged site, 2026-11-16)."""
    def fix(m: re.Match) -> str:
        ref = m.group(1)
        target = (ROOT / folder / ref.split("#")[0]).resolve()
        if target.is_file() and ROOT in target.parents:
            return f'href="{REPO}/blob/main/{target.relative_to(ROOT).as_posix()}"'
        return m.group(0)
    return re.sub(r'href="(?![a-z]+:|#|\.\./)([^"]+\.md(?:#[^"]*)?)"', fix, body)


def check_links() -> None:
    """Every relative href / src in a page resolves to a file on the site (a folder with an index.html counts).
    Template literals in inline scripts ("${esc(url)}") are not links."""
    bad = []
    for f in SITE.rglob("*.html"):
        if f.name == "404.html" or "py" in f.relative_to(SITE).parts:
            continue
        for ref in re.findall(r'(?:href|src)="([^"]*)"', f.read_text(encoding="utf-8")):
            if not ref or "${" in ref or re.match(r"[a-z][a-z0-9+.-]*:|#|//", ref, re.I):
                continue
            t = (f.parent / ref.split("#")[0].split("?")[0]).resolve()
            if not (t.is_file() or (t / "index.html").is_file()):
                bad.append(f"{f.relative_to(SITE).as_posix()}: {ref}")
    if bad:
        raise SystemExit("links to nothing on the site:\n  " + "\n  ".join(sorted(set(bad))[:20]))
    print("  links: all resolve")


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
