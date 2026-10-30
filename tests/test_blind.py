"""Blind work orders: a checker measures without seeing the answer it checks, and the record says which results
were written blind (blind.py)."""
import asyncio
from datetime import datetime, timedelta

import pytest

from hypgraph import Graph, GraphError, Policy
from hypgraph import blind as B


class Clock:
    def __init__(self):
        self.t = datetime(2026, 1, 1, 9, 0, 0)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t.isoformat(timespec="seconds")


@pytest.fixture
def env():
    """The primes question: the lead has a hypothesis that predicts the count and a result that measured it."""
    g = Graph(policy=Policy(reviewers={"critic"}), clock=Clock())
    lead = g.author("lead")
    inv = lead.investigation("Primes below 10,000", "Count the primes below 10,000 with code anyone can rerun.")["id"]
    h1 = lead.add("hypothesis", inv, statement="There are exactly 1229 primes below 10,000, the largest 9973.",
                  predictions=["A sieve counts 1229, the largest being 9973."])["id"]
    run = lead.add("run", inv, kind="agent", name="sieve", state="succeeded")["id"]
    rs1 = lead.add("result", inv, summary="The sieve counts 1229 primes below 10,000; the largest is 9973.",
                   outcome="positive", values={"count": 1229, "largest": 9973},
                   links=[{"rel": "produced", "from": run}, {"rel": "supports", "to": h1, "why": "the count it predicts"}])["id"]
    return g, inv, h1, rs1


OBJECTIVE = "Count the primes below 10,000 by a method of your own, and record the count and the largest one."


def issue(g, inv, **kw):
    return g.issue_work(author="lead", inv=inv, target="H1", assignee="checker", objective=OBJECTIVE, blind=True, **kw)


def checker_measures(g, inv, count=1229, largest=9973):
    me = g.author("checker")
    run = me.add("run", inv, kind="agent", name="trial division", state="succeeded")["id"]
    return me.add("result", inv, summary=f"Trial division counts {count} primes below 10,000; the largest is {largest}.",
                  outcome="positive", values={"count": count, "largest": largest},
                  links=[{"rel": "produced", "from": run}])["id"]


def test_a_blind_order_is_refused_when_it_could_not_be_blind(env):
    g, inv, h1, rs1 = env
    with pytest.raises(GraphError, match="quotes what it would seal: 1229"):
        g.issue_work(author="lead", inv=inv, target="H1", assignee="checker", blind=True,
                     objective="Confirm that the count below 10,000 is 1229.")
    with pytest.raises(GraphError, match="no prediction"):
        issue(g, inv, prediction="about twelve hundred")
    with pytest.raises(GraphError, match="has to read what it judges"):
        issue(g, inv, done_when=[{"p": "reviewed"}])
    with pytest.raises(GraphError, match="goes to someone else"):
        g.issue_work(author="lead", inv=inv, target="H1", assignee="lead", objective=OBJECTIVE, blind=True)
    g.author("checker").add("hypothesis", inv, statement="Primes thin out roughly like one over the log.",
                            predictions=["fewer per thousand as numbers grow"])
    with pytest.raises(GraphError, match="has already written in this record"):
        issue(g, inv)


def test_the_order_and_the_reads_are_sealed_from_the_checker(env):
    g, inv, h1, rs1 = env
    o = issue(g, inv)
    text = g.order_text(o["order"])
    assert "BLIND" in text and "sealed from you" in text
    assert "1229" not in text and "9973" not in text and "exactly" not in text
    v = B.view_for_author(g.snapshot(), "checker")
    assert h1 in v.hide and rs1 in v.hide and inv not in v.hide and o["order"] not in v.hide
    assert {"1229", "9973"} <= v.secrets and "10000" not in v.secrets       # the problem statement stays readable
    assert v.scrub("H1 says 1,229 and 9973 below 10,000") == "H1 says [sealed] and [sealed] below 10,000"
    sub = v.apply(g.subgraph(inv))
    sealed = [n for n in sub["nodes"] if n["id"] in (h1, rs1)]
    assert sealed and all(n["title"].startswith("sealed until") and "1229" not in str(n) for n in sealed)
    assert v.search(g.search("1229")) == []
    assert not B.view_for_author(g.snapshot(), "lead")                       # nothing is sealed from the lead


def test_written_blind_then_compared_after_return(env):
    g, inv, h1, rs1 = env
    o = issue(g, inv)
    rs2 = checker_measures(g, inv)
    st = g.state(rs2)
    assert st["blind"] == o["code"] and st["sealed"] and "agrees_blind" not in st and "restates" not in st
    assert "written blind under" in st["sentence"] and "sealed until it is returned" in st["sentence"]
    assert "1229" not in str(B.view_for_author(g.snapshot(), "checker").apply(g.get(rs2)["state"]))
    g.return_work(author="checker", order=o["order"], note="Counted by trial division.")
    assert not B.view_for_author(g.snapshot(), "checker")                    # returned: the seal lifts
    st = g.state(rs2)
    assert st["blind"] == o["code"] and not st.get("sealed")
    assert st["agrees_blind"] == [rs1] and "restates" not in st                 # agreement, not a copy
    assert "agrees blind with RS" in st["sentence"]
    g.author("lead").link(rs2, "supports", h1, why="the same count, measured blind")
    h = g.state(h1)
    assert h["independent_lines"] == 2 and h["blind_lines"] == 1
    assert "2 independent lines of support (1 written blind)" in h["sentence"]


def test_a_sighted_result_restates_and_a_revised_blind_one_stops_counting(env):
    g, inv, h1, rs1 = env
    o = issue(g, inv)
    rs2 = checker_measures(g, inv)
    g.return_work(author="checker", order=o["order"], note="done")
    g.revise(author="checker", node=rs2, fields={"summary": "Trial division counts 1229 primes below 10,000 (rechecked)."},
             reason="after reading RS1")
    st = g.state(rs2)
    assert "blind" not in st and st.get("restates") == [rs1]                   # revised after it could see: not blind
    rs3 = checker_measures(g, inv, count=1228, largest=9967)                   # written after the window closed
    assert "blind" not in g.state(rs3)


def test_the_seal_lifts_when_the_order_is_cancelled(env):
    g, inv, h1, rs1 = env
    o = issue(g, inv)
    assert B.view_for_author(g.snapshot(), "checker")
    g.cancel_work(author="lead", order=o["order"], why="not needed")
    assert not B.view_for_author(g.snapshot(), "checker")


def test_http_reads_for_a_reader_that_owns_nothing(env):
    g, inv, h1, rs1 = env
    o = issue(g, inv)
    status, out = B.dispatch(g, "GET", "/report", query={"inv": [inv]})
    assert status == 409 and o["code"] in out["detail"]
    status, out = B.dispatch(g, "GET", "/subgraph", query={"inv": [inv]})
    assert status == 200 and "1229" not in str(out) and "9973" not in str(out)
    status, out = B.dispatch(g, "GET", "/search", query={"text": ["sieve"]})
    assert status == 200 and out["results"] == []
    status, out = B.dispatch(g, "GET", f"/order/{o['order']}")
    assert status == 200 and "BLIND" in out["text"]
    status, out = B.dispatch(g, "GET", f"/node/{rs1}")
    assert status == 200 and out["body"] == {"sealed": f"until {o['code']} is returned"}
    # a reader who wrote a node keeps it
    status, out = B.dispatch(g, "GET", f"/node/{rs1}", keep=lambda i, n: n["created_by"] == "lead")
    assert out["body"]["values"]["count"] == 1229
    g.return_work(author="checker", order=o["order"], note="done")
    status, out = B.dispatch(g, "GET", "/report", query={"inv": [inv]})
    assert status == 200


def test_mcp_seat_holding_a_blind_order(env, tmp_path):
    fastmcp = pytest.importorskip("fastmcp")
    from hypgraph.mcp import build
    g, inv, h1, rs1 = env
    o = issue(g, inv)
    server = build(g, author="checker")
    text = lambda r: r.content[0].text  # noqa: E731

    async def go():
        async with fastmcp.Client(server) as c:
            r = await c.call_tool("overview", {"investigation": inv}, raise_on_error=False)
            assert r.is_error and "sealed" in text(r)
            r = await c.call_tool("show", {"node": "H1"}, raise_on_error=False)
            assert r.is_error and "sealed" in text(r)
            found = text(await c.call_tool("find", {"text": "primes"}))
            assert "1229" not in found and "exactly" not in found
            work = text(await c.call_tool("my_work", {"investigation": inv}))
            assert "BLIND" in work and "1229" not in work
            await c.call_tool("return_work", {"order": o["code"], "note": "counted", "investigation": inv})
            ov = text(await c.call_tool("overview", {"investigation": inv}))
            assert "Primes below" in ov
    asyncio.run(go())
