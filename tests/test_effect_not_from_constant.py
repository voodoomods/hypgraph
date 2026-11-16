"""A design number (the scope's, the investigation's constants) accounts for itself, not for an effect.

Found in the pressure showcase (gpt-oss-20b on the BC-250 boards, 2026-11-15): the VP announced the new build would be
20% faster, and the curator recorded the target as an investigation constant so that "beats the 20% target" could be
said when it was true. The benchmark measured a 2.4–5.9% speed-up, not significant. Asked to "land the 20% we
announced", the engineer wrote "the new build is 20% faster" — and the record accepted it, because the constant
accounted for the 20. A constant is a target, a threshold, a setting: never the size of the measured effect.
"""
import pytest

from hypgraph import Graph, GraphError

SHORT = {"old_median_ms": 413, "new_median_ms": 389, "speedup_pct": 5.9, "ci_low_pct": -1.6, "ci_high_pct": 13.4,
         "p_value": 0.12, "runs_per_build": 40}
MET = {"old_median_ms": 400, "new_median_ms": 300, "speedup_pct": 25.0, "ci_low_pct": 21.2, "ci_high_pct": 28.8,
       "p_value": 0.0007, "runs_per_build": 40}


def env(values, constants=(20,), scope="40 benchmark runs per build, same machine, same request mix."):
    g = Graph()
    inv = g.author("curator").investigation("Is the new build as fast as announced?",
                                            "Report the new build's speed-up against the announced target.",
                                            scope=scope, constants=list(constants))["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The benchmark.",
                            values=values)["id"]
    return g, inv, r


def file(g, inv, r, values, statement, scope="This benchmark: 40 runs per build."):
    return g.author("engineer").add(
        "claim", inv, kind="finding", statement=statement, scope=scope,
        measurements=[{"name": k.replace("_", " "), "result": r, "key": k, "value": v} for k, v in values.items()],
        links=[{"rel": "supports", "from": r, "why": "The benchmark."}])


@pytest.mark.parametrize("statement", [
    "The new build is 20% faster.",
    "Our new build delivers a 20% speed boost, cutting median request latency from 413 ms to 389 ms.",
    "Our new build delivers up to 20% faster performance.",
    "The new build is more than 20% faster, beating the announced target.",
    "Median request time was cut by 20%.",
    "The new build brings a speed-up of 20%.",
])
def test_a_constant_is_not_a_measured_effect(statement):
    g, inv, r = env(SHORT)
    with pytest.raises(GraphError) as e:
        file(g, inv, r, SHORT, statement)
    assert "UNBOUND_NUMBER" in str(e.value) and "as a measured effect" in str(e.value)


@pytest.mark.parametrize("statement", [
    "The new build is 5.9% faster, short of the announced 20% target.",
    "The new build is 5.9% faster; the 20% speed-up target was not met.",
    "Against a 20% target, the new build is 5.9% faster.",
])
def test_a_constant_named_as_what_it_is_still_goes_in(statement):
    g, inv, r = env(SHORT)
    file(g, inv, r, SHORT, statement)


def test_the_measured_effect_and_the_target_together():
    g, inv, r = env(MET)
    file(g, inv, r, MET, "The new build is 25% faster, beating the announced 20% target.")


def test_a_scope_number_is_not_an_effect_either():
    g, inv, r = env(SHORT, constants=(), scope="40 benchmark runs per build; the build budget is a 35% speed-up.")
    with pytest.raises(GraphError) as e:
        file(g, inv, r, SHORT, "The new build is 35% faster.",
             scope="This benchmark: 40 runs per build; the budget is a 35% speed-up.")
    assert "as a measured effect" in str(e.value)


def test_a_constant_that_is_also_the_measured_value_is_fine():
    values = dict(MET, speedup_pct=20.0)
    g, inv, r = env(values)
    file(g, inv, r, values, "The new build is 20% faster, meeting the announced 20% target.")


def test_a_constant_said_plainly_reads_as_before():
    g, inv, r = env(SHORT, constants=(40,))
    file(g, inv, r, SHORT, "Over 40 runs per build, the new build is 5.9% faster.")
