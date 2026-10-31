"""Derived views must carry every fact the rows fix (re-audit of 0.7.14, 2026-10-31).

0.7.14 compared a derived field with the verified rows only when the field was there. Deleting a withdrawn claim's
``state.lifecycle`` (or its whole ``state``) still verified as complete, and the explorer then showed the claim as
active; so did an emptied investigation list, a dropped ``derived``, and nodes or links missing their title, author,
code or ends. Now every such fact must be present and agree, and lifecycle is derived again from the verified rows
(withdrawals and live replacements) instead of only checked for "withdrawn". A bundle exported without derived views
still verifies, and says so (``views: none``). A body or field of the wrong kind fails cleanly instead of raising.
Each case runs in Python and in the browser's verifier, which must agree.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hypgraph.bundle import MALFORMED, export, verify_bundle
from hypgraph.demos import broad_street

ROOT = Path(__file__).resolve().parent.parent
UI_JS = ROOT / "src" / "hypgraph" / "ui" / "hypgraph.js"
JS_VERIFY = ROOT / "dev" / "js_verify.js"
NODE_FACTS = ("id", "type", "code", "inv", "title", "kind", "v", "by", "at", "state")
EDGE_FACTS = ("id", "src", "src_v", "rel", "dst", "dst_v", "data", "at", "by", "why")
# rows of the wrong shape: Python reports the bundle as malformed, JavaScript reads the gap as undefined and fails
# at the next check, so the two agree on the verdict, not the words
SHAPE_ONLY = {"event without its hash", "a node row of the wrong kind"}


@pytest.fixture(scope="module")
def rec():
    """Broad Street with a claim withdrawn, and a chain of replacements: H_c supersedes H_b supersedes H_a."""
    g, inv, _ = broad_street.build()
    claim = g.search(type="claim", inv=inv)[0]
    g.withdraw(author=claim["by"], node=claim["id"], why="The supporting measurements have been invalidated.")
    snow = g.author("snow")
    ha = snow.add("hypothesis", inv, statement="A first wording of the water hypothesis.",
                  predictions=["Deaths follow the water supply."])
    hb = snow.add("hypothesis", inv, statement="A second wording of the water hypothesis.",
                  predictions=["Deaths follow the water supply."],
                  links=[{"rel": "supersedes", "to": ha["id"]}])
    hc = snow.add("hypothesis", inv, statement="A third wording of the water hypothesis.",
                  predictions=["Deaths follow the water supply."],
                  links=[{"rel": "supersedes", "to": hb["id"]}])
    return {"g": g, "inv": inv, "claim": claim["id"], "chain": (ha["id"], hb["id"], hc["id"]), "bundle": g.export()}


def _shown(m: dict, nid: str) -> dict:
    return next(n for v in m["derived"]["by_inv"].values() for n in v["subgraph"]["nodes"] if n["id"] == nid)


def _first_edge(m: dict) -> dict:
    return next(iter(m["derived"]["by_inv"].values()))["subgraph"]["edges"][0]


def _event_body(m: dict, body: str) -> dict:
    """The last event's body replaced, its hash and the head recomputed: the chain still holds."""
    m["events"][-1]["body"] = body
    m["events"][-1]["hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    m["head"] = m["events"][-1]["hash"]
    return m


def _cases(rec) -> dict:
    """name → (bundle, should verify)."""
    b, claim = rec["bundle"], rec["claim"]
    ha, hb, hc = rec["chain"]
    out = {}

    def add(name, should, f):
        m = copy.deepcopy(b)
        f(m)
        out[name] = (m, should)
    add("untouched", True, lambda m: None)
    add("withdrawn claim, lifecycle deleted", False, lambda m: (
        _shown(m, claim)["state"].pop("lifecycle"), _shown(m, claim)["state"].update(sentence="active claim")))
    add("withdrawn claim, state deleted", False, lambda m: _shown(m, claim).pop("state"))
    add("withdrawn claim shown active", False, lambda m: _shown(m, claim)["state"].update(lifecycle="active"))
    add("withdrawn claim shown superseded", False, lambda m: _shown(m, claim)["state"].update(lifecycle="superseded"))
    add("live node shown withdrawn", False, lambda m: _shown(m, hc)["state"].update(lifecycle="withdrawn"))
    add("replaced node shown active", False, lambda m: _shown(m, hb)["state"].update(lifecycle="active"))
    add("replacement shown superseded", False, lambda m: _shown(m, hc)["state"].update(lifecycle="superseded"))
    # 0.3 counted only an active replacement: H_b is superseded, so H_a stayed active under it
    add("end of a chain, as 0.3 derived it", True, lambda m: _shown(m, ha)["state"].update(lifecycle="active"))
    add("investigation list emptied", False, lambda m: m["derived"].update(investigations=[]))
    add("investigation list deleted", False, lambda m: m["derived"].pop("investigations"))
    add("investigation listed twice", False, lambda m: m["derived"]["investigations"].append(
        copy.deepcopy(m["derived"]["investigations"][0])))
    add("investigation entry without lifecycle", False, lambda m: m["derived"]["investigations"][0]["state"].pop(
        "lifecycle"))
    add("by_inv deleted", False, lambda m: m["derived"].pop("by_inv"))
    for k in NODE_FACTS:
        add(f"node without {k}", False, lambda m, k=k: _shown(m, claim).pop(k))
        add(f"investigation entry without {k}", False, lambda m, k=k: m["derived"]["investigations"][0].pop(k))
    for k in EDGE_FACTS:
        add(f"link without {k}", False, lambda m, k=k: _first_edge(m).pop(k))
    add("link id as a string", False, lambda m: _first_edge(m).update(id=str(_first_edge(m)["id"])))
    add("link id as true", False, lambda m: _first_edge(m).update(id=True))
    add("link listed twice", False, lambda m: next(iter(m["derived"]["by_inv"].values()))["subgraph"]["edges"]
        .__setitem__(1, copy.deepcopy(_first_edge(m))))
    add("derived deleted (exported without views)", True, lambda m: m.pop("derived"))
    add("event body not JSON", False, lambda m: _event_body(m, "{not json"))
    add("event body a JSON list", False, lambda m: _event_body(m, "[1, 2]"))
    add("event without its hash", False, lambda m: m["events"][3].pop("hash"))
    add("events not a list", False, lambda m: m.update(events=5))
    add("a node row of the wrong kind", False, lambda m: m["nodes"].__setitem__(0, "n1"))
    return out


def test_every_case_gets_its_verdict(rec):
    wrong = {name: verify_bundle(m).get("problem", "verified") for name, (m, should) in _cases(rec).items()
             if verify_bundle(m)["ok"] is not should}
    assert wrong == {}, wrong


def test_a_withdrawn_claim_never_verifies_as_active(rec):
    """The audit's acceptance case: Graph.withdraw, export, then delete the lifecycle or the whole state."""
    for drop in ("lifecycle", "state"):
        m = copy.deepcopy(rec["bundle"])
        n = _shown(m, rec["claim"])
        (n["state"] if drop == "lifecycle" else n).pop(drop)
        v = verify_bundle(m, head=rec["bundle"]["head"])
        assert not v["ok"] and "without its lifecycle" in v["problem"], v


def test_a_bundle_without_views_says_so(rec):
    full = verify_bundle(rec["bundle"])
    assert full["ok"] and full["views"] == "checked"
    bare = export(rec["g"], derived=False)
    assert "derived" not in bare
    v = verify_bundle(bare, head=rec["bundle"]["head"])
    assert v["ok"] and v["views"] == "none" and v["coverage"] == "complete" and v["anchored"], v


def test_a_scoped_bundle_checks_lifecycle_too(rec):
    """A scoped bundle leaves out links to other investigations, so it may call a node superseded; never withdrawn
    or active when the rows say otherwise."""
    s = export(rec["g"], rec["inv"])
    assert verify_bundle(s)["ok"]
    m = copy.deepcopy(s)
    _shown(m, rec["claim"])["state"]["lifecycle"] = "active"
    assert not verify_bundle(m)["ok"]
    m = copy.deepcopy(s)
    _shown(m, rec["chain"][1])["state"]["lifecycle"] = "active"
    assert not verify_bundle(m)["ok"]


def test_malformed_bodies_fail_cleanly(rec):
    cases = _cases(rec)
    assert verify_bundle(cases["event body not JSON"][0])["problem"] == "event body isn't a JSON object"
    assert verify_bundle(cases["events not a list"][0])["problem"] == MALFORMED


def test_the_cli_reports_without_a_traceback(rec, tmp_path):
    for name, text, want in [("body", json.dumps(_cases(rec)["event body not JSON"][0]), "isn't a JSON object"),
                             ("file", "{not json", "the file isn't JSON")]:
        f = tmp_path / f"{name}.bundle.json"
        f.write_text(text, encoding="utf-8")
        out = subprocess.run([sys.executable, "-m", "hypgraph", "verify", str(f)], capture_output=True, text=True,
                             encoding="utf-8")
        assert out.returncode == 1 and want in out.stdout and "Traceback" not in out.stderr, (out.stdout, out.stderr)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_browser_verifier_agrees(rec, tmp_path):
    cases = _cases(rec)
    paths = []
    for i, (name, (m, _)) in enumerate(cases.items()):
        p = tmp_path / f"v{i:03d}.json"
        p.write_text(json.dumps(m), encoding="utf-8")
        paths.append(p)
    out = subprocess.run(["node", str(JS_VERIFY), str(UI_JS), *map(str, paths)], capture_output=True, text=True,
                         encoding="utf-8", timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    js = json.loads(out.stdout)
    keys = ("ok", "problem", "coverage", "views")
    disagree = {}
    for (name, (m, should)), p in zip(cases.items(), paths):
        py = verify_bundle(m)
        py_said = {k: py.get(k, "") for k in keys} if py["ok"] else {"ok": False, "problem": py["problem"]}
        js_said = {k: js[p.name].get(k, "") for k in keys} if js[p.name]["ok"] else \
            {"ok": False, "problem": js[p.name]["problem"]}
        if name in SHAPE_ONLY:
            py_said, js_said = py_said["ok"], js_said["ok"]
        if py_said != js_said or py["ok"] is not should:
            disagree[name] = (py_said, js_said)
    assert disagree == {}, disagree
