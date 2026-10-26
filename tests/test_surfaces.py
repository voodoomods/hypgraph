"""The surfaces around the engine: the demo, bundles (round trip, tampering, scope), memory graphs, the clock rule,
the HTTP API, the CLI and the MCP server."""
import copy
import json
import threading
import urllib.error
import urllib.request

import pytest

from hypgraph import Graph, GraphError, Policy, verify_bundle
from hypgraph.cli import main
from hypgraph.demos import broad_street


@pytest.fixture(scope="module")
def demo():
    return broad_street.build()


# ── the demo is a lesson: every refusal it shows really happens ───

def test_demo_tells_the_story_it_claims(demo):
    g, inv, story = demo
    refusals = [s for s in story if "refused" in s]
    assert len(refusals) == 3
    assert "'every' is absolute" in refusals[0]["refused"]
    assert "link the evidence" in refusals[1]["refused"]
    assert "exclusion needs a search" in refusals[2]["refused"]
    by = {n["code"]: n for n in g.subgraph(inv)["nodes"]}
    cl1 = by["CL1"]["state"]
    assert cl1["review"]["state"] == "checked" and cl1["evidence"] == "new_data" and cl1["independent_lines"] == 2
    assert by["D1"]["state"]["basis_changed"][0] == {"node": by["CL1"]["id"], "code": "CL1", "was_v": 1, "now_v": 2}
    assert by["H2"]["state"]["challenges"] == 1
    assert g.next_experiments(inv)["ranked"][0]["experiment"]["code"] == "X3"
    assert g.verify()["ok"]
    assert g.get(inv)["at"].startswith("1854-09-01")              # the demo clock, not the wall clock


def test_only_the_importer_sets_a_time():
    g = Graph()
    with pytest.raises(GraphError, match="sets a write's time"):
        g.create(author="sam", type="investigation", at="1900-01-01T00:00:00+00:00",
                 fields={"title": "Backdated", "objective": "Try to write into the past."})
    n = g.create(author="importer", type="investigation", at="1900-01-01T00:00:00+00:00",
                 fields={"title": "Legacy", "objective": "A legacy record imported with its date."})
    assert n["at"].startswith("1900")


# ── bundles ───────────────────────────────────────────────────────

def test_bundle_round_trip_and_tampering(demo):
    g, inv, _ = demo
    b = json.loads(json.dumps(g.export()))                          # through JSON, as it travels
    v = verify_bundle(b)
    assert v["ok"] and v["complete"] and v["checked"] == g.verify()["checked"]
    g2 = Graph.from_bundle(b)
    assert g2.verify() == g.verify()
    assert {n["id"]: n["state"]["sentence"] for n in g2.subgraph(inv)["nodes"]} == \
           {n["id"]: n["state"]["sentence"] for n in g.subgraph(inv)["nodes"]}

    bad = copy.deepcopy(b)                                          # rewrite a claim's text
    i = next(k for k, x in enumerate(bad["versions"]) if "Golden Square outbreak was spread" in x["body"])
    bad["versions"][i]["body"] = bad["versions"][i]["body"].replace("5 of the 535", "none of the 535")
    assert verify_bundle(bad) == {"ok": False, "problem": f"version {bad['versions'][i]['node']} "
                                                          f"v{bad['versions'][i]['v']} differs from its event"}
    bad = copy.deepcopy(b)                                          # hide a withdrawal / drop an event
    bad["events"].pop(10)
    assert not verify_bundle(bad)["ok"]
    bad = copy.deepcopy(b)                                          # an edge rewired
    bad["edges"][0]["dst"] = next(e["dst"] for e in bad["edges"] if e["dst"] != bad["edges"][0]["dst"])
    assert not verify_bundle(bad)["ok"]
    with pytest.raises(ValueError, match="does not verify"):
        Graph.from_bundle(bad)


def test_scoped_bundle_redacts_the_rest_and_says_so(demo):
    g, inv, _ = demo
    other = g.create(author="sam", type="investigation", fields={"title": "Another study",
                                                                 "objective": "Something unrelated to cholera."})
    b = g.export(inv)
    v = verify_bundle(b)
    assert v["ok"] and not v["complete"] and v["redacted"] >= 1 and "redacted" in v["warning"]
    assert other["id"] not in {n["id"] for n in b["nodes"]}
    assert all("Another study" not in json.dumps(e) for e in b["events"])
    with pytest.raises(ValueError, match="scoped"):
        Graph.from_bundle(b)


def test_memory_graph_and_author_handle():
    g = Graph(policy=Policy(reviewers={"ada"}))
    me = g.author("sam")
    inv = me.investigation("Cress", "Find out whether light colour changes how fast cress grows.")["id"]
    r = me.add("result", inv, summary="Blue trays averaged 41 mm, red trays 33 mm after 7 days.",
               values={"blue_mm": {"value": 41}, "red_mm": {"value": 33}})
    with pytest.raises(GraphError, match="numbers in the statement"):
        me.add("claim", inv, statement="Blue light grew cress 30 mm taller.", scope="Two trays each, one week, "
               "a windowless room.", links=[{"rel": "supports", "from": r["id"], "why": "the tray heights"}])
    c = me.add("claim", inv, statement="Blue-lit cress averaged 41 mm against 33 mm under red light.",
               scope="Two trays each, one week, a windowless room.",
               measurements=[{"name": "blue", "result": r["id"], "key": "blue_mm", "value": 41},
                             {"name": "red", "result": r["id"], "key": "red_mm", "value": 33}],
               links=[{"rel": "supports", "from": r["id"], "why": "the tray heights are the measurement"}])
    assert me.review(c["id"], "checked", "Looked at my own trays.", "Fine by me.")["state"]["review"][
        "state"] == "unchecked"                                     # sam isn't a reviewer: recorded as a comment
    assert g.author("ada").review(c["id"], "pass", "Re-measured the trays.", "41 and 33 hold.")["state"]["review"][
        "state"] == "checked"


# ── HTTP ──────────────────────────────────────────────────────────

@pytest.fixture
def server(tmp_path):
    from hypgraph.server import make_server
    db = tmp_path / "s.hypgraph"
    broad_street.build(path=str(db))
    srv = make_server(str(db), port=0, writable=True)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _get(url, **headers):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _post(url, body, **headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_http_api_serves_the_ui_and_the_record(server):
    st, body = _get(server + "/")
    assert st == 200 and b"HypGraph.mount" in body
    st, body = _get(server + "/hypgraph.js")
    assert st == 200 and b"global.HypAtlas" in body                              # the Atlas's name, kept for a release
    assert _get(server + "/atlas.js")[0] == 200
    st, body = _get(server + "/vendor/cytoscape.min.js")
    assert st == 200 and len(body) > 100_000
    st, body = _get(server + "/../pyproject.toml")
    assert st == 404
    invs = json.loads(_get(server + "/api/graph/investigations")[1])
    inv = invs["investigations"][0]["id"]
    sub = json.loads(_get(server + f"/api/graph/subgraph?inv={inv}")[1])
    cl1 = next(n for n in sub["nodes"] if n["code"] == "CL1")
    assert json.loads(_get(server + f"/api/graph/node/{cl1['id']}?history=1")[1])["versions"][1]["v"] == 2
    assert json.loads(_get(server + "/api/graph/verify")[1])["ok"]
    assert verify_bundle(json.loads(_get(server + f"/api/graph/export?inv={inv}")[1]))["ok"]
    assert _get(server + "/api/graph/node/nope")[0] == 404
    assert _get(server + "/api/graph/stats", Host="evil.example")[0] == 421          # DNS rebinding


def test_http_writes_refuse_reserved_authors_and_cross_origin(server):
    inv = json.loads(_get(server + "/api/graph/investigations")[1])["investigations"][0]["id"]
    for who in ("lab", "operator", "importer", "system", ""):
        assert _post(server + "/api/graph/write", {"op": "create", "author": who, "type": "question", "inv": inv,
                                                   "fields": {"text": "A question asked as someone else."}})[0] == 403
    st, n = _post(server + "/api/graph/write", {"op": "create", "author": "sam", "type": "question", "inv": inv,
                                                "fields": {"text": "Did the 1866 outbreak follow the water too?"}})
    assert st == 200 and n["code"] == "Q2"
    assert _post(server + "/api/graph/write", {"op": "create", "author": "sam", "type": "claim", "inv": inv,
                                               "fields": {"statement": "It never spreads by air."}})[0] == 400
    assert _post(server + "/api/graph/write", {"op": "delete", "author": "sam"})[0] == 400
    assert _post(server + "/api/graph/write", {"op": "create", "author": "sam"}, Origin="http://evil.example")[0] == 403


# ── CLI ───────────────────────────────────────────────────────────

def test_cli_a_student_session(tmp_path, capsys, monkeypatch):
    db = str(tmp_path / "cress.hypgraph")
    monkeypatch.setenv("HYPGRAPH_AUTHOR", "sam")
    run = lambda *a: main(["--db", db, *a])  # noqa: E731
    assert run("init", "Cress and light", "--objective", "Find out whether light colour changes cress growth.",
               "--reviewers", "ada") == 0
    assert run("add", "hypothesis", "statement=Blue light grows cress faster than red light.",
               'predictions=["Blue trays are taller after 7 days."]') == 0
    assert run("add", "result", "summary=Blue trays averaged 41 mm, red trays 33 mm after 7 days.",
               'values={"blue_mm": {"value": 41}, "red_mm": {"value": 33}}') == 0
    assert run("link", "RS1", "supports", "H1", "--why", "The blue trays grew taller, as H1 predicts.") == 0
    capsys.readouterr()
    assert run("add", "claim", "statement=Blue light always grows cress taller.", "scope=Two trays each, one week.",
               "--link", "supports:from:RS1:the tray heights") == 2
    assert "'always' is absolute" in capsys.readouterr().err
    assert run("--as", "ada", "review", "H1", "pass", "--method", "Re-measured", "--notes", "Heights hold.") == 0
    assert run("show", "H1") == 0
    assert "checked (ada:pass" in capsys.readouterr().out
    assert run("report", "-o", str(tmp_path / "facts.md")) == 0
    assert run("export", "-o", str(tmp_path / "b.json")) == 0
    assert run("verify", str(tmp_path / "b.json")) == 0
    assert run("verify") == 0
    assert main(["--db", str(tmp_path / "copy.hypgraph"), "import", str(tmp_path / "b.json")]) == 0
    assert run("schema") == 0


def test_cli_demo(tmp_path, capsys):
    db = str(tmp_path / "d.hypgraph")
    assert main(["--db", db, "demo"]) == 0
    out = capsys.readouterr().out
    assert "the record refused it" in out and "hypgraph --db" in out
    assert main(["--db", db, "demo"]) == 2                          # won't overwrite


# ── MCP ───────────────────────────────────────────────────────────

def test_mcp_server_tools(tmp_path):
    fastmcp = pytest.importorskip("fastmcp")
    import asyncio

    from hypgraph.mcp import build
    db = tmp_path / "m.hypgraph"
    broad_street.build(path=str(db))
    server = build(str(db), author="claude")
    with pytest.raises(SystemExit):
        build(str(db), author="operator")

    async def go():
        async with fastmcp.Client(server) as c:
            names = {t.name for t in await c.list_tools()}
            assert {"overview", "find", "show", "add", "link", "review", "register_run", "report", "verify", "bound",
                    "check_report", "refusal_log"} <= names
            text = lambda r: r.content[0].text  # noqa: E731
            ov = text(await c.call_tool("overview", {}))
            assert "How does cholera spread" in ov and "Next experiments: X3" in ov
            ok = text(await c.call_tool("add", {"type": "hypothesis", "fields": {
                "statement": "Cholera spreads by contact with the sick alone.",
                "predictions": ["Nurses die at higher rates than those who drink the pump water."]},
                "links": [{"rel": "alternative_to", "to": "H1"}]}))
            assert ok.startswith("Added H3")
            res = await c.call_tool("add", {"type": "claim", "fields": {
                "statement": "The pump water always kills."}}, raise_on_error=False)
            assert res.is_error and "absolute" in text(res)
            mine = text(await c.call_tool("review", {"node": "CL2", "verdict": "pass", "method": "Re-read the tally.",
                                                     "notes": "The tally holds."}))
            assert mine.split("·")[1].strip() == "unchecked"         # claude isn't a reviewer: a comment
            (tmp_path / "tally.py").write_text("print(315 / 37)\n")
            reg = text(await c.call_tool("register_run", {"name": "Recompute the ratio", "code_paths": ["tally.py"],
                                                          "result_summary": "The ratio is 8.5.",
                                                          "result_values": {"ratio": {"value": 8.5}}}))
            assert "1 file(s) hashed" in reg and "Result RS" in reg
            bad = await c.call_tool("register_run", {"name": "x", "code_paths": ["../../etc/passwd"]},
                                    raise_on_error=False)
            assert bad.is_error
            assert "Verified" in text(await c.call_tool("verify", {}))
            res = await c.read_resource("hypgraph://schema")
            assert "hypgraph/1" in res[0].text
    import os
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        server = build(str(db), author="claude")
        asyncio.run(go())
    finally:
        os.chdir(cwd)


def test_agent_skill_ships_and_installs(tmp_path, capsys):
    assert main(["skill"]) == 0
    text = capsys.readouterr().out
    head = text.split("---")[1]
    assert "name: hypgraph" in head and "description:" in head and len(head) < 1100
    assert main(["skill", "--install", "--dir", str(tmp_path)]) == 0
    assert (tmp_path / ".claude" / "skills" / "hypgraph" / "SKILL.md").read_text(encoding="utf-8").startswith("---")
