"""A nominal effect can't hide its correction in the scope. In a 20-outcome trial study (2026-10-27) two of twelve
runs settled "the supplement changes steps_k" as a checked finding — scope "unadjusted single-outcome test" — while
the same record's Holm-corrected p for steps_k was 0.25 and its Q2 claim said nothing survived correction. The
record held both and accepted the contradiction. Now a finding that asserts an effect on an outcome, while a live
result in the investigation holds that outcome's corrected p at or above 0.05 (or 0 outcomes surviving), must bind
a corrected value and name the correction in its statement — or be a lead."""
import pytest

from hypgraph import Graph, GraphError, Policy

SCOPE = "trial.csv, 240 randomised adults (120 per arm), steps_k, two-sided Welch test at alpha 0.05."


def env(corrected=True):
    g = Graph(policy=Policy(reviewers={"critic"}))
    me = g.author("analyst")
    inv = me.investigation("Supplement trial", "Find out which of the 20 outcomes the supplement changes.")["id"]
    raw = me.add("result", inv, summary="Welch tests on all 20 outcomes: only steps_k differs at uncorrected p < 0.05.",
                 values={"p_steps_k": 0.012, "mean_supplement": 7.07, "mean_placebo": 7.87, "p_hdl": 0.18})["id"]
    corr = None
    if corrected:
        corr = me.add("result", inv, summary="Holm and Bonferroni over the family of 20: nothing survives.",
                      values={"p_holm_steps_k": 0.248, "n_holm_sig": {"k": 0, "n": 20},
                              "bonferroni_alpha_threshold": 0.0025})["id"]
    return g, me, inv, raw, corr


def M(r, key, **kw):
    return {"name": key.replace("_", " "), "result": r, "key": key, **kw}


def nominal(raw):
    return [M(raw, "p_steps_k", value=0.012), M(raw, "mean_supplement", value=7.07), M(raw, "mean_placebo", value=7.87)]


def add(e, statement, meas, scope=SCOPE, **kw):
    g, me, inv, raw, corr = e
    return me.add("claim", inv, statement=statement, scope=scope, measurements=list(meas),
                  links=[{"rel": "supports", "from": raw, "why": "the Welch tests on every outcome"}], **kw)


def refused(e, statement, meas, **kw) -> list[dict]:
    with pytest.raises(GraphError) as x:
        add(e, statement, meas, **kw)
    return x.value.problems


OVERCLAIM = "The supplement changes steps_k: mean 7.07 on supplement vs 7.87 on placebo, p = 0.012."


def test_the_overclaim_is_refused_with_the_corrected_value_quoted():
    e = env()
    p = refused(e, OVERCLAIM, nominal(e[3]), scope=SCOPE + " Unadjusted single-outcome test.")
    assert [x["code"] for x in p] == ["UNCORRECTED_EFFECT"]
    assert "p_holm_steps_k = 0.248" in p[0]["message"] and "'changes'" in p[0]["message"]
    assert "kind=lead" in p[0]["fix"] and p[0]["words"] == ["changes"]


def test_the_honest_sentence_binds_the_corrected_p_and_says_so():
    e = env()
    honest = ("steps_k differs between the arms at uncorrected p = 0.012 (mean 7.07 vs 7.87), but the difference is "
              "not significant after Holm correction over the family (Holm p = 0.248).")
    c = add(e, honest, nominal(e[3]) + [M(e[4], "p_holm_steps_k", value=0.248)])
    assert c["type"] == "claim"          # and not SIGNIFICANCE_CONTRADICTED by the bound nominal 0.012


def test_binding_without_saying_and_saying_without_binding_are_both_refused():
    e = env()
    p = refused(e, OVERCLAIM, nominal(e[3]) + [M(e[4], "p_holm_steps_k", value=0.248)])
    assert [x["code"] for x in p] == ["UNCORRECTED_EFFECT"] and "bound, but the statement" in p[0]["message"]
    p = refused(e, OVERCLAIM + " It does not survive Holm correction.", nominal(e[3]))
    assert [x["code"] for x in p] == ["UNCORRECTED_EFFECT"] and "binds none" in p[0]["message"]


def test_a_sentence_that_says_uncorrected_tells_the_reader_what_it_rests_on():
    e = env()
    told = "Exactly one of the 20 outcomes differs between the arms at uncorrected p < 0.05: steps_k, p = 0.012."
    assert add(e, told, nominal(e[3]), scope=SCOPE + " 20 outcomes, no multiplicity correction.")["type"] == "claim"
    # ... but not when the qualifier sits in another sentence, far away in the same one, or only in the scope
    p = refused(e, OVERCLAIM + " The test was uncorrected.", nominal(e[3]))
    assert [x["code"] for x in p] == ["UNCORRECTED_EFFECT"]
    far = ("The supplement changes steps_k in this trial: mean steps_k is 7.07 on supplement against 7.87 on placebo, "
           "p = 0.012, so participants on the supplement took fewer steps; the statement of the direction above matches "
           "the press release's reported means while dropping its uncorrected p < 0.05 claim.")
    p = refused(e, far, nominal(e[3]))
    assert [x["code"] for x in p] == ["UNCORRECTED_EFFECT"]
    # the bare verb asserts it too ("does change" slipped past the replay once)
    p = refused(e, "The supplement does change steps_k in this trial: 7.07 vs 7.87, p = 0.012.", nominal(e[3]))
    assert [x["code"] for x in p] == ["UNCORRECTED_EFFECT"] and p[0]["words"] == ["change"]


def test_a_lead_may_say_it_and_so_may_a_finding_on_a_record_without_the_correction():
    e = env()
    assert add(e, OVERCLAIM, nominal(e[3]), kind="lead")["type"] == "claim"
    e2 = env(corrected=False)
    assert add(e2, OVERCLAIM, nominal(e2[3]))["type"] == "claim"


def test_only_the_corrected_outcome_is_held_to_it():
    e = env()
    g, me, inv, raw, corr = e
    me.add("result", inv, summary="Holm over the family, per outcome.", values={"p_holm_vitamin_d": 1.0})
    other = "hdl differs between the arms at p = 0.18."       # named in no corrected key; no nominal p < 0.05 bound
    assert add(e, other, [M(raw, "p_hdl", value=0.18)])["type"] == "claim"


def test_a_family_wide_value_applies_when_the_claim_rests_on_a_nominal_p():
    g = Graph(policy=Policy(reviewers={"critic"}))
    me = g.author("analyst")
    inv = me.investigation("Supplement trial", "Find out which of the 20 outcomes the supplement changes.")["id"]
    raw = me.add("result", inv, summary="Welch tests on all 20 outcomes.", values={"p_steps_k": 0.012})["id"]
    me.add("result", inv, summary="Holm over the family: the smallest adjusted p.", values={"min_adjusted_p": 0.25})
    e = (g, me, inv, raw, None)
    p = refused(e, "The supplement lowers steps_k (p = 0.012).", [M(raw, "p_steps_k", value=0.012)])
    assert [x["code"] for x in p] == ["UNCORRECTED_EFFECT"] and "min_adjusted_p = 0.25" in p[0]["message"]
    # a finding that binds no nominal p and names no corrected outcome is not about the family
    assert add(e, "The supplement arm walked less on average.", [])["type"] == "claim"


def test_a_surviving_or_withdrawn_corrected_value_does_not_refuse():
    g = Graph(policy=Policy(reviewers={"critic"}))
    me = g.author("analyst")
    inv = me.investigation("Supplement trial", "Find out which of the 20 outcomes the supplement changes.")["id"]
    raw = me.add("result", inv, summary="Welch tests on all 20 outcomes.", values={"p_steps_k": 0.0004})["id"]
    me.add("result", inv, summary="Holm over the family: steps_k survives.", values={"p_holm_steps_k": 0.008})
    e = (g, me, inv, raw, None)
    assert add(e, "The supplement changes steps_k (p = 0.0004).", [M(raw, "p_steps_k", value=0.0004)])["type"] == "claim"
    e = env()
    e[1].withdraw(e[4], why="the family was miscounted")
    assert add(e, OVERCLAIM, nominal(e[3]))["type"] == "claim"


def test_a_threshold_is_not_evidence():
    g = Graph(policy=Policy(reviewers={"critic"}))
    me = g.author("analyst")
    inv = me.investigation("Supplement trial", "Find out which of the 20 outcomes the supplement changes.")["id"]
    raw = me.add("result", inv, summary="Welch tests on all 20 outcomes.", values={"p_steps_k": 0.012})["id"]
    me.add("result", inv, summary="The Bonferroni threshold.", values={"bonferroni_alpha_threshold": 0.0025})
    e = (g, me, inv, raw, None)
    assert add(e, "The supplement changes steps_k (p = 0.012).", [M(raw, "p_steps_k", value=0.012)])["type"] == "claim"
