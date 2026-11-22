"""The report's per-experiment "preregistered" label reads the rule the record's own `preregistered` gate reads.

It used to read only that every `tests` link states an expected outcome, under every profile: an experiment written
after its run was labelled "preregistered" in the report beside a gate saying "X1 was written after RUN1 executed it —
not preregistered", and under scientific@3 / trading@4 / optimization@4 so was one whose hypothesis was linked, or
whose protocol or hypothesis was changed, after the run. Now the label says what the gate says, and why in a few
words; the gates themselves are unchanged."""
from __future__ import annotations

import os
import random

import pytest

from hypgraph import Graph, Policy
from .test_prereg_by_link import (LATE, NEW, RUN, T0, _exp, _g, _gate, _hyp, _link, _run)

ALL = [*NEW, *NEW.values()]


def _label(g, inv, code: str = "X1") -> dict:
    return next(x for x in g.report(inv)["experiments"] if x["code"] == code)


def _unpinned():
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={"harness"}))
    inv = g.create(author="harness", type="investigation", fields={"title": "A preregistration investigation.",
                   "objective": "See when an experiment counts as preregistered."})["id"]
    q = g.create(author="harness", type="question", inv=inv, code="Q1",
                 fields={"text": "Does the cache cut the latency?"})["id"]
    return g, inv, q


@pytest.mark.parametrize("profile", [*ALL, None])
def test_an_experiment_written_after_its_run_is_not_labelled_preregistered(profile):
    g, inv, q = _unpinned() if profile is None else _g(profile)
    x = _exp(g, inv, LATE, [_hyp(g, inv, q)])
    _run(g, inv, x, RUN)                                                   # its run is dated before it
    lab = _label(g, inv)
    assert not lab["preregistered"] and lab["not_preregistered_because"] == "written after RUN1"
    r = g.report(inv)
    assert r["open"]["experiments_not_preregistered"] == ["X1"]
    assert "X1 tests H1: NOT preregistered (written after RUN1), run" in r["markdown"]
    if profile:
        assert not _gate(g, q)["met"] and "X1 was written after RUN1" in _gate(g, q)["why"]


def _late_link(g, inv, q):
    x = _exp(g, inv, T0, [_hyp(g, inv, q)])
    _run(g, inv, x)
    _link(g, x, _hyp(g, inv, q, LATE, "Caching cuts the latency by a third."))


def _protocol_changed(g, inv, q):
    x = _exp(g, inv, T0, [_hyp(g, inv, q)])
    _run(g, inv, x)
    g.revise(author=g.policy.importer, node=x, fields={"protocol": "Five hundred requests each way."},
             reason="The first protocol was too small to show a change.")


def _hypothesis_changed(g, inv, q):
    h = _hyp(g, inv, q)
    _run(g, inv, _exp(g, inv, T0, [h]))
    g.revise(author=g.policy.importer, node=h, fields={"predictions": ["the p50 latency falls by a tenth"]},
             reason="Matched to what the run showed.")


@pytest.mark.parametrize("profile", ALL)
@pytest.mark.parametrize("make,why", [(_late_link, "H2 linked after RUN1"), (_protocol_changed, "protocol changed after "
                                      "RUN1"), (_hypothesis_changed, "H1 changed after RUN1")])
def test_after_the_fact_by_link_follows_the_version_pinned(profile, make, why):
    g, inv, q = _g(profile)
    make(g, inv, q)
    lab, gate = _label(g, inv), _gate(g, q)
    assert lab["preregistered"] == gate["met"]
    if profile in NEW.values():                                            # frozen: label and gate as they were
        assert lab["preregistered"] and lab["not_preregistered_because"] == ""
    else:
        assert lab["not_preregistered_because"] == why
        assert f"NOT preregistered ({why})" in g.report(inv)["markdown"]


@pytest.mark.parametrize("profile", ALL)
def test_what_the_label_still_says(profile):
    g, inv, q = _g(profile)
    _exp(g, inv, T0, [_hyp(g, inv, q)], expected="")
    assert _label(g, inv)["not_preregistered_because"] == "no expected outcome"
    _exp(g, inv, T0, [_hyp(g, inv, q)])
    assert _label(g, inv, "X2")["preregistered"]                           # not run yet: nothing late to see
    g, inv, q = _g(profile)
    _run(g, inv, _exp(g, inv, T0, [_hyp(g, inv, q)]))
    assert _label(g, inv)["preregistered"] and "X1 tests H1: preregistered, run" in g.report(inv)["markdown"]


@pytest.mark.parametrize("profile", NEW)
def test_a_late_link_to_a_withdrawn_hypothesis_no_longer_counts_against_it(profile):
    g, inv, q = _g(profile)
    x = _exp(g, inv, T0, [_hyp(g, inv, q)])
    _run(g, inv, x)
    h2 = _hyp(g, inv, q, LATE, "Caching cuts the latency by a third.")
    _link(g, x, h2)
    assert not _label(g, inv)["preregistered"]
    g.withdraw(author=g.policy.importer, node=h2, why="Written after the result; dropped.")
    assert _label(g, inv)["preregistered"] and _gate(g, q)["met"]


def _one_experiment(rng: random.Random, profile: str):
    """A random record with one experiment: hypotheses, some linked to it, runs, then late links and revisions."""
    g, inv, q = _g(profile)
    day = lambda: f"2026-02-{rng.randint(1, 28):02d}T{rng.randint(0, 23):02d}:00:00+00:00"  # noqa: E731
    hs = [_hyp(g, inv, q, day(), f"Caching changes the latency, variant {i}.") for i in range(rng.randint(1, 3))]
    x = _exp(g, inv, day(), rng.sample(hs, rng.randint(0, len(hs))), rng.choice(["p50 halves", "p50 halves", ""]))
    for _ in range(rng.randint(0, 2)):
        _run(g, inv, x, day())
    for _ in range(rng.randint(0, 2)):
        roll, s = rng.random(), g.snapshot()
        if roll < 0.4:
            free = [h for h in hs if not any(e["rel"] == "tests" and e["dst"] == h for e in s.out.get(x, []))]
            if free:
                _link(g, x, rng.choice(free))
        elif roll < 0.7:
            g.revise(author=g.policy.importer, node=x, fields={"protocol": f"Requests each way: {rng.randint(60, 99)}."},
                     reason="Changed how many requests are sent.")
        else:
            field = rng.choice([{"predictions": [f"the p50 latency falls by {rng.randint(2, 9)} ms"]},
                                {"open_questions": ["Does it hold under load?"]}])
            g.revise(author=g.policy.importer, node=rng.choice(hs), fields=field, reason="Revised after reading it.")
    return g, inv, q


@pytest.mark.parametrize("profile", ALL)
def test_with_one_experiment_the_label_is_the_gate(profile):
    # one experiment on the question: the gate is met exactly when that experiment is preregistered, so label and gate
    # must agree on every history, under the frozen versions and the new ones
    rng = random.Random(f"label-{profile}")
    seen = {True: 0, False: 0}
    for i in range(int(os.environ.get("HYPGRAPH_PREREG_HISTORIES", "120"))):
        g, inv, q = _one_experiment(rng, profile)
        lab, gate = _label(g, inv), _gate(g, q)
        assert lab["preregistered"] == gate["met"], (i, lab["not_preregistered_because"], gate["why"])
        assert bool(lab["not_preregistered_because"]) != lab["preregistered"]
        seen[gate["met"]] += 1
    assert seen[True] and seen[False]                                     # the generator reaches both
