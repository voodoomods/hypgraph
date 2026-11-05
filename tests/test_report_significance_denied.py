"""0.8.5: a report that says a difference was NOT significant isn't claiming a test passed, and a claim resting on a
named p-value carries its test. From gpt-oss runs on a small box: leads wrote "*not* significantly" and were refused
until they gave up, so two of six runs ended with no interpretation."""
import pytest

from hypgraph import Graph, Policy


def _record(values):
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.create(author="h", type="investigation", fields={"title": "Does A beat B.", "objective": "Compare A and B on the same items."})["id"]
    q = g.create(author="h", type="question", inv=inv, code="Q2",
                 fields={"text": "Is A significantly more accurate than B (two-sided, 0.05)?"})["id"]
    r = g.create(author="stats", type="run", inv=inv, fields={"kind": "agent", "name": "mcnemar", "state": "succeeded"})
    rs = g.create(author="stats", type="result", inv=inv, fields={"summary": "McNemar test on the same 1,000 items.", "values": values},
                  links=[{"rel": "produced", "from": r["id"]}])
    c = g.create(author="stats", type="claim", inv=inv,
                 fields={"statement": "The McNemar test on the 1,000 shared items gave the value in the result.",
                         "scope": "The 1,000 shared items."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs["id"]}])
    return g, inv, c["code"], rs["code"]


def _sig(g, text, inv):
    return [f["level"] for f in g.check_text(text, inv)["findings"] if f["code"] == "REPORT_SIGNIFICANCE_UNBACKED"]


@pytest.mark.parametrize("sentence", [
    "Model A is *not* significantly more accurate than model B.",
    "Model A is **not** significantly more accurate than model B.",
    "There is no statistically significant difference between A and B.",
    "The evidence does not support a statistically significant advantage for A.",
    "The test did not reach statistical significance, so A is not significantly better.",
])
def test_a_denial_is_a_warning_not_a_refusal(sentence):
    g, inv, _, _ = _record({"chi2": {"value": 3.0}})
    assert _sig(g, sentence, inv) in (["warning"], [])
    assert g.check_text(sentence, inv)["errors"] == 0


@pytest.mark.parametrize("sentence", [
    "A is significantly more accurate than B.",
    "A is not only significantly more accurate than B, it is cheaper.",
    "A is not worse, and it is significantly more accurate than B.",
    "B is not significantly cheaper, but A is significantly more accurate.",
])
def test_an_assertion_is_still_refused(sentence):
    g, inv, _, _ = _record({"chi2": {"value": 3.0}})
    assert _sig(g, sentence, inv) == ["error"]


@pytest.mark.parametrize("key", ["p", "p_value", "pvalue", "p-value", "p_exact", "p_two"])
def test_a_named_p_value_carries_the_test(key):
    g, inv, cl, rs = _record({key: {"value": 0.03}})
    assert _sig(g, f"A is significantly more accurate than B ({rs}).", inv) == []       # the result itself
    assert _sig(g, f"A is significantly more accurate than B ({cl}).", inv) == []       # the claim that rests on it


def test_a_claim_without_a_test_does_not_carry_one():
    g, inv, cl, rs = _record({"pct_a": {"value": 90.0}, "pairs": {"value": 322}, "chi2": {"value": 3.0}})
    assert _sig(g, f"A is significantly more accurate than B ({cl}).", inv) == ["error"]
    assert _sig(g, f"A is significantly more accurate than B ({rs}).", inv) == ["error"]
