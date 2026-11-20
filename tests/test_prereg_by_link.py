"""scientific@3, trading@4 and optimization@4: preregistration judged per `tests` link, by its own time.

Under the earlier versions the `preregistered` gate read only when the experiment was first written. A hypothesis
linked to an experiment after its run, with an expected outcome written once the result was in, counted as
preregistered, and so did a protocol changed after the run. In the records on disk, 14 questions under scientific@2 /
trading@2 had a hypothesis tested only that way and still read as preregistered. Under the new versions such a
hypothesis holds its question until a new experiment tests it before its run. The earlier versions are frozen."""
from __future__ import annotations

import dataclasses
import os
import random

import pytest

from hypgraph import Graph, Policy, profiles
from hypgraph import workflow as W
from hypgraph.server import dispatch

H = "harness"
NEW = {"scientific@3": "scientific@2", "trading@4": "trading@3", "optimization@4": "optimization@3"}
T0, RUN, LATE, LATER, LATEST = ("2026-01-01T00:00:00+00:00", "2026-01-02T00:00:00+00:00",
                                "2026-01-03T00:00:00+00:00", "2026-01-04T00:00:00+00:00", "2026-01-05T00:00:00+00:00")
LINKED_LATE = ("H2 is tested only through X1, linked after RUN1 executed it — a hypothesis written after its run's "
               "outcome is not preregistered; test it with a new experiment, written before its run")


def _g(profile: str, asks: str = ""):
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={H}))
    inv = g.create(author=H, type="investigation", fields={"title": "A preregistration investigation.",
                   "objective": "See when an experiment counts as preregistered.", "profile": profile})["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q1",
                 fields={"text": "Does the cache cut the latency?", **({"asks": asks} if asks else {})})["id"]
    return g, inv, q


def _hyp(g, inv, q, at: str = T0, statement: str = "Caching halves the latency.") -> str:
    return g.create(author=g.policy.importer, type="hypothesis", inv=inv, at=at,
                    fields={"statement": statement, "predictions": ["the p50 latency changes"]},
                    links=[{"rel": "answers", "to": q}])["id"]


def _exp(g, inv, at: str = T0, tests: list[str] = (), expected: str = "p50 halves") -> str:
    return g.create(author=g.policy.importer, type="experiment", inv=inv, at=at,
                    fields={"aim": "Measure latency with the cache on and off.", "protocol": "Fifty requests each way.",
                            "success_criteria": "The p50 latency with the cache is half of it without."},
                    links=[{"rel": "tests", "to": h, "data": {"expected": expected} if expected else {}}
                           for h in tests])["id"]


def _run(g, inv, x: str, at: str = RUN) -> str:
    return g.create(author=g.policy.importer, type="run", inv=inv, at=at,
                    fields={"kind": "agent", "name": "latency", "state": "succeeded"},
                    links=[{"rel": "executes", "to": x}])["id"]


def _link(g, x: str, t: str, expected: str = "p50 falls by a third") -> dict:
    return g.link(author=g.policy.importer, src=x, rel="tests", dst=t, why="The latency runs also bear on this.",
                  data={"expected": expected})


def _gate(g, q) -> dict:
    return next(gt for gt in g.stage(q)["gates"] if gt["gate"] == "preregistered")


def _order(g, t: str, since: str = "") -> dict:
    s = g.snapshot()
    return W.evaluate_predicate("preregistered", s, t, since, s.nodes[t]["inv"])


def _late_beside_early(profile: str):
    """H1 preregistered through X1; after RUN1, H2 is written and linked to X1 with its own expected outcome."""
    g, inv, q = _g(profile)
    h1 = _hyp(g, inv, q)
    x = _exp(g, inv, T0, [h1])
    _run(g, inv, x)
    h2 = _hyp(g, inv, q, LATE, "Caching cuts the latency by a third.")
    _link(g, x, h2)
    return g, inv, q, h1, h2, x


# ── the profiles ───────────────────────────────────────────────────

@pytest.mark.parametrize("new,old", NEW.items())
def test_each_new_version_is_its_predecessor_with_only_preregistration_per_link(new, old):
    p, o = profiles.PROFILES[new], profiles.PROFILES[old]
    assert p.workflow.prereg_by_link and not o.workflow.prereg_by_link
    assert dataclasses.replace(p.workflow, prereg_by_link=False) == o.workflow
    assert dataclasses.replace(p, version=o.version, about=o.about, workflow=o.workflow) == o
    assert p.about.startswith(o.about) and p.labels == o.labels
    assert profiles.describe()[new]["workflow"]["stages"] == profiles.describe()[old]["workflow"]["stages"]


def test_only_the_new_versions_judge_by_link_and_evaluation_stays_deprecated():
    assert sorted(k for k, p in profiles.PROFILES.items() if p.workflow and p.workflow.prereg_by_link) == sorted(NEW)
    assert profiles.PROFILES["evaluation@1"].deprecated and not profiles.PROFILES["evaluation@1"].workflow.prereg_by_link


# ── a hypothesis linked after the run ──────────────────────────────

@pytest.mark.parametrize("profile", [*NEW, *NEW.values()])
def test_a_hypothesis_linked_after_the_run_beside_a_preregistered_one_holds_the_question(profile):
    g, inv, q, h1, h2, x = _late_beside_early(profile)
    gate = _gate(g, q)
    if profile in NEW.values():                                            # frozen: the gap as it was
        assert gate["met"] and _order(g, h2)["met"]
        return
    assert not gate["met"] and gate["why"] == LINKED_LATE
    stages = [st.gate for st in profiles.PROFILES[profile].workflow.stages]
    assert g.stage(q)["index"] <= stages.index("preregistered") + 1 and not g.stage(q)["complete"]
    assert _order(g, h1)["met"] and not _order(g, h2)["met"]
    x2 = _exp(g, inv, LATER, [h2])                                         # what the reason says to do
    _run(g, inv, x2, LATEST)
    assert _gate(g, q)["met"] and set(_gate(g, q)["evidence"]) == {"X1", "X2"}
    assert _order(g, h2)["met"] and _order(g, h2)["evidence"] == [x2]


@pytest.mark.parametrize("profile", NEW)
def test_a_hypothesis_linked_after_the_run_alone(profile):
    g, inv, q = _g(profile)
    x = _exp(g, inv)
    _run(g, inv, x)
    _link(g, x, _hyp(g, inv, q, LATE))
    assert _gate(g, q)["why"] == LINKED_LATE.replace("H2", "H1")


@pytest.mark.parametrize("profile", NEW)
def test_a_hypothesis_written_before_the_run_but_linked_after_it_holds_and_says_which(profile):
    # seen live (optimization@4, gpt-oss-20b): H1 and X1 both before RUN2, `X1 tests H1` with its expected outcome
    # 48 s after RUN2. The expected outcome is on the link, so it came after the run; H1 itself did not
    g, inv, q = _g(profile)
    h = _hyp(g, inv, q)
    x = _exp(g, inv)
    _run(g, inv, x)
    _link(g, x, h)
    gate = _gate(g, q)
    assert not gate["met"]
    assert gate["why"] == ("H1 is tested only through X1, linked after RUN1 executed it — H1 was written before the "
                           "run, but the link's expected outcome after it; test it with a new experiment, written "
                           "before its run")
    x2 = _exp(g, inv, LATER, [h])
    _run(g, inv, x2, LATEST)
    assert _gate(g, q)["met"]


@pytest.mark.parametrize("profile", NEW)
def test_a_link_at_the_runs_own_second_counts_as_before_it(profile):
    g, inv, q = _g(profile)
    h = _hyp(g, inv, q)
    x = _exp(g, inv)
    _run(g, inv, x, T0)
    _link(g, x, h)                                                         # written at T0 too? no: now — see below
    assert not _gate(g, q)["met"]                                          # linked at the real clock, after T0
    g2, inv2, q2 = _g(profile)
    x2 = _exp(g2, inv2, T0, [_hyp(g2, inv2, q2)])
    _run(g2, inv2, x2, T0)                                                 # same timestamp as the link
    assert _gate(g2, q2)["met"]


@pytest.mark.parametrize("profile", NEW)
def test_a_late_hypothesis_holds_its_own_question_not_another_the_experiment_reaches(profile):
    # corpus, s2_regression bmw / cpa: an order on Q2 took in the assignee's later experiment, which also tested a
    # hypothesis on Q3 linked after its run; Q2's order was held for Q3's hypothesis
    g, inv, q1 = _g(profile)
    q2 = g.create(author=H, type="question", inv=inv, code="Q2", fields={"text": "Does the cache cut the cost?"})["id"]
    x = _exp(g, inv, T0, [_hyp(g, inv, q1)])
    _run(g, inv, x)
    _link(g, x, _hyp(g, inv, q2, LATE, "Caching cuts the cost by a third."))
    assert _gate(g, q1)["met"]
    assert not _gate(g, q2)["met"] and "H2 is tested only through X1, linked after RUN1" in _gate(g, q2)["why"]
    s = g.snapshot()
    under_order = W.evaluate_predicate("preregistered", s, q1, T0, inv, who=g.policy.importer)
    assert under_order["met"] and under_order["evidence"] == [x]
    orphan = g.create(author=g.policy.importer, type="hypothesis", inv=inv, at=LATE, fields={
        "statement": "Caching cuts the tail.", "predictions": ["the p99 changes"]})["id"]
    _link(g, x, orphan)                                                    # answers no question: it still holds
    s = g.snapshot()
    assert not W.evaluate_predicate("preregistered", s, q1, T0, inv, who=g.policy.importer)["met"]


@pytest.mark.parametrize("profile", NEW)
def test_a_claim_linked_after_the_run_does_not_hold_the_question(profile):
    g, inv, q = _g(profile)
    x = _exp(g, inv, T0, [_hyp(g, inv, q)])
    _run(g, inv, x)
    run = next(e["src"] for e in g.snapshot().inn[x] if e["rel"] == "executes")
    res = g.create(author="lab", type="result", inv=inv, fields={"summary": "The p50 latency fell with the cache.",
                   "outcome": "positive"}, links=[{"rel": "produced", "from": run}])["id"]
    c = g.create(author="ana", type="claim", inv=inv, fields={"statement": "The cache helps.", "kind": "finding",
                 "scope": "The latency runs."},
                 links=[{"rel": "answers", "to": q}, {"rel": "supports", "from": res, "why": "The runs measured it."}])["id"]
    _link(g, x, c)
    assert _gate(g, q)["met"]
    assert not _order(g, c)["met"] and "CL1 is tested only through X1" in _order(g, c)["why"]


@pytest.mark.parametrize("profile", NEW)
def test_a_withdrawn_hypothesis_or_a_retracted_link_no_longer_holds_the_question(profile):
    g, inv, q, h1, h2, x = _late_beside_early(profile)
    g.withdraw(author=g.policy.importer, node=h2, why="Written after the result; dropped.")
    assert _gate(g, q)["met"]
    g, inv, q, h1, h2, x = _late_beside_early(profile)
    edge = next(e for e in g.snapshot().out[x] if e["rel"] == "tests" and e["dst"] == h2)
    g.retract(author=g.policy.importer, edge=edge["id"], why="Linked by mistake after the run.")
    assert _gate(g, q)["met"]


# ── an experiment written or changed after its run ─────────────────

@pytest.mark.parametrize("profile", [*NEW, *NEW.values()])
def test_a_protocol_changed_after_the_run_holds_the_question(profile):
    g, inv, q = _g(profile)
    x = _exp(g, inv, T0, [_hyp(g, inv, q)])
    _run(g, inv, x)
    g.revise(author=g.policy.importer, node=x, fields={"protocol": "Five hundred requests each way."},
             reason="The first protocol was too small to show a change.")
    gate = _gate(g, q)
    if profile in NEW.values():
        assert gate["met"]
        return
    assert not gate["met"]
    assert gate["why"] == ("X1's protocol was changed after RUN1 executed it (version 2) — the test that ran is not the "
                           "one on the record; write the new protocol as a new experiment, before its run")


@pytest.mark.parametrize("fields", [{"aim": "Measure the p50 and p95 latency with the cache on and off."},
                                    {"protocol": "Fifty requests each way."}])
def test_a_change_that_leaves_protocol_and_criteria_alone_still_counts(fields):
    g, inv, q = _g("scientific@3")
    x = _exp(g, inv, T0, [_hyp(g, inv, q)])
    _run(g, inv, x)
    g.revise(author=g.policy.importer, node=x, fields=fields, reason="Clarified what is measured, not how.")
    assert _gate(g, q)["met"]


def test_criteria_changed_before_any_run_count():
    g, inv, q = _g("trading@4")
    x = _exp(g, inv, T0, [_hyp(g, inv, q)])
    g.revise(author=g.policy.importer, node=x, fields={"success_criteria": "The p50 latency falls by a third or more."},
             reason="Agreed the threshold before running.")
    _run(g, inv, x, "2099-01-01T00:00:00+00:00")
    assert _gate(g, q)["met"]


@pytest.mark.parametrize("profile", [*NEW, *NEW.values()])
def test_an_experiment_written_after_its_run_beside_a_preregistered_one(profile):
    g, inv, q = _g(profile)
    _run(g, inv, _exp(g, inv, T0, [_hyp(g, inv, q)]))
    h2 = _hyp(g, inv, q, T0, "Caching cuts the latency by a third.")
    x2 = _exp(g, inv, LATE, [h2])
    _run(g, inv, x2, RUN)                                                  # its run is dated before it
    gate = _gate(g, q)
    if profile in NEW.values():
        assert gate["met"]
        return
    assert gate["why"] == ("X2 was written after RUN2 executed it — not preregistered; the experiment (protocol, "
                           "expected outcome) comes before the run")


# ── unchanged ──────────────────────────────────────────────────────

@pytest.mark.parametrize("profile", NEW)
def test_what_did_not_change(profile):
    g, inv, q = _g(profile)
    assert _gate(g, q)["why"] == "no experiment tests a hypothesis on Q1"
    _exp(g, inv, T0, [_hyp(g, inv, q)], expected="")
    assert _gate(g, q)["why"].startswith("X1 tests nothing with an expected outcome")
    g, inv, q = _g(profile)
    _exp(g, inv, T0, [_hyp(g, inv, q)])
    assert _gate(g, q)["met"]                                              # no run yet
    g, inv, q = _g(profile, asks="measure")                               # a measure question skips the gate
    x = _exp(g, inv)
    _run(g, inv, x)
    _link(g, x, _hyp(g, inv, q, LATE))
    if "preregistered" in profiles.PROFILES[profile].workflow.measure_skips:
        assert _gate(g, q).get("skipped") or _gate(g, q)["met"]
    else:                                                                  # optimization has no measure skip
        assert _gate(g, q)["why"] == LINKED_LATE.replace("H2", "H1")


def test_an_order_reads_only_experiments_written_since_it():
    g, inv, q, h1, h2, x = _late_beside_early("scientific@3")
    assert not _order(g, q)["met"]
    assert _order(g, q, since=LATER)["why"] == "no experiment tests a hypothesis on Q1"
    x2 = _exp(g, inv, LATEST, [h2])
    _run(g, inv, x2, "2026-01-06T00:00:00+00:00")
    assert _order(g, q, since=LATER)["met"]


def test_the_server_serves_the_reason():
    g, inv, q, *_ = _late_beside_early("scientific@3")
    st, body = dispatch(g, "GET", f"/stage/{q}", {"inv": inv})
    gate = next(x for x in body["gates"] if x["gate"] == "preregistered")
    assert st == 200 and body["stage"] == "preregistered" and gate["why"] == LINKED_LATE
    st, body = dispatch(g, "GET", "/profiles")
    assert st == 200 and {"scientific@3", "trading@4", "optimization@4"} <= set(body)


# ── randomized histories: the new rule is never looser, and differs only on a post-hoc commitment ──

def _history(rng: random.Random, profile: str):
    """A random record: hypotheses, experiments linking some of them, runs, late links, revisions, in random order
    with random timestamps. Returns the graph, the question, and whether anything was committed after a run."""
    g, inv, q = _g(profile)
    day = lambda: f"2026-02-{rng.randint(1, 28):02d}T{rng.randint(0, 23):02d}:00:00+00:00"  # noqa: E731
    hs = [_hyp(g, inv, q, day(), f"Caching changes the latency, variant {i}.") for i in range(rng.randint(1, 3))]
    xs = []
    for _ in range(rng.randint(1, 3)):
        xs.append(_exp(g, inv, day(), rng.sample(hs, rng.randint(0, len(hs))), rng.choice(["p50 halves", "p50 halves",
                                                                                           ""])))
    for x in xs:
        for _ in range(rng.randint(0, 2)):
            _run(g, inv, x, day())
    s = g.snapshot()
    for _ in range(rng.randint(0, 2)):                                    # links / revisions written now (after all)
        x = rng.choice(xs)
        if rng.random() < 0.5:
            free = [h for h in hs if not any(e["rel"] == "tests" and e["dst"] == h for e in s.out.get(x, []))]
            if free:
                _link(g, x, rng.choice(free))
        else:
            g.revise(author=g.policy.importer, node=x, fields={"protocol": f"Requests each way: {rng.randint(60, 99)}."},
                     reason="Changed how many requests are sent.")
        s = g.snapshot()
    return g, q


@pytest.mark.parametrize("new,old", NEW.items())
def test_randomized_histories(new, old):
    rng = random.Random(f"prereg-{new}")
    seen = {"same": 0, "stricter": 0}
    for i in range(int(os.environ.get("HYPGRAPH_PREREG_HISTORIES", "120"))):
        state = rng.getstate()
        g_new, q_new = _history(rng, new)
        rng.setstate(state)
        g_old, q_old = _history(rng, old)
        a, b = _gate(g_new, q_new), _gate(g_old, q_old)
        assert not (a["met"] and not b["met"]), f"history {i}: the new rule passed what the old one refused"
        if a["met"] != b["met"]:
            seen["stricter"] += 1
            assert any(k in a["why"] for k in ("linked after", "was changed after", "was written after")), a["why"]
        else:
            seen["same"] += 1
            if not a["met"]:
                assert a["why"] == b["why"] or any(k in a["why"] for k in ("linked after", "was changed after"))
    assert seen["stricter"] and seen["same"]                              # the generator reaches both
