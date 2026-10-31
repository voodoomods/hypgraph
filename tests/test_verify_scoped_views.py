"""A scoped bundle can't show an active node as superseded and still say its views are checked (re-audit of 0.7.17,
2026-10-31).

The verifier let a scoped bundle call any non-withdrawn node superseded, since a scoped export leaves out links from
other investigations. But ``scope.inv`` isn't covered by the chain: naming one on the published Broad Street bundle,
which has no redacted events, let an active claim, or the investigation itself, be shown superseded and verify
against the published head with ``views: "checked"`` and coverage complete. Now the allowance needs redacted events
(without them every link is in the bundle) and a node of a type a ``supersedes`` / ``corrects`` link can reach (never
an investigation or a review), and even then the views are ``unconfirmed``, with each node named. The browser's
verifier must decide every case the same way.
"""
from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hypgraph.bundle import REPLACEABLE, verify_bundle
from hypgraph.demos import broad_street
from hypgraph.schema import RELS, SAME_TYPE, TYPES

ROOT = Path(__file__).resolve().parent.parent
UI_JS = ROOT / "src" / "hypgraph" / "ui" / "hypgraph.js"
JS_VERIFY = ROOT / "dev" / "js_verify.js"
PUBLISHED = ROOT / "site" / "data" / "broad-street.bundle.json"


def _nodes(m: dict, inv: str) -> list:
    return m["derived"]["by_inv"][inv]["subgraph"]["nodes"]


def _shown(m: dict, inv: str, nid: str) -> dict:
    return next(n for n in _nodes(m, inv) if n["id"] == nid)


def _first(m: dict, inv: str, type: str, life: str = "active") -> dict:
    return next(n for n in _nodes(m, inv) if n["type"] == type and n["state"]["lifecycle"] == life)


def _inv_shown_superseded(m: dict, inv: str) -> None:
    next(x for x in m["derived"]["investigations"] if x["id"] == inv)["state"]["lifecycle"] = "superseded"
    _shown(m, inv, inv)["state"]["lifecycle"] = "superseded"


@pytest.fixture(scope="module")
def pub():
    b = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    inv = next(n["id"] for n in b["nodes"] if n["type"] == "investigation")
    return {"bundle": b, "inv": inv}


@pytest.fixture(scope="module")
def rec():
    """Broad Street with one result withdrawn, plus a second investigation whose hypothesis supersedes one of Broad
    Street's: a scoped export of Broad Street shows that hypothesis superseded, and the link that does it is among the
    redacted events."""
    g, inv, _ = broad_street.build()
    full = g.export()
    old = _first(full, inv, "hypothesis")["id"]
    res = next(n for n in full["nodes"] if n["inv"] == inv and n["type"] == "result")
    g.withdraw(author=res["created_by"], node=res["id"], why="The tally was entered against the wrong street.")
    farr = g.author("farr")
    inv2 = farr.investigation("A second inquiry", "Whether the water theory holds in another district.")["id"]
    farr.add("hypothesis", inv2, links=[{"rel": "supersedes", "to": old}],
             statement="Cholera in the second district follows its water companies.",
             predictions=["Deaths follow the water company, not the street."])
    scoped = g.export(inv)
    return {"g": g, "inv": inv, "old": old, "scoped": scoped, "full": g.export()}


def _cases(pub, rec) -> dict:
    """name → (bundle or {bundle, head}, verdict): "checked", "unconfirmed" (verifies, views not checked) or False."""
    b, inv = pub["bundle"], pub["inv"]
    out = {}

    def scoped_pub(name, verdict, edit=None):
        m = copy.deepcopy(b)
        m["scope"]["inv"] = inv
        if edit:
            edit(m)
        out[name] = ({"bundle": m, "head": b["head"]}, verdict)
    scoped_pub("published, scope named", "checked")
    scoped_pub("published, scope named, active claim shown superseded", False,
               lambda m: _first(m, inv, "claim").setdefault("state", {}).update(lifecycle="superseded"))
    scoped_pub("published, scope named, investigation shown superseded", False,
               lambda m: _inv_shown_superseded(m, inv))

    s, sinv = rec["scoped"], rec["inv"]

    def scoped_rec(name, verdict, edit=None):
        m = copy.deepcopy(s)
        if edit:
            edit(m)
        out[name] = (m, verdict)
    scoped_rec("redacted, superseded from another investigation", "unconfirmed")
    scoped_rec("redacted, an active claim shown superseded", "unconfirmed",
               lambda m: _first(m, sinv, "claim").setdefault("state", {}).update(lifecycle="superseded"))
    scoped_rec("redacted, investigation shown superseded", False, lambda m: _inv_shown_superseded(m, sinv))
    scoped_rec("redacted, a review shown superseded", False,
               lambda m: _first(m, sinv, "review")["state"].update(lifecycle="superseded"))
    scoped_rec("redacted, withdrawn shown superseded", False,
               lambda m: _first(m, sinv, "result", "withdrawn")["state"].update(lifecycle="superseded"))
    scoped_rec("redacted, superseded hypothesis shown active", "checked",
               lambda m: _shown(m, sinv, rec["old"])["state"].update(lifecycle="active"))
    return out


def _verify(x):
    return verify_bundle(x["bundle"], head=x["head"]) if "bundle" in x else verify_bundle(x)


def _verdict(v: dict):
    return v["views"] if v["ok"] else False


def test_the_fixture_is_the_real_case(rec):
    """The scoped export redacts the second investigation's events and shows the old hypothesis superseded with no
    replacement among its rows: the case the allowance exists for."""
    s, old = rec["scoped"], rec["old"]
    assert s["redacted_events"] > 0
    assert _shown(s, rec["inv"], old)["state"]["lifecycle"] == "superseded"
    assert not any(e["dst"] == old and e["rel"] in SAME_TYPE for e in s["edges"])
    assert verify_bundle(rec["full"])["views"] == "checked"


def test_every_case_gets_its_verdict(pub, rec):
    wrong = {}
    for name, (x, want) in _cases(pub, rec).items():
        v = _verify(x)
        if _verdict(v) != want:
            wrong[name] = (_verdict(v), v.get("problem") or v.get("warning"))
    assert wrong == {}, wrong


def test_the_audits_reproduction_fails(pub):
    """The published bundle with a scope named and an active claim shown superseded: chain, rows and head untouched."""
    b, inv = copy.deepcopy(pub["bundle"]), pub["inv"]
    b["scope"]["inv"] = inv
    claim = _first(b, inv, "claim")
    claim["state"]["lifecycle"] = "superseded"
    v = verify_bundle(b, head=pub["bundle"]["head"])
    assert not v["ok"], v
    assert f'shows {claim["code"]} as "superseded"; the record makes it "active"' in v["problem"], v["problem"]


def test_unconfirmed_names_each_node(rec):
    v = verify_bundle(rec["scoped"], head=rec["scoped"]["head"])
    assert v["ok"] and v["anchored"] and v["coverage"] == "partial" and v["views"] == "unconfirmed", v
    code = _shown(rec["scoped"], rec["inv"], rec["old"])["code"]
    assert re.search(rf"1 node\(s\) are shown superseded with no replacement in this bundle \({re.escape(code)}\)",
                     v["warning"]), v["warning"]
    assert "The views are not checked" in v["warning"]


def test_the_cli_says_the_views_are_not_checked(rec, tmp_path):
    f = tmp_path / "unconfirmed.bundle.json"
    f.write_text(json.dumps(rec["scoped"]), encoding="utf-8")
    out = subprocess.run([sys.executable, "-m", "hypgraph", "verify", str(f)], capture_output=True, text=True,
                         encoding="utf-8")
    assert out.returncode == 0 and "views: NOT CHECKED" in out.stdout and "outside this bundle" in out.stdout, out.stdout


def test_replaceable_follows_the_schema():
    """Only a type a supersedes / corrects link can point at can be superseded; the browser's list is the same."""
    want = set().union(*(RELS[r][1] for r in SAME_TYPE))
    assert set(REPLACEABLE) == want and set(TYPES) - want == {"investigation", "review"}
    js = UI_JS.read_text(encoding="utf-8")
    listed = re.search(r"const REPLACEABLE = \[([^\]]*)\]", js).group(1)
    assert set(re.findall(r"'([a-z_]+)'", listed)) == want


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_browser_verifier_agrees(pub, rec, tmp_path):
    cases = _cases(pub, rec)
    paths = []
    for i, (name, (x, _)) in enumerate(cases.items()):
        p = tmp_path / f"s{i:03d}.json"
        p.write_text(json.dumps(x), encoding="utf-8")
        paths.append(p)
    out = subprocess.run(["node", str(JS_VERIFY), str(UI_JS), *map(str, paths)], capture_output=True, text=True,
                         encoding="utf-8", timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    js = json.loads(out.stdout)
    disagree = {}
    for (name, (x, want)), p in zip(cases.items(), paths):
        py = _verify(x)
        keys = ("ok", "views", "warning", "coverage", "anchored") if py["ok"] else ("ok", "problem")
        py_said = {k: py.get(k) or "" for k in keys}
        js_said = {k: js[p.name].get(k) or "" for k in keys}
        if py_said != js_said or _verdict(py) != want:
            disagree[name] = (py_said, js_said)
    assert disagree == {}, disagree
