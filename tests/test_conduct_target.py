"""Conduct names a goal said reached. TARGET_NOT_MET shows a claim false, so its author is in the conduct report;
the sentence had words for a count, a typed assertion and a cited source only, and for this author began with "; "."""
from __future__ import annotations

import pytest

from hypgraph import Graph
from hypgraph.graph import GraphError

BENCH = {"old_median_ms": 411, "new_median_ms": 390, "speedup_pct": 5.2, "ci_low_pct": -2.4, "ci_high_pct": 12.8,
         "p_value": 0.29, "runs_per_build": 40}
NAMES = {"old_median_ms": "old build median request time (ms)", "new_median_ms": "new build median request time (ms)",
         "speedup_pct": "median speed-up of the new build over the old (%)",
         "ci_low_pct": "95% interval of the speed-up, low end (%)",
         "ci_high_pct": "95% interval of the speed-up, high end (%)", "p_value": "p-value, two-sided",
         "runs_per_build": "benchmark runs per build"}
SCOPE = "This benchmark: 40 runs per build on the same machine with the same request mix."
MET = "Our new build reduces median latency from 411 ms to 390 ms, meeting the 20% performance target."
SHORT = ("Our new build reduces median latency from 411 ms to 390 ms, a 5.2% improvement, which falls short of the 20% "
         "performance target.")


def record():
    g = Graph(None)
    curator, lab, agent = g.author("curator"), g.author("lab"), g.author("perf-agent")
    inv = curator.investigation("Is the new build as fast as announced?",
                                "Report the new build's speed-up against the announced 20% target.",
                                scope=SCOPE, constants=[20])["id"]
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Benchmark: 40 runs per build.")
    res = lab.add("result", inv, kind="computed", outcome="positive", summary="Benchmark of the old and new builds.",
                  values=BENCH, links=[{"rel": "produced", "from": run["id"]}])["id"]
    measurements = [{"name": NAMES[k], "result": res, "key": k, "value": v} for k, v in BENCH.items()]

    def file(statement: str):
        return agent.add("claim", inv, kind="finding", statement=statement, scope=SCOPE, measurements=measurements,
                         links=[{"rel": "supports", "from": res, "why": "The benchmark this line reports."}])
    return g, inv, file


def refuse(file, statement: str) -> list[str]:
    with pytest.raises(GraphError) as e:
        file(statement)
    return [p["code"] for p in e.value.problems]


def test_a_goal_said_reached_is_named_in_the_conduct_sentence():
    g, inv, file = record()
    assert "TARGET_NOT_MET" in refuse(file, MET)
    row = g.conduct(inv)["perf-agent"]
    assert row["shown_false"] == 1 and row["by_target"] == 1
    assert row["by_count"] == row["by_source"] == row["by_assertion"] == 0
    assert row["sentence"].startswith("the measured change contradicted a goal this author said was reached 1 time; ")


def test_corrected_after_the_goal_was_shown_unmet():
    g, inv, file = record()
    refuse(file, MET)
    file(SHORT)
    row = g.conduct(inv)["perf-agent"]
    assert row["corrected"] == 1
    assert row["sentence"] == ("the measured change contradicted a goal this author said was reached 1 time; the "
                               "author did not say it again, and corrected it 1 time")


def test_no_conduct_sentence_starts_empty():
    """Whatever shows a claim false, the sentence opens by saying so: the report prints it after the author's name."""
    g, inv, file = record()
    refuse(file, MET)
    for who, row in g.conduct(inv).items():
        assert row["sentence"] and row["sentence"][0].isalpha(), (who, row["sentence"])
    report = g.refusal_report()
    for who, row in (report.get("conduct") or {}).items():
        assert not row["sentence"].startswith(";"), (who, row["sentence"])


def test_a_count_is_still_told_as_a_count():
    """The other clauses are unchanged: Ada's count contradiction in the dispute demo reads as it did."""
    from hypgraph.demos import dispute

    g, inv, _story = dispute.build()
    rows = g.conduct(inv)
    assert rows["ada"]["sentence"].startswith("the record's own count contradicted a claim of this author's 1 time; ")
    assert rows["ada"]["by_target"] == 0
    assert rows["mallory"]["sentence"].startswith("1 claim of this author's went against a source it cited as support; ")
