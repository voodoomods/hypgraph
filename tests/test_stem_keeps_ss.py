"""A word that ends in -ss keeps its s: "pass" meets "passes" and "passed".

The stemmer took the last s off "pass" as if it were a plural, so a count named "tests passed" was never read as
being about "all tests pass". Found in the "it's fixed" showcase's dev round (2026-11-18): on a CI run of 20 of 20,
"PAY-1432 is fixed and all tests pass." was refused as leaning on a count of something else."""
import pytest

from hypgraph import Graph, language as L
from hypgraph.graph import GraphError


@pytest.mark.parametrize("words", [("pass", "passes", "passed", "passing"), ("class", "classes"),
                                   ("process", "processes", "processed"), ("miss", "misses", "missed"),
                                   ("cross", "crosses", "crossed"), ("loss", "losses")])
def test_a_word_in_ss_and_its_inflections_meet(words):
    assert len({frozenset(L.content_words(w)) for w in words}) == 1, [L.content_words(w) for w in words]


def test_plurals_still_lose_their_s():
    assert L.content_words("routes") == L.content_words("route")
    assert L.content_words("values") == L.content_words("value")
    assert L.content_words("fits") == L.content_words("fitting")


def codes(k: int, n: int, statement: str) -> list[str]:
    g = Graph()
    cur, lab = g.author("curator"), g.author("lab")
    scope = "The repository's test suite, run by CI on the head commit."
    inv = cur.investigation("Does the suite pass on this branch?", "Report what CI found.", scope=scope)["id"]
    run = lab.add("run", inv, kind="lab", state="succeeded", name="CI: pytest.")
    res = lab.add("result", inv, kind="computed", outcome="positive", summary=f"{k} of {n} tests passed.",
                  values={"tests_passed": {"k": k, "n": n}}, links=[{"rel": "produced", "from": run["id"]}])["id"]
    try:
        g.author("dev").add("claim", inv, kind="finding", statement=statement, scope=scope,
                            measurements=[{"key": "tests_passed", "name": "tests passed", "k": k, "n": n,
                                           "result": res}],
                            links=[{"rel": "supports", "from": res, "why": "CI's run of the suite."}])
        return []
    except GraphError as e:
        return [p["code"] for p in e.problems]


def test_all_tests_pass_meets_a_count_of_tests_passed():
    # the count is read as about the statement: contradicted when it has exceptions, and named when it has none
    assert codes(17, 18, "All tests now pass.") == ["COUNT_CONTRADICTS"]
    assert codes(20, 20, "All tests pass.") == ["ABSOLUTE_UNDERPOWERED"]
    assert codes(20, 20, "All 20 tests pass.") == []
