"""Which way a count points, and what a unit says (audit of 0.7.22, HG-022-01..05).

A count of routes longer than 26 km says nothing against "the shortest route is 26 km", and a count of none shorter
than 26 doesn't back "nothing is longer than 26". A source's unit of record is compared only with the same thing's
unit of record: not with another thing that shares a word, and not with a quantity converted into another unit."""
import pytest

from hypgraph import Graph, GraphError, Policy

ROUTES = "The three surveyed routes, of 26, 31 and 35 km."


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


def write(g, inv, statement, links, meas=(), scope=ROUTES, who="a"):
    return g.author(who).add("claim", inv, statement=statement, scope=scope, measurements=list(meas),
                             links=[{"rel": "supports", "from": x, "why": "Cited for the claim."} for x in links])


def codes(e) -> list[str]:
    return [p["code"] for p in e.value.problems]


def count(r, key, name, k, n=3):
    return {"name": name, "result": r, "key": key, "k": k, "n": n}


SHORTEST = {"name": "shortest route km", "key": "shortest_km", "value": 26}


@pytest.mark.parametrize("typed", [{}, {"figure": 26}, {"figure": 26, "op": ">"}])
def test_a_count_the_other_way_does_not_refute_a_true_extreme(typed):
    """HG-022-01: the true "the shortest route is 26 km", with 2 of 3 routes longer than 26 bound, was refused as
    COUNT_CONTRADICTS: the count matched the figure, and nothing asked which way it pointed."""
    g, inv, r = record({"longer_than_26": {"k": 2, "n": 3, **typed}, "shortest_km": 26})
    write(g, inv, "The shortest route is 26 km.", [r],
          [count(r, "longer_than_26", "routes longer than 26 km", 2), {**SHORTEST, "result": r}])
    assert "a" not in g.conduct(inv)
    # the count the claim needs still decides: 1 of 3 shorter than 31 refutes "the shortest is 31"
    g, inv, r = record({"shorter_than_31": {"k": 1, "n": 3, **({"figure": 31} if typed else {})}, "x_km": 31})
    with pytest.raises(GraphError) as e:
        write(g, inv, "The shortest route is 31 km.", [r],
              [count(r, "shorter_than_31", "routes shorter than 31 km", 1),
               {"name": "route km", "result": r, "key": "x_km", "value": 31}])
    assert "COUNT_CONTRADICTS" in codes(e)


@pytest.mark.parametrize("typed", [{}, {"figure": 26}, {"figure": 26, "op": "<"}])
@pytest.mark.parametrize("statement", ["Nothing is longer than 26 km among the 3 routes.",
                                       "No route is longer than 26 km among the 3 routes."])
def test_a_count_the_other_way_does_not_back_an_absolute(typed, statement):
    """HG-022-02: none of 3 routes shorter than 26 backed "nothing is longer than 26 km among the 3 routes". It is
    the wrong count: the claim goes in only with a count of routes longer than 26, which here finds 2."""
    g, inv, r = record({"shorter_than_26": {"k": 0, "n": 3, **typed}, "longer_than_26": {"k": 2, "n": 3}})
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, "shorter_than_26", "routes shorter than 26 km", 0)])
    assert "ABSOLUTE_WITHOUT_COUNT" in codes(e) and "COUNT_CONTRADICTS" not in codes(e)
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, "shorter_than_26", "routes shorter than 26 km", 0),
                                       count(r, "longer_than_26", "routes longer than 26 km", 2)])
    assert "COUNT_CONTRADICTS" in codes(e)
    # the true absolute with its own count goes in
    write(g, inv, "No route is shorter than 26 km among the 3 routes.", [r],
          [count(r, "shorter_than_26", "routes shorter than 26 km", 0)])


def test_a_no_inside_a_phrase_is_not_an_absolute():
    """"no route is longer" opens its clause with "no"; "routes that visit no town twice" only describes them. A true
    count sentence with that phrase in it goes in."""
    g, inv, r = record({"shorter_than_31": {"k": 1, "n": 3}})
    write(g, inv, "One of the 3 routes that visit no town twice is shorter than 31 km.", [r],
          [count(r, "shorter_than_31", "routes shorter than 31 km", 1)])
    assert "a" not in g.conduct(inv)


def test_a_stated_direction_decides_and_a_label_cannot_flip_it():
    """A result can state which way its count points ({"op": "<"}); a measurement whose name points the other way is
    refused. Without one, a name and key that point opposite ways can widen what the count refutes, never what it
    backs."""
    g, inv, r = record({"shorter_than_26": {"k": 0, "n": 3, "figure": 26, "op": "<"},
                        "beyond_26": {"k": 0, "n": 3}})
    with pytest.raises(GraphError) as e:
        write(g, inv, "Nothing is longer than 26 km among the 3 routes.", [r],
              [count(r, "shorter_than_26", "routes longer than 26 km", 0)])
    assert "MEASUREMENT_MISMATCH" in codes(e) and "<" in str(e.value)
    # untyped: the name says longer, the key says shorter: a zero can't back "nothing longer"
    g, inv, r = record({"shorter_than_26": {"k": 0, "n": 3}})
    with pytest.raises(GraphError) as e:
        write(g, inv, "Nothing is longer than 26 km among the 3 routes.", [r],
              [count(r, "shorter_than_26", "routes longer than 26 km", 0)])
    assert "ABSOLUTE_WITHOUT_COUNT" in codes(e)


def test_the_direction_of_words():
    from hypgraph.checks import _claim_directions, _count_directions, _opposed
    d = lambda name, key="x", rv=None: _count_directions({"name": name, "key": key}, rv or {})   # noqa: E731
    assert d("routes longer than 26 km") == {("long", 1)}
    assert d("routes shorter than 26 km") == {("long", -1)}
    assert d("fitting selections worth more than 93") == {("", 1)}
    assert d("fitting selections worth exactly 93") == set()
    assert d("x", rv={"op": "<="}) == {("", -1)}
    assert d("routes longer than 26 km", "shorter_than_26") == {("long", 1), ("long", -1)}
    assert _claim_directions("The shortest route is 26 km.") == {("long", -1)}
    assert _claim_directions("The highest total value that fits is 93.") == {("", 1)}
    assert _claim_directions("Nothing worth more than 93 fits.", "Nothing") == {("", 1)}
    assert _opposed(("long", 1), ("long", -1)) and _opposed(("", 1), ("long", -1))
    assert not _opposed(("long", 1), ("fast", -1)) and not _opposed(("", 1), ("", 1))


UNITS = "Every recorded parcel weight is in kilograms, not pounds."


@pytest.mark.parametrize("statement", ["Recorded parcel weights use pounds.",
                                       "The recorded parcel weights are given in pounds.",
                                       "Recorded parcel weights were logged in pounds.",
                                       "The recorded parcel weights are expressed in pounds."])
def test_a_unit_of_record_said_without_a_copula(statement):
    """HG-022-03: only "is / are / was / were" said a unit, so "recorded parcel weights use pounds" went in beside
    the kilograms note. A short, fixed list of verbs that state a unit of record is read too."""
    g, inv, _r = record({"x": {"k": 0, "n": 3}})
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [source(g, inv, UNITS)], scope="The parcel register.")
    assert "SOURCE_CONTRADICTS" in codes(e)


@pytest.mark.parametrize("passage", [
    "Shipping weights are recorded in kilograms; passenger weights are recorded in pounds.",
    "Passenger weights are recorded in pounds; shipping weights are recorded in kilograms.",
    "Shipping weights are recorded in kilograms."])
def test_another_thing_that_shares_a_word_is_not_contradicted(passage):
    """HG-022-04: "passenger weights" was matched with "shipping weights" on the word "weights", and the true claim
    was refused as going against its source. Two things each named for something the other isn't are two things."""
    g, inv, _r = record({"x": {"k": 0, "n": 3}})
    write(g, inv, "Passenger weights are recorded in pounds.", [source(g, inv, passage)], scope="The register.")
    assert "a" not in g.conduct(inv)
    # the same thing still is: "recorded shipping weights" against shipping weights in kilograms
    with pytest.raises(GraphError) as e:
        write(g, inv, "The recorded shipping weights are in pounds.",
              [source(g, inv, "Shipping weights are recorded in kilograms.")], scope="The register.")
    assert "SOURCE_CONTRADICTS" in codes(e)


@pytest.mark.parametrize("statement", ["The parcel mass is approximately two pounds.",
                                       "The parcel mass is about 2.2 pounds.",
                                       "The parcel mass is a little over two pounds."])
def test_a_quantity_in_another_unit_is_not_a_unit_of_record(statement):
    """HG-022-05: "the parcel mass is about 2.2 pounds", citing "the parcel mass is one kilogram", was refused: a
    quantity converted to another unit was read as a claim about which unit the records use. A unit after a number is
    a quantity; conversions are not checked."""
    g, inv, _r = record({"x": {"k": 0, "n": 3}})
    try:
        write(g, inv, statement, [source(g, inv, "The parcel mass is one kilogram.")],
              scope="One parcel; 1 kg is about 2.2 pounds.")
    except GraphError as e:
        assert "SOURCE_CONTRADICTS" not in [p["code"] for p in e.problems], e.problems
