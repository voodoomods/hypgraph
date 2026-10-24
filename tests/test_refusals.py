"""Refusal is the feature. Every rule: the overclaim it refuses, the honest version it accepts, the arithmetic it
does for the writer, and the code an agent can act on. Plus the blast radius a correction reports."""
import math

import pytest

from hypgraph import Graph, GraphError, Policy, stats

SCOPE = "2,000 held-out items, greedy decoding, one seed."


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}))
    me = g.author("agent")
    inv = me.investigation("Eval", "Find out whether the fine-tune beats the baseline on held-out items.")["id"]
    r = me.add("result", inv, summary="Held-out accuracy and leak probes for both models.", values={
        "ft": {"k": 1624, "n": 2000}, "bl": {"k": 1568, "n": 2000}, "leaks": {"k": 0, "n": 3},
        "leaks_big": {"k": 0, "n": 3000}, "close_a": {"k": 812, "n": 1000}, "close_b": {"k": 800, "n": 1000},
        "p_ab": {"value": 0.21}})["id"]
    return g, me, inv, r


def M(r, name, key, **kw):
    return {"name": name, "result": r, "key": key, **kw}


def add(env, statement, meas=(), scope=SCOPE, **kw):
    g, me, inv, r = env
    return me.add("claim", inv, statement=statement, scope=scope, measurements=list(meas),
                  links=[{"rel": "supports", "from": r, "why": "the eval run"}], **kw)


def refused(env, statement, meas=(), **kw) -> list[dict]:
    with pytest.raises(GraphError) as e:
        add(env, statement, meas, **kw)
    assert e.value.problems and all({"code", "message", "fix", "words"} <= set(p) for p in e.value.problems)
    for p in e.value.problems:
        assert f"[{p['code']}]" in str(e.value)                 # the code is in the text agents and people see
    return e.value.problems


def codes(problems) -> list[str]:
    return [p["code"] for p in problems]


def arms(r):
    return [M(r, "fine-tune", "ft", k=1624, n=2000), M(r, "baseline", "bl", k=1568, n=2000)]


# ── the arithmetic ────────────────────────────────────────────────

def test_rate_bounds_are_the_textbook_numbers():
    assert stats.rate_bounds(0, 3)[1] == pytest.approx(1 - 0.05 ** (1 / 3))     # 63%
    assert stats.rate_bounds(0, 300)[1] == pytest.approx(3 / 300, rel=0.01)     # rule of three
    assert stats.trials_for(0.001) == 2995
    lo, hi = stats.rate_bounds(1, 1000)
    assert lo < 0.001 < hi < 0.006
    t = stats.two_proportions(1624, 2000, 1568, 2000)
    z = 0.028 / math.sqrt(0.798 * 0.202 * (2 / 2000))
    assert t["diff"] == pytest.approx(0.028) and t["p"] == pytest.approx(math.erfc(z / math.sqrt(2)), rel=1e-6)
    assert t["lo"] < 0.028 < t["hi"] and t["lo"] > 0                            # significant: interval excludes 0
    assert stats.detectable(1624, 2000, 1568, 2000) == pytest.approx(0.0356, abs=0.0005)


# ── numbers ───────────────────────────────────────────────────────

def test_numbers_that_follow_from_the_counts_are_accepted(env):
    r = env[3]
    for s in ("The fine-tune scored 2.8 points higher than the baseline.",
              "The fine-tune scored 81.2% against 78.4% for the baseline.",
              "The fine-tune got 3.6% more items right than the baseline.",
              "The fine-tune got 1,624 of 2,000 right, against 1,568 for the baseline."):
        assert add(env, s, arms(r))["type"] == "claim", s


def test_a_number_from_nowhere_is_refused_even_near_a_statistic(env):
    """'5 points' must not pass because the difference's 95% interval happens to end at 5.3."""
    p = refused(env, "The fine-tune is 5 points better than the baseline.", arms(env[3]))
    assert codes(p) == ["UNBOUND_NUMBER"] and p[0]["words"] == ["5"]
    assert add(env, "The fine-tune is 2.8 points better (95% interval 0.3 to 5.3).", arms(env[3]))


# ── never / always ────────────────────────────────────────────────

def test_never_without_a_count(env):
    p = refused(env, "The fine-tune eliminates hallucinations entirely.")
    assert codes(p) == ["ABSOLUTE_WITHOUT_COUNT"] and "eliminates" in p[0]["words"]


def test_never_on_too_few_trials_says_what_the_count_supports_and_the_cost_at_scale(env):
    p = refused(env, "The model never leaks training data.", [M(env[3], "leaks", "leaks", k=0, n=3)],
                exposure=1_000_000, exposure_unit="users")
    assert codes(p) == ["ABSOLUTE_UNDERPOWERED"]
    msg = p[0]["message"]
    assert "0 of 3" in msg and "63%" in msg and "2,995" in msg and "631,597" in msg and "users" in msg
    assert "no occurrences in 3 trials" in p[0]["fix"]


def test_never_leaning_on_a_count_of_something_else(env):
    p = refused(env, "The fine-tune never makes arithmetic errors.", [M(env[3], "leaks", "leaks", k=0, n=3)])
    assert codes(p) == ["ABSOLUTE_UNRELATED_COUNT"]


def test_never_must_show_its_denominator_then_carries_its_bound(env):
    meas = [M(env[3], "leaks", "leaks_big", k=0, n=3000)]
    p = refused(env, "The model never leaks training data.", meas, exposure=1_000_000, exposure_unit="users")
    assert codes(p) == ["ABSOLUTE_HIDES_DENOMINATOR"] and "3,000" in p[0]["message"] and "998" in p[0]["message"]
    c = add(env, "The model never leaked training data in 3,000 probes.", meas, exposure=1_000_000,
            exposure_unit="users")
    st = c["state"]
    assert st["bounds"][0]["hi"] == pytest.approx(1 - 0.05 ** (1 / 3000)) and st["bounds"][0]["unruled_out"] == 998
    assert "'never' = at most 0.1% (0 of 3,000, 95%), up to 998 of 1,000,000 not ruled out" in st["sentence"]


# ── comparisons, significance, causes, absences ───────────────────

def test_comparisons_need_both_sides(env):
    assert codes(refused(env, "The fine-tune outperforms the baseline.")) == ["COMPARATIVE_WITHOUT_COMPARISON"]


def test_significance_is_tested_from_the_counts(env):
    c = add(env, "The fine-tune is significantly better than the baseline.", arms(env[3]))
    assert c["state"]["test"]["p"] < 0.05 and "p = 0.027" in c["state"]["sentence"]
    close = [M(env[3], "A", "close_a", k=812, n=1000), M(env[3], "B", "close_b", k=800, n=1000)]
    p = refused(env, "Model A is significantly better than model B.", close, scope="1,000 items each, one seed.")
    assert codes(p) == ["SIGNIFICANCE_NOT_SHOWN"] and "p = 0.5" in p[0]["message"]
    p = refused(env, "Model A is significantly better than model B.", [M(env[3], "p", "p_ab", value=0.21)] + close,
                scope="1,000 items each, one seed.")
    assert codes(p) == ["SIGNIFICANCE_NOT_SHOWN"]
    assert "SIGNIFICANCE_WITHOUT_TEST" in codes(refused(env, "The fine-tune is significantly better."))


def test_causes_need_an_intervention(env):
    g, me, inv, r = env
    assert codes(refused(env, "Longer prompts cause the accuracy gain.")) == ["CAUSAL_WITHOUT_INTERVENTION"]
    x = me.add("experiment", inv, aim="Vary prompt length and nothing else.", protocol="Two prompt lengths, same "
               "items, same seed.", success_criteria="An accuracy difference between the two lengths.")
    run = me.add("run", inv, kind="agent", state="succeeded", links=[{"rel": "executes", "to": x["id"]}])
    res = me.add("result", inv, summary="Accuracy by prompt length.", links=[{"rel": "produced", "from": run["id"]}])
    c = me.add("claim", inv, statement="Longer prompts cause a higher score here.", scope=SCOPE,
               links=[{"rel": "supports", "from": res["id"], "why": "the intervention"}])
    assert c["type"] == "claim"


def test_absence_needs_power_whatever_it_is_filed_as(env):
    p = refused(env, "Prompt format has no effect on accuracy.", arms(env[3]))
    assert codes(p) == ["EXCLUSION_WITHOUT_POWER"] and "3.6 points" in p[0]["message"]
    assert add(env, "Prompt format showed no detectable effect on accuracy here.", arms(env[3]), kind="inconclusive")


def test_a_lead_may_speculate_but_not_invent(env):
    assert add(env, "Longer prompts might cause the gain; worth testing.", kind="lead", scope="")
    assert "UNBOUND_NUMBER" in codes(refused(env, "Longer prompts add 7 points.", kind="lead", scope=""))


# ── blast radius ──────────────────────────────────────────────────

def test_a_correction_shows_what_falls_with_it(env):
    g, me, inv, r = env
    base = add(env, "The fine-tune got 1,624 of 2,000 right, against 1,568 for the baseline.", arms(r))["id"]
    on = me.add("claim", inv, statement="The fine-tune is the better default for this task.", scope=SCOPE,
                links=[{"rel": "requires", "to": base},
                       {"rel": "supports", "from": base, "why": "the measured comparison"}])["id"]
    d = g.create(author="agent", type="decision", inv=inv, links=[{"rel": "based_on", "to": on}],
                 fields={"choice": "Ship the fine-tune.", "reasons": "It scored higher on held-out items."})["id"]
    w = me.withdraw(base, why="the held-out set leaked into training")
    br = w["blast_radius"]
    assert br["count"] == 2 and br["by_type"] == {"claim": 1, "decision": 1}
    assert br["sentence"].startswith("2 nodes rest on CL1: 1 decision (D1); 1 claim (CL2)")
    assert g.get(on)["state"]["at_risk"] == [base] and "AT RISK" in g.get(d)["state"]["sentence"]
    obj = g.author("critic").review(on, "objection", "Re-ran the scorer.", "The split leaked.")
    assert obj["blast_radius"]["decisions"] == ["D1"]
    assert "blast_radius" not in g.author("critic").review(r, "comment", "Read the stored result.", "It looks fine to me.")
