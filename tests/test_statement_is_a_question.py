"""A claim that is a question says nothing. On a BC-250 run of the bug-fix challenge (2026-11-07) a seat wrote the
question's own text as a claim, "Which tests in test_semver.py fail on the original semver.py, and what causes each
failure?", linked it as superseding its right answer, and the reviewer checked it: the question settled on a question."""
from __future__ import annotations

import pytest

from hypgraph import Graph, GraphError, Policy

QUESTION = "Which tests in test_semver.py fail on the original semver.py, and what causes each failure?"
ANSWER = ("test_minor_numeric, test_prerelease_before_release and test_newest fail on the original semver.py, because "
          "compare() orders numeric parts as strings.")


def _record():
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.create(author="a", type="investigation", fields={
        "title": "semver", "objective": "Fix the version comparison.", "profile": "software@2"})["id"]
    q = g.create(author="a", type="question", inv=inv, fields={"text": QUESTION})["id"]
    run = g.create(author="a", type="run", inv=inv, fields={"kind": "agent", "name": "pytest on the original",
                                                            "state": "succeeded", "config": {"source": "pytest -q _base"}})["id"]
    res = g.create(author="a", type="result", inv=inv, fields={
        "summary": "Three of six tests fail on the original.", "values": {"tests_passed": {"k": 3, "n": 6}}},
        links=[{"rel": "produced", "from": run}])["id"]
    return g, inv, q, res


def _claim(g, inv, q, res, statement):
    return g.create(author="a", type="claim", inv=inv, fields={
        "statement": statement, "scope": "The six tests in test_semver.py, run on the kept copy of semver.py."},
        links=[{"rel": "answers", "to": q}, {"rel": "supports", "from": res, "why": "the run shows which tests fail"}])


@pytest.mark.parametrize("statement", [QUESTION, "Does the original fail test_newest?", "Which tests fail? "])
def test_a_claim_that_is_a_question_is_refused(statement):
    g, inv, q, res = _record()
    with pytest.raises(GraphError, match="STATEMENT_EMPTY") as e:
        _claim(g, inv, q, res, statement)
    assert "is a question" in str(e.value)


@pytest.mark.parametrize("statement", [ANSWER, f"Which tests fail on the original semver.py? {ANSWER}", "Why? Because compare() orders numeric parts as strings."])
def test_an_answer_passes_with_or_without_the_question_before_it(statement):
    g, inv, q, res = _record()
    assert _claim(g, inv, q, res, statement)["id"]


def test_the_refusal_names_what_to_write():
    g, inv, q, res = _record()
    with pytest.raises(GraphError, match="write the answer to it"):
        _claim(g, inv, q, res, QUESTION)
