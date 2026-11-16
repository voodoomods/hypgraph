"""A statement that names the counted set by its size is about that set, though it leaves out a kind word.

Found by re-checking the telephone showcase on merged main (2026-11-16): "All 14 encodings handled flawlessly" on 14 of
14 "text encodings read correctly" was refused as a count of something else, because the statement doesn't say
"text" (audit HG-024-02: a count of cargo routes doesn't back a claim about every route). "All 14 encodings" can only
be the 14 that were counted. "Every encoding", "every tested encoding" and "all 14 binary encodings" stay refused, as
does anything else in the clause that reaches past the set. A number in words is no kind either: "all nine
encodings" read "nine" as one, as if it were "cargo".
"""
import pytest

from hypgraph import Graph, GraphError

E = "text encodings read correctly"


def codes(statement, k, n, what=E):
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How does the parser do?", scope="One run of each suite.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The counts from one run.",
                            values={"r3_count": {"k": k, "n": n}})["id"]
    try:
        g.author("writer").add("claim", inv, kind="finding", statement=statement,
                               scope="This test campaign, one run of each.",
                               measurements=[{"name": what, "result": r, "key": "r3_count", "k": k, "n": n}],
                               links=[{"rel": "supports", "from": r, "why": "The campaign count."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("statement, k, n", [
    ("All 14 encodings handled flawlessly—compatibility nailed.", 14, 14),
    ("All 14 encodings handled perfectly.", 14, 14),
    ("All nine encodings handled flawlessly.", 9, 9),
    ("All 9 encodings handled flawlessly.", 9, 9),
    ("Each of the 14 encodings was handled flawlessly.", 14, 14),
    ("The 14 encodings were all handled flawlessly.", 14, 14),
])
def test_the_set_named_by_its_size(statement, k, n):
    assert codes(statement, k, n) == []


@pytest.mark.parametrize("statement, k, n", [
    ("Every encoding was handled flawlessly.", 14, 14),
    ("All encodings handled flawlessly.", 14, 14),
    ("Every tested encoding was handled flawlessly.", 14, 14),
    ("All 14 binary encodings handled flawlessly.", 14, 14),           # another kind
    ("All 20 encodings handled flawlessly.", 14, 14),                  # another size
    ("All 14 encodings handled flawlessly.", 13, 14),                  # an exception
    ("All 14 encodings and every other format handled flawlessly.", 14, 14),
    ("All 14 encodings handled flawlessly, so every encoding works.", 14, 14),
    ("The 14 encodings were handled flawlessly, and so will any encoding be.", 14, 14),
    ("All 14 file formats handled flawlessly.", 14, 14),               # not what was counted
])
def test_still_refused(statement, k, n):
    assert codes(statement, k, n)


def test_a_size_two_sets_share_pins_neither():
    # 3 cargo routes and 3 passenger routes: "all 3 routes" could be either
    g = Graph()
    inv = g.author("curator").investigation("Routes", "Do the routes load?", scope="One load of each route.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="Loads per kind.",
                            values={"cargo_loaded": {"k": 3, "n": 3}, "passenger_loaded": {"k": 2, "n": 3}})["id"]
    with pytest.raises(GraphError) as e:
        g.author("writer").add("claim", inv, kind="finding", statement="All 3 routes loaded flawlessly.",
                               scope="One load of each route.",
                               measurements=[{"name": "cargo routes loaded without error", "result": r,
                                              "key": "cargo_loaded", "k": 3, "n": 3}],
                               links=[{"rel": "supports", "from": r, "why": "Loads."}])
    assert "ABSOLUTE_WITHOUT_COUNT" in {p["code"] for p in e.value.problems}


def test_cargo_routes_still_apart():
    # HG-024-02 unchanged: a count of cargo routes doesn't back every route, with or without a size
    assert codes("No route is longer than 26 km.", 0, 3, "cargo routes longer than 26 km")
    assert codes("All 3 passenger routes are at most 26 km.", 0, 3, "cargo routes longer than 26 km")
