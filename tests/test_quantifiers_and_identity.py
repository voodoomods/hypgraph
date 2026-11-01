"""What a quantifier needs, where a comparison's boundary falls, and which thing a unit is said of (audit of 0.7.23,
HG-023-01..05).

"Nothing is longer than 26 km" needs none of the routes longer than 26; "every route is longer than 26 km" needs all
of them. A count of routes at least 26 km long is not a count of routes longer than 26: the routes of exactly 26 lie
between. Two extremes in one sentence are two claims. And "weights of cargo" and "weights of passengers" are two
things, as a source saying "not in pounds but in kilograms" says kilograms."""
import pytest

from hypgraph import Graph, GraphError, Policy


def record(values):
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.author("curator").investigation("Routes", "Which surveyed route is shortest?")["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Measured the surveyed routes.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="Route counts against 26 km.",
                values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    return g, inv, r


def source(g, inv, passage):
    return g.author("curator").add("source", inv, citation="Records note", passage=passage, kind="primary")["id"]


def write(g, inv, statement, links, meas=(), scope="The three surveyed routes, against a 26 km mark."):
    return g.author("a").add("claim", inv, statement=statement, scope=scope, measurements=list(meas),
                             links=[{"rel": "supports", "from": x, "why": "Cited for the claim."} for x in links])


def codes(e) -> list[str]:
    return [p["code"] for p in e.value.problems]


def count(r, key, name, k, n=3):
    return {"name": name, "result": r, "key": key, "k": k, "n": n}


def typed(k, op=">", figure=26):
    return {"k": k, "n": 3, "figure": figure, "op": op}


LONGER = "routes longer than 26 km"


@pytest.mark.parametrize("stated", [True, False])
@pytest.mark.parametrize("statement,k", [
    ("Nothing is longer than 26 km among the 3 routes.", 3),           # routes of 31, 35, 40
    ("Nothing is longer than 26 km among the 3 routes.", 2),
    ("No route is longer than 26 km among the 3 routes.", 3),
    ("Every route is longer than 26 km among the 3 routes.", 0),       # routes of 20, 22, 24
    ("Every route is longer than 26 km among the 3 routes.", 1),
    ("All 3 routes are always longer than 26 km.", 0)])
def test_a_count_of_the_wrong_extreme_refutes_a_quantifier(stated, statement, k):
    """HG-023-01: any count of none or all backed an absolute. "Nothing" needs none of what it rules out; "every"
    needs all of what it asserts; the other extreme shows the claim false."""
    g, inv, r = record({"longer_26": typed(k) if stated else {"k": k, "n": 3}})
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, "longer_26", LONGER, k)])
    assert "COUNT_CONTRADICTS" in codes(e)


@pytest.mark.parametrize("stated", [True, False])
@pytest.mark.parametrize("statement,k", [
    ("Nothing is longer than 26 km among the 3 routes.", 0),
    ("No route is longer than 26 km among the 3 routes.", 0),
    ("Every route is longer than 26 km among the 3 routes.", 3),
    ("All 3 routes are always longer than 26 km.", 3)])
def test_the_right_extreme_backs_a_quantifier(stated, statement, k):
    g, inv, r = record({"longer_26": typed(k) if stated else {"k": k, "n": 3}})
    write(g, inv, statement, [r], [count(r, "longer_26", LONGER, k)])
    assert "a" not in g.conduct(inv)


def test_every_that_names_the_set_counted_is_not_a_quantifier():
    """"a count of every route finds 1 of 76 shorter than 35 km" says what was counted, not that every route is
    shorter than 35 (the record replay of earlier runs found a correction refused this way)."""
    from hypgraph.checks import _absolute_targets
    stmt = "The shortest route is 25 km; a count of every route finds 1 of 76 shorter than 35 km."
    assert _absolute_targets(stmt, "every") == [(frozenset({35.0}), frozenset({("long", -1, True)}))]
    assert _absolute_targets("Every route is shorter than 35 km.", "Every") == [
        (frozenset({35.0}), frozenset({("long", 1, False)}))]


def test_a_count_whose_direction_is_not_known_is_read_as_before():
    """A count named for nothing that compares ("failures") is still taken at either extreme."""
    g, inv, r = record({"failures": {"k": 0, "n": 3}, "successes": {"k": 3, "n": 3}})
    write(g, inv, "The parser never fails on the 3 routes.", [r], [count(r, "failures", "parser failures", 0)])
    write(g, inv, "The parser always succeeds on the 3 routes.", [r], [count(r, "successes", "parser successes", 3)])
    assert "a" not in g.conduct(inv)


@pytest.mark.parametrize("op,name", [(">=", "routes at least 26 km"), (">=", "routes 26 km or longer"),
                                     (">=", "routes not shorter than 26 km"), (">=", "routes no shorter than 26 km"),
                                     (None, "routes at least 26 km"), (None, "routes 26 km or longer")])
def test_at_least_is_not_longer_than(op, name):
    """HG-023-02: routes of 22, 26 and 26 km. Two are at least 26 and none is longer, so a count of 2 at least 26
    neither refutes "no route is longer than 26 km" nor backs it, and "at least" was read as pointing down."""
    g, inv, r = record({"at_least_26": typed(2, op) if op else {"k": 2, "n": 3}})
    with pytest.raises(GraphError) as e:
        write(g, inv, "No route is longer than 26 km among the 3 routes.", [r], [count(r, "at_least_26", name, 2)])
    assert codes(e) == ["ABSOLUTE_WITHOUT_COUNT"]


@pytest.mark.parametrize("statement", ["No route is 26 km or longer among the 3 routes.",
                                       "Every route is shorter than 26 km among the 3 routes.",
                                       "No route is at least 26 km long among the 3 routes."])
def test_a_strict_count_does_not_back_a_claim_about_the_boundary(statement):
    """Routes of 22, 24 and 26 km: none is longer than 26, one is 26. "No route is 26 km or longer" is false, and a
    count of none longer than 26 can't back it."""
    g, inv, r = record({"longer_26": typed(0)})
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, "longer_26", LONGER, 0)])
    assert "ABSOLUTE_WITHOUT_COUNT" in codes(e)


def test_a_count_that_covers_the_boundary_backs_and_refutes():
    """A count of none at least 26 backs "nothing is longer than 26"; two longer than 26 refute "no route is 26 km or
    longer"."""
    g, inv, r = record({"at_least_26": typed(0, ">="), "longer_26": typed(2)})
    write(g, inv, "Nothing is longer than 26 km among the 3 routes.", [r],
          [count(r, "at_least_26", "routes at least 26 km", 0)])
    with pytest.raises(GraphError) as e:
        write(g, inv, "No route is 26 km or longer among the 3 routes.", [r], [count(r, "longer_26", LONGER, 2)])
    assert "COUNT_CONTRADICTS" in codes(e)


def test_six_comparisons_and_their_boundaries():
    from hypgraph.checks import _comparisons_in, stated_op
    assert {stated_op({"op": o}) for o in ("<", "<=", "=", "!=", ">=", ">", "~")} == {"<", "<=", "=", "!=", ">=", ">",
                                                                                     None}
    assert _comparisons_in("routes longer than 26 km") == {("long", 1, True)}
    assert _comparisons_in("routes at least 26 km") == {("", 1, False)}
    assert _comparisons_in("routes at most 26 km") == {("", -1, False)}
    assert _comparisons_in("routes 26 km or longer") == {("long", 1, False)}
    assert _comparisons_in("routes not shorter than 26 km") == {("long", 1, False)}
    assert _comparisons_in("selections worth no more than 93") == {("", -1, False)}
    assert _comparisons_in("the least costly route") == {("", -1, True)}


@pytest.mark.parametrize("statement", ["The shortest route is 26 km; the longest route is 35 km.",
                                       "The longest route is 35 km and the shortest route is 26 km.",
                                       "The shortest route is 26 km, while the longest is 35 km."])
def test_two_extremes_are_two_claims(statement):
    """HG-023-03: routes of 26, 31 and 35 km. The count of 2 longer than 26 was checked against both extremes at
    once, and the true sentence was refused. Each extreme is checked with its own figure and direction."""
    g, inv, r = record({"longer_26": {"k": 2, "n": 3}, "shortest_km": 26, "longest_km": 35})
    write(g, inv, statement, [r], [count(r, "longer_26", LONGER, 2),
                                   {"name": "shortest route km", "result": r, "key": "shortest_km", "value": 26},
                                   {"name": "longest route km", "result": r, "key": "longest_km", "value": 35}],
          scope="The three surveyed routes, of 26, 31 and 35 km.")
    assert "a" not in g.conduct(inv)
    # a false extreme beside a true one is still refused: 1 of 3 shorter than 31
    g, inv, r = record({"shorter_31": {"k": 1, "n": 3}, "x_km": 31, "longest_km": 35})
    with pytest.raises(GraphError) as e:
        write(g, inv, "The shortest route is 31 km; the longest route is 35 km.", [r],
              [count(r, "shorter_31", "routes shorter than 31 km", 1),
               {"name": "route km", "result": r, "key": "x_km", "value": 31},
               {"name": "longest route km", "result": r, "key": "longest_km", "value": 35}],
              scope="The three surveyed routes, of 26, 31 and 35 km.")
    assert "COUNT_CONTRADICTS" in codes(e)


@pytest.mark.parametrize("cargo,passenger,claim", [
    ("Weights of cargo are recorded in kilograms.", "Weights of passengers are recorded in pounds.",
     "Weights of passengers are recorded in pounds."),
    ("Shipping cargo weights are recorded in kilograms.", "Shipping passenger weights are recorded in pounds.",
     "Shipping passenger weights are recorded in pounds."),
    ("The weights for cargo are in kilograms.", "The weights for passengers are in pounds.",
     "The weights for passengers are in pounds.")])
def test_things_named_apart_are_two_things(cargo, passenger, claim):
    """HG-023-04: "weights of cargo" lost its "of cargo", and "shipping cargo" met "shipping passenger" on one
    shared word. Two subjects that each say something the other doesn't are left apart: unresolved, not false."""
    g, inv, _r = record({"x": {"k": 0, "n": 3}})
    write(g, inv, claim, [source(g, inv, cargo), source(g, inv, passenger)], scope="The manifest.")
    assert "a" not in g.conduct(inv)
    # one that only adds a word to the other is the same thing
    with pytest.raises(GraphError) as e:
        write(g, inv, "The recorded weights of cargo are in pounds.",
              [source(g, inv, "Weights of cargo are recorded in kilograms.")], scope="The manifest.")
    assert "SOURCE_CONTRADICTS" in codes(e)


@pytest.mark.parametrize("passage", ["The parcel weights are not in pounds but in kilograms.",
                                     "The parcel weights are in kilograms rather than pounds.",
                                     "The parcel weights are in kilograms instead of pounds.",
                                     "The parcel weights were never in pounds, but always in kilograms.",
                                     "Pounds were never used; the parcel weights were recorded in kilograms."])
def test_a_contrast_keeps_the_unit_it_asserts(passage):
    """HG-023-05: "not in pounds but in kilograms" lost its kilograms (the clause after "but" had no subject of its
    own), and "kilograms rather than pounds" kept both. A clause with no subject of its own takes its sentence's;
    what follows "rather than" or "instead of" is not asserted."""
    g, inv, _r = record({"x": {"k": 0, "n": 3}})
    with pytest.raises(GraphError) as e:
        write(g, inv, "The parcel weights are in pounds.", [source(g, inv, passage)], scope="The parcel register.")
    assert "SOURCE_CONTRADICTS" in codes(e)
    write(g, inv, "The parcel weights are in kilograms.", [source(g, inv, passage)], scope="The parcel register.",)


def test_a_clause_with_its_own_subject_does_not_take_another():
    """"cargo weights are in kilograms and passenger weights in pounds": the second clause names its own subject, so
    it doesn't say kilograms of passenger weights."""
    g, inv, _r = record({"x": {"k": 0, "n": 3}})
    write(g, inv, "Passenger weights are in pounds.",
          [source(g, inv, "Cargo weights are in kilograms and passenger weights in pounds.")], scope="The manifest.")
    assert "a" not in g.conduct(inv)
