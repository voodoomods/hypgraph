"""A word that says more than half of the counted set, said its own way, on a count under half.

Found in the telephone showcase's run3 (gpt-oss-20b on the BC-250 boards, 2026-11-16): "We met deadlines on most large
files" went in twice on 3 of 7 files over 1 GB parsed within the time budget, blind-labelled false. Either side of a
count may be the one a sentence means, so a clause that says the contrary or negates is left alone.
"""
import pytest

from hypgraph import Graph, GraphError

SCOPE = "This test campaign, one run of each."
TIME = "files over 1 GB parsed within the time budget"
CRASH = "test suites in which the parser crashed"


def write(k, n, statement, what=TIME):
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How well does the parser handle large input?",
                                             scope="One run of each test suite and file set.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary=f"{k} of {n} {what}.",
                            values={"count": {"k": k, "n": n}})["id"]
    return g.author("writer").add(
        "claim", inv, kind="finding", statement=statement, scope=SCOPE,
        measurements=[{"name": what, "result": r, "key": "count", "k": k, "n": n}],
        links=[{"rel": "supports", "from": r, "why": "The campaign count this headline reports."}])


@pytest.mark.parametrize("k,n,statement,phrase", [
    (3, 7, "We met deadlines on most large files, opening the door to faster processing.", "most large files"),
    (3, 7, "Most large files parsed within the time budget.", "most large files"),
    (2, 7, "The parser handled the majority of large files on time.", "the majority of large files"),
    (1, 7, "Nearly all large files cleared the time budget.", "nearly all large files"),
    (3, 7, "Most of the large files finished in time.", "most of the large files"),
])
def test_a_majority_word_on_the_counted_side_under_half_is_refused(k, n, statement, phrase):
    with pytest.raises(GraphError) as e:
        write(k, n, statement)
    p = next(p for p in e.value.problems if p["code"] == "COUNT_CONTRADICTS")
    assert f"'{phrase.lower()}'" in p["message"].lower() and f"{k} of {n}" in p["fix"]


@pytest.mark.parametrize("k,n,statement,what", [
    # the other side, said with a contrary word or a negation
    (2, 7, "Most large files overran the time budget, so big-file performance remains a challenge.", TIME),
    (2, 7, "Most large files missed the time budget.", TIME),
    (3, 7, "Most large files ran too slow for the budget.", TIME),
    (3, 7, "Most large files did not finish within the time budget.", TIME),
    (3, 7, "Most large files fell short of the time budget.", TIME),
    (3, 7, "The parser still pushes its limits on most large files.", TIME),
    # a count put the contrary way: the plain clause is the other side
    (0, 7, "Most test suites ran cleanly.", CRASH),
    (0, 7, "Most test suites finished without a crash.", CRASH),
    # not the counted set
    (2, 7, "While it speeds through most data, the parser is slow on 5 of 7 large files.", TIME),
    # over half, and the stated count itself
    (5, 7, "Most large files parsed within the time budget.", TIME),
    (3, 7, "3 of 7 large files parsed within the time budget; at most 3 of 7.", TIME),
    # a superlative or bound, not a majority
    (3, 7, "The most demanding files: 3 of 7 large files parsed within the time budget.", TIME),
    (3, 7, "Not most large files: 3 of 7 parsed within the time budget.", TIME),
])
def test_a_majority_word_that_fits_goes_in(k, n, statement, what):
    assert write(k, n, statement, what)["id"]


def test_the_honest_line_goes_in():
    assert write(3, 7, "3 of 7 large files met the time budget.")["id"]
