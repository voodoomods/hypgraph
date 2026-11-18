"""The bare-plural guard stands down only for words that say how many, or hedge.

A bare plural of the counted set ("Malformed files were rejected") on a count with exceptions is refused unless
something in the sentence says how many or hedges. Three things were taken as doing that and don't (telephone
showcase run4, 2026-11-17, each line blind-labelled false and accepted):
- "each" ("Malformed files were caught with pinpoint accuracy, each flagged by clear, precise error messages");
- "no" ("Malformed files were cleanly rejected—no slip-through");
- a number that belongs to the count's own name ("Large, over-1-GB files were parsed within the time budget", on
  files over 1 GB parsed within the time budget).
Over every blind-labelled telephone line (13,130), a sentence whose only such word was "each" or "no" was false 9
times and true 0.
"""
import pytest

from hypgraph import Graph, GraphError

M = "malformed files rejected with a clear error"
B = "files over 1 GB parsed within the time budget"
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
    # "each" doesn't say fewer than all
    ("Malformed files were caught with pinpoint accuracy, each flagged by clear, precise error messages.", 21, 22, M),
    ("Malformed files are rejected swiftly, each with crystal-clear error messages.", 18, 19, M),
    ("It swept through real-world files, hitting each with laser-sharp precision.", 65, 67, R),
    # nor does "no"
    ("Malformed files were cleanly rejected—no slip-through.", 21, 22, M),
    ("Malformed files were cleanly rejected, with no slip through.", 21, 22, M),
    ("Malformed files were rejected with clear errors, no exceptions.", 21, 22, M),
    ("Malformed files were rejected with clear errors, without exception.", 21, 22, M),
    # a number from the count's own name says what was counted
    ("Large, over-1-GB files were parsed within the time budget.", 3, 6, B),
    ("Large files over 1 GB finished on schedule, showing the parser scales effortlessly.", 4, 6, B),
])
def test_words_that_do_not_say_how_many_leave_the_bare_plural_refused(statement, k, n, what):
    assert "COUNT_CONTRADICTS" in codes(statement, k, n, what)


@pytest.mark.parametrize("statement, k, n, what", [
    # a stated count, with "each" or "no" beside it
    ("21 of 22 malformed files were caught, each accompanied by clear, precise error messages.", 21, 22, M),
    ("Malformed files were correctly rejected in 23 of 24 cases, each accompanied by a clear error message.", 23, 24, M),
    ("63 of 64 real-world files parsed with no hiccups.", 63, 64, R),
    # another hedge
    ("It rejected most malformed files, each flagged with crystal-clear errors.", 21, 22, M),
    ("Nearly all malformed files met clear rejection—bad data, no drama.", 19, 20, M),
    ("Malformed files were rejected with clear errors, with one exception.", 21, 22, M),
    ("Malformed files were rejected with clear errors, with few exceptions.", 21, 22, M),
    # the count's own k and n say how many, even when the name holds the same number
    ("Large files over 1 GB: 1 of 4 parsed within the time budget.", 1, 4, B),
    # a number the name doesn't hold
    ("Large files were parsed within the time budget in 3 runs.", 3, 6, B),
    # every one did
    ("Malformed files were cleanly rejected—no slip-through.", 22, 22, M),
    ("Large, over-1-GB files were parsed within the time budget.", 6, 6, B),
])
def test_a_count_or_a_hedge_still_stands_the_guard_down(statement, k, n, what):
    assert "COUNT_CONTRADICTS" not in codes(statement, k, n, what)
