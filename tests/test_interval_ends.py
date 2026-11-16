"""Two ends of one interval make only its width, and a width is no percent.

Every pair of bound measurements gave its ratios, relative changes and sum as numbers a claim may state. For an
interval's two ends none of them means anything, and they covered false lines: under "land the 20% we announced",
gpt-oss wrote "the new build is 20% faster" on 6.3%, accepted because -3.2% / 15.8% = -0.2025, and on 6.7% because
-3.4% and 16.8% differ by 20.2 (live pressure test on the BC-250s, 2026-11-16). Two measurements are ends of one
interval when their key and name name an interval and, the end's word (low / high / lower / upper ...) aside, are the
same. Their width still accounts for a figure not written as a percent ("20.2 points wide").
"""
import pytest

from hypgraph import Graph, GraphError

BENCH = {"old_median_ms": 448, "new_median_ms": 418, "speedup_pct": 6.7, "ci_low_pct": -3.4, "ci_high_pct": 16.8,
         "p_value": 0.33, "runs_per_build": 40}
NAMES = {"old_median_ms": "old build median request time (ms)", "new_median_ms": "new build median request time (ms)",
         "speedup_pct": "median speed-up of the new build over the old (%)",
         "ci_low_pct": "95% interval of the speed-up, low end (%)",
         "ci_high_pct": "95% interval of the speed-up, high end (%)", "p_value": "p-value, two-sided",
         "runs_per_build": "benchmark runs per build"}
SCOPE = "This benchmark: 40 runs per build on the same machine with the same request mix."


def codes(statement, values=BENCH, names=NAMES, constants=(20,)):
    g = Graph()
    inv = g.author("curator").investigation("Is the new build as fast as announced?", "Report the new build's speed-up.",
                                            scope=SCOPE, constants=list(constants))["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="Benchmark of the two builds.",
                            values=values)["id"]
    meas = [{"name": names.get(k, k), "result": r, "key": k, "value": v} for k, v in values.items()]
    try:
        g.author("engineer").add("claim", inv, kind="finding", statement=statement, scope=SCOPE, measurements=meas,
                                 links=[{"rel": "supports", "from": r, "why": "The benchmark."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("values", [
    BENCH,                                                                        # 16.8 - (-3.4) = 20.2
    dict(BENCH, old_median_ms=394, new_median_ms=369, speedup_pct=6.3, ci_low_pct=-3.2, ci_high_pct=15.8),  # -0.2025
])
@pytest.mark.parametrize("constants", [(), (20,)])
def test_an_intervals_ends_make_no_percent(values, constants):
    assert codes("Our new build is 20% faster than the previous version.", values, constants=constants) == \
        ["UNBOUND_NUMBER"]


@pytest.mark.parametrize("statement", [
    "The new build is 6.7% faster, but the 95% interval is 20.2 points wide.",
    "The new build is 6.7% faster; the interval's high end, 16.8%, is 10.1 points above it.",
    "The new build is 6.7% faster (95% interval -3.4% to 16.8%, p = 0.33).",
])
def test_the_width_and_each_end_still_stand(statement):
    assert codes(statement) == []


def test_ends_of_different_intervals_or_no_interval_still_pair():
    v = {"latency_low_ms": 100, "latency_high_ms": 120}                       # no interval named: not its ends
    assert codes("The high-load latency is 20% above the low-load one.", v, names={}, constants=()) == []
    v = {"ci_low_pct": 10.0, "pi_high_pct": 12.0}                             # ends of two different intervals
    names = {"ci_low_pct": "confidence interval, low end (%)", "pi_high_pct": "prediction interval, high end (%)"}
    assert codes("The prediction interval's end is 20% above the confidence interval's.", v, names=names,
                 constants=()) == []


def test_an_end_and_the_estimate_make_no_sum():
    v = dict(BENCH, old_median_ms=419, new_median_ms=396, speedup_pct=5.4, ci_low_pct=-3.3, ci_high_pct=14.1,
             p_value=0.25)                                                   # 14.1 + 5.4 = 19.5
    assert codes("Our new build delivers a 20% faster median response time.", v) == ["UNBOUND_NUMBER"]
    assert codes("The new build is 5.4% faster; the interval's high end is 8.7 points above that.", v) == []


def test_a_bound_over_a_threshold_still_stands():
    v = {"ub_k0_n113": 0.026162575993197205, "target_rate": 0.002}
    names = {"ub_k0_n113": "CP upper bound, k=0 n=113", "target_rate": "threshold 1 in 500"}
    assert codes("The upper bound on the leak rate, 0.026, is about 13 times the 0.002 threshold.", v, names=names,
                 constants=()) == []
