"""What a count is of, what its key says it compared, and comparisons joined by both "and" and "or" (audit of 0.7.25,
HG-025-01..03).

A count of the cargo route is a count of cargo routes, singular or plural, and says nothing about passenger routes. A
count the lab keyed `route_speed_above_26` is a count of speeds, whatever the claimant names it. And "every route is
longer than 10 km and shorter than 30 km or shorter than 6 km" groups its parts in a way the words don't settle, so no
count of one part shows it true or false."""
import pytest

from hypgraph import Graph, GraphError, Policy

SCOPE = "The three surveyed routes, of 5, 20 and 25 km, against 6, 10, 26 and 30 km marks."


def record(values):
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.author("curator").investigation("Routes", "Which surveyed route is shortest?")["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Measured the surveyed routes.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="Route counts.",
                values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    return g, inv, r


def write(g, inv, statement, links, meas=(), scope=SCOPE):
    return g.author("a").add("claim", inv, statement=statement, scope=scope, measurements=list(meas),
                             links=[{"rel": "supports", "from": x, "why": "Cited for the claim."} for x in links])


def codes(e) -> list[str]:
    return [p["code"] for p in e.value.problems]


def count(r, key, name, k, n=3):
    return {"name": name, "result": r, "key": key, "k": k, "n": n}


def typed(k, op=">", figure=26):
    return {"k": k, "n": 3, "figure": figure, "op": op}


PASSENGER = ["No passenger route is longer than 26 km among the 3 routes.",
             "Nothing is longer than 26 km among the 3 passenger routes."]


@pytest.mark.parametrize("statement", PASSENGER)
@pytest.mark.parametrize("key,name", [("cargo_route_longer_26", "cargo route longer than 26 km"),
                                      ("cargo_longer_26", "cargo longer than 26 km"),
                                      ("longer_26", "cargo route longer than 26 km")])
def test_a_count_of_another_kind_in_the_singular_does_not_back_the_claim(statement, key, name):
    """HG-025-01: kinds were read only before a plural, so none of 3 "cargo route longer than 26 km" backed a claim
    about passenger routes while the passenger count was 1 of 3."""
    g, inv, r = record({key: typed(0), "passenger_routes_longer_26": typed(1)})
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, key, name, 0)])
    assert codes(e) == ["ABSOLUTE_WITHOUT_COUNT"]


@pytest.mark.parametrize("statement", PASSENGER)
@pytest.mark.parametrize("key,name", [("passenger_route_longer_26", "passenger route longer than 26 km"),
                                      ("passenger_routes_longer_26", "routes longer than 26 km"),
                                      ("longer_26", "route longer than 26 km")])
def test_a_count_of_the_same_kind_or_of_all_backs_it(statement, key, name):
    g, inv, r = record({key: typed(0)})
    write(g, inv, statement, [r], [count(r, key, name, 0)])


def test_a_count_of_another_kind_in_the_singular_does_not_contradict():
    g, inv, r = record({"cargo_route_longer_26": typed(1)})
    with pytest.raises(GraphError) as e:
        write(g, inv, PASSENGER[0], [r], [count(r, "cargo_route_longer_26", "cargo route longer than 26 km", 1)])
    assert codes(e) == ["ABSOLUTE_WITHOUT_COUNT"]


@pytest.mark.parametrize("statement", ["Nothing is longer than 26 km among the 3 routes.",
                                       "No route is longer than 26 km among the 3 routes."])
@pytest.mark.parametrize("key", ["route_speed_above_26", "speed_above_26", "routes_faster_than_26"])
def test_a_name_cannot_turn_a_count_of_one_property_into_another(statement, key):
    """HG-025-02: a count the lab keyed for speed, named "routes longer than 26 km" by the claimant, backed a claim
    about length. The key says what was counted; a name that compares something else is refused."""
    g, inv, r = record({key: typed(0)})
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, key, "routes longer than 26 km", 0)])
    assert "MEASUREMENT_MISMATCH" in codes(e) and "COUNT_CONTRADICTS" not in codes(e)


def test_a_name_cannot_turn_a_count_of_one_kind_into_another():
    g, inv, r = record({"cargo_longer_26": typed(0), "passenger_longer_26": typed(1)})
    with pytest.raises(GraphError) as e:
        write(g, inv, PASSENGER[0], [r], [count(r, "cargo_longer_26", "passenger routes longer than 26 km", 0)])
    assert "MEASUREMENT_MISMATCH" in codes(e)


@pytest.mark.parametrize("key,name", [("routes_longer_26", "routes longer than 26 km"),
                                      ("route_length_above_26", "route length above 26 km"),
                                      ("passenger_routes_longer_26", "routes longer than 26 km")])
def test_a_name_that_keeps_what_the_key_counted_is_accepted(key, name):
    g, inv, r = record({key: typed(0)})
    write(g, inv, PASSENGER[0], [r], [count(r, key, name, 0)])


MIXED = {"longer_10": typed(2, ">", 10), "shorter_30": typed(3, "<", 30), "shorter_6": typed(1, "<", 6)}
PARTS = [("longer_10", "routes longer than 10 km", 2), ("shorter_30", "routes shorter than 30 km", 3),
         ("shorter_6", "routes shorter than 6 km", 1)]


@pytest.mark.parametrize("statement", [
    "Every route is longer than 10 km and shorter than 30 km or shorter than 6 km among the 3 routes.",
    "Every route is shorter than 6 km or longer than 10 km and shorter than 30 km among the 3 routes.",
    "No route is longer than 10 km and shorter than 30 km or shorter than 6 km among the 3 routes."])
def test_and_with_or_in_one_clause_is_left_unresolved(statement):
    """HG-025-03: with both "and" and "or" the parts were checked one by one, so routes of 5, 20 and 25 km, which make
    the first two statements true, gave COUNT_CONTRADICTS. No count of a part settles such a clause either way."""
    g, inv, r = record(MIXED)
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, k, nm, kk) for k, nm, kk in PARTS])
    assert codes(e) == ["ABSOLUTE_WITHOUT_COUNT"]


def test_and_or_or_alone_still_reads_as_before():
    g, inv, r = record(MIXED)
    with pytest.raises(GraphError) as e:
        write(g, inv, "Every route is longer than 10 km and shorter than 30 km among the 3 routes.", [r],
              [count(r, k, nm, kk) for k, nm, kk in PARTS[:2]])
    assert codes(e) == ["COUNT_CONTRADICTS"]
    write(g, inv, "Every route is shorter than 30 km or shorter than 6 km among the 3 routes.", [r],
          [count(r, "shorter_30", "routes shorter than 30 km", 3)])


@pytest.mark.parametrize("k", [0, 2])
def test_what_was_compared_is_not_what_was_counted(k):
    """"fitting selections worth more" counts selections; "worth" says what they were compared on. The count speaks to
    "nothing worth more fits" either way, as it did before."""
    g, inv, r = record({"fitting_selections_worth_more": {"k": k, "n": 8, "figure": 120, "op": ">"}})
    stmt = "The highest total value that fits within 37 kg is 120; nothing worth more fits among the 8 selections."
    m = count(r, "fitting_selections_worth_more", "fitting selections worth more", k, 8)
    if k:
        with pytest.raises(GraphError) as e:
            write(g, inv, stmt, [r], [m], scope="All 8 selections of the inventory within 37 kg.")
        assert "COUNT_CONTRADICTS" in codes(e)
    else:
        write(g, inv, stmt, [r], [m], scope="All 8 selections of the inventory within 37 kg.")


def test_a_bound_in_the_statement_is_not_what_it_is_about():
    """"the limit is at most 49 kg" bounds the claim; it doesn't make a count of selections a count of something else."""
    g, inv, r = record({"fitting_selections_worth_more": {"k": 3, "n": 8, "figure": 117, "op": ">"}})
    with pytest.raises(GraphError) as e:
        write(g, inv, "The weight limit is at most 49 kg, and the highest total value that fits within it is 117.",
              [r], [count(r, "fitting_selections_worth_more", "fitting selections worth more", 3, 8)],
              scope="All 8 selections of the inventory within 49 kg.")
    assert "COUNT_CONTRADICTS" in codes(e)
