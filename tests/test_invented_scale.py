"""A size the record doesn't hold: "dozens of runs", "countless test runs", "a dozen trials".

Found in the telephone showcase (2026-11-17): "No crashes emerged in countless test runs" and "In our initial 10
trials across dozens of test suites" went in on 0 of 10 test suites in which the parser crashed, "Across a dozen
trials" on 14 encodings. A reader takes the claim to rest on far more than was counted. Read on the counted set or its
runs / trials / tests, when every count and number bound to the claim is below the least the word can mean.
"""
import pytest

from hypgraph import Graph, GraphError

C = "test suites in which the parser crashed"
E = "text encodings read correctly"
R = "real-world files parsed without error"


def codes(statement, k, n, what, value=None):
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How does the parser do?", scope="One run of each suite.")["id"]
    values = {"c": {"k": k, "n": n}}
    if value is not None:
        values["v"] = value
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The counts from one run.",
                            values=values)["id"]
    ms = [{"name": what, "result": r, "key": "c", "k": k, "n": n}]
    if value is not None:
        ms.append({"name": "runs of the whole campaign", "result": r, "key": "v", "value": value})
    try:
        g.author("writer").add("claim", inv, kind="finding", statement=statement,
                               scope="This test campaign, one run of each.", measurements=ms,
                               links=[{"rel": "supports", "from": r, "why": "The campaign count."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("statement, k, n, what", [
    ("No crashes emerged in countless test runs, underscoring its stability.", 0, 10, C),
    ("Unbroken performance: no crashes observed across dozens of runs.", 0, 10, C),
    ("Across dozens of test suites, the parser never crashed.", 0, 10, C),
    ("No crashes in a dozen tests, so stability is solid.", 0, 10, C),
    ("Across a dozen trials, the parser read diverse text encodings.", 14, 14, E),
    ("Hundreds of real-world files parsed cleanly, nearly all of them.", 58, 60, R),
])
def test_a_size_beyond_every_count_is_refused(statement, k, n, what):
    assert "COUNT_CONTRADICTS" in codes(statement, k, n, what)


@pytest.mark.parametrize("statement, k, n, what", [
    ("Out of dozens of real files, it parsed almost all flawlessly.", 52, 54, R),    # 54 is dozens
    ("We tested numerous common text encodings and the parser handled each.", 14, 14, E),   # no size named
    ("Over a dozen encodings were read correctly, 14 of 14.", 14, 14, E),          # a bound, and true
    ("About a dozen test suites ran without a crash.", 0, 10, C),                  # rough
    ("A dozen encodings were read correctly.", 12, 12, E),
    ("No crashes, after countless hours of tuning.", 0, 10, C),                    # not the counted set
    ("Not dozens of runs, just ten, and no crashes.", 0, 10, C),
    ("Two dozen test suites would tell us more; none of the 10 crashed.", 0, 10, C),
])
def test_a_size_the_record_holds_or_a_size_of_something_else_stands(statement, k, n, what):
    assert "COUNT_CONTRADICTS" not in codes(statement, k, n, what)


def test_a_bound_number_that_large_backs_the_size():
    assert "COUNT_CONTRADICTS" not in codes("No crashes across thousands of runs.", 0, 10, C, value=3200)
