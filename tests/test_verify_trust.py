"""What a verifier trusts (re-audit of 0.7.13, 2026-10-31).

A bundle's ``policy`` isn't covered by the hash chain. 0.7.13 took the importer's name from it, and older events don't
vouch for the author of a node the importer wrote, so whoever edited a bundle could name any historical writer the
importer and re-attribute that writer's nodes: it verified against the unchanged published head. Now the verifier
trusts only the policy its caller supplies (the default importer otherwise), every supplied field must match the
bundle's, and the result says at the top whether every row field was vouched for (``coverage``).

Event sequence numbers aren't hashed either: they must run 1 to n. Each case runs in Python and in the browser's
verifier, which must agree.
"""
from __future__ import annotations

import copy
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from hypgraph.bundle import export, verify_bundle
from hypgraph.demos import broad_street
from hypgraph.store import verify_file

ROOT = Path(__file__).resolve().parent.parent
UI_JS = ROOT / "src" / "hypgraph" / "ui" / "hypgraph.js"
JS_VERIFY = ROOT / "dev" / "js_verify.js"
LEGACY = ROOT / "dev" / "ui-fixtures" / "scientific.bundle.json"


def _legacy() -> dict:
    return json.loads(LEGACY.read_text(encoding="utf-8"))


def _launder(b: dict) -> tuple[dict, str]:
    """The re-audit's case: name a historical writer the importer, then re-attribute one of its older nodes, in the
    rows and in the derived views alike."""
    bodies = [json.loads(e["body"]) for e in b["events"] if not e.get("redacted")]
    e = next(x for x in bodies if x["kind"] == "create" and x["actor"] == "harness" and "reason_sha" not in x["payload"])
    m = copy.deepcopy(b)
    m["policy"]["importer"] = "harness"
    for n in m["nodes"]:
        if n["id"] == e["ref"]:
            n["created_by"] = "FAKE_PROVENANCE"
    for n in m["derived"].get("investigations", []):
        if n["id"] == e["ref"]:
            n["by"] = "FAKE_PROVENANCE"
    for v in m["derived"]["by_inv"].values():
        for n in v["subgraph"]["nodes"]:
            if n["id"] == e["ref"]:
                n["by"] = "FAKE_PROVENANCE"
    return m, e["ref"]


@pytest.fixture(scope="module")
def fresh():
    g, inv, _ = broad_street.build()
    return {"g": g, "inv": inv, "bundle": g.export()}


def _cases(fresh) -> dict:
    """name → (bundle, head, trusted policy, should verify)."""
    old, b = _legacy(), fresh["bundle"]
    laundered, _ = _launder(old)
    relabelled = copy.deepcopy(b)
    for i, ev in enumerate(relabelled["events"]):
        ev["seq"] = i + 100
    gap = copy.deepcopy(b)
    gap["events"][-1]["seq"] += 5
    stated = copy.deepcopy(b)
    stated["policy"]["reviewers"] = ["fake_reviewer"]
    return {
        "legacy, untouched": (old, "", None, True),
        "legacy, untouched, against its head": (old, old["head"], None, True),
        "laundered author": (laundered, "", None, False),
        "laundered author, against the published head": (laundered, old["head"], None, False),
        "laundered author, caller trusts that importer": (laundered, old["head"], {"importer": "harness"}, True),
        "fresh, untouched": (b, b["head"], None, True),
        "fresh, the policy its publisher states": (b, b["head"], {"reviewers": ["whitehead"], "importer": "importer"}, True),
        "fresh, a policy the bundle doesn't state": (b, b["head"], {"reviewers": ["fake_reviewer"]}, False),
        "reviewers edited, caller supplies the real ones": (stated, b["head"], {"reviewers": ["whitehead"]}, False),
        "reviewers edited, nothing supplied": (stated, b["head"], None, True),
        "sequence numbers relabelled": (relabelled, b["head"], None, False),
        "a gap in the sequence": (gap, b["head"], None, False),
        "scoped bundle": (export(fresh["g"], fresh["inv"]), "", None, True),
    }


def test_a_bundle_cannot_name_its_own_importer():
    m, ref = _launder(_legacy())
    for head in ("", _legacy()["head"]):
        v = verify_bundle(m, head=head)
        assert not v["ok"], v
        assert "created_by" in v["problem"] and "names harness as its importer" in v["problem"], v["problem"]


def test_the_supplied_policy_is_the_one_trusted(fresh):
    m, _ = _launder(_legacy())
    v = verify_bundle(m, head=_legacy()["head"], policy={"importer": "harness"})
    assert v["ok"] and v["coverage"] == "partial" and v["policy"] == {"trusted": ["importer"], "importer": "harness"}
    v = verify_bundle(fresh["bundle"], policy={"reviewers": ["fake_reviewer"]})
    assert not v["ok"] and v["problem"].startswith("the bundle states reviewers"), v


def test_coverage_is_stated_at_the_top(fresh):
    assert verify_bundle(fresh["bundle"])["coverage"] == "complete"
    assert verify_bundle(_legacy())["coverage"] == "partial"
    named = copy.deepcopy(fresh["bundle"])
    named["policy"]["importer"] = "someone"
    v = verify_bundle(named)
    assert v["ok"] and "names someone as its importer" in v["warning"], v


def test_rederived_standing_names_the_policy_it_took_on_trust(fresh):
    b = fresh["bundle"]
    on_trust = verify_bundle(b, standing=True)["standing"]
    assert on_trust["checked"] and "reviewers" in on_trust["policy_as_stated"] and "importer" in on_trust["policy_as_stated"]
    supplied = verify_bundle(b, standing=True, policy=b["policy"])["standing"]
    assert supplied == {"checked": True, "policy_as_stated": []}


@pytest.mark.parametrize("name", ["laundered author", "laundered author, against the published head",
                                  "sequence numbers relabelled", "a gap in the sequence",
                                  "fresh, a policy the bundle doesn't state",
                                  "reviewers edited, caller supplies the real ones"])
def test_each_forgery_fails_in_python(fresh, name):
    b, head, policy, _ = _cases(fresh)[name]
    assert not verify_bundle(b, head=head, policy=policy)["ok"], name


def test_renumbered_events_fail_in_a_graph_file(tmp_path):
    g, _, _ = broad_street.build(path=str(tmp_path / "r.hypgraph"))
    p = Path(g.path)
    assert verify_file(str(p))["ok"] and verify_file(str(p))["coverage"] == "complete"
    con = sqlite3.connect(p)
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'").fetchall():
        con.execute(f"DROP TRIGGER {t}")
    con.execute("UPDATE events SET seq = seq + 100")
    con.commit()
    con.close()
    v = verify_file(str(p))
    assert not v["ok"] and "numbered" in v["problem"], v


def test_the_cli_refuses_a_laundered_bundle(tmp_path):
    m, _ = _launder(_legacy())
    f = tmp_path / "laundered.bundle.json"
    f.write_text(json.dumps(m), encoding="utf-8")
    run = [sys.executable, "-m", "hypgraph", "verify", str(f), "--head", _legacy()["head"]]
    bad = subprocess.run(run, capture_output=True, text=True, encoding="utf-8")
    assert bad.returncode == 1 and "names harness as its importer" in bad.stdout, bad.stdout
    trusted = subprocess.run(run + ["--importer", "harness"], capture_output=True, text=True, encoding="utf-8")
    assert trusted.returncode == 0 and "coverage: PARTIAL" in trusted.stdout, trusted.stdout


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_browser_verifier_agrees(fresh, tmp_path):
    cases = _cases(fresh)
    paths = []
    for i, (name, (b, head, policy, _)) in enumerate(cases.items()):
        p = tmp_path / f"t{i:03d}.json"
        p.write_text(json.dumps({"bundle": b, "head": head, "policy": policy}), encoding="utf-8")
        paths.append(p)
    out = subprocess.run(["node", str(JS_VERIFY), str(UI_JS), *map(str, paths)], capture_output=True, text=True,
                         encoding="utf-8", timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    js = json.loads(out.stdout)
    keys = ("ok", "problem", "coverage", "warning", "anchored")
    for (name, (b, head, policy, should)), p in zip(cases.items(), paths):
        py = verify_bundle(b, head=head, policy=policy)
        assert py["ok"] is should, (name, py.get("problem"))
        py_said = {k: py.get(k, False if k == "anchored" else "") for k in keys}
        js_said = {k: js[p.name].get(k, False if k == "anchored" else "") for k in keys}
        if not py["ok"]:
            py_said.update(coverage="", warning="", anchored=False)
        assert py_said == js_said, name
