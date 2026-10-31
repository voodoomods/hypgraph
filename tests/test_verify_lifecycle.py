"""A superseded node can't verify as active (pre-launch audit of 0.7.16, 2026-10-31).

The verifier accepted a lifecycle under either the current rule or 0.3's (which counted only an active replacement).
In a chain RS3 supersedes RS2 supersedes RS1, 0.3 calls RS1 active; so an exported bundle edited to show RS1 active
verified with ``views: "checked"``, rows, chain and head untouched. Setting the bundle's ``generator`` (not covered by
the chain) to 0.3 also turned ``--standing`` from a problem into "not checked". Now a lifecycle is checked against the
current rule only: one that matches only 0.3's still verifies (rows and chain are intact, and a 0.3 export shows it
so) but the views are reported ``historical``, not checked, with each such node named, whatever the generator says.
The browser's verifier must decide every case the same way.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hypgraph.bundle import verify_bundle
from hypgraph.demos import broad_street

ROOT = Path(__file__).resolve().parent.parent
UI_JS = ROOT / "src" / "hypgraph" / "ui" / "hypgraph.js"
JS_VERIFY = ROOT / "dev" / "js_verify.js"


def _chain(g, inv, who, kind, rel, n=3, **body):
    a = g.author(who)
    out = []
    for i in range(n):
        links = [{"rel": rel, "to": out[-1]["id"]}] if out else []
        out.append(a.add(kind, inv, links=links, **{k: (v.format(i=i + 1) if isinstance(v, str) else v)
                                                   for k, v in body.items()}))
    return [x["id"] for x in out]


@pytest.fixture(scope="module")
def rec():
    """Broad Street with three chains of three: one by supersedes, one by corrects, and one whose newest replacement
    is withdrawn (so its middle node is active again under every rule)."""
    g, inv, _ = broad_street.build()
    hyp = dict(statement="Wording {i} of the water hypothesis.", predictions=["Deaths follow the water supply."])
    sup = _chain(g, inv, "snow", "hypothesis", "supersedes", **hyp)
    cor = _chain(g, inv, "snow", "source", "corrects", citation="Registrar General's weekly return, revision {i}.")
    wd = _chain(g, inv, "snow", "hypothesis", "supersedes", **{**hyp, "statement": "Pump wording {i}."})
    g.withdraw(author="snow", node=wd[2],
               why="The newest wording was entered against the wrong investigation.")
    return {"g": g, "inv": inv, "sup": sup, "cor": cor, "wd": wd, "bundle": g.export()}


def _shown(m: dict, nid: str) -> dict:
    return next(n for v in m["derived"]["by_inv"].values() for n in v["subgraph"]["nodes"] if n["id"] == nid)


def _code(rec, nid: str) -> str:
    return _shown(rec["bundle"], nid)["code"]


def _set(m: dict, nid: str, life: str) -> None:
    _shown(m, nid)["state"]["lifecycle"] = life


def _cases(rec) -> dict:
    """name → (bundle, verdict): "checked" (verifies, views checked), "historical" (verifies, views not checked) or
    False (fails)."""
    b = rec["bundle"]
    (s1, s2, s3), (c1, c2, c3), (w1, w2, w3) = rec["sup"], rec["cor"], rec["wd"]
    out = {}

    def add(name, verdict, *edits, generator=None):
        m = copy.deepcopy(b)
        for nid, life in edits:
            _set(m, nid, life)
        if generator == "":
            m.pop("generator")
        elif generator:
            m["generator"] = generator
        out[name] = (m, verdict)
    add("untouched", "checked")
    add("oldest of a supersedes chain shown active", "historical", (s1, "active"))
    add("oldest of a corrects chain shown active", "historical", (c1, "active"))
    add("both chains' oldest shown active", "historical", (s1, "active"), (c1, "active"))
    add("oldest shown active, generator says 0.3", "historical", (s1, "active"), generator="hypgraph 0.3.0")
    add("untouched, generator says 0.3", "checked", generator="hypgraph 0.3.0")
    add("oldest shown active, generator deleted", "historical", (s1, "active"), generator="")
    add("middle of a chain shown active", False, (s2, "active"))
    add("middle of a corrects chain shown active", False, (c2, "active"))
    add("newest shown superseded", False, (s3, "superseded"))
    add("newest of a corrects chain shown superseded", False, (c3, "superseded"))
    add("oldest shown withdrawn", False, (s1, "withdrawn"))
    add("0.3 view, middle also active", False, (s1, "active"), (s2, "active"))
    # the withdrawn newest replaces nothing, under either rule: the middle is active again, the oldest superseded
    add("withdrawn replacement shown active", False, (w3, "active"))
    add("withdrawn replacement shown superseded", False, (w3, "superseded"))
    add("node under a withdrawn replacement shown superseded", False, (w2, "superseded"))
    add("oldest under a withdrawn replacement shown active", False, (w1, "active"))
    return out


def _verdict(v: dict):
    return v["views"] if v["ok"] else False


def test_the_true_lifecycles(rec):
    b = rec["bundle"]
    want = {**dict(zip(rec["sup"], ("superseded", "superseded", "active"))),
            **dict(zip(rec["cor"], ("superseded", "superseded", "active"))),
            **dict(zip(rec["wd"], ("superseded", "active", "withdrawn")))}
    assert {k: _shown(b, k)["state"]["lifecycle"] for k in want} == want


def test_every_case_gets_its_verdict(rec):
    wrong = {}
    for name, (m, want) in _cases(rec).items():
        v = verify_bundle(m)
        if _verdict(v) != want:
            wrong[name] = (_verdict(v), v.get("problem") or v.get("warning"))
    assert wrong == {}, wrong


def test_superseded_never_verifies_as_checked_active(rec):
    """The audit's reproduction: only the exported lifecycle edited; chain, rows and head untouched."""
    m = copy.deepcopy(rec["bundle"])
    _set(m, rec["sup"][0], "active")
    v = verify_bundle(m, head=rec["bundle"]["head"])
    assert v["ok"] and v["anchored"] and v["coverage"] == "complete"
    assert v["views"] == "historical", v
    code = _code(rec, rec["sup"][0])
    assert f"{code} shown active, the current rule makes it superseded" in v["warning"], v["warning"]
    assert "The views are not checked" in v["warning"]


def test_the_generator_changes_nothing(rec):
    """``generator`` isn't covered by the chain: naming 0.3, or nothing, can't make a 0.3-rule view count as checked,
    and an untouched bundle stays checked whatever it names."""
    cases = _cases(rec)
    for a, b in [("oldest of a supersedes chain shown active", "oldest shown active, generator says 0.3"),
                 ("oldest of a supersedes chain shown active", "oldest shown active, generator deleted")]:
        va, vb = verify_bundle(cases[a][0]), verify_bundle(cases[b][0])
        assert {k: va.get(k) for k in ("ok", "views", "warning")} == {k: vb.get(k) for k in ("ok", "views", "warning")}


def test_standing_still_catches_it_on_this_version(rec):
    m = copy.deepcopy(rec["bundle"])
    _set(m, rec["sup"][0], "active")
    v = verify_bundle(m, standing=True)
    assert not v["ok"] and "differs from what its record derives" in v["problem"], v


def test_the_cli_says_the_views_are_not_checked(rec, tmp_path):
    m = copy.deepcopy(rec["bundle"])
    _set(m, rec["sup"][0], "active")
    f = tmp_path / "historical.bundle.json"
    f.write_text(json.dumps(m), encoding="utf-8")
    out = subprocess.run([sys.executable, "-m", "hypgraph", "verify", str(f)], capture_output=True, text=True,
                         encoding="utf-8")
    assert out.returncode == 0 and "views: NOT CHECKED" in out.stdout and "Traceback" not in out.stderr, out.stdout


def test_a_scoped_bundle_follows_the_same_rule(rec):
    s = rec["g"].export(rec["inv"])
    assert verify_bundle(s)["views"] == "checked"
    m = copy.deepcopy(s)
    _set(m, rec["sup"][0], "active")
    v = verify_bundle(m)
    assert v["ok"] and v["views"] == "historical", v
    m = copy.deepcopy(s)
    _set(m, rec["sup"][1], "active")
    assert not verify_bundle(m)["ok"]


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_browser_verifier_agrees(rec, tmp_path):
    cases = _cases(rec)
    paths = []
    for i, (name, (m, _)) in enumerate(cases.items()):
        p = tmp_path / f"l{i:03d}.json"
        p.write_text(json.dumps(m), encoding="utf-8")
        paths.append(p)
    out = subprocess.run(["node", str(JS_VERIFY), str(UI_JS), *map(str, paths)], capture_output=True, text=True,
                         encoding="utf-8", timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    js = json.loads(out.stdout)
    disagree = {}
    for (name, (m, want)), p in zip(cases.items(), paths):
        py = verify_bundle(m)
        keys = ("ok", "views", "warning", "coverage") if py["ok"] else ("ok", "problem")
        py_said = {k: py.get(k) or "" for k in keys}
        js_said = {k: js[p.name].get(k) or "" for k in keys}
        if py_said != js_said or _verdict(py) != want:
            disagree[name] = (py_said, js_said)
    assert disagree == {}, disagree
