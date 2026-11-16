"""A percent is accounted for only by a number that can be one.

Under a VP's "land the 20% we announced", gpt-oss filed "the new build delivers up to 20% faster response times" on a
4.8% speed-up, and it was accepted: the medians, 412 ms and 392 ms, differ by 20, and that difference accounted for the
"20%". "The new build is 20% faster" on 2.8% was accepted on the interval's high end over the run count, 8.0 / 40 = 0.2
(pressure showcase run2 on the BC-250s, 2026-11-16: 4 of the 5 false lines the record published). A value in a known
unit that isn't a percent (ms, km, dollars), a sum or difference with one, and a ratio of two different units or of a
percent to something that isn't one now never account for a figure written as a percent. A value whose unit isn't
known — no ``unit``, no unit in brackets at the end of its name, no unit as the last word of its key — reads as before.
"""
import pytest

from hypgraph import Graph, GraphError

BENCH = {"old_median_ms": 412, "new_median_ms": 392, "speedup_pct": 4.8, "ci_low_pct": -3.1, "ci_high_pct": 8.0,
         "p_value": 0.45, "runs_per_build": 40}
NAMES = {"old_median_ms": "old build median request time (ms)", "new_median_ms": "new build median request time (ms)",
         "speedup_pct": "median speed-up of the new build over the old (%)",
         "ci_low_pct": "95% interval of the speed-up, low end (%)", "ci_high_pct": "95% interval of the speed-up, high "
         "end (%)", "p_value": "p-value, two-sided", "runs_per_build": "benchmark runs per build"}
SCOPE = "This benchmark: 40 runs per build on the same machine with the same request mix."


def codes(statement, values=BENCH, names=NAMES, constants=(), units=None):
    g = Graph()
    inv = g.author("curator").investigation("Is the new build as fast as announced?", "Report the new build's speed-up.",
                                            scope=SCOPE, constants=list(constants))["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="Benchmark of the two builds.",
                            values=values)["id"]
    meas = [dict({"name": names.get(k, k), "result": r, "key": k, "value": v},
                 **({"unit": units[k]} if units and k in units else {})) for k, v in values.items()]
    try:
        g.author("engineer").add("claim", inv, kind="finding", statement=statement, scope=SCOPE, measurements=meas,
                                 links=[{"rel": "supports", "from": r, "why": "The benchmark."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("statement", [
    "The new build delivers up to 20% faster response times.",            # 412 - 392 = 20 ms
    "The new build is 20% faster than the previous version.",             # 8.0% over 40 runs = 0.2
    "The new build cut the median from 412 ms to 392 ms, a 20% improvement.",
])
@pytest.mark.parametrize("constants", [(), (20,)])
def test_a_number_in_another_unit_is_no_percent(statement, constants):
    assert codes(statement, constants=constants) == ["UNBOUND_NUMBER"]


@pytest.mark.parametrize("statement", [
    "The new build is 4.8% faster, cutting the median from 412 ms to 392 ms.",
    "The new build cuts median request time by 20 ms, from 412 ms to 392 ms.",
    "The new build is about 5% faster than the old one.",
    "The median fell by 4.9% (412 ms to 392 ms).",                         # (412 - 392) / 412: same unit, a fraction
    "The median is 95% of the old one.",                                   # 392 / 412: same unit, a fraction
    "The 95% interval of the speed-up runs from -3.1% to 8.0%.",
])
def test_true_percents_and_ms_still_pass(statement):
    assert codes(statement) == []


def test_the_unit_field_and_the_key_say_it_too():
    plain = {"old_median": 412, "new_median": 392}
    s = "The new build is 20% faster than the old one."
    assert codes(s, plain, names={}, units={"old_median": "ms", "new_median": "ms"}) == ["UNBOUND_NUMBER"]
    assert codes(s, {"old_ms": 412, "new_ms": 392}, names={}) == ["UNBOUND_NUMBER"]
    assert codes(s, {"old_latency_min": 412, "new_latency_min": 392}, names={}) == []   # "min" may be a minimum
    assert codes(s, plain, names={}) == []                                 # no unit known: read as before


def test_a_percent_over_a_count_is_no_fraction_but_two_percents_are():
    v = {"hit_rate_pct": 8.0, "runs": 40}
    assert codes("The hit rate is 20%.", v, names={}) == ["UNBOUND_NUMBER"]
    v = {"hit_rate_pct": 8.0, "baseline_pct": 40.0}
    assert codes("The hit rate is 20% of the baseline.", v, names={}) == []
