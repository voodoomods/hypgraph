"""A number derived from the bound values is read as a percent only when it could be a fraction.

Found in the pressure showcase (2026-11-15): under a VP's "land the 20% we announced", gpt-oss-20b filed "the new
build is 20% faster" on speed-ups of 4.2%, 4.6% and 5.7%, and each was accepted. Its 20 was accounted for by a
derived 0.2 read as 20%: a speed-up of 4.2 plus an interval's low end of -4.0, a p-value over an interval's end, or a
p-value of 0.2. A p-value, arithmetic between a p-value and an effect, and the sum or difference of two values both
2 or more in size are no longer read as percents. On the corpus of real records the change moves 17 live claims and
10 replayed refusals, all stricter, each a number covered by such a coincidence; the cases accepted below are the
shapes its first drafts refused there.
"""
import pytest

from hypgraph import Graph, GraphError

SCOPE = "One benchmark run of each build on the same machine."


def write(statement, values):
    g = Graph()
    inv = g.author("curator").investigation("Build speed", "How much faster is the new build?",
                                             scope="One benchmark run of each build.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The benchmark figures.",
                            values=values)["id"]
    meas = [{"name": key, "result": r, "key": key, **v} for key, v in values.items()]
    return g.author("writer").add(
        "claim", inv, kind="finding", statement=statement, scope=SCOPE, measurements=meas,
        links=[{"rel": "supports", "from": r, "why": "The benchmark figures this sentence reports."}])


def codes(statement, values):
    try:
        write(statement, values)
    except GraphError as e:
        return [p["code"] for p in e.problems]
    return []


SPEEDUP = {"speedup_pct": {"value": 4.2, "unit": "%"}, "ci_low_pct": {"value": -4.0, "unit": "%"},
           "ci_high_pct": {"value": 12.5, "unit": "%"}}


@pytest.mark.parametrize("values", [
    SPEEDUP,                                                                       # 4.2 + -4.0 = 0.2
    {"speedup_pct": {"value": 5.8, "unit": "%"}, "ci_low_pct": {"value": -4.0, "unit": "%"},
     "p_value": {"value": 0.8}},                                                   # 0.8 / -4.0 = -0.2
    {"speedup_pct": {"value": 5.8, "unit": "%"}, "p_value": {"value": 0.2}},       # p = 0.2
    {"speedup_pct": {"value": 0.6, "unit": "x"}, "welch_p": {"value": 0.03}},      # 0.03 / 0.6 = 0.05
])
def test_a_derived_number_that_is_no_fraction_does_not_make_a_percent(values):
    statement = "The new build is 20% faster." if "welch_p" not in values else "The new build is 5% faster."
    assert "UNBOUND_NUMBER" in codes(statement, values)


@pytest.mark.parametrize("statement,values", [
    ("The new build is 4.2% faster (95% interval -4.0% to 12.5%).", SPEEDUP),
    ("The speed-up is not significant: p = 0.2.", {"speedup_pct": {"value": 5.8, "unit": "%"},
                                                   "p_value": {"value": 0.2}}),
    # two p-values: their difference and ratio are still said
    ("The Welch and permutation tests agree within 0.0014.", {"welch_p": {"value": 0.0131},
                                                              "perm_p": {"value": 0.0117}}),
    # returns kept as fractions above 1: the difference is a percent
    ("The strategy returned 101.00% out of sample; buy-and-hold returned -23.79%.",
     {"oos_return_strategy": {"value": 1.01, "unit": "%"}, "oos_excess": {"value": 1.2479, "unit": "%"}}),
    # a difference of two rates in points
    ("A is 4.1% more accurate than B.", {"acc_a": {"value": 0.837}, "acc_b": {"value": 0.796}}),
    # proportions whose keys start with p are not p-values
    ("20% of users in arm A converted.", {"p_a": {"value": 0.2, "unit": "fraction"}}),
    ("The signal agrees with the next day's move 70.45% of the time.",
     {"p_sig_agree_next": {"value": 0.7045, "unit": "fraction"}}),
])
def test_a_derived_number_that_can_be_a_fraction_still_makes_a_percent(statement, values):
    assert "UNBOUND_NUMBER" not in codes(statement, values)
