"""Verification is exhaustive: every row a record shows must be written by an event, every event must have its row,
and every field an event records must match (pre-launch audit, 2026-10-31).

Before this, the Python bundle verifier, the SQLite file verifier and the browser's verifier each checked only the
rows present, and only some of their fields: a bundle with its withdrawal row dropped verified against the unchanged
published head, and `load()` replayed it as a live claim. Each mutation below is checked by all three, independently.
"""
from __future__ import annotations

import copy
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from hypgraph import Graph
from hypgraph.bundle import export, load, verify_bundle
from hypgraph.demos import broad_street
from hypgraph.store import canon, verify_file

ROOT = Path(__file__).resolve().parent.parent
UI_JS = ROOT / "src" / "hypgraph" / "ui" / "hypgraph.js"
JS_VERIFY = ROOT / "dev" / "js_verify.js"


def _record(path: Path) -> tuple[Graph, str, dict]:
    """Broad Street plus every kind of row the demo lacks: a withdrawal, a retraction, a lease taken and returned, a
    node the importer brings in under its original author, and a second investigation (so a scoped bundle has
    something redacted)."""
    g, inv, _ = broad_street.build(path=str(path))
    claims = g.search(type="claim", inv=inv)
    g.withdraw(author=claims[0]["by"], node=claims[0]["id"], why="the pump counts were copied from the wrong page")
    eid, eby = g._connect().execute("SELECT id, by FROM edges WHERE rel != 'reviews' ORDER BY id DESC").fetchone()
    g.retract(author=eby, edge=eid, why="filed against the wrong result by mistake")
    target = claims[-1]["id"]
    g.lease(author="farr", node=target, task="T1", note="checking the death counts")
    g.lease(author="farr", node=target, task="T1", release=True, note="done; counts agree")
    g.create(author="importer", type="question", inv=inv, attribute_to="snow", at="1854-09-30T09:00:00+00:00",
             fields={"text": "Did the outbreak end before the pump handle was removed?"},
             reason="imported from the 1855 report")
    other = g.create(author="operator", type="investigation",
                     fields={"title": "Was the Lambeth supply safer than Southwark and Vauxhall?",
                             "objective": "Compare deaths per household by water company in the 1854 epidemic."})["id"]
    g.create(author="snow", type="question", inv=other,
             fields={"text": "Did households on the Lambeth supply die at a lower rate?"})
    return g, inv, export(g)


@pytest.fixture(scope="module")
def rec(tmp_path_factory):
    path = tmp_path_factory.mktemp("rec") / "record.hypgraph"
    g, inv, b = _record(path)
    assert verify_bundle(b, head=b["head"])["ok"], verify_bundle(b)
    for t in ("withdrawals", "retractions", "leases"):
        assert b[t], t
    return {"path": path, "inv": inv, "bundle": b, "g": g}


def _bump(x):
    if isinstance(x, bool) or x is None:
        return 1
    if isinstance(x, int):
        return x + 1
    if isinstance(x, str) and x.startswith("{"):
        return canon({"forged": True})
    return f"{x}-forged" if x else "forged"


# (table, field): every field an event can vouch for
FIELDS = [("nodes", f) for f in ("id", "type", "code", "inv", "created_at", "created_by")] + \
         [("versions", f) for f in ("node", "v", "at", "by", "reason", "body")] + \
         [("edges", f) for f in ("id", "src", "src_v", "rel", "dst", "dst_v", "data", "at", "by", "why")] + \
         [("withdrawals", f) for f in ("node", "at", "by", "why")] + \
         [("retractions", f) for f in ("edge", "at", "by", "why")] + \
         [("leases", f) for f in ("node", "agent", "task", "kind", "at", "expires", "note")]
TABLES = ["nodes", "versions", "edges", "withdrawals", "retractions", "leases"]


def _row_with(b: dict, table: str, field: str) -> int:
    """The row to change: one where the field is set, so the change is a change."""
    rows = b[table]
    for i, r in enumerate(rows):
        if r.get(field) not in (None, "", "{}"):
            if table == "versions" and field == "reason" and not r["reason"]:
                continue
            return i
    return 0


def _mutations(b: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}

    def add(name, f):
        m = copy.deepcopy(b)
        f(m)
        out[name] = m
    for t in TABLES:
        add(f"drop first {t}", lambda m, t=t: m[t].pop(0))
        add(f"drop last {t}", lambda m, t=t: m[t].pop())
        add(f"empty {t}", lambda m, t=t: m.__setitem__(t, []))
        add(f"duplicate {t}", lambda m, t=t: m[t].append(copy.deepcopy(m[t][0])))
    add("empty every table", lambda m: [m.__setitem__(t, []) for t in TABLES])
    for t, f in FIELDS:
        add(f"{t}.{f}", lambda m, t=t, f=f: m[t][_row_with(m, t, f)].__setitem__(f, _bump(m[t][_row_with(m, t, f)][f])))
    # substitutions that keep every hash valid: two version bodies swapped between nodes, an edge's ends swapped
    def swap_bodies(m):
        a, c = m["versions"][0], m["versions"][1]
        a["node"], c["node"] = c["node"], a["node"]
    add("versions swapped between nodes", swap_bodies)
    add("edge ends swapped", lambda m: m["edges"][0].update(src=m["edges"][0]["dst"], dst=m["edges"][0]["src"]))
    add("forged withdrawal", lambda m: m["withdrawals"].append(
        {"node": m["nodes"][3]["id"], "at": m["nodes"][3]["created_at"], "by": m["nodes"][3]["created_by"],
         "why": "never written by any event"}))
    add("forged retraction", lambda m: m["retractions"].append(
        {"edge": m["edges"][0]["id"], "at": m["edges"][0]["at"], "by": m["edges"][0]["by"], "why": "forged here"}))
    return out


def test_every_mutation_fails_in_python(rec):
    b = rec["bundle"]
    passed = [name for name, m in _mutations(b).items() if verify_bundle(m, head=b["head"])["ok"]]
    assert passed == [], f"verified against the unchanged head: {passed}"


def test_a_dropped_withdrawal_is_not_replayed(rec, tmp_path):
    m = copy.deepcopy(rec["bundle"])
    m["withdrawals"] = []
    with pytest.raises(ValueError):
        load(Graph(str(tmp_path / "loaded.hypgraph")), m)


SQL = {
    "delete a node": "DELETE FROM nodes WHERE rowid = (SELECT MAX(rowid) FROM nodes)",
    "delete a version": "DELETE FROM versions WHERE rowid = (SELECT MAX(rowid) FROM versions WHERE v > 1)",
    "delete an edge": "DELETE FROM edges WHERE id = (SELECT MIN(id) FROM edges)",
    "delete the withdrawal": "DELETE FROM withdrawals",
    "delete the retraction": "DELETE FROM retractions",
    "delete a lease": "DELETE FROM leases WHERE id = (SELECT MAX(id) FROM leases)",
    "forge a withdrawal": "INSERT INTO withdrawals (node, at, by, why) SELECT id, created_at, created_by, 'forged' "
                          "FROM nodes WHERE id NOT IN (SELECT node FROM withdrawals) AND type = 'hypothesis' LIMIT 1",
    "forge a retraction": "INSERT INTO retractions (edge, at, by, why) SELECT id, at, by, 'forged' FROM edges "
                          "WHERE id NOT IN (SELECT edge FROM retractions) LIMIT 1",
    "forge a lease": "INSERT INTO leases (node, agent, task, kind, at, expires, note) "
                     "SELECT node, 'mallory', task, kind, at, expires, note FROM leases LIMIT 1",
    "nodes.type": "UPDATE nodes SET type = 'hypothesis' WHERE rowid = (SELECT MIN(rowid) FROM nodes WHERE type='claim')",
    "nodes.code": "UPDATE nodes SET code = 'CL99' WHERE type = 'claim'",
    "nodes.inv": "UPDATE nodes SET inv = 'inv-elsewhere' WHERE type = 'claim'",
    "nodes.created_by": "UPDATE nodes SET created_by = 'mallory' WHERE rowid = 2",
    "nodes.created_at": "UPDATE nodes SET created_at = '1999-01-01T00:00:00+00:00' WHERE rowid = 2",
    "versions.by": "UPDATE versions SET by = 'mallory' WHERE rowid = 2",
    "versions.at": "UPDATE versions SET at = '1999-01-01T00:00:00+00:00' WHERE rowid = 2",
    "versions.reason": "UPDATE versions SET reason = 'forged' WHERE reason != ''",
    "edges.src": "UPDATE edges SET src = (SELECT id FROM nodes LIMIT 1) WHERE id = 2",
    "edges.src_v": "UPDATE edges SET src_v = 7 WHERE id = 2",
    "edges.by": "UPDATE edges SET by = 'mallory' WHERE id = 2",
    "edges.at": "UPDATE edges SET at = '1999-01-01T00:00:00+00:00' WHERE id = 2",
    "edges.why": "UPDATE edges SET why = 'forged' WHERE why != ''",
    "withdrawals.by": "UPDATE withdrawals SET by = 'mallory'",
    "withdrawals.why": "UPDATE withdrawals SET why = 'forged'",
    "retractions.by": "UPDATE retractions SET by = 'mallory'",
    "retractions.why": "UPDATE retractions SET why = 'forged'",
    "leases.agent": "UPDATE leases SET agent = 'mallory'",
    "leases.note": "UPDATE leases SET note = 'forged'",
}


@pytest.mark.parametrize("name", list(SQL))
def test_every_file_edit_fails_in_sqlite(rec, tmp_path, name):
    p = tmp_path / "edited.hypgraph"
    shutil.copy(rec["path"], p)
    con = sqlite3.connect(p)
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'").fetchall():
        con.execute(f"DROP TRIGGER {t}")                    # what someone with the file can do first
    changed = con.execute(SQL[name]).rowcount
    con.commit()
    con.close()
    assert changed >= 1, f"{name} changed nothing: the test is wrong"
    assert not verify_file(str(p))["ok"], name


def test_the_untouched_file_verifies(rec):
    assert verify_file(str(rec["path"]))["ok"]


def test_a_scoped_bundle_checks_what_it_shows(rec):
    s = export(rec["g"], rec["inv"])
    v = verify_bundle(s)
    assert v["ok"] and not v["complete"] and v["redacted"] >= 2, v
    for name in ("drop first versions", "drop first edges", "empty withdrawals", "edges.by", "nodes.created_by"):
        m = _mutations(s)[name]
        assert not verify_bundle(m)["ok"], name


def test_fields_no_event_vouches_for_are_named(rec):
    """Bundles from before this release carry rows whose why / reason / note no event recorded: they still verify,
    and the result names what was not checked, instead of implying it was."""
    old = json.loads((ROOT / "dev" / "ui-fixtures" / "scientific.bundle.json").read_text(encoding="utf-8"))
    v = verify_bundle(old)
    assert v["ok"] and v["unchecked"].get("edges.why"), v
    assert not verify_bundle(rec["bundle"])["unchecked"], "new events vouch for every field"


# ── derived views: presentation, checked against the rows where they can be ─────────────────────────────────────

def _derived_nodes(m: dict) -> list[dict]:
    return [n for v in m["derived"]["by_inv"].values() for n in v["subgraph"]["nodes"]]


def _derived_mutations(b: dict) -> dict[str, dict]:
    out = {}

    def add(name, f):
        m = copy.deepcopy(b)
        f(m)
        out[name] = m
    add("derived node title", lambda m: _derived_nodes(m)[1].update(title="Something nobody wrote"))
    add("derived node code", lambda m: _derived_nodes(m)[1].update(code="CL99"))
    add("derived node author", lambda m: _derived_nodes(m)[1].update(by="mallory"))
    add("derived withdrawn node shown live", lambda m: [n["state"].update(lifecycle="active") for n in _derived_nodes(m)
                                                        if n["state"].get("lifecycle") == "withdrawn"])
    add("derived node dropped", lambda m: next(iter(m["derived"]["by_inv"].values()))["subgraph"]["nodes"].pop())
    add("derived edge invented", lambda m: next(iter(m["derived"]["by_inv"].values()))["subgraph"]["edges"].append(
        {**next(iter(m["derived"]["by_inv"].values()))["subgraph"]["edges"][0], "id": 9999}))
    add("derived investigations emptied", lambda m: m["derived"].update(investigations=[], by_inv={}))
    return out


def test_derived_views_that_contradict_the_rows_fail(rec):
    b = rec["bundle"]
    passed = [n for n, m in _derived_mutations(b).items() if verify_bundle(m)["ok"]]
    assert passed == [], f"derived views contradicting the record verified: {passed}"


def test_standing_is_reported_as_exported_unless_rederived(rec):
    """Standing (review state, support, the sentence) is the exporting engine's; the chain doesn't cover it. Plain
    verification says so; `standing=True` re-derives it from the verified rows and fails on a difference."""
    b = rec["bundle"]
    m = copy.deepcopy(b)
    for n in _derived_nodes(m):
        if n["type"] == "claim":
            n["state"].setdefault("review", {})["state"] = "checked"
            n["state"]["sentence"] = "checked claim · replicated twice"
    v = verify_bundle(m)
    assert v["ok"] and v["standing"]["checked"] is False, v
    assert verify_bundle(b, standing=True)["standing"]["checked"] is True
    w = verify_bundle(m, standing=True)
    assert not w["ok"] and "standing" in w["problem"], w


# ── the browser's verifier: the same mutations, the same answers ───────────────────────────────────────────────

def _js(paths: list[Path]) -> dict:
    out = subprocess.run(["node", str(JS_VERIFY), str(UI_JS), *map(str, paths)], capture_output=True, text=True,
                         encoding="utf-8", timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_browser_verifier_agrees(rec, tmp_path):
    b = rec["bundle"]
    cases = {"original": b, "scoped": export(rec["g"], rec["inv"]), **_mutations(b), **_derived_mutations(b)}
    paths = []
    for i, (name, m) in enumerate(cases.items()):
        p = tmp_path / f"m{i:03d}.bundle.json"
        p.write_text(json.dumps(m), encoding="utf-8")
        paths.append(p)
    js = _js(paths)
    said = {name: ({k: verify_bundle(m).get(k, "") for k in ("ok", "problem", "unchecked")},
                   {k: js[p.name].get(k, "") for k in ("ok", "problem", "unchecked")}) for (name, m), p in zip(cases.items(), paths)}
    disagree = {name: pair for name, pair in said.items() if pair[0] != pair[1]}
    assert disagree == {}, f"python vs browser: {disagree}"
    assert js[paths[0].name]["ok"] and js[paths[1].name]["ok"]
    assert sum(not js[p.name]["ok"] for p in paths[2:]) == len(paths) - 2


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_every_published_bundle_still_verifies():
    """Honest bundles from every earlier release still verify, in Python and in the browser."""
    files = sorted({*ROOT.glob("site/data/*.bundle.json"), *ROOT.glob("site/data/examples/*.bundle.json"),
                    *ROOT.glob("dev/ui-fixtures/*.bundle.json")})
    assert files
    js = _js(files)
    for f in files:
        b = json.loads(f.read_text(encoding="utf-8"))
        assert verify_bundle(b)["ok"], (f.name, verify_bundle(b).get("problem"))
        assert js[f.name]["ok"], (f.name, js[f.name].get("problem"))
        assert js[f.name]["unchecked"] == verify_bundle(b)["unchecked"], f.name
