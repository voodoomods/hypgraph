"""A result a claim derives from, or binds a measurement to, is a line of support; two bound results from one run are
one line; a bound result that fell leaves the claim unsupported. 73 of 113 active claims in the challenge records
read "no live support" beside the result they were bound to."""
import pytest

from hypgraph import Graph, Policy
from hypgraph import derive as D


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}, instrument="lab"))
    lead = g.author("lead")
    inv = lead.investigation("Support", "Find out what a bound claim rests on.")["id"]
    run = g.create(author="lab", type="run", inv=inv, fields={"kind": "lab", "name": "count", "state": "succeeded"})["id"]
    r1 = g.create(author="lab", type="result", inv=inv, fields={"summary": "607 of 821 rows pass the check.",
                  "values": {"rows": {"k": 607, "n": 821}}}, links=[{"rel": "produced", "from": run}])["id"]
    r2 = g.create(author="lab", type="result", inv=inv, fields={"summary": "214 of 821 rows carry a comma.",
                  "values": {"commas": {"k": 214, "n": 821}}}, links=[{"rel": "produced", "from": run}])["id"]
    return g, inv, run, r1, r2


def _state(g, nid):
    return D.state(g.snapshot(), nid)


def test_a_claim_bound_by_measurements_and_derived_from_is_supported_by_its_result(env):
    g, inv, run, r1, r2 = env
    c = g.author("analyst").add("claim", inv, statement="607 of 821 rows pass the check.", scope="corpus.csv's 821 rows.",
                                measurements=[{"name": "rows", "result": r1, "key": "rows", "k": 607, "n": 821}],
                                links=[{"rel": "derived_from", "to": r1}])
    st = _state(g, c["id"])
    assert st["independent_lines"] == 1 and st["evidence"] != "unverified" and not st["unsupported"]
    assert "1 independent line of support" in st["sentence"]


def test_two_bound_results_from_one_run_are_one_line_and_a_supports_edge_adds_none(env):
    g, inv, run, r1, r2 = env
    c = g.author("analyst").add("claim", inv, statement="607 of 821 rows pass and 214 of 821 carry a comma.",
                                scope="corpus.csv's 821 rows.",
                                measurements=[{"name": "rows", "result": r1, "key": "rows", "k": 607, "n": 821},
                                              {"name": "commas", "result": r2, "key": "commas", "k": 214, "n": 821}])
    assert _state(g, c["id"])["independent_lines"] == 1
    g.author("lab").link(r1, "supports", c["id"], why="the count is the claim's measurement")
    assert _state(g, c["id"])["independent_lines"] == 1                 # the same result, not a second line


def test_a_claim_whose_bound_result_fell_is_unsupported(env):
    g, inv, run, r1, r2 = env
    c = g.author("analyst").add("claim", inv, statement="607 of 821 rows pass the check.", scope="corpus.csv's 821 rows.",
                                measurements=[{"name": "rows", "result": r1, "key": "rows", "k": 607, "n": 821}],
                                links=[{"rel": "derived_from", "to": r1}])
    g.author("lab").withdraw(r1, "the count read the wrong column")
    st = _state(g, c["id"])
    assert st["unsupported"] and st["independent_lines"] == 0
