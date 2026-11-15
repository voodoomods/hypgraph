"""A word that says more than half, on a count that is exactly half.

Found in the say-no-more-than-the-data showcase run 3 (gpt-oss-20b on the BC-250 boards, 2026-11-15): "Parsed a
majority of large files within the time budget" went in on 3 of 6 files over 1 GB parsed within the time budget.
"""
import pytest

from hypgraph import Graph, GraphError

SCOPE = "This test campaign, one run of each."


def write(k, n, statement, what="files over 1 GB parsed within the time budget"):
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How well does the parser handle large input?",
                                             scope="One run of each test suite and file set.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary=f"{k} of {n} {what}.",
                            values={"count": {"k": k, "n": n}})["id"]
    return g.author("writer").add(
        "claim", inv, kind="finding", statement=statement, scope=SCOPE,
        measurements=[{"name": what, "result": r, "key": "count", "k": k, "n": n}],
        links=[{"rel": "supports", "from": r, "why": "The campaign count this headline reports."}])


@pytest.mark.parametrize("statement", [
    "Parsed a majority of large files within the time budget.",
    "Most large files parsed within the time budget.",
    "More than half of the large files parsed within the time budget.",
    "Nearly all large files parsed within the time budget."])
def test_a_majority_word_on_an_even_split_is_refused(statement):
    with pytest.raises(GraphError) as e:
        write(3, 6, statement)
    p = next(p for p in e.value.problems if p["code"] == "COUNT_CONTRADICTS")
    assert "an even split" in p["message"] and p["fix"] == "say '3 of 6', or 'half'"


@pytest.mark.parametrize("k,n,statement", [
    (4, 6, "Most large files parsed within the time budget."),
    # the other side: 2 of 20 parsed, so most did not
    (2, 20, "Most large files missed the time budget."),
    (3, 6, "Half of the large files parsed within the time budget."),
    (3, 6, "3 of 6 large files parsed within the time budget, not most."),
    (3, 6, "The parser is at most twice as slow on large files: 3 of 6 parsed within the time budget."),
    (3, 6, "The most demanding files: 3 of 6 large files parsed within the time budget.")])
def test_a_majority_word_that_fits_goes_in(k, n, statement):
    assert write(k, n, statement)["id"]
