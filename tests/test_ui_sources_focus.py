"""The Explorer's Sources view and the graph focus, without a browser: `HypGraph.focusIds` (the set a focus draws,
from the record's own edges — the same walks graph.py makes for why / impact / neighborhood), `HypGraph.bibtex`, and
the static contract (the view in the sidebar, the focus in the link, the strings). dev/ui_smoke.py renders the view
in headless Chrome; CI runs it."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from hypgraph.ui import static_dir

ROOT = Path(__file__).resolve().parents[1]
UI = static_dir()
FIXTURE = ROOT / "dev" / "ui-fixtures" / "knowledge.bundle.json"
node = pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")


def _run(js: str) -> dict:
    out = subprocess.run(["node", "-e", f"""
      global.window = global; global.document = undefined;
      require({str(UI / 'hypgraph.js')!r});
      const H = global.HypGraph;
      const bundle = JSON.parse(require('fs').readFileSync({str(FIXTURE)!r}, 'utf8'));
      const inv = Object.values(bundle.derived.by_inv)[0];
      const nodes = inv.subgraph.nodes, edges = inv.subgraph.edges, board = inv.board;
      const byCode = Object.fromEntries(nodes.map((n) => [n.code, n.id]));
      const codes = (set) => set ? [...set].map((id) => nodes.find((n) => n.id === id).code).sort() : null;
      {js}
    """], capture_output=True, text=True, check=False, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _fixture():
    bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))
    inv = next(iter(bundle["derived"]["by_inv"].values()))
    return inv["subgraph"]["nodes"], inv["subgraph"]["edges"], inv["board"]


def test_the_fixture_has_claims_that_cite_sources():
    nodes, edges, board = _fixture()
    by_id = {n["id"]: n for n in nodes}
    cites = [(by_id[e["src"]]["code"], by_id[e["dst"]]["code"]) for e in edges if e["rel"] == "cites"]
    assert cites and all(b.startswith("S") for _, b in cites)
    assert any(q.get("answers") for q in board)


@node
def test_why_walks_to_the_sources_and_impact_walks_back():
    nodes, edges, _ = _fixture()
    by_id = {n["id"]: n for n in nodes}
    claim, source = next((by_id[e["src"]]["code"], by_id[e["dst"]]["code"]) for e in edges if e["rel"] == "cites")
    got = _run(f"""
      const why = codes(H.focusIds(nodes, edges, {{ node: byCode[{claim!r}], lens: 'why' }}, board));
      const impact = codes(H.focusIds(nodes, edges, {{ node: byCode[{source!r}], lens: 'impact' }}, board));
      const none = H.focusIds(nodes, edges, {{ node: 'not-a-node', lens: 'why' }}, board);
      console.log(JSON.stringify({{ why, impact, none }}));
    """)
    assert claim in got["why"] and source in got["why"], got                 # the claim rests on the source it cites
    assert got["impact"] == [source] or claim in got["impact"], got           # cites is not a risky relation: nothing falls with a source
    assert got["none"] is None                                                # a centre not in the record: no focus


@node
def test_neighbours_grow_with_depth_and_stop_at_three():
    nodes, edges, _ = _fixture()
    centre = next(n["code"] for n in nodes if n["type"] == "claim")
    got = _run(f"""
      const at = (d) => H.focusIds(nodes, edges, {{ node: byCode[{centre!r}], lens: 'near', depth: d }}, board).size;
      console.log(JSON.stringify({{ d1: at(1), d2: at(2), d3: at(3), d9: at(9), d0: at(0) }}));
    """)
    assert 1 < got["d1"] <= got["d2"] <= got["d3"]
    assert got["d9"] == got["d3"] and got["d0"] == got["d1"]                  # depth is clamped to 1–3


@node
def test_a_question_focus_holds_its_answers_and_what_they_rest_on():
    nodes, edges, board = _fixture()
    q = next(q for q in board if q.get("answers"))
    by_code = {n["code"]: n["id"] for n in nodes}
    cited = {next(n["code"] for n in nodes if n["id"] == e["dst"]) for a in q["answers"]
             for e in edges if e["rel"] == "cites" and e["src"] == by_code[a]}
    got = _run(f"""
      const set = codes(H.focusIds(nodes, edges, {{ node: {q['id']!r}, lens: 'question' }}, board));
      console.log(JSON.stringify(set));
    """)
    assert q["code"] in got and set(q["answers"]) <= set(got) and cited <= set(got), got
    assert not any(c.startswith("Q") and c != q["code"] for c in got)         # not the other questions


@node
def test_bibtex_is_one_misc_entry_per_source_with_braces_escaped():
    got = _run("""
      console.log(JSON.stringify(H.bibtex([
        { code: 'S1', citation: "Britannica, 'Peace of {Westphalia}'.", kind: 'secondary', doi: '', url: 'https://x.test/a', retrieved: '2026-10-25', cited_by: ['CL1', 'CL2'] },
        { code: 'S2', citation: 'A paper', doi: '10.1000/xyz', url: '', retrieved: '', cited_by: [] }])));
    """)
    assert got.startswith("@misc{S1,\n  title = {Britannica, 'Peace of \\{Westphalia\\}'.},\n  url = {https://x.test/a},\n  urldate = {2026-10-25},\n  note = {secondary source; cited by CL1, CL2},\n}")
    assert "@misc{S2,\n  title = {A paper},\n  doi = {10.1000/xyz},\n}" in got and "note" not in got.split("@misc{S2")[1]


def test_the_sources_view_and_the_focus_are_in_the_app():
    js = (UI / "hypgraph.js").read_text(encoding="utf-8")
    assert "['sources', '❝', 'Sources']" in js and "sources: vSources" in js      # the ninth view, in the sidebar
    assert "/^[1-9]$/.test(ev.key)" in js                                         # key 9 reaches the last view
    assert "p.set('focus', S.m.codeOf(S.focus.node)); p.set('lens', S.focus.lens)" in js   # the focus is in the link
    assert "data-fq=" in js and "'question'" in js                                # the questions under Graph, each a focus
    assert "data-focus=" in js and "dr.focus.why" in js                           # the way in from a node's details
    strings = json.JSONDecoder().raw_decode(js, js.index("/* strings:en */") + len("/* strings:en */"))[0]
    for k in ("view.sources", "so.honest", "so.only.uncited", "so.only.nolink", "so.only.fallen", "so.bibtex",
              "fo.why", "fo.impact", "fo.near", "fo.question", "fo.link", "dr.graph"):
        assert k in strings, k
    assert "checked nothing" in strings["so.honest"]                             # what the record did not check is said
    css = (UI / "hypgraph.css").read_text(encoding="utf-8")
    assert ".hg .focusbar" in css and ".hg .hg-nav .subnav" in css and ".hg .so-cite" in css
    smoke = (ROOT / "dev" / "ui_smoke.py").read_text(encoding="utf-8")
    assert '"sources"' in re.search(r"VIEWS = \[([^\]]*)\]", smoke).group(1)        # the browser smoke renders it too
