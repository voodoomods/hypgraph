"""Pinned references between records: record B cites a node of record A as a source that names the version it read
and that version's hash. The pin is built by A (``pin``), checked against A (``verify_reference``), and listed by B
(``references``). A is read the way a host reads it: through the API's node route with history."""
import json
import threading
import urllib.request

import pytest

from hypgraph import Graph, GraphError, Policy, verify_reference
from hypgraph import derive as D
from hypgraph.references import body_hash, check_fields, normalize_record
from hypgraph.server import dispatch, make_server

RECORD_A = "https://mesh.example.org/q/demo-a"


@pytest.fixture
def a():
    """Record A: one checked claim with a bound measurement."""
    g = Graph(policy=Policy(reviewers={"critic"}, instrument="lab"))
    me = g.author("ada")
    inv = me.investigation("Treatment effect", "Does the treatment group score higher?")["id"]
    run = me.add("run", inv, kind="agent", name="scores", state="succeeded")["id"]
    r = me.add("result", inv, kind="computed", outcome="positive", summary="The treatment group scored higher in 41 of 50 pairs.",
               values={"higher": {"k": 41, "n": 50}}, links=[{"rel": "produced", "from": run}])["id"]
    c = me.add("claim", inv, statement="The treatment group scores higher in 41 of 50 matched pairs.",
               scope="The 50 matched pairs in the pilot data.",
               measurements=[{"name": "higher", "result": r, "key": "higher", "k": 41, "n": 50}],
               links=[{"rel": "supports", "from": r, "why": "the measurement the claim states"}])["id"]
    return g, inv, c


def reader_of(g):
    """A fetch that reads ``g`` the way a host reads a served record: through the node route with history."""
    def fetch(url):
        assert url.startswith(RECORD_A + "/api/graph/"), url
        path, _, query = url[len(RECORD_A + "/api/graph"):].partition("?")
        q = {k: [v] for k, v in (kv.split("=", 1) for kv in query.split("&") if kv)}
        status, obj = dispatch(g, "GET", path, query=q)
        assert status == 200, (status, obj)
        return json.loads(json.dumps(obj, default=str))
    return fetch


def test_pin_carries_version_hash_and_the_nodes_own_words(a):
    g, inv, c = a
    p = g.pin("CL1", RECORD_A + "/")                          # a display code resolves; the trailing slash goes
    assert p["record"] == RECORD_A and p["node"] == c and p["version"] == 1
    assert p["hash"] == body_hash(g.get(c)["body"]) and len(p["hash"]) == 64
    assert "41 of 50" in p["says"] and p["citation"].startswith("CL1 (claim) in " + RECORD_A)
    assert p["url"] == f"{RECORD_A}/#node={c}" and p["kind"] == "primary" and p["retrieved"]


def test_b_cites_a_and_the_reference_is_a_line_of_support(a):
    g_a, _, c = a
    g_b = Graph()
    bob = g_b.author("bob")
    inv = bob.investigation("Follow-up", "Does the effect hold at scale?")["id"]
    s = bob.add("source", inv, **g_a.pin(c, RECORD_A))
    assert s["body"]["version"] == 1 and isinstance(s["body"]["version"], int)
    cl = bob.add("claim", inv, statement="A pilot found the treatment group higher in 41 of 50 matched pairs.",
                 scope="The pilot's 50 matched pairs, as recorded in demo-a.", links=[{"rel": "cites", "to": s["id"]}])
    st = D.state(g_b.snapshot(), cl["id"])
    assert st["independent_lines"] == 1 and st["evidence"] == "external"
    refs = g_b.references()
    assert len(refs) == 1 and refs[0]["record"] == RECORD_A and refs[0]["node"] == c and refs[0]["cited_by"] == [cl["id"]]
    assert g_b.references("inv-nothing") == []


def test_verify_against_the_cited_record(a):
    g_a, _, c = a
    fields = g_a.pin(c, RECORD_A)
    v = verify_reference(fields, fetch=reader_of(g_a))
    assert v["ok"] and v["current_version"] == 1 and not v["revised"] and not v["withdrawn"] and v["lifecycle"] == "active"

    g_a.author("ada").revise(c, "the scope was too narrow", scope="The 50 matched pairs in the pilot data, both sites.")
    v = verify_reference(fields, fetch=reader_of(g_a))
    assert v["ok"] and v["revised"] and v["current_version"] == 2            # what was read still stands as read

    g_a.author("ada").withdraw(c, "the pairs were matched after the scores were seen")
    v = verify_reference(fields, fetch=reader_of(g_a))
    assert v["ok"] and v["withdrawn"] and v["lifecycle"] == "withdrawn"


def test_a_rewritten_body_or_a_wrong_pin_fails(a):
    g_a, _, c = a
    fields = g_a.pin(c, RECORD_A)
    bad = {**fields, "hash": "0" * 64}
    v = verify_reference(bad, fetch=reader_of(g_a))
    assert not v["ok"] and "hashes to" in v["problem"]
    v = verify_reference({**fields, "version": 7}, fetch=reader_of(g_a))
    assert not v["ok"] and "version 7 does not exist" in v["problem"]
    v = verify_reference({**fields, "node": "n-nowhere"}, fetch=reader_of(g_a))
    assert not v["ok"] and "problem" in v

    def down(url):
        raise OSError("connection refused")
    v = verify_reference(fields, fetch=down)
    assert not v["ok"] and v["problem"].startswith("could not read the record")


def test_the_schema_refuses_half_a_reference(a):
    g_a, _, c = a
    g_b = Graph()
    bob = g_b.author("bob")
    inv = bob.investigation("Follow-up", "Does the effect hold at scale?")["id"]
    p = g_a.pin(c, RECORD_A)
    with pytest.raises(GraphError) as e:
        bob.add("source", inv, **{k: v for k, v in p.items() if k != "hash"})
    assert "missing: hash" in str(e.value)
    with pytest.raises(GraphError) as e:
        bob.add("source", inv, **{**p, "hash": "nope"})
    assert "64-hex" in str(e.value)
    with pytest.raises(GraphError) as e:
        bob.add("source", inv, **{**p, "version": 1.5})
    assert "whole number" in str(e.value)
    with pytest.raises(GraphError):
        bob.add("source", inv, **{**p, "record": "ftp://mesh/q/a"})
    plain = bob.add("source", inv, citation="A plain outside source, cited by its DOI.", doi="10.1000/xyz")
    assert "record" not in plain["body"] and g_b.references() == []


def test_check_fields_and_normalize_record():
    assert normalize_record("HTTPS://Mesh.example.org/q/a/?x=1#node=n") == "https://Mesh.example.org/q/a"
    assert check_fields({"citation": "x"}) == {"citation": "x"}
    out = check_fields({"record": "https://m/q/a", "node": " n1 ", "version": 2.0, "hash": "A" * 64})
    assert out["version"] == 2 and out["node"] == "n1" and out["hash"] == "a" * 64


def test_the_routes_pin_and_list(a, tmp_path):
    g_a, inv, c = a
    srv = make_server(g_a, "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        with urllib.request.urlopen(f"{base}/api/graph/pin/{c}?record={RECORD_A}") as r:
            p = json.load(r)
        assert p["hash"] == body_hash(g_a.get(c)["body"]) and p["version"] == 1
        try:
            urllib.request.urlopen(f"{base}/api/graph/pin/{c}")
            assert False, "record= is required"
        except urllib.error.HTTPError as e:
            assert e.code == 400
        g_b = Graph(str(tmp_path / "b.hypgraph"))
        bob = g_b.author("bob")
        inv_b = bob.investigation("Follow-up", "Does the effect hold at scale?")["id"]
        bob.add("source", inv_b, **p)
        status, obj = dispatch(g_b, "GET", "/references", query={"inv": [inv_b]})
        assert status == 200 and [x["node"] for x in obj["references"]] == [c]
        # verified over real HTTP, the way a mesh or another host does it
        v = verify_reference({**p, "record": base})
        assert v["ok"] and not v["revised"]
    finally:
        srv.shutdown()
        g_b.close()
