"""A count of containers named by what they hold, or as one container.

Found in the telephone showcase (2026-11-17): on 7 of 8 test suites passed, "The parser smashed test suites" was
refused while "The parser smashed tests" went in, and "Tests triumph" on 6 of 7 and "Parser dominated the test suite"
on 5 of 6 went in too. The counted noun is compared by content words, and "test" is a stop word, so "tests" named
nothing. A suite passes when every test in it does: the tests all passing, or the suite as one being beaten, says every
suite passed. The rules that read the bare plural (subject or deed object) now read these names too, with the same
guards: a stated count, a quantifier or an exception keeps it.
"""
import pytest

from hypgraph import Graph, GraphError

T = "test suites passed"
R = "real-world files parsed without error"
C = "test suites in which the parser crashed"


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
    ("The parser smashed tests, delivering blazingly fast performance.", 7, 8, T),
    ("Tests triumph, so our coverage stands unshakable.", 6, 7, T),
    ("Parser dominated the test suite, coverage solid, fine-tuning pending.", 5, 6, T),
    ("Our parser conquered the entire suite.", 8, 9, T),
    ("The parser smashed test suites.", 9, 10, T),                       # as before
])
def test_the_set_by_another_name_is_read_as_every_one(statement, k, n, what):
    assert "COUNT_CONTRADICTS" in codes(statement, k, n, what)


@pytest.mark.parametrize("statement, k, n, what", [
    ("Parser dominated the test suite, only a single glitch left.", 9, 10, T),     # the exception is said
    ("The parser crushed the test suite, with only one hiccup.", 7, 8, T),
    ("Parser crushes tests with near-perfect coverage.", 8, 9, T),                 # hedged
    ("Parser nailed 8 of 9 tests, almost flawless.", 8, 9, T),                     # the count is said
    ("Almost every test passed, just one small hiccup.", 8, 9, T),
    ("We tackled a suite of tests and conquered most of them.", 5, 6, T),          # a suite, not the suite
    ("The parser smashed tests, delivering blazingly fast performance.", 8, 8, T),  # every one did
    ("Tests never crashed the parser.", 0, 10, C),                                 # no exception to hide
    ("The parser smashed tests.", 58, 60, R),                                      # files aren't containers
])
def test_a_named_count_a_hedge_or_a_whole_count_stands(statement, k, n, what):
    assert "COUNT_CONTRADICTS" not in codes(statement, k, n, what)
