"""Which counts bear on a claim, and what two joined comparisons rule out (audit of 0.7.24, HG-024-01..04).

A count of routes processed says nothing about routes longer than 26 km. A count of cargo routes says nothing about
passenger routes, nor about every route. "No route is shorter than 20 km and longer than 30 km" rules out a route that
is both, so a route shorter than 20 doesn't show it false; "every route is longer than 10 km and shorter than 30 km" is
false if either fails. And a count made with ">=" is not one of routes "longer than" its figure."""
import pytest

from hypgraph import Graph, GraphError, Policy

SCOPE = "The three surveyed routes, of 18, 25 and 35 km, against 10, 20, 26 and 30 km marks."


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


@pytest.mark.parametrize("statement,k", [("Nothing is longer than 26 km among the 3 routes.", 3),
                                         ("No route is longer than 26 km among the 3 routes.", 3),
                                         ("Every route is longer than 26 km among the 3 routes.", 0),
                                         ("Every route is longer than 26 km among the 3 routes.", 3)])
def test_a_count_with_no_comparison_does_not_back_one(statement, k):
    """HG-024-01: with no comparison of its own, a count of none or all backed any claim that ruled one out."""
    g, inv, r = record({"processed": {"k": k, "n": 3}})
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, "processed", "routes processed", k)])
    assert codes(e) == ["ABSOLUTE_WITHOUT_COUNT"]


def test_a_claim_with_no_comparison_reads_a_plain_count_as_before():
    g, inv, r = record({"failed": {"k": 0, "n": 3}})
    write(g, inv, "No route ever failed to load among the 3 routes.", [r],
          [count(r, "failed", "routes that failed to load", 0)])


@pytest.mark.parametrize("statement", ["No passenger route is longer than 26 km among the 3 routes.",
                                       "Nothing is longer than 26 km among the 3 passenger routes.",
                                       "No route is longer than 26 km among the 3 routes."])
def test_a_count_of_another_kind_does_not_back_the_claim(statement):
    """HG-024-02: none of 3 cargo routes longer backed a claim about passenger routes (1 of 3 of them longer), and about
    every route, because the count and the claim shared the word "route"."""
    g, inv, r = record({"cargo_longer_26": typed(0), "passenger_longer_26": typed(1)})
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, "cargo_longer_26", "cargo routes longer than 26 km", 0)])
    assert codes(e) == ["ABSOLUTE_WITHOUT_COUNT"]


@pytest.mark.parametrize("name", ["passenger routes longer than 26 km", "routes longer than 26 km"])
def test_a_count_of_the_same_kind_or_all_of_them_backs_it(name):
    g, inv, r = record({"longer_26": typed(0)})
    write(g, inv, "No passenger route is longer than 26 km among the 3 routes.", [r],
          [count(r, "longer_26", name, 0)])


def test_a_count_of_one_kind_still_refutes_a_claim_about_all():
    g, inv, r = record({"cargo_longer_26": typed(1)})
    with pytest.raises(GraphError) as e:
        write(g, inv, "No route is longer than 26 km among the 3 routes.", [r],
              [count(r, "cargo_longer_26", "cargo routes longer than 26 km", 1)])
    assert codes(e) == ["COUNT_CONTRADICTS"]


def test_two_kinds_named_apart_do_not_contradict():
    g, inv, r = record({"cargo_longer_26": typed(1)})
    with pytest.raises(GraphError) as e:
        write(g, inv, "No passenger route is longer than 26 km among the 3 routes.", [r],
              [count(r, "cargo_longer_26", "cargo routes longer than 26 km", 1)])
    assert codes(e) == ["ABSOLUTE_WITHOUT_COUNT"]


BOTH = {"shorter_20": typed(1, "<", 20), "longer_30": typed(1, ">", 30), "shorter_10": typed(0, "<", 10),
        "longer_10": typed(3, ">", 10), "shorter_30": typed(2, "<", 30)}


def test_no_route_both_shorter_and_longer_is_not_refuted_by_either():
    """HG-024-03: "and" ended the clause, so a route shorter than 20 refuted a claim that rules out only a route both
    shorter than 20 and longer than 30. With no count of both, it's unresolved."""
    g, inv, r = record(BOTH)
    with pytest.raises(GraphError) as e:
        write(g, inv, "No route is shorter than 20 km and longer than 30 km among the 3 routes.", [r],
              [count(r, "shorter_20", "routes shorter than 20 km", 1),
               count(r, "longer_30", "routes longer than 30 km", 1)])
    assert codes(e) == ["ABSOLUTE_WITHOUT_COUNT"]


def test_none_of_one_part_backs_none_of_both():
    g, inv, r = record(BOTH)
    write(g, inv, "No route is shorter than 10 km and longer than 30 km among the 3 routes.", [r],
          [count(r, "shorter_10", "routes shorter than 10 km", 0)])


def test_no_route_shorter_or_longer_is_refuted_by_either():
    g, inv, r = record(BOTH)
    with pytest.raises(GraphError) as e:
        write(g, inv, "No route is shorter than 20 km or longer than 30 km among the 3 routes.", [r],
              [count(r, "shorter_20", "routes shorter than 20 km", 1),
               count(r, "longer_30", "routes longer than 30 km", 1)])
    assert "COUNT_CONTRADICTS" in codes(e)


def test_every_route_between_two_marks_needs_both():
    """The same split left "shorter than 30 km" unread after "every route is longer than 10 km and": the claim went in
    with 2 of 3 shorter than 30 bound beside it."""
    g, inv, r = record(BOTH)
    statement = "Every route is longer than 10 km and shorter than 30 km among the 3 routes."
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, "longer_10", "routes longer than 10 km", 3)])
    assert codes(e) == ["ABSOLUTE_WITHOUT_COUNT"]
    with pytest.raises(GraphError) as e:
        write(g, inv, statement, [r], [count(r, "longer_10", "routes longer than 10 km", 3),
                                       count(r, "shorter_30", "routes shorter than 30 km", 2)])
    assert codes(e) == ["COUNT_CONTRADICTS"]


def test_and_with_a_subject_of_its_own_still_ends_the_clause():
    g, inv, r = record(BOTH)
    with pytest.raises(GraphError) as e:
        write(g, inv, "No route is shorter than 20 km and the register lists 3 routes.", [r],
              [count(r, "shorter_20", "routes shorter than 20 km", 1)])
    assert codes(e) == ["COUNT_CONTRADICTS"]


@pytest.mark.parametrize("op,name", [(">=", "routes longer than 26 km"), (">", "routes 26 km or longer"),
                                     (">", "routes at least 26 km"), ("<", "routes no longer than 26 km")])
def test_a_name_must_say_the_boundary_the_count_used(op, name):
    """HG-024-04: only a name pointing the other way was caught; "longer than 26" on a ">=" count went in."""
    g, inv, r = record({"routes_26": typed(2, op)})
    with pytest.raises(GraphError) as e:
        write(g, inv, "2 of 3 routes are at least 26 km long.", [r], [count(r, "routes_26", name, 2)])
    assert "MEASUREMENT_MISMATCH" in codes(e)


@pytest.mark.parametrize("op,name", [(">=", "routes at least 26 km"), (">=", "routes 26 km or longer"),
                                     (">", "routes longer than 26 km"), ("<=", "routes no longer than 26 km")])
def test_a_name_that_says_the_boundary_is_accepted(op, name):
    g, inv, r = record({"routes_26": typed(2, op)})
    write(g, inv, "2 of 3 routes are at least 26 km long.", [r], [count(r, "routes_26", name, 2)])
