"""Coordinating a team through the record: work orders, predicates, acceptance, rework, the cascade, the briefing."""
from datetime import datetime, timedelta

import pytest

from hypgraph import Graph, GraphError, Policy


class Clock:
    def __init__(self):
        self.t = datetime(2026, 1, 1, 9, 0, 0)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t.isoformat(timespec="seconds")


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}), clock=Clock())
    lead = g.author("lead")
    inv = lead.investigation("Does the fine-tune help?",
                             "Find out whether the fine-tune beats the baseline on held-out items.",
                             success_criteria="A checked claim either way, with its interval.")["id"]
    h1 = lead.add("hypothesis", inv, statement="The fine-tune is more accurate on held-out items.",
                  predictions=["paired accuracy difference above zero"])["id"]
    h2 = lead.add("hypothesis", inv, statement="The two models are equally accurate on held-out items.",
                  predictions=["paired difference indistinguishable from zero"],
                  links=[{"rel": "alternative_to", "to": h1}])["id"]
    x1 = lead.add("experiment", inv, aim="Compare paired accuracy on the held-out set.",
                  protocol="Score both models on the same 2,000 items; paired test on per-item correctness.",
                  success_criteria="A paired interval for the difference.", method="paired McNemar",
                  links=[{"rel": "tests", "to": h1, "data": {"expected": "difference > 0"}},
                         {"rel": "tests", "to": h2, "data": {"expected": "difference ~ 0"}}])["id"]
    return g, lead, inv, h1, h2, x1


def run_and_result(g, who, inv, x, outcome="positive", replicates=""):
    a = g.author(who)
    links = [{"rel": "executes", "to": x}]
    if replicates:                                   # the same numbers again: only as a declared rerun
        links.append({"rel": "replicates", "to": replicates, "data": {"differs": "new_seed"}})
    r = a.add("run", inv, kind="agent", name="paired eval", state="succeeded", links=links)["id"]
    rs = a.add("result", inv, summary="Fine-tune 1,624 of 2,000 vs baseline 1,568 of 2,000 on the same items.",
               outcome=outcome, values={"ft": {"k": 1624, "n": 2000}, "bl": {"k": 1568, "n": 2000}},
               links=[{"rel": "produced", "from": r}])["id"]
    return r, rs


def test_issue_leases_the_target_and_refuses_a_duplicate(env):
    g, lead, inv, h1, h2, x1 = env
    o = g.issue_work(author="lead", inv=inv, target="X1", assignee="analyst", role="analyst",
                     objective="Run the paired comparison and record the result.")
    assert o["code"].startswith("T") and set(o["premises"]) >= {"H1", "H2"}
    assert [p["p"] for p in o["done_when"]] == ["run_registered", "result_exists"]
    s = g.snapshot()
    assert s.leases[x1]["agent"] == "analyst" and s.leases[x1]["task"] == o["order"]
    with pytest.raises(GraphError, match="already works on X1"):
        g.issue_work(author="lead", inv=inv, target=x1, assignee="stats", objective="Run the comparison again.")
    assert g.orders(inv)[0]["status"] == "open"


def test_order_text_carries_everything_the_assignee_needs(env):
    g, lead, inv, *_ = env
    o = g.issue_work(author="lead", inv=inv, target="X1", assignee="analyst", objective="Run the paired comparison.",
                     method="McNemar on per-item correctness", budget={"calls": 40, "usd": 0.05})
    t = o["text"]
    for part in ("WORK ORDER", "OBJECTIVE", "TARGET", "PREMISES", "PREDICTION", "H1: difference > 0", "METHOD",
                 "DONE WHEN", "[run_registered]", "BUDGET", "calls 40", "LEASE", "RETURN"):
        assert part in t, part


def test_only_evidence_after_the_order_counts_and_acceptance_needs_every_predicate(env):
    g, lead, inv, h1, h2, x1 = env
    r0, _ = run_and_result(g, "analyst", inv, x1)             # done before anyone asked: doesn't count
    o = g.issue_work(author="lead", inv=inv, target="X1", assignee="analyst", objective="Run the paired comparison.")
    chk = g.check_work(o["order"])
    assert not chk["all_met"] and all("under this order" in c["why"] for c in chk["predicates"])
    with pytest.raises(GraphError, match="isn't done"):
        g.accept_work(author="lead", order=o["order"])
    with pytest.raises(GraphError, match="RESULT_RESTATES"):   # the same numbers again, undeclared: refused
        run_and_result(g, "analyst", inv, x1)
    _r, rs = run_and_result(g, "analyst", inv, x1, replicates=r0)
    back = g.return_work(author="analyst", order=o["order"], note="Ran it; result RS2.")
    assert back["all_met"] and back["status"] == "returned"
    with pytest.raises(GraphError, match="analyst's order"):
        g.return_work(author="lead", order=o["order"])
    acc = g.accept_work(author="lead", order=o["order"], reason="as specified")
    assert acc["status"] == "accepted" and rs in acc["evidence"]
    assert g.orders(inv)[0]["status"] == "accepted"
    d = g.get(g.resolve(acc["decision"], inv))
    assert {e["rel"] for e in d["out"]} == {"settles", "based_on"}


def test_rework_supersedes_and_keeps_the_target(env):
    g, lead, inv, h1, h2, x1 = env
    o = g.issue_work(author="lead", inv=inv, target="X1", assignee="analyst", objective="Run the paired comparison.")
    g.return_work(author="analyst", order=o["order"], note="Couldn't get the item file.")
    r = g.rework(author="lead", order=o["order"], missing="no run and no result were registered")
    st = {x["code"]: x["status"] for x in g.orders(inv)}
    assert st[o["code"]] == "reworked" and st[r["code"]] == "open"
    assert "Rework of" in r["text"] and "earlier order" in r["text"]


def test_a_fallen_premise_makes_orders_moot_and_cancel_moot_stops_exactly_those(env):
    g, lead, inv, h1, h2, x1 = env
    a = g.author("analyst")
    r0 = a.add("result", inv, summary="Baseline accuracy is 1,568 of 2,000 on the held-out set.", outcome="positive",
               values={"bl": {"k": 1568, "n": 2000}})["id"]
    cl = a.add("claim", inv, statement="The baseline scores 1,568 of 2,000 on the held-out set.",
               scope="2,000 held-out items.", links=[{"rel": "derived_from", "to": r0}],
               measurements=[{"name": "baseline", "result": r0, "key": "bl", "k": 1568, "n": 2000}])["id"]
    h3 = lead.add("hypothesis", inv, statement="The fine-tune's gain holds beyond the baseline's level.",
                  predictions=["gain above the baseline"], links=[{"rel": "requires", "to": cl}])["id"]
    dep = g.issue_work(author="lead", inv=inv, target=h3, assignee="stats", objective="Test H3 against the baseline.")
    other = g.issue_work(author="lead", inv=inv, target="X1", assignee="analyst", objective="Run the comparison.")
    assert g.resolve(dep["code"], inv) and "CL1" in dep["premises"]
    out = g.withdraw(author="analyst", node=r0, why="the item file was corrupted in transfer")
    assert out["blast_radius"]["by_type"].get("task") == 1
    st = {x["code"]: x["status"] for x in g.orders(inv)}
    assert st[dep["code"]] == "moot" and st[other["code"]] == "open"
    gone = g.cancel_moot(author="lead", inv=inv)
    assert [c["order"] for c in gone] == [dep["code"]]
    st = {x["code"]: x["status"] for x in g.orders(inv)}
    assert st[dep["code"]] == "cancelled" and st[other["code"]] == "open"


def test_briefing_is_deterministic_and_reports_the_delta(env):
    g, lead, inv, h1, h2, x1 = env
    roster = [{"name": "analyst", "takes": "runs and results"}, {"name": "critic", "takes": "reviews"}]
    b1 = g.briefing(inv, roster=roster)
    assert b1["sha256"] == g.briefing(inv, roster=roster)["sha256"]
    for part in ("MISSION", "Success:", "RULES", "ROSTER", "STANDING", "FRONTIER", "X1", "IN FLIGHT", "RETURNED"):
        assert part in b1["text"], part
    assert "SINCE LAST" not in b1["text"]
    o = g.issue_work(author="lead", inv=inv, target="X1", assignee="analyst", objective="Run the paired comparison.")
    b2 = g.briefing(inv, roster=roster, since_seq=b1["seq"])
    assert f"{o['code']} → analyst on X1" in b2["text"]
    assert "X1 Compare" not in b2["text"].split("FRONTIER")[1].split("IN FLIGHT")[0]   # in flight: off the frontier
    run_and_result(g, "analyst", inv, x1)
    g.return_work(author="analyst", order=o["order"], note="done")
    b3 = g.briefing(inv, roster=roster, since_seq=b2["seq"])
    assert "run_registered=MET result_exists=MET" in b3["text"]
    assert "SINCE LAST" in b3["text"] and "returned:" in b3["text"]
    assert b1["sections"]["RULES"] == b3["sections"]["RULES"]          # the stable prefix doesn't move


def test_review_orders_and_report_orders(env):
    g, lead, inv, h1, h2, x1 = env
    _r, rs = run_and_result(g, "analyst", inv, x1)
    cl = g.author("analyst").add("claim", inv, statement="The fine-tune scores 1,624 of 2,000 on held-out items.",
                                 scope="2,000 held-out items, one seed.",
                                 links=[{"rel": "derived_from", "to": rs}],
                                 measurements=[{"name": "fine-tune", "result": rs, "key": "ft", "k": 1624,
                                                "n": 2000}])["id"]
    o = g.issue_work(author="lead", inv=inv, target=cl, assignee="critic", objective="Check CL1 against its result.")
    assert [p["p"] for p in o["done_when"]] == ["reviewed"]
    g.author("critic").review(cl, "checked", "Recomputed from the result values.", "Matches 1,624 of 2,000.")
    assert g.check_work(o["order"])["all_met"]
    rep = g.issue_work(author="lead", inv=inv, target=inv, assignee="lead", objective="Write the final report.")
    assert not g.check_work(rep["order"])["all_met"]
    assert not g.check_work(rep["order"], text="The fine-tune never fails, as CL9 established.")["all_met"]
    assert g.check_work(rep["order"], text="CL1 is checked: 1,624 of 2,000.")["all_met"]


def test_mcp_orchestrator_and_assignee_coordinate_through_the_record(tmp_path):
    fastmcp = pytest.importorskip("fastmcp")
    import asyncio
    import os

    from hypgraph.demos import broad_street
    from hypgraph.mcp import build
    db = tmp_path / "c.hypgraph"
    broad_street.build(path=str(db))
    text = lambda r: r.content[0].text  # noqa: E731

    async def go():
        lead, analyst = build(str(db), author="lead"), build(str(db), author="analyst")
        async with fastmcp.Client(lead) as L, fastmcp.Client(analyst) as A:
            assert {"briefing", "issue_work", "my_work", "check_work", "return_work", "accept_work", "rework",
                    "cancel_work", "cancel_moot"} <= {t.name for t in await L.list_tools()}
            b = text(await L.call_tool("briefing", {}))
            assert "FRONTIER" in b and "X3" in b and "(seq " in b
            order = text(await L.call_tool("issue_work", {"target": "X3", "assignee": "analyst",
                                                          "objective": "Run X3 and record what it found."}))
            assert "WORK ORDER" in order and "DONE WHEN" in order
            code = order.split()[2]
            dup = await L.call_tool("issue_work", {"target": "X3", "assignee": "someone",
                                                   "objective": "Run X3 as well, separately."}, raise_on_error=False)
            assert dup.is_error and "already works on X3" in text(dup)
            assert code in text(await A.call_tool("my_work", {}))
            assert "NOT MET" in text(await L.call_tool("check_work", {"order": code}))
            (tmp_path / "count.py").write_text("print(1)\n")
            await A.call_tool("register_run", {"name": "X3 count", "experiment": "X3", "code_paths": ["count.py"],
                                               "result_summary": "Counted the houses by water company.",
                                               "outcome": "positive"})
            back = text(await A.call_tool("return_work", {"order": code, "note": "Ran it."}))
            assert "every predicate met" in back
            assert "accepted" in text(await L.call_tool("accept_work", {"order": code}))
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        asyncio.run(go())
    finally:
        os.chdir(cwd)


def test_unknown_predicates_and_targets_are_refused(env):
    g, lead, inv, *_ = env
    with pytest.raises(GraphError, match="unknown predicate"):
        g.issue_work(author="lead", inv=inv, target="X1", assignee="a", objective="x" * 20, done_when=[{"p": "vibes"}])
    with pytest.raises(GraphError, match="no node"):
        g.issue_work(author="lead", inv=inv, target="X99", assignee="a", objective="x" * 20)
