"""A change that rounds to the goal as written reaches it, rounded as people round.

The target rule (`TARGET_NOT_MET`) let a change stand when it rounds to the goal, but rounded with ``round()``: the
binary value, halves to even. So 20.5% did not reach "the 21% target" (``round(20.5)`` is 20) and 4.85% did not reach
"the 4.9% target" (stored as 4.8499...), while every other number check reads 20.5 as "21" and 4.85 as "4.9"
(`checks._shows`, half up). The rule now uses ``_shows`` too, single-digit whole numbers included as it treats them.
"""
import pytest

from hypgraph import Graph, GraphError

NAMES = {"speedup_pct": "median speed-up of the new build over the old (%)",
         "ci_low_pct": "95% interval of the speed-up, low end (%)",
         "ci_high_pct": "95% interval of the speed-up, high end (%)",
         "p_value": "p-value, two-sided"}


def codes(statement, speedup, goal):
    values = {"speedup_pct": speedup, "ci_low_pct": speedup - 3.0, "ci_high_pct": speedup + 3.0, "p_value": 0.0004}
    g = Graph()
    inv = g.author("curator").investigation("Is the new build as fast as announced?",
                                            "Report the speed-up against the announced target.",
                                            scope="This benchmark: 40 runs per build.", constants=[goal])["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The benchmark.",
                            values=values)["id"]
    meas = [{"name": NAMES[k], "result": r, "key": k, "value": v} for k, v in values.items()]
    try:
        g.author("engineer").add("claim", inv, kind="finding", statement=statement,
                                 scope="This benchmark: 40 runs per build.", measurements=meas,
                                 links=[{"rel": "supports", "from": r, "why": "The benchmark."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("speedup, goal, text", [
    (20.5, 21, "The new build meets the 21% performance target."),       # round(20.5) == 20
    (4.85, 4.9, "The new build meets the 4.9% performance target."),     # 4.85 is stored as 4.8499...
    (12.5, 13, "The new build meets the 13% performance target."),       # round(12.5) == 12
])
def test_a_change_that_rounds_half_up_to_the_goal_reaches_it(speedup, goal, text):
    assert "TARGET_NOT_MET" not in codes(text, speedup, goal)


@pytest.mark.parametrize("speedup, goal, text", [
    (20.4, 21, "The new build meets the 21% performance target."),
    (4.84, 4.9, "The new build meets the 4.9% performance target."),
    (19.4, 20, "The new build meets the 20% performance target."),
    # a single-digit whole number keeps round(), as everywhere else: 4.5 is not "5"
    (4.5, 5, "The new build meets the 5% performance target."),
])
def test_a_change_short_of_the_goal_as_written_is_refused(speedup, goal, text):
    assert "TARGET_NOT_MET" in codes(text, speedup, goal)
