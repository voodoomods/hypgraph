"""'Half of the counted set' on a count that isn't half.

Found pooling every blind-labelled line of the telephone showcase (2026-11-17, 5,175 sentences): "Half of the massive
files met the deadline" on 2 of 6 and "Only half of the massive files met deadlines" on 2 of 5 went in, both labelled
false. Either side of a count is half only when the count is, so no side has to be worked out. "half" stood on a count
that isn't half in 4 lines, all false, and on an even split in 15.
"""
import pytest

from hypgraph import Graph, GraphError

B = "files over 1 GB parsed within the time budget"
T = "test suites passed"


def codes(statement, k, n, what):
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How does the parser do?", scope="One run of each suite.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The counts from one run.",
                            values={"c": {"k": k, "n": n}})["id"]
    try:
        g.author("writer").add("claim", inv, kind="finding", statement=statement,
                               scope="This test campaign, one run of each.",
                               measurements=[{"name": what, "result": r, "key": "c", "k": k, "n": n}],
                               links=[{"rel": "supports", "from": r, "why": "The campaign count."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("statement, k, n, what", [
    ("Half of the massive files met the deadline, so big-file speed is still a hurdle.", 2, 6, B),
    ("Only half of the massive files met deadlines, signaling a performance gap.", 2, 5, B),
    ("Half the large files finished on time.", 4, 6, B),                      # the other side is not half either
    ("The parser passed half of its test suites.", 7, 10, T),
])
def test_half_on_a_count_that_is_not_half_is_refused(statement, k, n, what):
    assert "COUNT_CONTRADICTS" in codes(statement, k, n, what)


@pytest.mark.parametrize("statement, k, n, what", [
    ("Half of the massive files met the deadline.", 3, 6, B),                # an even split
    ("Half of the test suites passed.", 99, 200, T),                         # rounds to 50%
    ("About half of the large files finished on time.", 2, 5, B),
    ("Fewer than half of the large files finished on time.", 2, 5, B),
    ("More than half of the large files finished on time.", 4, 6, B),
    ("Half or more of the large files finished on time.", 4, 6, B),
    ("Not half of the large files finished on time.", 2, 6, B),
    ("Parse time on large files was cut in half.", 2, 6, B),                 # not a share of the set
    ("In the first half of the run, two of six large files finished on time.", 2, 6, B),
    ("Half of them finished on time.", 2, 6, B),                             # no counted noun
])
def test_even_splits_qualifiers_negation_and_other_halves_pass(statement, k, n, what):
    assert "COUNT_CONTRADICTS" not in codes(statement, k, n, what)
