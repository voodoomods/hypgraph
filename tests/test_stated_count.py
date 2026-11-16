"""A count the statement states is held to the record's own count.

Found by the /play/ challenges (2026-11-15): on 23 of 24 malformed files rejected, "All 24 malformed files were
rejected with a clear error" and "The parser caught 24 of 24 malformed files" went in. Every number in them is
accounted for (24 is the bound n), so nothing compared the stated 24 of 24 with the bound 23 of 24. On the corpus of
real records the check moves three live claims, each "all 6 tests pass" bound to a result of 3 of 6 passed; the
exclusions below are the false refusals its first drafts made there.
"""
import pytest

from hypgraph import Graph, GraphError

SCOPE = "This test campaign, one run of each."
WHAT = "malformed files rejected with a clear error"


def write(statement, values=None, names=None):
    values = values or {"count": {"k": 23, "n": 24}}
    names = names or {"count": WHAT}
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How well does the parser handle bad input?",
                                             scope="One run of each test suite and file set.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The campaign counts.",
                            values=values)["id"]
    meas = [{"name": names.get(key, key), "result": r, "key": key, **v} for key, v in values.items()]
    return g.author("writer").add(
        "claim", inv, kind="finding", statement=statement, scope=SCOPE, measurements=meas,
        links=[{"rel": "supports", "from": r, "why": "The campaign counts this sentence reports."}])


def codes(statement, **kw):
    try:
        write(statement, **kw)
    except GraphError as e:
        return [p["code"] for p in e.problems]
    return []


@pytest.mark.parametrize("statement", [
    "All 24 malformed files were rejected with a clear error.",
    "The parser caught 24 of 24 malformed files.",
    "Each of the 24 malformed files was rejected with a clear error.",
    "Every one of the 24 malformed files was rejected.",
    "The parser rejected 21 of 24 malformed files.",
])
def test_a_stated_count_the_record_contradicts_is_refused(statement):
    assert "COUNT_CONTRADICTS" in codes(statement)


def test_the_message_names_both_counts():
    with pytest.raises(GraphError) as e:
        write("The parser caught 24 of 24 malformed files.")
    p = [x for x in e.value.problems if x["code"] == "COUNT_CONTRADICTS"][0]
    assert "says 24 of 24" in p["message"] and "23 of 24" in p["message"] and p["words"] == ["24 of 24"]


@pytest.mark.parametrize("statement", [
    "23 of 24 malformed files were rejected with a clear error.",
    "The parser rejected 23 out of the 24 malformed files.",
    "1 of 24 malformed files parsed without an error.",            # the other side of the count
    "One of the 24 malformed files parsed without an error.",
    "Twenty-three of 24 malformed files were rejected.",
    "Across all 24 malformed files, 23 were rejected with a clear error.",   # "all 24" is the set
    "All 24 malformed files were run; 23 were rejected with a clear error.",
    "Not all 24 malformed files were rejected.",
    "In run 3 of 24 the parser rejected the file; 23 of 24 were rejected.",  # a label
])
def test_a_count_that_fits_or_isnt_a_count_goes_in(statement):
    assert "COUNT_CONTRADICTS" not in codes(statement)


def test_a_stated_k_that_is_another_bound_number_is_left_alone():
    # 66 of 400 rows overlap: 66 is the n of the overlap accuracy, not a wrong count of correct rows
    values = {"correct": {"k": 295, "n": 400}, "acc_overlap": {"k": 65, "n": 66}}
    s = "66 of 400 validation rows duplicate training text, where the classifier is correct on 65 of 66."
    assert "COUNT_CONTRADICTS" not in codes(s, values=values, names={"correct": "correct"})


def test_n_of_n_on_a_bound_total_is_left_alone():
    values = {"n_lines": {"value": 24}, "count": {"k": 23, "n": 24}}
    assert "COUNT_CONTRADICTS" not in codes("The objects in 24 of 24 lines have an id key.", values=values)


def test_a_sentence_that_states_the_record_count_may_count_something_else():
    s = "23 of 24 malformed files were rejected; 24 of 24 were logged."
    assert "COUNT_CONTRADICTS" not in codes(s)


def test_two_different_counts_over_one_n_are_left_alone():
    values = {"acc_a": {"k": 812, "n": 950}, "acc_b": {"k": 779, "n": 950}}
    s = "950 of 950 item ids are unique, so A and B are compared on 950 paired items."
    assert "COUNT_CONTRADICTS" not in codes(s, values=values)


def test_a_part_of_a_total_kept_as_a_count_is_left_alone():
    values = {"n_with": {"k": 1564, "n": 1564}}
    s = "Among users who used the feature, 311 of 1564 users converted."
    assert "COUNT_CONTRADICTS" not in codes(s, values=values, names={"n_with": "n users with feature"})


def test_membership_is_not_a_count():
    values = {"beat": {"k": 0, "n": 20}}
    s = "The in-sample winner is one of 20 settings tested, none of which beat buy and hold."
    assert "COUNT_CONTRADICTS" not in codes(s, values=values, names={"beat": "settings beating buy and hold"})
