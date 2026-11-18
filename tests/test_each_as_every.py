""""Each" on the counted set, with nothing to say how many.

Found in the telephone showcase (2026-11-17): "The parser flagged each malformed file" on 19 of 20 and "Malformed
files? Each one triggered a crystal-clear error alert" on 23 of 24 went in, while the same lines with "every" were
refused. Most "each" is distributive and honest ("rejected nearly every bad file, each with a clear error", "11 trades,
each incurring a 0.1% fee"): reading every "each" as "every" refused 193 items of the corpus of real records. So it is
read only as the determiner of the counted set, and only when nothing else in the sentence says how many.
"""
import pytest

from hypgraph import Graph, GraphError

M = "malformed files rejected with a clear error"
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
    ("The parser flagged each malformed file, delivering crystal-clear errors.", 19, 20, M),
    ("Malformed files? Each one triggered a crystal-clear error alert.", 23, 24, M),
    ("Each malformed file was rejected with a clear error.", 23, 24, M),
    ("The parser swept through the real-world file set, nailing each file with pinpoint accuracy.", 65, 67, R),
])
def test_each_on_the_counted_set_with_exceptions_is_refused(statement, k, n, what):
    assert "COUNT_CONTRADICTS" in codes(statement, k, n, what)


@pytest.mark.parametrize("statement, k, n, what", [
    ("Each malformed file was rejected with a clear error.", 24, 24, M),                # every one was
    ("Rejected nearly every malformed file, each with a clear error.", 23, 24, M),      # each of those rejected
    ("It rejected most malformed files. Each one got a clear error.", 23, 24, M),
    ("The parser checked each malformed file; 23 of 24 were rejected.", 23, 24, M),     # the count is said
    ("We ran each suite once and the parser rejected malformed input cleanly.", 23, 24, M),  # not the counted set
    ("The two parsers checked each other's output on malformed files.", 23, 24, M),
    ("Each widow was paid four shillings a week.", 23, 24, M),
    ("Not each malformed file was rejected with a clear error.", 23, 24, M),
])
def test_distributive_counted_or_other_each_stands(statement, k, n, what):
    assert "COUNT_CONTRADICTS" not in codes(statement, k, n, what)
