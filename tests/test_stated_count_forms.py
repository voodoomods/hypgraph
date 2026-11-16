"""A stated count is read in its other written forms: "24/24", and in words, compounds whole.

Found by a second /play/ attack round (2026-11-15): on 23 of 24 malformed files rejected, "The parser rejected
malformed files 24/24", "Twenty-four of twenty-four malformed files were rejected" and "The parser rejected all
twenty-four malformed files" went in while "24 of 24" and "all 24" were refused. On the corpus of real records
(3,237) 182 statements with a slash count and 57 with a count in words reach the comparison (their n is a bound
count's n) and none moves; its first draft refused one, "154 users per arm; 22/154 in A vs 31/154 in B", which read
the 22 as an arm label across the semicolon.
"""
import pytest

from hypgraph import Graph, GraphError

SCOPE = "This test campaign, one run of each."


def codes(statement, values=None, names=None):
    values = values or {"count": {"k": 23, "n": 24}}
    names = names or {"count": "malformed files rejected with a clear error"}
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How well does the parser handle bad input?",
                                             scope="One run of each test suite and file set.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The campaign counts.",
                            values=values)["id"]
    meas = [{"name": names.get(key, key), "result": r, "key": key, **v} for key, v in values.items()]
    try:
        g.author("writer").add("claim", inv, kind="finding", statement=statement, scope=SCOPE, measurements=meas,
                               links=[{"rel": "supports", "from": r, "why": "The campaign counts."}])
    except GraphError as e:
        return [p["code"] for p in e.problems]
    return []


@pytest.mark.parametrize("statement", [
    "The parser rejected malformed files 24/24.",
    "The parser rejected malformed files 24 / 24.",
    "Malformed files rejected: 21/24.",
    "Twenty-four of twenty-four malformed files were rejected.",
    "Twenty‑four of twenty‑four malformed files were rejected.",          # U+2011, as gpt-oss writes it
    "The parser rejected all twenty-four malformed files.",
    "The parser rejected twenty-one out of the twenty-four malformed files.",
])
def test_a_stated_count_in_another_form_is_held_to_the_record(statement):
    assert "COUNT_CONTRADICTS" in codes(statement)


@pytest.mark.parametrize("statement", [
    "The parser rejected malformed files 23/24.",
    "1/24 malformed files parsed without an error.",
    "Twenty-three of twenty-four malformed files were rejected.",
    "One of twenty-four malformed files parsed without an error.",
    "The parser rejected 23 of all twenty-four malformed files.",
])
def test_the_record_s_count_in_another_form_goes_in(statement):
    assert "COUNT_CONTRADICTS" not in codes(statement)


def test_a_count_stated_beside_its_arm_is_no_label():
    # the corpus claim its first draft refused: the record binds A's count only
    values = {"k_A": {"k": 22, "n": 154}, "p_value": {"value": 0.174}}
    s = "The test is inconclusive (154 users per arm; 22/154 in A vs 31/154 in B; p=0.174)."
    assert "COUNT_CONTRADICTS" not in codes(s, values, {"k_A": "k_A"})


@pytest.mark.parametrize("statement", [
    "On 11/24/2026 the parser rejected 23 of 24 malformed files.",       # a date
    "The parser in src/24/24 rejected 23 of 24 malformed files.",         # a path
    "Run 24/24 of the campaign: the parser rejected 23 of 24 malformed files.",   # a label
])
def test_a_slash_that_is_no_count_is_not_read_as_one(statement):
    assert "COUNT_CONTRADICTS" not in codes(statement)
