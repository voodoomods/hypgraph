"""A question that asks for a measurement skips the gates its workflow lists in ``measure_skips`` — in the stage
derivation and as an order predicate. Every profile's gates used to apply to every question: a timing question was
reworked for a diff it didn't need, a count for a preregistered hypothesis, a look-ahead check for a backtest
(studies: E2, E4, S1, T1)."""
import pytest

from hypgraph import Graph, GraphError, Policy, profiles

H = "harness"


def _g(profile: str, asks: str | None = "measure"):
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={H}))
    inv = g.create(author=H, type="investigation", fields={"title": "A measure investigation.", "profile": profile,
                   "objective": "See a measure question skip the gates it doesn't need."})["id"]
    f = {"text": "What is each model's overall accuracy in results.csv?"}
    if asks:
        f["asks"] = asks
    q = g.create(author=H, type="question", inv=inv, code="Q1", fields=f)["id"]
    return g, inv, q


def _measured(g, inv, q):
    run = g.create(author="w", type="run", inv=inv, fields={"kind": "agent", "name": "count", "state": "succeeded"},
                   links=[{"rel": "part_of", "to": q}])["id"]
    rs = g.create(author="w", type="result", inv=inv, fields={"summary": "A is right on 781 of 1000 items.",
                  "values": {"a_correct": {"k": 781, "n": 1000}}, "outcome": "positive"},
                  links=[{"rel": "produced", "from": run}])["id"]
    c = g.create(author="w", type="claim", inv=inv, fields={
        "statement": "Model A is right on 781 of 1000 items in results.csv.", "scope": "results.csv, every row.",
        "measurements": [{"name": "A", "key": "a_correct", "result": rs}]},
        links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
    return c


def test_a_scientific_measure_question_needs_no_hypothesis():
    g, inv, q = _g("scientific@2")
    st = g.stage(q)
    assert st["stage"] == "run"                                        # conjectured and preregistered are skipped
    skipped = {gt["gate"] for gt in st["gates"] if gt["skipped"]}
    assert skipped == {"hypothesis_stated", "preregistered"}
    c = _measured(g, inv, q)
    assert g.stage(q)["stage"] == "reviewed"
    g.review(author="critic", target=c, verdict="checked", method="Recounted the file.", notes="781 of 1000.")
    assert g.stage(q)["complete"]


def test_without_asks_every_gate_still_applies():
    g, inv, q = _g("scientific@2", asks=None)
    assert g.stage(q)["stage"] == "conjectured"
    assert not any(gt["skipped"] for gt in g.stage(q)["gates"])


@pytest.mark.parametrize("profile, gate", [("scientific@2", "hypothesis_stated"), ("software@2", "diff_registered"),
                                           ("software@2", "tests_pass_current"), ("trading@2", "backtested")])
def test_a_skipped_gate_is_met_as_an_order_predicate(profile, gate):
    from hypgraph import workflow as W
    g, inv, q = _g(profile)
    s = g.snapshot()
    assert W.evaluate_predicate(gate, s, q, "", inv)["met"]
    g2, inv2, q2 = _g(profile, asks=None)
    assert not W.evaluate_predicate(gate, g2.snapshot(), q2, "", inv2)["met"]


def test_a_measure_question_is_not_a_requirement():
    g, inv, q = _g("software@2")
    c = _measured(g, inv, q)
    g.review(author="critic", target=c, verdict="checked", method="Recounted.", notes="As stated.")
    crit = {x["name"]: x for x in profiles.completion(g.snapshot(), inv)["criteria"]}
    assert crit["questions_settled"]["met"] and crit["requirements_verified_current"]["met"]


def test_asks_takes_only_known_values():
    g = Graph(policy=Policy(extra_reserved={H}))
    inv = g.create(author=H, type="investigation", fields={"title": "An investigation.", "objective": "Ask badly."})["id"]
    with pytest.raises(GraphError):
        g.create(author=H, type="question", inv=inv, fields={"text": "What is it?", "asks": "guess"})


def test_the_profile_view_lists_what_a_measure_question_skips():
    assert profiles.view("trading@2")["workflow"]["measure_skips"][:3] == ["hypothesis_stated", "preregistered",
                                                                          "backtested"]
