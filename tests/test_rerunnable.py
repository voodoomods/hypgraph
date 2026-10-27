"""A computational gate counts only a result something can re-run: the run that produced it carries its code, or it is
the instrument's (kind=lab). Through the CLI, with no tool that executes code, the seats of an optimization run
wrote "exact DP over capacity" and "brute force over 2^21" as prose, the verifier passed a wrong optimum (757 for
656) and the question settled. solved (optimization), backtested (trading) and the scientific workflow's evidenced
stage now want the code."""
import pytest

from hypgraph import Graph, Policy

H = "harness"
SHA = "a" * 64


def _g(profile: str, reviewers=("verifier",)):
    g = Graph(policy=Policy(reviewers=set(reviewers), extra_reserved={H}))
    inv = g.create(author=H, type="investigation", fields={"title": "Load the van.", "profile": profile,
                   "objective": "Find the best selection under the weight limit."})["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q1",
                 fields={"text": "What is the highest total value that fits in the van?"})["id"]
    return g, inv, q


def _gate(g, q, name):
    return next(x for x in g.stage(q)["gates"] if x["gate"] == name)


def _solve(g, inv, q, run_fields, author="solver"):
    inst = g.search("", "artifact", inv, 5)
    inst = inst[0]["id"] if inst else g.create(author="lead", type="artifact", inv=inv, fields={
        "sha256": SHA, "path": "items.csv", "kind": "instance"}, links=[{"rel": "part_of", "to": q}])["id"]
    run = g.create(author=author, type="run", inv=inv, fields={"name": "dp", "state": "succeeded", **run_fields},
                   links=[{"rel": "uses", "to": inst}])["id"]
    rs = g.create(author=author, type="result", inv=inv, fields={"summary": "Exact DP over capacity: the optimum.",
                  "values": {"objective": {"value": 757}, "feasible": {"value": True}, "bound": {"value": 757}},
                  "outcome": "positive"}, links=[{"rel": "produced", "from": run}])["id"]
    g.create(author=author, type="claim", inv=inv, fields={"statement": "The highest total value is 757 (bound 757).",
             "scope": "items.csv at a 212 kg limit."}, links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])
    return rs


def test_a_solve_with_no_code_behind_it_is_not_solved():
    g, inv, q = _g("optimization@2")
    rs = _solve(g, inv, q, {"kind": "agent"})
    gate = _gate(g, q, "solved")
    assert not gate["met"] and "no code behind it" in gate["why"] and g.get(rs)["code"] in gate["why"]


@pytest.mark.parametrize("fields", [{"kind": "agent", "config": {"source": "import csv\nprint('objective', 656)"}},
                                    {"kind": "agent", "code": ["solve.py"]}, {"kind": "lab"}])
def test_a_solve_with_its_code_or_by_the_instrument_is_solved(fields):
    g, inv, q = _g("optimization@2")
    _solve(g, inv, q, fields, author="lab" if fields["kind"] == "lab" else "solver")
    assert _gate(g, q, "solved")["met"]


def test_a_backtest_with_no_code_is_not_backtested():
    g, inv, q = _g("trading@2", reviewers=("risk",))
    run = g.create(author="quant", type="run", inv=inv, fields={"kind": "agent", "name": "bt", "state": "succeeded"})["id"]
    g.create(author="quant", type="result", inv=inv, fields={"summary": "Backtest out of sample after costs.",
             "values": {"oos_return": {"value": -0.18}, "fees": {"value": 0.001}, "trials": {"value": 20}},
             "outcome": "negative"}, links=[{"rel": "produced", "from": run}, {"rel": "part_of", "to": q}])
    gate = _gate(g, q, "backtested")
    assert not gate["met"] and "no code behind it" in gate["why"]


def test_a_scientific_result_needs_its_code_but_a_sourced_one_does_not():
    g, inv, q = _g("scientific@2", reviewers=("critic",))
    run = g.create(author="w", type="run", inv=inv, fields={"kind": "agent", "name": "count", "state": "succeeded"},
                   links=[{"rel": "part_of", "to": q}])["id"]
    g.create(author="w", type="result", inv=inv, fields={"summary": "A is right on 781 of 1000 items.",
             "values": {"a_correct": {"k": 781, "n": 1000}}, "outcome": "positive"}, links=[{"rel": "produced", "from": run}])
    assert not _gate(g, q, "result_exists")["met"]
    from hypgraph import workflow as W
    assert W.GATES["result_exists"] is W.g_result_exists                 # the knowledge workflow doesn't use the gate
    assert "result_exists" not in {st.gate for st in __import__("hypgraph").profiles.KNOWLEDGE2.workflow.stages}
