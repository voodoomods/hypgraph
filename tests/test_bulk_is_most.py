""""The bulk of" says most; "a lone" or "a sole" exception is a single one.

Found in the telephone showcase (2026-11-17): "The bulk of tests succeeded" on 5 of 6 and "Parser crushed the test
suite, slipping on a lone case" on 7 of 8, both blind-labelled true, were refused as bare plurals with nothing to say
how many. "The bulk" hedges as "most" does, so it is also held to what "most" is held to: not on an even split, and
not on its own side of a count under half ("finishing the bulk on time" on 3 of 6 is false, as "most" is).
"""
import pytest

from hypgraph import Graph, GraphError

M = "malformed files rejected with a clear error"
B = "files over 1 GB parsed within the time budget"
T = "test suites passed"
R = "real-world files parsed without error"


def codes(statement, k, n, what):
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How does the parser do?",
                                            scope="One run of each suite; large means over 1 GB.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The counts from one run.",
                            values={"c": {"k": k, "n": n}})["id"]
    try:
        g.author("writer").add("claim", inv, kind="finding", statement=statement,
                               scope="This test campaign, one run of each; large means over 1 GB.",
                               measurements=[{"name": what, "result": r, "key": "c", "k": k, "n": n}],
                               links=[{"rel": "supports", "from": r, "why": "The campaign count."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("statement, k, n, what", [
    ("The bulk of suites passed, underscoring robust yet improvable coverage.", 5, 6, T),
    ("Malformed files? The parser flagged the bulk, delivering clear error messages.", 21, 22, M),
    ("Large files met deadlines, with the bulk arriving on schedule.", 3, 5, B),
    ("Parser crushed the test suites, slipping on a lone case.", 7, 8, T),
    ("Malformed files were rejected with clear errors, bar a lone straggler.", 21, 22, M),
    ("Malformed files were rejected with clear errors, a sole file aside.", 21, 22, M),
    ("Real-world files parsed flawlessly, with a lone exception.", 60, 61, R),  # as "a single exception" is
    ("Real-world files parsed flawlessly, with a sole exception.", 60, 61, R),
    ("The bulk of large files missed the time budget.", 2, 6, B),             # the other side of the count
    ("Large files arrive in bulk, and 4 of 6 finished on time.", 4, 6, B),    # not "the bulk"
])
def test_the_bulk_and_a_lone_exception_say_how_many(statement, k, n, what):
    assert "COUNT_CONTRADICTS" not in codes(statement, k, n, what)


@pytest.mark.parametrize("statement, k, n, what", [
    ("It delivered massive files on schedule, finishing the bulk on time.", 3, 6, B),   # an even split
    ("The bulk of large files finished on time.", 3, 6, B),
    ("The bulk of large files finished within the time budget.", 2, 6, B),              # under half, its own side
    ("Malformed files were rejected with clear errors.", 21, 22, M),                    # nothing says how many
    ("Real-world files parsed flawlessly, without a lone exception.", 60, 61, R),      # denied, not admitted
])
def test_the_bulk_is_held_to_what_most_is(statement, k, n, what):
    assert "COUNT_CONTRADICTS" in codes(statement, k, n, what)
