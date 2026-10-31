"""
The website in other languages. English pages are the source; each translated page is made from its English page by
swapping text segments for their translations in i18n/site/<lang>.json, so markup, figures, links and scripts can't
drift between languages.

A segment is the text of one block (a paragraph, heading, list item, cell, button…) with its inline markup, whitespace
collapsed. Its translation must carry exactly the same tags (attributes and all) and the same text inside <code>.
Text under translate="no", <script>, <style>, <pre> and <code> stays as written, and so does a segment made only of
names the glossary keeps (i18n/glossary.json). A few attributes (alt, title, aria-label, placeholder, a meta
description) are segments of their own.

Strings the site's scripts show are written t('English text', {vars}) and translated from the catalog's "js" table,
which the build writes to site/assets/strings.<lang>.js for translated pages to load.

    python dev/site_i18n.py     # writes i18n/site/en.json (the msgids) and lists what each language is missing
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
I18N = ROOT / "i18n"
LANGS = {"es": "Español", "fr": "Français", "de": "Deutsch", "zh-Hans": "简体中文"}
ALL = {"en": "English", **LANGS}
ORIGIN = "https://hypgraph.com/"
# what the build itself writes on a translated page, in English (each catalog's "build" table translates it)
BUILD = {"note": "This page is a translation. The English page is the authoritative version:",
         "note_spec": "This page's navigation is translated; the specification itself is in English, which is authoritative:",
         "menu": "Language"}
# the English pages that have translations, as paths under site/ (the build writes site/<lang>/<path>)
PAGES = ["index.html", "agents/index.html", "engineers/index.html", "examples/index.html",
         *(f"examples/{k}/index.html" for k in ("scientific", "software", "trading", "knowledge", "optimization")),
         "explore/index.html", "never/index.html", "verify/index.html", "play/index.html", "spec/index.html",
         "disclaimer/index.html"]

INLINE = {"a", "b", "i", "em", "strong", "code", "span", "br", "kbd", "sup", "sub", "small", "abbr", "time", "mark",
          "s", "u", "q", "button", "img", "wbr", "label"}
RAW = {"script", "style", "pre", "textarea"}          # contents never translated (or segmented)
VOID = {"br", "img", "wbr", "input", "meta", "link", "hr", "source", "col", "area", "base", "embed", "param", "track"}
ATTRS = ("alt", "title", "aria-label", "placeholder")
TOKEN = re.compile(r"(<!--.*?-->|<![^>]*>|<[^>]+>)", re.S)
TAG = re.compile(r"<(/?)([a-zA-Z][\w-]*)([^>]*)>", re.S)
LETTER = re.compile(r"[^\W\d_]", re.U)


def keep_terms() -> list[str]:
    return json.loads((I18N / "glossary.json").read_text(encoding="utf-8"))["keep"]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def plain(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def worth(seg: str, keep: list[str]) -> bool:
    """A segment needs a translation when it has words other than names the glossary keeps."""
    t = plain(re.sub(r"<code\b[^>]*>.*?</code>", " ", seg, flags=re.S))
    if re.fullmatch(r"[\s\d.,%]*(s|ms|MB|KB)?", t) or ("_" in t and re.fullmatch(r"[A-Z0-9_\s·,]+", t)):
        return False                                  # a figure with its unit, or refusal codes
    for k in sorted(keep, key=len, reverse=True):
        t = re.sub(rf"(?<![\w]){re.escape(k)}(?![\w])", " ", t)
    return bool(LETTER.search(t))


def _attr(tag: str, name: str) -> str | None:
    m = re.search(rf'\s{re.escape(name)}="([^"]*)"', tag)
    return m.group(1) if m else None


def _runs(tokens: list[str]):
    """Yield (start, end) token ranges of inline runs that can be translated, skipping raw and translate="no" parts."""
    skip, start, depth_no = [], None, []        # skip: stack of raw tags; depth_no: stack depths of translate="no"
    stack: list[str] = []
    for i, tok in enumerate(tokens):
        m = TAG.match(tok) if tok.startswith("<") and not tok.startswith("<!") else None
        if skip:
            if m and m.group(1) and m.group(2).lower() == skip[-1]:
                skip.pop()
            continue
        if m:
            closing, name, rest = m.group(1), m.group(2).lower(), m.group(3)
            if not closing and name in RAW:
                if start is not None:
                    yield start, i
                    start = None
                skip.append(name)
                continue
            if name == "code" and not closing:          # inline code is part of the run, but its text isn't translated
                pass
            if name in INLINE:
                if start is None and not depth_no:
                    start = i
                continue
            if start is not None:
                yield start, i
                start = None
            if not closing:
                if name not in VOID and not rest.rstrip().endswith("/"):
                    stack.append(name)
                    if 'translate="no"' in rest:
                        depth_no.append(len(stack))
            else:
                while stack:
                    top = stack.pop()
                    if depth_no and depth_no[-1] > len(stack):
                        depth_no.pop()
                    if top == name:
                        break
            continue
        if tok.startswith("<!"):
            if start is not None:
                yield start, i
                start = None
            continue
        if start is None and not depth_no and tok.strip():
            start = i
    if start is not None:
        yield start, len(tokens)


def _split(run: str) -> list[tuple[str, str, str]] | None:
    """A run that is only elements side by side (a nav, a row of buttons, a link alone) is translated element by
    element, each element's inner text on its own."""
    parts = re.findall(r"(\s*)(<([a-zA-Z]+)\b[^>]*>)(.*?)(</\3>)", run, re.S)
    rebuilt = "".join(a + b + c + d for a, b, _, c, d in parts)
    if not parts or rebuilt.strip() != run.strip() or any(n.lower() in ("code", "br") for _, _, n, _, _ in parts):
        return None
    lead = run[:len(run) - len(run.lstrip())]
    return [(lead + a + b if i == 0 else a + b, c, d) for i, (a, b, _, c, d) in enumerate(parts)]


def encode(seg: str) -> tuple[str, list[str]]:
    """A segment's msgid: inline tags become numbered placeholders, <1>…</1>, and an element whose text isn't
    translated (<code>, a data-fact or data-v span, an empty or void element) becomes <2/> whole."""
    toks, out, elems, stack, i = TOKEN.split(seg), [], [], [], 0
    while i < len(toks):
        tok = toks[i]
        m = TAG.match(tok) if tok.startswith("<") and not tok.startswith("<!") else None
        if not m:
            out.append(tok)
            i += 1
            continue
        closing, name, rest = m.group(1), m.group(2).lower(), m.group(3)
        if closing:
            out.append(f"</{stack.pop()}>" if stack else tok)
            i += 1
            continue
        whole = name in VOID or rest.rstrip().endswith("/")
        if not whole and (name == "code" or "data-fact" in rest or "data-v" in rest
                          or (i + 2 < len(toks) and not toks[i + 1] and TAG.match(toks[i + 2] or "")
                              and toks[i + 2].lower() == f"</{name}>")):
            depth, j = 0, i
            while j < len(toks):
                mm = TAG.match(toks[j]) if toks[j].startswith("<") else None
                if mm and mm.group(2).lower() == name:
                    depth += -1 if mm.group(1) else 1
                    if depth == 0:
                        break
                j += 1
            elems.append("".join(toks[i:j + 1]))
            out.append(f"<{len(elems)}/>")
            i = j + 1
            continue
        elems.append(tok)
        if whole:
            out.append(f"<{len(elems)}/>")
        else:
            out.append(f"<{len(elems)}>")
            stack.append(str(len(elems)))
        i += 1
    return norm("".join(out)), elems


def decode(text: str, elems: list[str]) -> str:
    def put(m: re.Match) -> str:
        n = int(m.group(2)) - 1
        if m.group(3):
            return elems[n]
        if m.group(1):
            name = TAG.match(elems[n]).group(2)
            return f"</{name}>"
        return elems[n]
    return re.sub(r"<(/?)(\d+)(/?)>", put, text)


def placeholders(s: str) -> list[str]:
    return sorted(re.findall(r"</?\d+/?>", s))


def key(msgid: str) -> str:
    return hashlib.sha1(msgid.encode("utf-8")).hexdigest()[:10]


def segments(src: str, keep: list[str] | None = None) -> list[str]:
    """Every msgid in a page, in order (duplicates once)."""
    out: list[str] = []
    translate(strip_blocks(src), None, keep=keep, collect=out)
    return list(dict.fromkeys(out))


def translate(src: str, table: dict | None, keep: list[str] | None = None, collect: list | None = None,
              missing: list | None = None) -> str:
    """The page with each segment replaced from table (key(msgid) -> translation); collect gathers msgids instead."""
    keep = keep if keep is not None else keep_terms()
    src, held = _hold(src)
    tokens = TOKEN.split(src)

    def tr(seg: str) -> str:
        cut = _unbalanced(seg)
        if cut:                                   # a tag whose partner is outside the run: translate around it
            toks, out_, i = TOKEN.split(seg), [], 0
            for j in sorted(cut) + [len(toks)]:
                out_.append(tr("".join(toks[i:j])))
                if j < len(toks):
                    out_.append(toks[j])
                i = j + 1
            return "".join(out_)
        if not norm(seg) or not worth(norm(seg), keep):
            return seg
        msgid, elems = encode(seg)
        if collect is not None:
            collect.append(msgid)
            return seg
        got = (table or {}).get(key(msgid))
        if got is None or placeholders(got) != placeholders(msgid):
            if missing is not None:
                missing.append(msgid)
            return seg
        lead, trail = re.match(r"\s*", seg).group(0), re.search(r"\s*$", seg).group(0)
        return lead + decode(got, elems) + trail

    out = list(tokens)
    for a, b in _runs(tokens):
        run = "".join(tokens[a:b])
        parts = _split(run)
        new = "".join(o + tr(c) + cl for o, c, cl in parts) if parts else tr(run)
        out[a] = new
        for j in range(a + 1, b):
            out[j] = ""
    page = "".join(out)

    def attrs(m: re.Match) -> str:
        tag = m.group(0)
        names = ATTRS + (("content",) if tag.startswith("<meta") and re.search(r'name="description"', tag) else ())
        for name in names:
            v = _attr(tag, name)
            if v is None or not worth(html.unescape(v), keep):
                continue
            msgid = norm(html.unescape(v))
            if collect is not None:
                collect.append(msgid)
                continue
            got = (table or {}).get(key(msgid))
            if got is None:
                if missing is not None:
                    missing.append(msgid)
                continue
            tag = tag.replace(f'{name}="{v}"', f'{name}="{html.escape(got, quote=True)}"', 1)
        return tag

    pieces = re.split(r"(<script\b.*?</script>|<style\b.*?</style>)", page, flags=re.S | re.I)
    page = "".join(p if i % 2 else re.sub(r"<[a-zA-Z][^>]*>", attrs, p) for i, p in enumerate(pieces))
    return re.sub(r"<!--held:(\d+)-->", lambda m: held[int(m.group(1))], page)


def _unbalanced(seg: str) -> set[int]:
    """Token positions of tags in seg without their partner in seg (an <a> card whose blocks end the run)."""
    toks, stack, bad = TOKEN.split(seg), [], set()
    for i, tok in enumerate(toks):
        m = TAG.match(tok) if tok.startswith("<") and not tok.startswith("<!") else None
        if not m or m.group(2).lower() in VOID or m.group(3).rstrip().endswith("/"):
            continue
        if not m.group(1):
            stack.append((m.group(2).lower(), i))
        elif stack and stack[-1][0] == m.group(2).lower():
            stack.pop()
        else:
            bad.add(i)
    return bad | {i for _, i in stack}


def _hold(src: str) -> tuple[str, list[str]]:
    """Set aside every element marked translate="no" (it stays exactly as written), leaving a marker in its place."""
    held: list[str] = []
    while True:
        m = re.search(r'<([a-zA-Z][\w-]*)\b[^>]*\stranslate="no"[^>]*>', src)
        if not m:
            return src, held
        name, depth, end = m.group(1).lower(), 0, len(src)
        for t in re.finditer(rf"<(/?){name}\b[^>]*>", src[m.start():], re.I):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                end = m.start() + t.end()
                break
        held.append(src[m.start():end])
        src = src[:m.start()] + f"<!--held:{len(held) - 1}-->" + src[end:]


def js_strings(src: str) -> list[str]:
    """The t('…') strings a script shows."""
    return [bytes(m.group(2), "utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
            if "\\" in m.group(2) else m.group(2)
            for m in re.finditer(r"""\bt\((['"`])((?:(?!\1)[^\\]|\\.)*)\1""", src)]


def script_sources() -> dict[str, str]:
    """Every script whose strings are translated: the site's own assets and the pages' inline scripts."""
    out = {f"assets/{p.name}": p.read_text(encoding="utf-8") for p in sorted((SITE / "assets").glob("*.js"))
           if not p.name.startswith("strings.")}
    for p in PAGES:
        f = SITE / p
        if f.is_file():
            body = "\n".join(re.findall(r"<script>(.*?)</script>", f.read_text(encoding="utf-8"), re.S))
            if body.strip():
                out[p] = body
    return out


def catalog(lang: str) -> dict:
    f = I18N / "site" / f"{lang}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {"build": {}, "html": {}, "js": {}}


def wanted() -> tuple[dict[str, list[str]], list[str]]:
    keep = keep_terms()
    pages = {p: segments((SITE / p).read_text(encoding="utf-8"), keep) for p in PAGES if (SITE / p).is_file()}
    js = list(dict.fromkeys(s for src in script_sources().values() for s in js_strings(src)))
    return pages, js


def problems(lang: str) -> list[str]:
    """What's wrong with one language's catalog against the current English pages."""
    cat, (pages, js) = catalog(lang), wanted()
    out = []
    for s in dict.fromkeys(x for segs in pages.values() for x in segs):
        t = cat["html"].get(key(s))
        if t is None:
            out.append(f"missing {key(s)}: {s[:90]}")
        elif placeholders(t) != placeholders(s):
            out.append(f"markup differs {key(s)}: {s[:90]}")
    for k in BUILD:
        if k not in cat.get("build", {}):
            out.append(f"missing build: {k}")
    for s in js:
        t = cat["js"].get(s)
        if t is None:
            out.append(f"missing js: {s[:90]}")
        elif sorted(set(re.findall(r"\{(\w+)\}", t))) != sorted(set(re.findall(r"\{(\w+)\}", s))):
            out.append(f"placeholders differ: {s[:90]}")
    return out


# ── building the translated site ──────────────────────────────────
BLOCK = re.compile(r"<!--i18n:(\w+)-->.*?<!--/i18n:\1-->\n?", re.S)
URL_ATTR = re.compile(r'(\s(?:href|src|data-bundle)=")([^"]*)(")')
LIT = re.compile(r"""(['"])(\.\.?/[^'"\s]*)\1""")


def strip_blocks(src: str) -> str:
    """A page without the language menu, alternates and note the build adds (what the msgids come from)."""
    return BLOCK.sub("", src)


def url_of(path: str) -> str:
    """site/<path> as the folder URL people visit: index.html → '', agents/index.html → 'agents/'."""
    return path[: -len("index.html")] if path.endswith("index.html") else path


def rel(from_path: str, to_path: str) -> str:
    """A relative link from one page to another (both paths under site/)."""
    a, b = url_of(from_path).rstrip("/").split("/") if url_of(from_path) else [], url_of(to_path)
    a = [x for x in a if x]
    return "../" * len(a) + b or "./"


def _relocate(url: str, page: str, pages: set[str]) -> str:
    """A link on page as it must read one folder down (site/<lang>/<page>): kept when it points at a page that is
    translated too (it then lands on the translation), one '../' more otherwise."""
    if not url or re.match(r"[a-zA-Z][\w+.-]*:|//|#|/", url):
        return url
    base = url_of(page).split("/")[:-1] if url_of(page) else []
    path = re.match(r"[^?#]*", url).group(0)
    parts = list(base)
    for seg in path.split("/"):
        if seg == "..":
            if parts:
                parts.pop()
        elif seg not in (".", ""):
            parts.append(seg)
    is_dir = path == "" or path.endswith("/") or path.split("/")[-1] in (".", "..")
    target = "/".join(parts)
    as_page = (target + "/" if target else "") + "index.html" if is_dir else target
    return url if as_page in pages else "../" + url


def localize(src: str, page: str, lang: str, table: dict, keep: list[str], missing: list) -> str:
    """The English page in one language: text from the catalog, links one folder down, the strings for its
    scripts, and a note that English is authoritative."""
    out = translate(strip_blocks(src), table["html"], keep=keep, missing=missing)
    pages = set(PAGES)
    out = out.replace('<html lang="en">', f'<html lang="{lang}">', 1)
    out = URL_ATTR.sub(lambda m: m.group(1) + _relocate(m.group(2), page, pages) + m.group(3), out)
    out = re.sub(r"<script>(.*?)</script>", lambda m: "<script>" + LIT.sub(
        lambda n: n.group(1) + _relocate(n.group(2), page, pages) + n.group(1), m.group(1)) + "</script>", out, flags=re.S)
    up = "../" * (url_of(page).count("/") + 1)
    out = out.replace("</head>", f'<!--i18n:strings--><script src="{up}assets/strings.{lang}.js"></script><!--/i18n:strings-->\n</head>', 1)
    b = {**BUILD, **table.get("build", {})}
    note = b["note_spec"] if page == "spec/index.html" else b["note"]
    english = rel(f"{lang}/{page}", page)
    html_note = (f'<!--i18n:note--><p class="i18n-note{" appnote" if "<main" not in out else ""}">{note} '
                 f'<a href="{english}" hreflang="en" lang="en">English</a></p><!--/i18n:note-->')
    if '<main id="main">' in out:
        out = out.replace('<main id="main">', '<main id="main">\n' + html_note, 1)
    else:
        out = out.replace("</header>", "</header>\n" + html_note, 1)
    return out


def chrome(src: str, page: str, lang: str, menu_label: str) -> str:
    """Add the hreflang alternates and the language menu to a page (English or not), replacing any earlier ones."""
    src = re.sub(r"<!--i18n:(alt|menu)-->.*?<!--/i18n:\1-->\n?", "", src, flags=re.S)
    here = page if lang == "en" else f"{lang}/{page}"
    def at(code: str) -> str:
        return page if code == "en" else f"{code}/{page}"
    alt = "".join(f'<link rel="alternate" hreflang="{c}" href="{ORIGIN}{url_of(at(c))}" data-rel="{rel(here, at(c))}">'
                  for c in ALL)
    alt += f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}{url_of(page)}">'
    src = src.replace("</head>", f"<!--i18n:alt-->{alt}<!--/i18n:alt-->\n</head>", 1)
    items = "".join(f'<a href="{rel(here, at(c))}" hreflang="{c}" lang="{c}"{CURRENT if c == lang else ""}>{name}</a>'
                    for c, name in ALL.items())
    code = {"zh-Hans": "中文"}.get(lang, lang.upper())
    menu = (f'<!--i18n:menu--><details class="langs"><summary aria-label="{html.escape(menu_label)}" title="{html.escape(menu_label)}">'
            f'{code}</summary><div class="langs-menu">{items}</div></details><!--/i18n:menu-->')
    theme = '<button class="iconbtn" data-toggle-theme'
    if theme in src:
        src = src.replace(theme, menu + theme, 1)
    else:
        src = src.replace("</header>", menu + "</header>", 1)
    return src


CURRENT = ' aria-current="page"'


def build(write) -> None:
    """Write every translated page, the strings file per language, the menus, and the sitemap."""
    keep = keep_terms()
    english = {p: strip_blocks((SITE / p).read_text(encoding="utf-8")) for p in PAGES}
    gaps = {}
    for lang in LANGS:
        table = catalog(lang)
        shutil.rmtree(SITE / lang, ignore_errors=True)
        missing: list[str] = []
        for p in PAGES:
            out = chrome(localize(english[p], p, lang, table, keep, missing), p, lang,
                         table.get("build", {}).get("menu", BUILD["menu"]))
            (SITE / lang / p).parent.mkdir(parents=True, exist_ok=True)
            (SITE / lang / p).write_text(out, encoding="utf-8")
        js = {k: v for k, v in table["js"].items()}
        write(SITE / "assets" / f"strings.{lang}.js",
              f"// generated by dev/build_site.py from i18n/site/{lang}.json — do not edit\n"
              f"window.HG_T = {json.dumps(js, ensure_ascii=False, indent=0)};\n")
        gaps[lang] = len(set(missing))
    for p in PAGES:
        (SITE / p).write_text(chrome(english[p], p, "en", "Language"), encoding="utf-8")
    print("  site/{" + ",".join(LANGS) + "}/: " + ", ".join(f"{len(PAGES)} pages in {k}" for k in LANGS)
          + ("" if not any(gaps.values()) else "  — untranslated segments: " + ", ".join(f"{k} {n}" for k, n in gaps.items() if n)))
    sitemap()


def sitemap() -> None:
    f = SITE / "sitemap.xml"
    locs = re.findall(r"<loc>([^<]+)</loc>", f.read_text(encoding="utf-8"))
    english = [u for u in locs if not any(u.startswith(f"{ORIGIN}{c}/") for c in LANGS)]
    by_url = {url_of(p): p for p in PAGES}
    rows = []
    for u in english:
        p = by_url.get(u[len(ORIGIN):]) if u.startswith(ORIGIN) else None
        if p is None:
            rows.append(f"  <url><loc>{u}</loc></url>")
            continue
        alts = "".join(f'<xhtml:link rel="alternate" hreflang="{c}" href="{ORIGIN}{url_of(p if c == "en" else f"{c}/{p}")}"/>'
                       for c in ALL)
        for c in ALL:
            rows.append(f"  <url><loc>{ORIGIN}{url_of(p if c == 'en' else f'{c}/{p}')}</loc>{alts}</url>")
    f.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                 'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(rows) + "\n</urlset>\n", encoding="utf-8")


def write_source() -> None:
    """i18n/site/en.json: every msgid by key, page by page — what a translator works from."""
    pages, js = wanted()
    src = {p: {key(m): m for m in segs} for p, segs in pages.items()}
    (I18N / "site").mkdir(parents=True, exist_ok=True)
    (I18N / "site" / "en.json").write_text(json.dumps({"html": src, "js": js}, ensure_ascii=False, indent=1) + "\n",
                                           encoding="utf-8")


def main() -> int:
    write_source()
    bad = 0
    for lang in LANGS:
        p = problems(lang)
        bad += len(p)
        print(f"{lang}: {len(p)} problem(s)")
        for x in p[:15]:
            print("   ", x)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
