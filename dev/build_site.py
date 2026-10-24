"""
Regenerate the website's generated files from the package:

    site/data/broad-street.bundle.json   the demo, as a verifiable bundle
    site/schema/hypgraph-1.json          the vocabulary
    site/atlas/{atlas.js, atlas.css, vendor/}   the explorer, copied from src/hypgraph/ui
    site/py/                             the engine's source + manifest.json, for the Pyodide playground
    site/spec/index.html                 docs/spec.md as a page
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


def page(title: str, lede: str, body: str, toc: list[tuple[str, str]], current: str) -> str:
    nav = "".join(f'<a href="{h}"{" aria-current=\"page\"" if h == current else ""}{c}>{t}</a>'
                  for h, t, c in (("../humans/", "Humans", ""), ("../agents/", "Agents", ""),
                                  ("../play/", "Playground", ' class="hide-sm"'), ("../verify/", "Verify", ' class="hide-sm"'),
                                  ("../spec/", "Spec", ' class="hide-sm"'),
                                  ("https://github.com/voodoomods/hypgraph", "GitHub", ' class="hide-sm"')))
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
<div class="phead"><div class="wrap"><div class="kicker">hypgraph/1 · draft 1</div><h1>{html.escape(title)}</h1>
<p>{html.escape(lede)}</p></div></div>
<div class="wrap doc"><nav class="toc" aria-label="On this page">{toc_html}</nav><article class="prose">
{body}
</article></div>
</main>
<footer><div class="wrap"><span class="slogan">Don't believe the hype. Test the hyp.</span>
<span>Code Apache-2.0 · format &amp; docs CC BY 4.0 · <a href="https://github.com/voodoomods/hypgraph">GitHub</a></span></div></footer>
<script src="../assets/site.js" defer></script>
</body>
</html>
"""


def main() -> None:
    print(f"hypgraph {__version__} -> site/")
    g, inv, story = broad_street.build()
    b = g.export()
    b["story"] = story
    write(SITE / "data" / "broad-street.bundle.json", json.dumps(b, ensure_ascii=False, separators=(",", ":")))
    write(SITE / "schema" / "hypgraph-1.json", json.dumps(describe(), indent=1, ensure_ascii=False))

    atlas = SITE / "atlas"
    for f in ("atlas.js", "atlas.css"):
        write(atlas / f, (PKG / "ui" / f).read_text(encoding="utf-8"))
    shutil.copytree(PKG / "ui" / "vendor", atlas / "vendor", dirs_exist_ok=True)
    shutil.copy2(PKG / "ui" / "hypgraph.svg", SITE / "assets" / "hypgraph.svg")
    print("  site/atlas/vendor/, site/assets/hypgraph.svg")

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
                                                                   "records.", body, toc, "../spec/"))
    shutil.copy2(ROOT / "AGENTS.md", SITE / "agents.md")
    skill = PKG / "skill" / "SKILL.md"
    shutil.copy2(skill, SITE / "SKILL.md")
    (ROOT / "skills" / "hypgraph").mkdir(parents=True, exist_ok=True)
    shutil.copy2(skill, ROOT / "skills" / "hypgraph" / "SKILL.md")
    print("  site/agents.md, site/SKILL.md, skills/hypgraph/SKILL.md")
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
        bad += [f"{f.relative_to(SITE)}: {m}" for m in re.findall(r"""['"]/(?:data|py|assets|atlas)/""", f.read_text(encoding="utf-8"))]
    if bad:
        raise SystemExit("root-absolute paths break the site under a prefix:\n  " + "\n  ".join(bad[:20]))
    print("  paths: all relative")


if __name__ == "__main__":
    main()
