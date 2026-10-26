"""The report check reads the ```answers block: the part of a report a harness scores and a reader copies. Every
answer has to be one a live, fresh claim on the question makes; an answer only old evidence gives is
REPORT_ANSWER_STALE, one nothing gives is REPORT_ANSWER_UNBACKED. Found by the change suite (HypSwarm P3): a report
carrying the pre-change answers passed the check on all 13 records it was tried on, because fenced blocks were
skipped."""
import json

from hypgraph import Graph, Policy

H = "harness"
SHA_A, SHA_B = "a1" * 32, "b2" * 32


def _record():
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={H}))
    inv = g.create(author=H, type="investigation", fields={"title": "Does A beat B on the items?",
                   "objective": "Count each model's correct items and test the difference.",
                   "profile": "scientific@2"})["id"]
    q1 = g.create(author=H, type="question", inv=inv, code="Q1", fields={"text": "How many items is A right on?"})["id"]
    q2 = g.create(author=H, type="question", inv=inv, code="Q2", fields={"text": "How many items is B right on?"})["id"]
    return g, inv, q1, q2


def _file(g, inv, q, sha):
    return g.create(author="analyst", type="artifact", inv=inv, fields={"sha256": sha, "path": "items.csv"},
                    links=[{"rel": "part_of", "to": q}])["id"]


def _count(g, inv, q, data, key, k, significant=None, by="analyst"):
    run = g.create(author=by, type="run", inv=inv, fields={"kind": "agent", "name": "count", "state": "succeeded"},
                   links=[{"rel": "uses", "to": data, "data": {"role": "data"}}])["id"]
    values = {key: {"k": k, "n": 1000}}
    if significant is not None:
        values["significant"] = {"value": significant}
    rs = g.create(author=by, type="result", inv=inv, fields={"summary": f"Counted {key} over items.csv.",
                  "values": values, "outcome": "positive"}, links=[{"rel": "produced", "from": run}])["id"]
    meas = [{"name": key, "key": key, "result": rs, "k": k, "n": 1000}]
    if significant is not None:
        meas.append({"name": "significant", "key": "significant", "result": rs, "value": significant})
    c = g.create(author=by, type="claim", inv=inv,
                 fields={"statement": f"The model is right on {k:,} of the 1,000 items in items.csv.",
                         "scope": "items.csv as registered.", "measurements": meas},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
    return rs, c


def _report(answers, prose="The answers come from the claims on the current file."):
    return f"## Interpretation\n\n{prose}\n\n```answers\n{json.dumps(answers)}\n```\n"


def _codes(g, text, inv):
    return [f["code"] for f in g.check_text(text, inv)["findings"] if f["level"] == "error"]


def _corrected(g, inv, q1, q2):
    """The vendor corrects items.csv after both counts: B's count moves from 789 to 795, A's stays 827."""
    a1 = _file(g, inv, q2, SHA_A)
    _rs_a, c_a = _count(g, inv, q1, a1, "a_correct", 827)
    _rs_b, c_b = _count(g, inv, q2, a1, "b_correct", 789)
    a2 = _file(g, inv, q2, SHA_B)
    g.link(author="analyst", src=a2, rel="supersedes", dst=a1, why="the vendor's corrected file")
    return a2, c_a, c_b


def test_a_stale_answer_is_an_error_and_the_current_one_passes():
    g, inv, q1, q2 = _record()
    a2, _c_a, c_b = _corrected(g, inv, q1, q2)
    assert g.state(c_b).get("stale")
    _count(g, inv, q2, a2, "b_correct", 795, by="stats")
    _count(g, inv, q1, a2, "a_correct", 827, by="stats")
    assert _codes(g, _report({"Q1": {"a_correct": 827}, "Q2": {"b_correct": 795}}), inv) == []
    found = g.check_text(_report({"Q1": {"a_correct": 827}, "Q2": {"b_correct": 789}}), inv)["findings"]
    stale = [f for f in found if f["code"] == "REPORT_ANSWER_STALE"]
    assert len(stale) == 1 and "Q2.b_correct" in stale[0]["excerpt"] and "795" in stale[0]["message"]
    assert stale[0]["line"] == 6                       # the line of the field inside the block (the fence is 5)


def test_an_answer_nothing_claims_is_unbacked():
    g, inv, q1, q2 = _record()
    a1 = _file(g, inv, q2, SHA_A)
    _count(g, inv, q1, a1, "a_correct", 827)
    _count(g, inv, q2, a1, "b_correct", 789)
    assert _codes(g, _report({"Q1": {"a_correct": 830}, "Q2": {"b_correct": 789}}), inv) == ["REPORT_ANSWER_UNBACKED"]
    # rounding to the answer's own precision is the same number; a percent of a fraction is not
    assert _codes(g, _report({"Q1": {"a_correct": 8.27}, "Q2": {"b_correct": 789}}), inv) == ["REPORT_ANSWER_UNBACKED"]


def test_a_question_with_no_claim_or_only_stale_claims_is_flagged():
    g, inv, q1, q2 = _record()
    a1 = _file(g, inv, q2, SHA_A)
    _count(g, inv, q1, a1, "a_correct", 827)
    assert _codes(g, _report({"Q1": {"a_correct": 827}, "Q2": {"b_correct": 789}}), inv) == ["REPORT_ANSWER_UNBACKED"]
    g2, inv2, p1, p2 = _record()
    _corrected(g2, inv2, p1, p2)                        # both claims rest on the superseded file
    found = g2.check_text(_report({"Q2": {"b_correct": 789}}), inv2)["findings"]
    assert [f["code"] for f in found] == ["REPORT_ANSWER_STALE"] and "every claim on it" in found[0]["message"]


def test_true_false_answers_are_checked_by_field():
    g, inv, q1, q2 = _record()
    a1 = _file(g, inv, q2, SHA_A)
    _count(g, inv, q1, a1, "a_correct", 827)
    _count(g, inv, q2, a1, "b_correct", 789, significant=True)
    a2 = _file(g, inv, q2, SHA_B)
    g.link(author="analyst", src=a2, rel="supersedes", dst=a1, why="the vendor's corrected file")
    _count(g, inv, q1, a2, "a_correct", 827, by="stats")
    _count(g, inv, q2, a2, "b_correct", 795, significant=False, by="stats")
    assert _codes(g, _report({"Q1": {"a_correct": 827}, "Q2": {"b_correct": 795, "significant": False}}), inv) == []
    assert _codes(g, _report({"Q1": {"a_correct": 827}, "Q2": {"b_correct": 795, "significant": True}}), inv) == \
        ["REPORT_ANSWER_STALE"]


def test_a_current_claim_naming_the_old_figure_does_not_back_it():
    g, inv, q1, q2 = _record()
    a2, _c_a, c_b = _corrected(g, inv, q1, q2)
    run = g.create(author="analyst", type="run", inv=inv, fields={"kind": "agent", "name": "count", "state": "succeeded"},
                   links=[{"rel": "uses", "to": a2, "data": {"role": "data"}}])["id"]
    rs = g.create(author="analyst", type="result", inv=inv, fields={"summary": "Counted b_correct on the corrected file.",
                  "values": {"b_correct": {"k": 795, "n": 1000}}, "outcome": "positive"},
                  links=[{"rel": "produced", "from": run}])["id"]
    g.create(author="analyst", type="claim", inv=inv, fields={
        "statement": "On the corrected items.csv model B is right on 795 of the 1,000 items.",
        "scope": "items.csv as it stands now; the earlier count of 789 is superseded.",
        "measurements": [{"name": "b_correct", "key": "b_correct", "result": rs, "k": 795, "n": 1000}]},
        links=[{"rel": "answers", "to": q2}, {"rel": "derived_from", "to": rs}, {"rel": "supersedes", "to": c_b}])
    _count(g, inv, q1, a2, "a_correct", 827, by="stats")
    assert _codes(g, _report({"Q1": {"a_correct": 827}, "Q2": {"b_correct": 795}}), inv) == []
    assert _codes(g, _report({"Q1": {"a_correct": 827}, "Q2": {"b_correct": 789}}), inv) == ["REPORT_ANSWER_STALE"]


def test_keys_in_any_case_a_flat_block_and_signs():
    g, inv, q1, q2 = _record()
    a1 = _file(g, inv, q2, SHA_A)
    _count(g, inv, q1, a1, "a_correct", 827)
    _count(g, inv, q2, a1, "b_correct", 789)
    assert _codes(g, _report({"q1": {"a_correct": 827}, "q2": {"b_correct": 789}}), inv) == []
    assert _codes(g, _report({"a_correct": 827, "b_correct": 789}), inv) == []          # checked against the investigation
    assert _codes(g, _report({"a_correct": 827, "b_correct": 788}), inv) == ["REPORT_ANSWER_UNBACKED"]
    assert _codes(g, _report({"q1": {"a_correct": -827}, "q2": {"b_correct": 789}}), inv) == ["REPORT_ANSWER_UNBACKED"]


def test_an_unreadable_block_is_an_error_and_other_code_blocks_are_still_skipped():
    g, inv, q1, q2 = _record()
    a1 = _file(g, inv, q2, SHA_A)
    _count(g, inv, q1, a1, "a_correct", 827)
    assert _codes(g, "Done.\n\n```answers\n{\"Q1\": {\"a_correct\": 827,}}\n```\n", inv) == ["REPORT_ANSWERS_UNREADABLE"]
    assert _codes(g, "Done.\n\n```python\nprint({'a_correct': 999})  # never measured\n```\n", inv) == []
    assert _codes(g, "No answers block: nothing to check here.", inv) == []


def test_the_record_s_own_report_with_its_answers_passes():
    g, inv, q1, q2 = _record()
    a2, _c_a, _c_b = _corrected(g, inv, q1, q2)
    _count(g, inv, q1, a2, "a_correct", 827, by="stats")
    _count(g, inv, q2, a2, "b_correct", 795, by="stats")
    facts = g.report(inv)["markdown"]
    assert _codes(g, facts + "\n\n" + _report({"Q1": {"a_correct": 827}, "Q2": {"b_correct": 795}}), inv) == []
    assert "REPORT_ANSWER_STALE" in _codes(g, facts + "\n\n" + _report({"Q1": {"a_correct": 827},
                                                                         "Q2": {"b_correct": 789}}), inv)


def test_numbers_in_answer_strings_count_and_urls_do_not():
    """From the 2026-10-25 discovery reports: "48,500 megalitres" is an answer at its printed precision (a thousands
    comma is not a clause break), and the source URL beside it is provenance, not a number to back."""
    g, inv, q1, q2 = _record()
    a1 = _file(g, inv, q2, SHA_A)
    _count(g, inv, q1, a1, "a_correct", 827)
    _count(g, inv, q2, a1, "b_correct", 789)
    ok = {"Q1": {"answer": "827 of 1,000 items", "source": "http://127.0.0.1:61728/items.csv"},
          "Q2": {"answer": "789", "source": "data/items.csv", "sha256": "c545bea3" * 8}}
    assert _codes(g, _report(ok), inv) == []
    found = g.check_text(_report({"Q1": {"answer": "830 of 1,000 items"}, "Q2": {"answer": "789"}}), inv)["findings"]
    assert [f["code"] for f in found] == ["REPORT_ANSWER_UNBACKED"] and "Q1.answer: 830" in found[0]["excerpt"]


def test_a_count_backs_its_rate():
    """HypSwarm's scripted reports answer accuracy as a rate (0.812) where the claim says "812 of 1000"."""
    g, inv, q1, q2 = _record()
    a1 = _file(g, inv, q2, SHA_A)
    _count(g, inv, q1, a1, "a_correct", 827)
    _count(g, inv, q2, a1, "b_correct", 789)
    assert _codes(g, _report({"Q1": 0.827, "Q2": {"b_rate": 0.789}}), inv) == []
    assert _codes(g, _report({"Q1": 0.83, "Q2": 0.789}), inv) == []                  # at the precision written
    assert _codes(g, _report({"Q1": 0.828, "Q2": 0.789}), inv) == ["REPORT_ANSWER_UNBACKED"]
