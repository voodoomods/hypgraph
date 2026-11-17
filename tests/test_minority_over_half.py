"""'Only a few' of the counted set on a count over half: the mirror of 'most' on a count under half.

Found pooling every blind-labelled line of the telephone showcase (2026-11-17, 5,175 sentences): "Only a few of our
biggest files finish on time" on 4 of 7 files over 1 GB parsed within the time budget, "Only a handful of massive
files kept pace" on 3 of 5. The labellers split (11 false, 7 true); the labelling guide now calls it false, since a
reader takes most of them to have failed and most passed. Either side of a count may be the one meant, so the word
stands when its clause speaks of the rest, and exactly half isn't over half.
"""
import pytest

from hypgraph import Graph, GraphError

B = "files over 1 GB parsed within the time budget"
T = "test suites passed"
R = "real-world files parsed without error"


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
    ("Only a few of our biggest files finish on time, so speed upgrades are underway.", 4, 7, B),
    ("Only a handful of massive files kept pace with the time budget.", 3, 5, B),
    ("Large files challenge the parser's speed; only a few finish on schedule.", 4, 7, B),
    ("Big files test it, yet only a select few finish on schedule.", 3, 5, B),
    ("Few large files finished within the time budget.", 5, 7, B),
    ("A minority of test suites passed.", 6, 8, T),
    ("The parser struggles with the largest files, finishing only a few on time.", 4, 7, B),  # still says few
])
def test_a_shrinking_word_on_a_count_over_half_is_refused(statement, k, n, what):
    assert "COUNT_CONTRADICTS" in codes(statement, k, n, what)


@pytest.mark.parametrize("statement, k, n, what", [
    ("Only a few of the massive files finished on time.", 3, 6, B),           # exactly half
    ("Only a few large files finished on time.", 2, 7, B),                     # a minority
    ("A few large files finished on time.", 4, 7, B),                          # plain 'a few'
    ("Only a few large files exceeded the time limit.", 4, 7, B),              # the other side
    ("Only a handful of massive files challenged the time limits.", 3, 5, B),
    ("A minority of large files hit time limits, so tweaks are ahead.", 4, 7, B),
    ("From a wide array of real-world files, only a handful slipped.", 65, 67, R),
    ("All but a handful of real-world files parsed without error.", 64, 67, R),
    ("Most large files finished on time, with only a few delays.", 5, 7, B),   # another noun
    ("Not only a few large files finished on time.", 5, 7, B),                 # negated
])
def test_half_minorities_plain_a_few_the_other_side_and_negation_pass(statement, k, n, what):
    assert "COUNT_CONTRADICTS" not in codes(statement, k, n, what)
