"""Multi-language support: the UI's string tables (src/hypgraph/ui/hypgraph.js holds English, the source;
hypgraph.i18n.js the translations), how the UI picks a language, the glossary that keeps terms consistent
(i18n/glossary.json) and the website's catalogs (i18n/site/<lang>.json, applied by dev/site_i18n.py).

What the engine and the verifier say stays English and byte-identical in every language: test_verify_* compare the
Python and JS messages, and agents and audits parse them."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hypgraph.ui import static_dir

ROOT = Path(__file__).resolve().parents[1]
UI = static_dir()
LANGS = ("es", "fr", "de", "zh-Hans")


def _table(path: Path, marker: str) -> dict:
    s = path.read_text(encoding="utf-8")
    return json.JSONDecoder().raw_decode(s, s.index(marker) + len(marker))[0]


EN = _table(UI / "hypgraph.js", "/* strings:en */")
TR = _table(UI / "hypgraph.i18n.js", "/* strings */")
GLOSSARY = json.loads((ROOT / "i18n" / "glossary.json").read_text(encoding="utf-8"))

PLACEHOLDER = re.compile(r"\{(\w+)\}")
TAG = re.compile(r"</?([a-z][a-z0-9]*)\b[^>]*>")
CODE = re.compile(r"<code>.*?</code>", re.S)
# a node type's display noun comes in four forms (T.noun): a translation may need another form than the English
NOUN = {"N": "noun", "Ns": "noun", "noun": "noun", "nouns": "noun"}
# the same word in that language, not English left behind
SAME_WORD = {
    "es": {"au.actor", "err.one"},                                                        # actor, error
    "fr": {"lvl.info", "col.code", "col.type", "lv.k.budget", "lv.pause", "lv.trace", "dr.versions", "dr.provenance"},
    "de": {"drawer.aria", "view.graph", "stream.offline", "optional", "col.status", "col.code", "lv.k.budget", "lv.pause",
           "lv.trace"},                                                                    # Details, Graph, Status …
}


def _vars(s: str) -> set:
    return {NOUN.get(v, v) for v in PLACEHOLDER.findall(s)}


def test_every_language_has_every_key_and_nothing_else():
    assert set(TR) == set(LANGS)
    for lang, t in TR.items():
        keys = set(t) - {"nouns"}
        assert keys == set(EN), (lang, sorted(set(EN) - keys)[:10], sorted(keys - set(EN))[:10])


def test_placeholders_and_markup_survive_translation():
    for lang, t in TR.items():
        for k, en in EN.items():
            assert _vars(t[k]) == _vars(en), (lang, k, t[k])
            assert sorted(TAG.findall(t[k])) == sorted(TAG.findall(en)), (lang, k, t[k])


def test_every_display_noun_has_a_singular_and_a_plural():
    nouns = {lang: t["nouns"] for lang, t in TR.items()}
    first = set(nouns["es"])
    assert first, "no nouns"
    for lang, n in nouns.items():
        assert set(n) == first, lang
        for label, pair in n.items():
            assert isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, str) and x for x in pair), (lang, label)


def _strip(s: str) -> str:
    """A string without its placeholders, markup, glossary-approved words and numbers: what's left should be words."""
    s = TAG.sub(" ", PLACEHOLDER.sub(" ", s))
    for term in sorted(GLOSSARY["keep"], key=len, reverse=True):
        s = re.sub(r"(?<![\w-])" + re.escape(term) + r"(?![\w-])", " ", s, flags=re.I)
    return re.sub(r"[^A-Za-z]+", " ", s).strip()


def test_no_english_left_in_the_translated_tables():
    """A value identical to the English one is untranslated, unless it holds nothing but glossary-approved terms,
    codes, numbers and symbols (Python, MCP, k/n, ⛓ …)."""
    for lang, t in TR.items():
        left = [k for k, en in EN.items() if t[k] == en and _strip(en) and k not in SAME_WORD.get(lang, ())]
        assert not left, (lang, left[:15])


def test_glossary_terms_are_used_where_the_english_uses_them():
    """Where an English UI string uses a glossary term, its translation uses that term's rendering — the same word for
    claim, standing, bundle … everywhere. Terms with no `match` are listed for translators only (prose refers back to
    them in ways a pattern can't follow); code stays code."""
    misses = []
    for term in GLOSSARY["terms"]:
        if not term["match"]:
            continue
        rx = re.compile(term["match"], re.I)
        for k, en in EN.items():
            if not rx.search(TAG.sub(" ", PLACEHOLDER.sub(" ", CODE.sub(" ", en)))):
                continue
            for lang in LANGS:
                stems = term.get(lang) or []
                if stems and not any(st.lower() in TR[lang][k].lower() for st in stems):
                    misses.append((lang, term["en"], k, TR[lang][k]))
    assert not misses, misses[:15]


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_ui_picks_a_language():
    """?lang= first, then the host page's language, then the saved choice, then the browser's languages; English when
    none is one the UI speaks. zh / zh-CN / zh-SG are Simplified Chinese; zh-TW and zh-Hant are not."""
    js = f"""
      global.window = global; global.document = undefined;
      require({str(UI / 'hypgraph.js')!r});
      const H = global.HypGraph, out = {{}};
      out.match = ['es', 'es-MX', 'fr_CA', 'DE-at', 'zh', 'zh-CN', 'zh-Hans-SG', 'zh-SG', 'zh-TW', 'zh-Hant', 'pt-BR', 'en-GB', '', 'xx']
        .map(H.matchLang);
      out.pick = [
        H.pickLang({{ query: 'de', host: 'fr', saved: 'es', languages: ['zh-CN'] }}),
        H.pickLang({{ query: 'xx', host: 'fr', saved: 'es' }}),
        H.pickLang({{ saved: 'es', languages: ['de'] }}),
        H.pickLang({{ languages: ['pt-BR', 'zh-TW', 'de-CH', 'fr'] }}),
        H.pickLang({{ languages: ['pt-BR', 'ja'] }}),
        H.pickLang(),
      ];
      out.langs = Object.keys(H.languages);
      console.log(JSON.stringify(out));
    """
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=False)
    assert out.returncode == 0, out.stderr
    got = json.loads(out.stdout)
    assert got["match"] == ["es", "es", "fr", "de", "zh-Hans", "zh-Hans", "zh-Hans", "zh-Hans", "", "", "", "en", "", ""]
    assert got["pick"] == ["de", "fr", "es", "de", "en", "en"]
    assert got["langs"] == ["en", *LANGS]


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_translations_register_with_the_ui():
    js = f"""
      global.window = global; global.document = undefined;
      require({str(UI / 'hypgraph.js')!r}); require({str(UI / 'hypgraph.i18n.js')!r});
      console.log('ok');
    """
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=False)
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr


def _site():
    sys.path.insert(0, str(ROOT / "dev"))
    try:
        import site_i18n
    finally:
        sys.path.pop(0)
    return site_i18n


def test_the_site_catalogs_are_complete():
    """Every text of every translated page, and every string its scripts show, in every language, with the markup
    placeholders intact (dev/site_i18n.py reports what's missing)."""
    si = _site()
    for lang in LANGS:
        assert si.problems(lang) == [], (lang, si.problems(lang)[:5])


def test_the_built_pages_link_their_translations():
    """Each translated page names its English original and its siblings as hreflang alternates, says the English is
    authoritative, and loads its strings; the English page links the translations."""
    site = ROOT / "site"
    en = (site / "index.html").read_text(encoding="utf-8")
    for lang in LANGS:
        assert f'hreflang="{lang}"' in en
        page = (site / lang / "index.html").read_text(encoding="utf-8")
        assert f'<html lang="{lang}"' in page
        assert 'hreflang="en"' in page and 'hreflang="x-default"' in page
        assert 'class="i18n-note"' in page and f"strings.{lang}.js" in page
    assert "xhtml:link" in (site / "sitemap.xml").read_text(encoding="utf-8")


def test_the_site_ships_the_app_byte_for_byte():
    """site/app/ is a copy of the package's UI: the same hypgraph.js and the same translations."""
    for f in ("hypgraph.js", "hypgraph.i18n.js"):
        assert (ROOT / "site" / "app" / f).read_bytes().replace(b"\r\n", b"\n") == (UI / f).read_bytes().replace(b"\r\n", b"\n"), f
