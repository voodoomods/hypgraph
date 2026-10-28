"""Honest sentences the rules were refusing — each one read off the refusal log of the challenge studies (96 records,
846 refusals, 2026-10-28) and replayed on all of them before shipping. The rule each test loosens is named; the
overclaim it still refuses is asserted beside it."""
import pytest

from hypgraph import Graph, GraphError, Policy

SCOPE = "SPEC.md's 12 cases on the current diff; corpus.csv's 400 rows; trial.csv, 20 outcomes, 120 per arm."


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}))
    me = g.author("tester")
    inv = me.investigation("Friction", "Find out which honest sentences the record refuses.")["id"]
    r = me.add("result", inv, summary="Counts and tests behind the sentences below.", values={
        "valid_pass": {"k": 7, "n": 8}, "quoted_differ": {"k": 49, "n": 49}, "padded": {"k": 0, "n": 49},
        "acf1": -0.100, "t": -3.87, "ci_lo": -0.149, "ci_hi": -0.050, "gap": 0, "objective": 656,
        "welch_two_sided_p": 0.012, "top_p": 0.9, "n_sig_holm": {"k": 0, "n": 20}, "p_holm_steps_k": 0.248,
        "violations": {"k": 2, "n": 4}, "gain_shared": 0.9})["id"]
    return g, me, inv, r


def M(r, key, **kw):
    return {"name": key.replace("_", " "), "result": r, "key": key, **kw}


def codes(env, statement, meas=(), scope=SCOPE, **kw) -> list[str]:
    g, me, inv, r = env
    try:
        me.add("claim", inv, statement=statement, scope=scope, measurements=list(meas),
               links=[{"rel": "supports", "from": r, "why": "the counts and tests behind it"}], **kw)
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


# ── absolutes ─────────────────────────────────────────────────────

def test_an_absolute_over_a_set_the_sentence_counts_is_not_a_generalisation(env):
    r = env[3]
    for s, m in (("Cases 1-7 all pass, so 7 of 8 valid cases are right.", [M(r, "valid_pass", k=7, n=8)]),
                 ("49 rows hold a quoted comma and all 49 of that kind differ.", [M(r, "quoted_differ", k=49, n=49)]),
                 ("None of these 49 core rows carries a space-padded field.", [M(r, "padded", k=0, n=49)]),
                 ("Almost all of the gain is shared with the untutored group.", [M(r, "gain_shared", value=0.9)])):
        assert "ABSOLUTE_WITHOUT_COUNT" not in codes(env, s, m), s
    assert "ABSOLUTE_WITHOUT_COUNT" in codes(env, "The parser never drops a field.", [])


def test_zero_as_a_number_and_an_interval_s_side_are_not_absolutes(env):
    r = env[3]
    m = [M(r, "acf1", value=-0.100), M(r, "t", value=-3.87), M(r, "ci_lo", value=-0.149), M(r, "ci_hi", value=-0.050)]
    s = ("The lag-1 autocorrelation is -0.100 and is distinguishable from zero: t = -3.87, and the 95% interval "
         "-0.149 to -0.050 lies entirely below zero.")
    assert "ABSOLUTE_WITHOUT_COUNT" not in codes(env, s, m)


def test_cannot_be_used_and_proven_with_its_bound_are_deductions(env):
    r = env[3]
    assert "ABSOLUTE_WITHOUT_COUNT" not in codes(
        env, "PLAN.md's rota cannot be used: it breaks 2 of the 4 certification rules.", [M(r, "violations", k=2, n=4)])
    s = "The optimum is 656, proven by exhaustive enumeration (gap 0)."
    assert "ABSOLUTE_WITHOUT_COUNT" not in codes(env, s, [M(r, "objective", value=656), M(r, "gap", value=0)])
    assert "ABSOLUTE_WITHOUT_COUNT" in codes(env, "The optimum is 656, proven.", [M(r, "objective", value=656)])


# ── significance and exclusion ────────────────────────────────────

def test_a_p_value_is_found_by_its_key_s_tokens(env):
    r = env[3]
    s = "steps_k differs between the arms at uncorrected p = 0.012, significant at 0.05."
    assert "SIGNIFICANCE_WITHOUT_TEST" not in codes(env, s, [M(r, "welch_two_sided_p", value=0.012)])
    from hypgraph.checks import _is_p_key
    assert all(_is_p_key(k) for k in ("p", "p_value", "p_welch", "welch_two_sided_p", "raw_p_steps_k", "steps_k_p", "pval"))
    assert not any(_is_p_key(k) for k in ("top_p", "n_participants", "mean_placebo", "steps_k", "min_p_holm_thr",
                                           "bonferroni_alpha_threshold", "p_cutoff"))


def test_no_difference_remains_significant_denies_a_test_and_needs_no_power(env):
    r = env[3]
    s = ("After correcting for the 20 outcomes tested, no difference between the arms remains significant: "
         "0 of 20 survive Holm (smallest Holm p = 0.248).")
    out = codes(env, s, [M(r, "n_sig_holm", k=0, n=20), M(r, "p_holm_steps_k", value=0.248)])
    assert "EXCLUSION_WITHOUT_POWER" not in out and "SIGNIFICANCE_CONTRADICTED" not in out
    assert "EXCLUSION_WITHOUT_POWER" not in codes(
        env, "The 95% interval -0.149 to -0.050 excludes zero.", [M(r, "ci_lo", value=-0.149), M(r, "ci_hi", value=-0.050)])
    # "not significant after correction" is not contradicted by the raw p it binds, and a denial beside an asserted
    # effect ("exactly one differs; the other 19 are not significant") is about the others
    s = "After Holm correction for the 20 outcomes, no outcome remains significant (raw p = 0.012 for steps_k)."
    assert "SIGNIFICANCE_CONTRADICTED" not in codes(env, s, [M(r, "welch_two_sided_p", value=0.012)])
    s = "Exactly one of the 20 outcomes differs at uncorrected p = 0.012: steps_k; the other 19 are not significant."
    assert "SIGNIFICANCE_CONTRADICTED" not in codes(env, s, [M(r, "welch_two_sided_p", value=0.012)])
    assert "SIGNIFICANCE_CONTRADICTED" in codes(env, "steps_k is not significant (p = 0.012).", [M(r, "welch_two_sided_p", value=0.012)])
    # "statistically indistinguishable" denies a test; it is not "statistically" asserted with a p of 0.617
    s = "The selected days are statistically indistinguishable from the rest (Mann-Whitney p = 0.617)."
    assert "SIGNIFICANCE_NOT_SHOWN" not in codes(env, s, [M(r, "mannwhitney_p", value=0.617)])
    assert "EXCLUSION_WITHOUT_POWER" in codes(env, "The supplement has no effect on steps_k.", [])


# ── numbers and keys ──────────────────────────────────────────────

def test_a_key_beside_its_value_and_a_hyphenated_number_word_and_a_date_pass(env):
    r = env[3]
    s = "n_sig_holm = 0 of 20 after a two-sided Welch test on 2026-10-28."
    out = codes(env, s, [M(r, "n_sig_holm", k=0, n=20)])
    assert "KEY_FOR_NUMBER" not in out and "UNBOUND_NUMBER" not in out
    assert "KEY_FOR_NUMBER" in codes(env, "The value of n_sig_holm says it.", [M(r, "n_sig_holm", k=0, n=20)])


# ── results ───────────────────────────────────────────────────────

def _opt():
    g = Graph(policy=Policy(reviewers={"verifier"}, instrument="instrument"))
    inv = g.create(author="lead", type="investigation", fields={"title": "Load the van.", "profile": "optimization@2",
                   "objective": "Find the best selection under the weight limit."})["id"]
    return g, inv


def test_the_instrument_s_re_execution_is_not_asked_for_feasibility_but_the_solver_is():
    g, inv = _opt()
    body = {"kind": "computed", "summary": "Re-executed RUN3's code: 7 of 9 registered values confirmed.",
            "values": {"objective": 656, "bound": 656, "gap": 0}}

    def refused_as(author):
        try:
            g.create(author=author, type="result", inv=inv, fields=body)
        except GraphError as e:
            return {p["code"] for p in e.problems}
        return set()
    assert "OBJECTIVE_WITHOUT_FEASIBILITY" not in refused_as("instrument")   # (the workflow still wants an instance)
    assert "OBJECTIVE_WITHOUT_FEASIBILITY" in refused_as("solver")


def test_a_count_s_k_and_n_must_be_numbers():
    g = Graph(policy=Policy(reviewers={"risk"}))
    inv = g.create(author="lead", type="investigation", fields={"title": "Test the crossover.",
                   "objective": "Find out whether the crossover beats buy and hold after costs."})["id"]
    with pytest.raises(GraphError) as e:
        g.create(author="quant", type="result", inv=inv, fields={"summary": "The best in-sample setting of the grid and how many beat buy and hold.", "values": {
            "best_of_grid": {"k": "40/50", "n": "rank 1 of 20"}, "beaters": {"k": 2, "n": 20}}})
    assert "VALUE_NOT_A_NUMBER" in str(e.value) and "values.best_of_grid" in str(e.value) and "40/50" in str(e.value)
    ok = {"summary": "The best in-sample setting of the grid and how many beat buy and hold.", "values": {"best_of_grid": {"value": "40/50"}, "beaters": {"k": 2, "n": 20}}}
    assert g.create(author="quant", type="result", inv=inv, fields=ok)["type"] == "result"


def test_a_benchmark_s_return_is_not_a_return_earned_and_the_refusal_names_the_fields():
    g = Graph(policy=Policy(reviewers={"risk"}))
    inv = g.create(author="lead", type="investigation", fields={"title": "Test the crossover.", "profile": "trading@2",
                   "objective": "Find out whether the crossover beats buy and hold after costs."})["id"]
    ok = {"kind": "computed", "summary": "Buy and hold over the out-of-sample window.",
          "values": {"buy_hold_oos_return": -0.027, "n_returns": 749}}
    assert g.create(author="quant", type="result", inv=inv, fields=ok)["type"] == "result"
    with pytest.raises(GraphError) as e:
        g.create(author="quant", type="result", inv=inv, fields={"kind": "computed", "summary": "The strategy.",
                 "values": {"oos_return": -0.19, "buy_hold_oos_return": -0.027}})
    assert "BACKTEST_WITHOUT_COSTS" in str(e.value) and "oos_return" in str(e.value) and "values.fees" in str(e.value)
