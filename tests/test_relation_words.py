"""A relation word the grammar doesn't have is read as the relation it names; a hypothesis derived from a claim is
motivated by it. The link refusals left after 0.7.3's translation table."""
import pytest

from hypgraph import Graph, GraphError, Policy


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}))
    lead = g.author("lead")
    inv = lead.investigation("Words", "Find out which relation words the record reads.")["id"]
    return g, inv


def test_a_run_that_generated_an_artifact_produced_it(env):
    g, inv = env
    a = g.author("quant")
    art = a.add("artifact", inv, sha256="b" * 64, path="grid.csv", kind="data")["id"]
    run = a.add("run", inv, kind="agent", name="grid", state="succeeded", links=[{"rel": "generated", "to": art}])
    assert ("produced", art) in {(x["rel"], x["dst"]) for x in g.snapshot().out[run["id"]]}
    assert any("read as produced" in n for n in run["notes"])
    out = a.link(run["id"], "used", art, why="the run read the grid", role="data")
    assert out["rel"] == "uses" and out["notes"]


def test_a_hypothesis_derived_from_a_claim_is_motivated_by_it_and_nonsense_is_still_refused(env):
    g, inv = env
    a = g.author("stats")
    c = a.add("claim", inv, statement="steps_k is lower on the supplement arm in the pilot.", scope="pilot.csv, 40 rows.",
              kind="lead")["id"]
    h = a.add("hypothesis", inv, statement="The supplement lowers steps_k.",
              predictions=["steps_k is lower on the supplement arm in the trial."],
              links=[{"rel": "derived_from", "to": c}])
    assert ("motivated_by", c) in {(x["rel"], x["dst"]) for x in g.snapshot().out[h["id"]]}
    with pytest.raises(GraphError) as e:
        a.link(h["id"], "resembles", c, why="no such relation, and no word for it")
    assert {p["code"] for p in e.value.problems} == {"LINK_UNKNOWN_RELATION"}
