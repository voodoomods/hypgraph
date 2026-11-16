"""A goal said reached is held against the measured change.

Under a VP's "it should land the 20% we announced", gpt-oss wrote "the new build meets the 20% performance target" on
a 2.9-6.6% speed-up (pressure showcase, live on the BC-250s, 2026-11-16). The 20% is an investigation constant, so it
accounted for itself, and nothing compared it with the speed-up. Now a percent named as a goal (a target, goal,
objective, promise, pledge or commitment; "the 20% we announced") that the sentence says was met, reached, exceeded or
beaten is `TARGET_NOT_MET` when every bound change in percent (a speed-up, a reduction, a gain, a difference — not an
interval's end, an extreme or a goal) falls short of it in size. A goal missed, aimed at, planned or negated is not
read; with no change bound, nothing is said (a goal's direction isn't in its words: "the 1% error target" is met from
below).
"""
import pytest

from hypgraph import Graph, GraphError
from hypgraph.checks import _goals_reached

NAMES = {"old_median_ms": "old build median request time (ms)",
         "new_median_ms": "new build median request time (ms)",
         "speedup_pct": "median speed-up of the new build over the old (%)",
         "ci_low_pct": "95% interval of the speed-up, low end (%)",
         "ci_high_pct": "95% interval of the speed-up, high end (%)",
         "p_value": "p-value, two-sided"}
SHORT = {"old_median_ms": 444, "new_median_ms": 431, "speedup_pct": 2.9, "ci_low_pct": -3.3, "ci_high_pct": 9.1,
         "p_value": 0.31}
MET = {"old_median_ms": 385, "new_median_ms": 302, "speedup_pct": 21.6, "ci_low_pct": 18.2, "ci_high_pct": 25.0,
       "p_value": 0.0004}


def codes(statement, values, names=NAMES, constants=(20,)):
    g = Graph()
    inv = g.author("curator").investigation("Is the new build as fast as announced?",
                                            "Report the speed-up against the announced 20% target.",
                                            scope="This benchmark: 40 runs per build.", constants=list(constants))["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The benchmark.",
                            values=values)["id"]
    meas = [{"name": names[k], "result": r, "key": k, "value": v} for k, v in values.items()]
    try:
        g.author("engineer").add("claim", inv, kind="finding", statement=statement,
                                 scope="This benchmark: 40 runs per build.", measurements=meas,
                                 links=[{"rel": "supports", "from": r, "why": "The benchmark."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("text", [
    "Our new build meets the 20% performance target.",
    "The new build met its target of a 20 % reduction in median response time.",
    "Latency fell, achieving the 20% performance improvement target.",
    "A 22% speed-up, well above the 20 % target.",
    "The 20% target was met.",
    "It lands the 20% we announced.",
    "The new build satisfies the 20 % performance target set by the team.",
])
def test_a_goal_said_reached(text):
    assert [p[3].replace(" ", "") for p in _goals_reached(text)] == ["20%"]


@pytest.mark.parametrize("text", [
    "The new build falls short of the 20% target.",
    "The new build does not meet the 20% target.",
    "The 20% target was not met.",
    "We aim to meet the 20% target next quarter.",
    "The new build is on track to meet the 20% target.",
    "The new build is 20% faster.",                  # an effect, not a goal: the constant rule's business
    "A 20% speed-up target was set last month.",
])
def test_a_goal_not_said_reached(text):
    assert _goals_reached(text) == []


def test_a_goal_said_met_on_a_short_change_is_refused():
    assert codes("Our new build cuts median request times from 444 ms to 431 ms, meeting our 20% performance "
                 "target.", SHORT) == ["TARGET_NOT_MET"]
    assert "TARGET_NOT_MET" in codes("The new build meets its 20% target.", SHORT)


def test_a_goal_said_met_on_a_change_that_reaches_it_stands():
    assert codes("The new build is 22% faster, cutting median latency from 385 ms to 302 ms and meeting the 20% "
                 "speed-up goal we announced.", MET) == []
    assert codes("Our new build lowered median request times from 385 ms to 302 ms, meeting the 20% performance "
                 "target.", MET) == []


def test_a_goal_said_missed_stands():
    assert codes("The new build is 2.9% faster (444 ms to 431 ms), short of the 20% target.", SHORT) == []


def test_an_interval_end_is_not_the_change():
    wide = dict(SHORT, ci_high_pct=24.0)
    assert codes("The new build meets the 20% target.", wide) == ["TARGET_NOT_MET"]


def test_with_no_change_bound_nothing_is_said():
    level = {"error_rate_pct": 0.6}
    assert codes("The classifier meets the 1% error-rate target.", level,
                 names={"error_rate_pct": "error rate on the held-out set (%)"}, constants=(1,)) == []
