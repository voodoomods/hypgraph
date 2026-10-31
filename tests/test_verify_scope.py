"""A bundle's scope must be what the exporter would write (re-audit of 0.7.15, 2026-10-31).

``scope.inv`` isn't covered by the chain. 0.7.15 took the investigation set to check from it without asking whether
it named an investigation, so a claim, question, result or hypothesis could pose as the scope: the views showed that
one node, the rest of the record vanished, and the bundle still verified against the published head. A full export of
a record with two investigations, relabelled as one investigation's scope, hid the other the same way.

The exporter (``bundle.export``) only ever writes one shape: the scope names an investigation node, and every node row
is that investigation or belongs to it; events outside it are redacted, and only a scoped export redacts. The
verifiers now require that shape. A redacted event keeps only its hash, so what it was can't be checked: a scoped
bundle says so, and only the full record against the published head rules out a change hidden among them.
Each case runs in Python and in the browser's verifier, which must agree.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hypgraph.bundle import export, verify_bundle
from hypgraph.demos import broad_street

ROOT = Path(__file__).resolve().parent.parent
UI_JS = ROOT / "src" / "hypgraph" / "ui" / "hypgraph.js"
JS_VERIFY = ROOT / "dev" / "js_verify.js"
PUBLISHED = ROOT / "site" / "data" / "broad-street.bundle.json"


def _pose(b: dict, target: dict) -> dict:
    """The audit's forgery: name one node the scope and show only it."""
    m = copy.deepcopy(b)
    m["scope"] = {"inv": target["id"], "title": "whole graph — verified"}
    m["derived"]["investigations"] = [copy.deepcopy(target)]
    m["derived"]["by_inv"] = {target["id"]: {"subgraph": {"nodes": [copy.deepcopy(target)], "edges": []},
                                             "report": {"markdown": "No competing evidence exists."}}}
    return m


@pytest.fixture(scope="module")
def two():
    """Broad Street plus a second investigation with a node of its own."""
    g, inv, _ = broad_street.build()
    farr = g.author("farr")
    inv2 = farr.investigation("A second inquiry", "Whether the elevation law holds elsewhere.")["id"]
    farr.add("question", inv2, text="Does mortality fall with elevation outside London?",
             why="If it does, the miasma account gains ground.")
    return {"g": g, "inv": inv, "inv2": inv2, "full": g.export(), "scoped": export(g, inv)}


def _cases(two) -> dict:
    """name → (bundle, head, should verify)."""
    pub = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    real = next(iter(pub["derived"]["by_inv"]))
    shown = pub["derived"]["by_inv"][real]["subgraph"]["nodes"]
    out = {"published, untouched": (pub, pub["head"], True)}
    for t in ("claim", "question", "result", "hypothesis"):
        target = next(n for n in shown if n["type"] == t)
        out[f"a {t} poses as the scope"] = (_pose(pub, target), pub["head"], False)
    m = copy.deepcopy(pub)
    m["scope"]["inv"] = "inv-00000000"
    out["the scope names no node"] = (m, pub["head"], False)
    full, scoped, inv, inv2 = two["full"], two["scoped"], two["inv"], two["inv2"]
    m = copy.deepcopy(full)
    m["scope"] = copy.deepcopy(scoped["scope"])
    m["derived"]["investigations"] = [x for x in m["derived"]["investigations"] if x["id"] == inv]
    m["derived"]["by_inv"] = {inv: m["derived"]["by_inv"][inv]}
    out["a full export relabelled as one investigation"] = (m, full["head"], False)
    m = copy.deepcopy(scoped)
    del m["scope"]
    m["derived"]["investigations"] = copy.deepcopy(full["derived"]["investigations"][:1])
    out["a scoped export with its scope removed"] = (m, full["head"], False)
    out["full export of two investigations"] = (full, full["head"], True)
    out["scoped export of the first"] = (scoped, full["head"], True)
    out["scoped export of the second"] = (export(two["g"], inv2), full["head"], True)
    out["scoped export without views"] = (export(two["g"], inv, derived=False), full["head"], True)
    return out


def test_the_audit_case_is_refused():
    """The audit's own regression, on a fresh Broad Street record."""
    g, _, _ = broad_street.build()
    original = g.export()
    head = original["head"]
    assert verify_bundle(original, head=head)["ok"]
    real = next(iter(original["derived"]["by_inv"]))
    shown = original["derived"]["by_inv"][real]["subgraph"]["nodes"]
    for t in ("claim", "question", "result", "hypothesis"):
        altered = _pose(original, next(n for n in shown if n["type"] == t))
        assert altered["head"] == head
        v = verify_bundle(altered, head=head)
        assert not v["ok"] and "not an investigation" in v["problem"], (t, v)


def test_every_case_gets_its_verdict(two):
    wrong = {name: verify_bundle(b, head=h).get("problem", "verified") for name, (b, h, should) in _cases(two).items()
             if verify_bundle(b, head=h)["ok"] is not should}
    assert wrong == {}, wrong


def test_a_relabelled_full_export_names_what_it_hides(two):
    b, h, _ = _cases(two)["a full export relabelled as one investigation"]
    v = verify_bundle(b, head=h)
    assert not v["ok"] and "other investigations" in v["problem"], v


def test_a_scoped_bundle_says_its_redactions_cant_be_checked(two):
    v = verify_bundle(two["scoped"], head=two["full"]["head"])
    assert v["ok"] and v["anchored"] and v["coverage"] == "partial" and not v["complete"], v
    assert "can't be checked" in v["warning"] and "full record" in v["warning"], v["warning"]
    full = verify_bundle(two["full"], head=two["full"]["head"])
    assert full["ok"] and full["coverage"] == "complete" and "warning" not in full, full


def test_the_cli_refuses_a_posing_scope(tmp_path):
    pub = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    real = next(iter(pub["derived"]["by_inv"]))
    claim = next(n for n in pub["derived"]["by_inv"][real]["subgraph"]["nodes"] if n["type"] == "claim")
    f = tmp_path / "posing.bundle.json"
    f.write_text(json.dumps(_pose(pub, claim)), encoding="utf-8")
    out = subprocess.run([sys.executable, "-m", "hypgraph", "verify", str(f), "--head", pub["head"]],
                         capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 1 and "not an investigation" in out.stdout, out.stdout


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_browser_verifier_agrees(two, tmp_path):
    cases = _cases(two)
    paths = []
    for i, (name, (b, h, _)) in enumerate(cases.items()):
        p = tmp_path / f"s{i:03d}.json"
        p.write_text(json.dumps({"bundle": b, "head": h}), encoding="utf-8")
        paths.append(p)
    out = subprocess.run(["node", str(JS_VERIFY), str(UI_JS), *map(str, paths)], capture_output=True, text=True,
                         encoding="utf-8", timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    js = json.loads(out.stdout)
    keys = ("ok", "problem", "coverage", "views", "warning", "anchored")
    disagree = {}
    for (name, (b, h, should)), p in zip(cases.items(), paths):
        py = verify_bundle(b, head=h)
        py_said = {k: py.get(k, False if k == "anchored" else "") for k in keys}
        js_said = {k: js[p.name].get(k, False if k == "anchored" else "") for k in keys}
        if not py["ok"]:
            py_said = {"ok": False, "problem": py["problem"]}
            js_said = {"ok": False, "problem": js[p.name]["problem"]}
        if py_said != js_said or py["ok"] is not should:
            disagree[name] = (py_said, js_said)
    assert disagree == {}, disagree
