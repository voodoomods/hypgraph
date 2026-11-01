"""Linked records in the Explorer: a record's pinned references followed into the records they cite, each read as its
own bundle and verified, each pin checked against it. The demo (hypgraph.demos.linked) is three records joined that
way; the Explorer's pin check (checkPin, in JavaScript) must agree with verify_reference (Python) on every outcome,
and the loader (linkRecords) must follow pins transitively without looping, and stop where it's told."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hypgraph import verify_reference
from hypgraph.demos import linked
from hypgraph.server import dispatch

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "src" / "hypgraph" / "ui" / "hypgraph.js"
SITE = ROOT / "site"
node = pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")


def reader(records):
    """A fetch that reads each record the way a host serves it: the node route with history."""
    def fetch(url):
        for name, (g, _) in records.items():
            base = linked.URLS[name] + "/api/graph"
            if url.startswith(base + "/"):
                path, _, query = url[len(base):].partition("?")
                q = {k: [v] for k, v in (kv.split("=", 1) for kv in query.split("&") if kv)}
                status, obj = dispatch(g, "GET", path, query=q)
                assert status == 200, (status, obj)
                return json.loads(json.dumps(obj, default=str))
        raise AssertionError(url)
    return fetch


@pytest.fixture(scope="module")
def records():
    return linked.build()


def test_the_demo_records_pin_each_other_and_every_pin_holds(records):
    refs = {name: g.references(inv) for name, (g, inv) in records.items()}
    assert len(refs["london"]) == 3 and len(refs["east-london-1866"]) == 1 and refs["broad-street"] == []
    assert {r["record"] for r in refs["london"]} == {linked.URLS["broad-street"], linked.URLS["east-london-1866"]}
    assert refs["east-london-1866"][0]["record"] == linked.URLS["broad-street"]
    fetch = reader(records)
    for name in ("london", "east-london-1866"):
        g, inv = records[name]
        for r in refs[name]:
            v = verify_reference(g.get(r["id"])["body"], fetch=fetch)
            assert v["ok"] and not v["revised"] and not v["withdrawn"], v
    for g, _ in records.values():
        assert g.export()["head"]


def run_js(tmp_path, script, data):
    """Run `script` with HypGraph loaded from the UI file and `data` as DATA; it prints JSON."""
    f = tmp_path / "t.js"
    f.write_text("'use strict';\nconst fs = require('fs');\nglobalThis.window = globalThis;\n"
                 f"eval(fs.readFileSync({json.dumps(str(UI))}, 'utf8'));\nconst H = globalThis.HypGraph;\n"
                 f"const DATA = JSON.parse(fs.readFileSync({json.dumps(str(tmp_path / 'd.json'))}, 'utf8'));\n"
                 f"(async () => {{ {script} }})().catch((e) => {{ console.error(e); process.exit(1); }});\n", encoding="utf-8")
    (tmp_path / "d.json").write_text(json.dumps(data, default=str), encoding="utf-8")
    out = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@node
def test_the_explorer_checks_a_pin_as_verify_reference_does(tmp_path):
    """ok, a wrong hash, a missing version or node, then the pinned claim revised, then withdrawn: at each stage the
    Explorer's check, reading Broad Street's bundle, says what verify_reference says reading its node route."""
    recs = linked.build()
    bs, bs_inv = recs["broad-street"]
    lo, lo_inv = recs["london"]
    pin = next(lo.get(r["id"])["body"] for r in lo.references(lo_inv) if lo.get(r["id"])["code"] == "S2")
    cases = {"ok": pin, "tampered": {**pin, "hash": "0" * 64}, "no-version": {**pin, "version": 9},
             "no-node": {**pin, "node": "n-nowhere"}}
    stages = []

    def stage(name, which):
        fetch = reader({**recs, "broad-street": (bs, bs_inv)})
        want = {}
        for k in which:
            v = verify_reference(cases[k], fetch=fetch)
            want[k] = {"ok": v["ok"], "revised": v.get("revised"), "withdrawn": v.get("withdrawn"), "problem": v.get("problem", "")}
        stages.append({"name": name, "bundle": bs.export(), "cases": {k: cases[k] for k in which}, "want": want})

    stage("as built", ["ok", "tampered", "no-version"])
    bs.author("snow").revise(pin["node"], "a limitation stated", limitations="Which company supplied a house was found by asking; a few may be wrong.")
    stage("revised", ["ok"])
    bs.author("snow").withdraw(pin["node"], "for the test: the comparison is withdrawn")
    stage("withdrawn", ["ok"])
    got = run_js(tmp_path, """
      const out = [];
      for (const s of DATA) {
        const r = {};
        for (const [k, p] of Object.entries(s.cases)) {
          const c = await H.checkPin({ ...p, version: Number(p.version), hash: String(p.hash).toLowerCase() }, s.bundle);
          r[k] = { ok: c.ok, revised: c.revised, withdrawn: c.withdrawn, problem: c.problem || '' };
        }
        const nn = await H.checkPin({ ...s.cases.ok, node: 'n-nowhere' }, s.bundle);
        r['no-node'] = { ok: nn.ok };
        out.push(r);
      }
      console.log(JSON.stringify(out));
    """, stages)
    for s, g in zip(stages, got):
        for k, w in s["want"].items():
            assert g[k]["ok"] == w["ok"], (s["name"], k, g[k], w)
            if w["ok"]:
                assert (g[k]["revised"], g[k]["withdrawn"]) == (w["revised"], w["withdrawn"]), (s["name"], k, g[k], w)
            else:
                assert g[k]["problem"] == w["problem"], (s["name"], k, g[k], w)
        assert g["no-node"]["ok"] is False
    assert got[0]["ok"]["ok"] and not got[0]["ok"]["revised"]
    assert got[1]["ok"]["ok"] and got[1]["ok"]["revised"] and not got[1]["ok"]["withdrawn"]
    assert got[2]["ok"]["ok"] and got[2]["ok"]["withdrawn"]
    assert "hashes to" in got[0]["tampered"]["problem"] and "version 9 does not exist" in got[0]["no-version"]["problem"]


@node
def test_the_explorer_follows_pins_through_the_network(tmp_path, records):
    """From London: Broad Street and East London, and East London's own pin into Broad Street, read once each; every
    pin holds. A record not allowed is listed but not read; max caps the records read; depth 1 from East London alone
    lists its pin into Broad Street without reading it, while a pin into a record already read is checked at any depth."""
    bundles = {linked.URLS[n]: g.export() for n, (g, _) in records.items()}
    got = run_js(tmp_path, """
      const london = DATA.bundles[DATA.self];
      const refs = H.bundleReferences(london, london.nodes.find((n) => n.type === 'investigation').inv);
      const fetchBundle = H.resolveWith(DATA.bundles);
      const sum = (d) => ({ records: d.records.map((r) => [r.record, r.status, r.depth]).sort(),
        pins: d.pins.map((p) => [p.fromCode, p.from === 'self' ? 'self' : p.from.split('#')[0], p.toCode || '', p.check.ok, !!p.check.local]).sort() });
      const out = {};
      out.all = sum(await H.linkRecords(refs, { self: DATA.self, fetchBundle }));
      out.depth1 = sum(await H.linkRecords(refs, { self: DATA.self, fetchBundle, depth: 1 }));
      out.el1 = sum(await H.linkRecords(refs.filter((r) => r.code === 'S3'), { self: DATA.self, fetchBundle, depth: 1 }));
      out.blocked = sum(await H.linkRecords(refs, { self: DATA.self, fetchBundle, allow: (r) => !r.endsWith('/east-london-1866') }));
      out.max1 = sum(await H.linkRecords(refs, { self: DATA.self, fetchBundle, max: 1 }));
      out.noself = sum(await H.linkRecords(refs, { fetchBundle }));
      out.refs = refs.length;
      console.log(JSON.stringify(out));
    """, {"bundles": bundles, "self": linked.URLS["london"]})
    bs, el = linked.URLS["broad-street"], linked.URLS["east-london-1866"]
    assert got["refs"] == 3
    assert got["all"]["records"] == sorted([[bs, "loaded", 1], [el, "loaded", 1]])
    assert len(got["all"]["pins"]) == 4 and all(p[3] is True for p in got["all"]["pins"])
    assert [p for p in got["all"]["pins"] if p[1] == el] == [["S1", el, "CL2", True, False]]
    assert got["depth1"] == got["all"]                         # Broad Street was read at depth 1: the pin is checked
    assert sorted(r[1] for r in got["el1"]["records"]) == ["limit", "loaded"]
    assert [p[3] for p in got["el1"]["pins"] if p[1] == el] == [None]
    assert [r[:2] for r in got["blocked"]["records"]] == sorted([[bs, "loaded"], [el, "blocked"]])
    assert [p for p in got["blocked"]["pins"] if p[0] == "S3"][0][3] is None              # listed, not read
    assert sorted(r[1] for r in got["max1"]["records"]) == ["limit", "loaded"]
    assert got["noself"] == got["all"]


@node
def test_a_cycle_of_pins_ends_and_a_pin_into_the_open_record_stays_local(tmp_path):
    """Broad Street, revised later to pin London's claim back: London → Broad Street → London. Opened as London, the
    pin back is drawn to London's own node; opened without knowing its own URL, London is read once as another record
    and the walk still ends."""
    recs = linked.build()
    bs, bs_inv = recs["broad-street"]
    lo, lo_inv = recs["london"]
    cl = next(n for n, x in lo.snapshot().nodes.items() if x["inv"] == lo_inv and x["code"] == "CL1")
    bs.author("snow").add("source", bs_inv, reliability="the later synthesis that cites this record",
                          **lo.pin(cl, linked.URLS["london"]))
    bundles = {linked.URLS["london"]: lo.export(), linked.URLS["broad-street"]: bs.export(),
               linked.URLS["east-london-1866"]: recs["east-london-1866"][0].export()}
    got = run_js(tmp_path, """
      const london = DATA.bundles[DATA.self];
      const refs = H.bundleReferences(london, london.nodes.find((n) => n.type === 'investigation').inv);
      const fetchBundle = H.resolveWith(DATA.bundles);
      const a = await H.linkRecords(refs, { self: DATA.self, fetchBundle });
      const b = await H.linkRecords(refs, { fetchBundle, depth: 6 });
      console.log(JSON.stringify({ a: { n: a.records.length, local: a.pins.filter((p) => p.check.local).map((p) => p.to) },
        b: { records: b.records.map((r) => r.record).sort(), pins: b.pins.length, ok: b.pins.every((p) => p.check.ok) } }));
    """, {"bundles": bundles, "self": linked.URLS["london"]})
    assert got["a"] == {"n": 2, "local": ["self"]}
    assert got["b"]["records"] == sorted(linked.URLS.values()) and got["b"]["ok"]
    assert got["b"]["pins"] == 5 + 3       # London's 3, East London's 1, Broad Street's 1 back, and London (read) again


def test_the_site_serves_the_three_records_and_maps_every_pin():
    pages = [SITE / "examples" / "linked" / "index.html", SITE / "examples" / "linked" / "broad-street" / "index.html",
             SITE / "examples" / "linked" / "east-london-1866" / "index.html"]
    for p in pages:
        html = p.read_text(encoding="utf-8")
        assert 'data-view="graph"' in html and "data-record=" in html and "data-records=" in html
    for name in linked.URLS:
        b = json.loads((SITE / "data" / "examples" / "linked" / f"{name}.bundle.json").read_text(encoding="utf-8"))
        for ref in [n for n in b["nodes"] if n["type"] == "source"]:
            body = json.loads(next(v["body"] for v in b["versions"] if v["node"] == ref["id"]))
            if "record" in body:
                assert body["record"] in linked.URLS.values()
    assert 'href="linked/"' in (SITE / "examples" / "index.html").read_text(encoding="utf-8")
