"""0.4.1: three rules the hypswarm examples exposed. A cited source accounts for the numbers in its passage; a
rework keeps the evidence its chain already produced; a claim of passing tests may rest on the author's result once
the instrument's re-run of that run is positive."""
import time

from hypgraph import Graph, GraphError, Policy
from hypgraph.coord import chain_root

import pytest

H = "harness"


def _g(profile):
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={H}, instrument="lab"))
    inv = g.create(author=H, type="investigation", fields={"title": "A profiled investigation.",
                                                          "objective": "See the 0.4.1 rules hold.", "profile": profile})["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q1", fields={"text": "When was it signed?"})["id"]
    return g, inv, q


def test_a_cited_source_accounts_for_its_numbers():
    g, inv, q = _g("knowledge@1")
    src = g.create(author="r", type="source", inv=inv, fields={"citation": "Britannica, 'Peace of Westphalia'.",
                                                              "url": "https://www.britannica.com/event/Peace-of-Westphalia",
                                                              "passage": "the treaties were signed on October 24, 1648"})["id"]
    c = g.create(author="r", type="claim", inv=inv, fields={"statement": "The Peace of Westphalia was signed on 24 October 1648.",
                                                           "scope": "The treaties of Osnabrück and Münster.", "kind": "finding"},
                 links=[{"rel": "answers", "to": q}, {"rel": "cites", "to": src}])
    assert c["code"].startswith("CL")
    with pytest.raises(GraphError, match="UNBOUND_NUMBER"):                      # a number the source does not contain
        g.create(author="r", type="claim", inv=inv, fields={"statement": "It was signed by 109 delegations.",
                                                           "scope": "The treaties of Osnabrück and Münster.", "kind": "finding"},
                 links=[{"rel": "answers", "to": q}, {"rel": "cites", "to": src}])


def test_a_rework_keeps_its_chains_evidence():
    g, inv, q = _g("software@1")
    o = g.issue_work(author=H, inv=inv, target=q, assignee="tester", objective="Run the tests.")
    time.sleep(1.1)
    r = g.create(author="tester", type="run", inv=inv, fields={"kind": "agent", "name": "pytest", "state": "succeeded"})
    rs = g.create(author="tester", type="result", inv=inv, fields={"summary": "Ran pytest.", "values": {"passed": {"k": 3, "n": 3}}, "outcome": "positive"},
                  links=[{"rel": "produced", "from": r["id"]}])
    lab = g.create(author="lab", type="run", inv=inv, fields={"kind": "lab", "name": "re-run of pytest", "state": "succeeded"},
                   links=[{"rel": "replicates", "to": r["id"], "data": {"differs": "same_code"}}])
    g.create(author="lab", type="result", inv=inv, fields={"summary": "Re-executed: 1 of 1 values confirmed.", "values": {"passed": {"k": 3, "n": 3}}, "outcome": "positive"},
             links=[{"rel": "produced", "from": lab["id"]}])
    first = {p["p"]: p["met"] for p in g.check_work(o["order"])["predicates"]}
    assert first == {"tests_pass": True, "claim_made": False}
    rw = g.rework(author=H, order=o["order"], missing="no live claim on Q1 since the order was issued")
    assert chain_root(g.snapshot(), rw["order"]) == o["order"]
    second = {p["p"]: p["met"] for p in g.check_work(rw["order"])["predicates"]}
    assert second["tests_pass"] is True                                          # 0.4.0 lost it: evidence predated the rework
    # (c) the claim of passing may now rest on the author's result: the instrument replicated its run positively
    c = g.create(author="tester", type="claim", inv=inv, fields={"statement": "The importer passes all 3 of 3 tests in test_importer.py.",
                                                                "scope": "test_importer.py at this commit."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs["id"]}])
    assert c["code"].startswith("CL")
    assert all(p["met"] for p in g.check_work(rw["order"])["predicates"])


def test_passing_still_needs_the_instrument():
    g, inv, q = _g("software@1")
    r = g.create(author="tester", type="run", inv=inv, fields={"kind": "agent", "name": "pytest", "state": "succeeded"})
    rs = g.create(author="tester", type="result", inv=inv, fields={"summary": "Ran pytest.", "values": {"passed": {"k": 3, "n": 3}}, "outcome": "positive"},
                  links=[{"rel": "produced", "from": r["id"]}])
    with pytest.raises(GraphError, match="PASS_WITHOUT_INSTRUMENT_RUN"):
        g.create(author="tester", type="claim", inv=inv, fields={"statement": "The importer passes all 3 of 3 tests.", "scope": "test_importer.py at this commit."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs["id"]}])
