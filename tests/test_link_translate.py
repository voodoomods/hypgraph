"""A link whose relation can't join its two types is read as the one relation that says the same thing between them,
with a note; an experiment may use the artifact it is designed on; a link that lands fixes the refusal on its pair.
23 LINK_NOT_ALLOWED refusals in nine challenge runs: every hint named the relation, 3 were taken."""
import pytest

from hypgraph import Graph, GraphError, Policy


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}))
    lead = g.author("lead")
    inv = lead.investigation("Links", "Find out which links the record reads for the agent.")["id"]
    q = lead.add("question", inv, text="Does the supplement change steps_k?")["id"]
    h = lead.add("hypothesis", inv, statement="The supplement raises steps_k.",
                 predictions=["steps_k is higher on the supplement arm."])["id"]
    a = lead.add("artifact", inv, sha256="a" * 64, path="trial.csv", kind="data")["id"]
    return g, inv, q, h, a


def test_an_experiment_that_supports_a_hypothesis_tests_it(env):
    g, inv, q, h, a = env
    e = g.author("stats").add("experiment", inv, aim="Compare the arms on steps_k.",
                              protocol="Two-sided Welch test on steps_k between the arms, Holm over 20 outcomes.",
                              success_criteria="Holm-adjusted p below 0.05.",
                              links=[{"rel": "supports", "to": h, "why": "this experiment bears on the hypothesis",
                                      "data": {"expected": "steps_k higher on the supplement arm"}},
                                     {"rel": "uses", "to": a, "data": {"role": "data"}}])
    rels = {(x["rel"], x["dst"]) for x in g.snapshot().out[e["id"]]}
    assert ("tests", h) in rels and ("uses", a) in rels
    assert any("read as tests" in n for n in e["notes"])


def test_a_run_that_uses_an_experiment_executes_it_and_a_result_that_answers_is_part_of(env):
    g, inv, q, h, a = env
    stats = g.author("stats")
    e = stats.add("experiment", inv, aim="Compare the arms.", protocol="Welch test on steps_k between the arms.",
                  success_criteria="p below 0.05.", links=[{"rel": "tests", "to": h, "data": {"expected": "higher"}}])["id"]
    run = stats.add("run", inv, kind="agent", name="welch", state="succeeded",
                    links=[{"rel": "uses", "to": e}, {"rel": "uses", "to": a, "data": {"role": "data"}}])
    assert ("executes", e) in {(x["rel"], x["dst"]) for x in g.snapshot().out[run["id"]]}
    r = stats.add("result", inv, summary="steps_k differs between the arms at p = 0.012.", values={"p_welch": 0.012},
                  links=[{"rel": "produced", "from": run["id"]}, {"rel": "answers", "to": q}])
    assert ("part_of", q) in {(x["rel"], x["dst"]) for x in g.snapshot().out[r["id"]]}
    out = stats.link(r["id"], "uses", a, why="the result was computed from the trial data")
    assert out["rel"] == "derived_from" and out["notes"]


def test_a_pair_no_relation_joins_is_still_refused_and_the_landed_link_fixes_it(env):
    g, inv, q, h, a = env
    stats = g.author("stats")
    e = stats.add("experiment", inv, aim="Compare the arms.", protocol="Welch test on steps_k between the arms.",
                  success_criteria="p below 0.05.", links=[{"rel": "tests", "to": h, "data": {"expected": "higher"}}])["id"]
    c = stats.add("claim", inv, statement="steps_k is higher on the supplement arm.", scope="trial.csv, 240 rows.",
                  kind="lead")["id"]
    with pytest.raises(GraphError) as x:
        stats.link(c, "uses", e, why="the claim came out of this experiment")
    assert {p["code"] for p in x.value.problems} == {"LINK_NOT_ALLOWED"}
    row = g.refusals(inv)[0]
    assert row["type"] == "link" and row["fixed_by"] is None
    out = stats.link(e, "tests", c, why="the experiment tests this claim", expected="higher steps_k")
    assert out["fixes_refusals"] == [row["id"]]
    assert g.refusals(inv)[0]["fixed_by"]


def test_an_allowed_relation_is_never_translated(env):
    g, inv, q, h, a = env
    stats = g.author("stats")
    r = stats.add("result", inv, summary="steps_k differs between the arms at p = 0.012.", values={"p_welch": 0.012})
    out = stats.link(r["id"], "supports", h, why="the measurement bears on the hypothesis")
    assert out["rel"] == "supports" and "notes" not in out
