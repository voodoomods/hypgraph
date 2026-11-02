"""An extreme that quotes its own counterexample is still false.

"The shortest route is 30 km, since a count finds 1 of 77 shorter than 30 km" states the very count that refutes it.
A stated count used to exempt an extreme whenever its clause said "k of n ... than", so the counterexample, quoted,
made the claim pass. A count about a figure of the statement's own ("the shortest is 21 km; 1 of 77 are shorter than
26 km") is still not an exception to the extreme. Invariants: quoting the refuting count never turns a refusal into an
acceptance, with or without the figure on the result; the honest correction that quotes it is accepted; a count about
another figure stays out of the way."""
import pytest

from hypgraph import Graph, GraphError, Policy

SCOPE = "Every simple route between the two towns in the register (77 routes), distances in km."
WHY = "The route counts bear on the claim."


def outcome(values, statement, meas):
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.author("curator").investigation("Routes", "What is the shortest route between the two towns?")["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Counted the routes.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="Counts of the routes.",
                values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    try:
        g.author("a").add("claim", inv, statement=statement, scope=SCOPE,
                          measurements=[{**m, "result": r} for m in meas],
                          links=[{"rel": "supports", "from": r, "why": WHY}])
        return []
    except GraphError as e:
        return [p["code"] for p in e.problems] or [str(e)]


def shorter(k, figure=None, n=77):
    v = {"k": k, "n": n}
    return v if figure is None else {**v, "figure": figure, "op": "<"}


def case(figure):
    """A route measured at 30 km and the instrument's count of routes shorter than it: 1 of 77. Named as the
    instrument names it, with no figure in the name; the figure on the result or not."""
    values = {"route_length": 30.0, "shorter_routes_connecting": shorter(1, figure)}
    meas = [{"key": "route_length", "name": "route_length", "value": 30.0},
            {"key": "shorter_routes_connecting", "name": "shorter routes connecting", "k": 1, "n": 77}]
    return values, meas


FIGURE = pytest.mark.parametrize("figure", [None, 30], ids=["no figure on the result", "figure on the result"])

LIES = ["The shortest route is 30 km, since a count of every route that visits no town twice finds 1 of 77 shorter "
        "than 30 km.",
        "The shortest route is 30 km: 1 of 77 routes are shorter than 30 km.",
        "The shortest route between the towns is 30 km, and 1 of 77 routes is shorter than 30 km."]


@FIGURE
@pytest.mark.parametrize("s", LIES)
def test_an_extreme_quoting_its_own_counterexample_is_refused(s, figure):
    assert "COUNT_CONTRADICTS" in outcome(*case(figure)[:1], s, case(figure)[1]), s


@FIGURE
def test_the_same_extreme_without_the_quote_is_refused(figure):
    assert "COUNT_CONTRADICTS" in outcome(case(figure)[0], "The shortest route is 30 km.", case(figure)[1])


@FIGURE
@pytest.mark.parametrize("s", ["The shortest route is not 30 km, since a count of every route finds 1 of 77 shorter "
                               "than 30 km.",
                               "30 km is not the shortest route: 1 of 77 routes are shorter than 30 km."])
def test_the_correction_that_quotes_the_count_is_accepted(s, figure):
    assert outcome(case(figure)[0], s, case(figure)[1]) == [], s


def test_a_count_about_another_figure_is_not_an_exception_to_the_extreme():
    """The count beyond 26 the statement gives says nothing against "the shortest is 21"; the count at 21 backs it."""
    s = "The shortest route is 21 km; 1 of 77 routes are shorter than 26 km."
    values = {"route_length": 21.0, "shorter_than_21": shorter(0, 21), "shorter_than_26": shorter(1, 26)}
    meas = [{"key": "route_length", "name": "route_length", "value": 21.0},
            {"key": "shorter_than_21", "name": "routes shorter than 21 km", "k": 0, "n": 77},
            {"key": "shorter_than_26", "name": "routes shorter than 26 km", "k": 1, "n": 77}]
    assert "COUNT_CONTRADICTS" not in outcome(values, s, meas)


# Two readings the quoted-count exemption used to hide: once a quoted count no longer excuses an extreme, an honest
# sentence must not be read as claiming one.

@FIGURE
@pytest.mark.parametrize("s", ["The shortest route is therefore not 30 km: 1 of 77 routes are shorter than 30 km.",
                               "1 of 77 routes are shorter than 30 km, so 30 km is therefore not the shortest route.",
                               "A count finds 1 of 77 routes shorter than 30 km; the shortest route is thus not 30 km."])
def test_a_denial_with_an_adverb_is_a_correction(s, figure):
    assert outcome(case(figure)[0], s, case(figure)[1]) == [], s


@FIGURE
@pytest.mark.parametrize("s", ["The shortest route is at most 30 km: 1 of 77 routes are shorter than 30 km.",
                               "The shortest route is 30 km or less; 1 of 77 routes are shorter than 30 km."])
def test_a_bound_in_the_extremes_own_direction_is_not_its_value(s, figure):
    """At most 30 km, with a route shorter than 30 found, is true: the bound is not a claim that 30 is the shortest."""
    assert "COUNT_CONTRADICTS" not in outcome(case(figure)[0], s, case(figure)[1]), s


@FIGURE
def test_a_bound_the_other_way_still_claims_its_figure(figure):
    """At least 30 km, with a route shorter than 30 found, is false."""
    s = "The shortest route is at least 30 km."
    assert "COUNT_CONTRADICTS" in outcome(case(figure)[0], s, case(figure)[1])
