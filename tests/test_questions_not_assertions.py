"""0.4.2: a question is not an assertion. From the first real HypSwarm mixed-swarm run: the lead headed a report
section with the question it was answering and the report was refused three times for 'significantly'."""
from hypgraph import Graph, Policy
from hypgraph import language as L


def test_interrogatives_assert_nothing():
    assert L.asserted(L.SIGNIFICANCE, "Is A significantly more accurate than B?") == []
    assert L.asserted(L.SIGNIFICANCE, "**Q2 — Is A significantly more accurate than B at the two-sided 0.05 level?**") == []
    assert L.asserted(L.ABSOLUTE, "Does it never fail?") == []
    assert L.asserted(L.SIGNIFICANCE, "A is significantly more accurate than B.") == ["significantly"]
    assert L.interrogative("Is it so?\"") and not L.interrogative("It is so.")


def _record():
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.create(author="h", type="investigation", fields={"title": "Does A beat B.", "objective": "Compare A and B on the same items."})["id"]
    q = g.create(author="h", type="question", inv=inv, code="Q2",
                 fields={"text": "Is A significantly more accurate than B (two-sided, 0.05)?"})["id"]
    r = g.create(author="stats", type="run", inv=inv, fields={"kind": "agent", "name": "mcnemar", "state": "succeeded"})
    rs = g.create(author="stats", type="result", inv=inv, fields={"summary": "Compared A and B on the same 1,000 items.",
                                                                  "values": {"a": {"k": 900, "n": 1000}, "b": {"k": 800, "n": 1000}}},
                  links=[{"rel": "produced", "from": r["id"]}])
    c = g.create(author="stats", type="claim", inv=inv, fields={"statement": "A is right on 900 of 1000 items and B on 800 of 1000.",
                                                                "scope": "The 1,000 shared items."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs["id"]}])
    g.review(author="critic", target=c["id"], verdict="checked", method="Recounted both columns from the file.", notes="The counts hold and the claim says what the result says.")
    return g, inv, c["code"]


def test_a_report_may_quote_the_question_it_answers():
    g, inv, cl = _record()
    text = ("## Q2 — Is A significantly more accurate than B at the two-sided 0.05 level?\n\n"
            f"A is right on 900 of 1000 items and B on 800 of 1000 ({cl}).\n\n"
            "The question 'Is A significantly more accurate than B (two-sided, 0.05)?' is what this section answers.\n")
    r = g.check_text(text, inv)
    assert not [f for f in r["findings"] if f["code"] == "REPORT_SIGNIFICANCE_UNBACKED"], r["findings"]
    assert r["ok"]
    # the assertion itself is still caught, and an unknown code in a question heading is still an unknown code
    bad = g.check_text("A is significantly more accurate than B.", inv)
    assert any(f["code"] == "REPORT_SIGNIFICANCE_UNBACKED" and f["level"] == "error" for f in bad["findings"])
    unk = g.check_text("## Is CL99 significantly better?", inv)
    assert any(f["code"] == "REPORT_UNKNOWN_CODE" for f in unk["findings"])
