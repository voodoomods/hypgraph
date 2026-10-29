"""The last claims reading 'no live support' after bound results counted: a knowledge claim resting on the sources it
cites, and claims on results whose author wrote outcome 'failed' for the code under test failing its spec, on runs
that succeeded (E4: 13 checked claims read UNSUPPORTED — every support has fallen)."""
import pytest

from hypgraph import Graph, Policy
from hypgraph import derive as D


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}, instrument="lab"))
    inv = g.author("lead").investigation("Support", "Find out what a claim rests on.")["id"]
    return g, inv


def _state(g, nid):
    return D.state(g.snapshot(), nid)


def test_a_cited_source_is_a_line_of_support_rated_external(env):
    g, inv = env
    r = g.author("researcher")
    s1 = r.add("source", inv, citation="config.py in the 2.4.0 release", url="file:sources/config.py",
               passage='"retry_backoff": 30,       # seconds; 60 before 2.3.0')["id"]
    s2 = r.add("source", inv, citation="The 2.4 configuration guide", url="file:sources/config-guide.md",
               passage="retry_backoff defaults to 30 seconds")["id"]
    c = r.add("claim", inv, statement="The default retry_backoff in the current release is 30 seconds.",
              scope="The 2.4.0 release's config module and its configuration guide.",
              links=[{"rel": "cites", "to": s1}, {"rel": "cites", "to": s2}])
    st = _state(g, c["id"])
    assert st["independent_lines"] == 2 and st["evidence"] == "external" and not st["unsupported"]


def test_a_failed_outcome_on_a_succeeded_run_is_a_finding_not_a_fall(env):
    g, inv = env
    t = g.author("tester")
    run = t.add("run", inv, kind="agent", name="spec cases", state="succeeded")["id"]
    r = t.add("result", inv, kind="computed", outcome="failed",
              summary="Of the 8 valid-input cases, parse_duration gets exactly 1 wrong: case 8.",
              values={"valid_wrong": {"k": 1, "n": 8}}, links=[{"rel": "produced", "from": run}])["id"]
    assert not D.fallen(g.snapshot(), r)
    c = t.add("claim", inv, statement="parse_duration gets exactly 1 of the 8 valid-input cases wrong.",
              scope="SPEC.md's 8 valid-input cases on the current diff.",
              measurements=[{"name": "valid wrong", "result": r, "key": "valid_wrong", "k": 1, "n": 8}],
              links=[{"rel": "derived_from", "to": r}])
    st = _state(g, c["id"])
    assert st["independent_lines"] == 1 and not st["unsupported"] and "UNSUPPORTED" not in st["sentence"]


def test_a_failed_outcome_still_falls_when_the_run_failed_or_there_is_none(env):
    g, inv = env
    t = g.author("tester")
    bad = t.add("run", inv, kind="agent", name="spec cases", state="failed")["id"]
    r1 = t.add("result", inv, kind="computed", outcome="failed", summary="The harness crashed before the cases ran.",
               values={"n_cases": 12}, links=[{"rel": "produced", "from": bad}])["id"]
    r2 = t.add("result", inv, kind="computed", outcome="failed", summary="pytest could not import the module.",
               values={"n_collected": 0})["id"]
    s = g.snapshot()
    assert D.fallen(s, r1) and D.fallen(s, r2)
