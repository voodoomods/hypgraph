"""Claim policies: checks on one kind of claim that attach to an investigation beside whatever profile it pins.

A profile says how the work proceeds. A claim policy says what one kind of sentence is held to. `evaluation@1` was
released as a profile that copies `scientific@2`'s lifecycle and adds three checks; as a claim policy
(`baseline_comparison@1`) the same checks run under any profile, or under none."""
from __future__ import annotations

import pytest

from hypgraph import Graph, profiles
from hypgraph.graph import GraphError

SCOPE = "AUC of the new model and the baseline on the validation and test splits, test as the mean of 5 seeds."
RED = {"val_auc_model": 0.84, "val_auc_baseline": 0.82, "test_auc_model": 0.79, "test_auc_baseline": 0.81,
       "test_seeds_ahead": {"k": 1, "n": 5}, "higher_is_better": True}
WIN = "The new churn model beats the baseline."
PIN = {"claim_policies": ["baseline_comparison@1"]}


def investigation(g: Graph, **pin) -> str:
    return g.author("curator").investigation("Is the new model better than the baseline?",
                                             "Report how the new model compares with the baseline.", scope=SCOPE,
                                             **pin)["id"]


def filed(statement: str, values: dict = RED, **pin) -> list[str]:
    """File one claim against a result with these values under what is pinned; the refusal codes, or []."""
    g = Graph(None)
    lab = g.author("lab")
    inv = investigation(g, **pin)
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Evaluation run.")
    res = lab.add("result", inv, kind="computed", outcome="negative", summary="The evaluation harness's scores.",
                  values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    meas = [dict({"key": k, "name": k.replace("_", " "), "result": res}, **(v if isinstance(v, dict) else {"value": v}))
            for k, v in values.items() if not isinstance(v, bool)]
    try:
        g.author("ml-agent").add("claim", inv, kind="finding", statement=statement, scope=SCOPE, measurements=meas,
                                 links=[{"rel": "supports", "from": res, "why": "The evaluation report."}])
        return []
    except GraphError as e:
        return [p["code"] for p in e.problems]
    finally:
        g.close()


# ── the same checks, wherever they are pinned ──
@pytest.mark.parametrize("pin", [
    {"profile": "evaluation@1"},                                   # the released profile
    {"profile": "scientific@2", **PIN},                            # what it is a name for
    PIN,                                                           # the policy with no profile
    {"profile": "software@3", **PIN},                              # beside another discipline
])
def test_the_win_is_held_to_the_held_out_scores_wherever_the_policy_is_pinned(pin):
    assert filed(WIN, **pin) == ["WIN_CONTRADICTED"]
    assert filed("The new churn model does not beat the baseline on the test split: 0.79 against 0.81.", **pin) == []


def test_a_policys_refusals_are_added_to_the_profiles_own():
    # trading@3 reads "beats the baseline" as an edge claim and has its own two things to say about it
    alone, both = filed(WIN, profile="trading@3"), filed(WIN, profile="trading@3", **PIN)
    assert alone and "WIN_CONTRADICTED" not in alone
    assert set(both) == set(alone) | {"WIN_CONTRADICTED"}


@pytest.mark.parametrize("pin", [{}, {"profile": "scientific@2"}, {"profile": "software@3"}])
def test_without_the_policy_the_line_is_read_as_it_was(pin):
    assert filed(WIN, **pin) == []


def test_evaluation1_is_exactly_scientific2_with_the_policy():
    e, s, c = profiles.get("evaluation@1"), profiles.get("scientific@2"), profiles.CLAIM_POLICIES["baseline_comparison@1"]
    assert e.validators == s.validators + c.validators
    assert (e.workflow, e.done_when, e.predicates, e.completion, e.seats) == \
        (s.workflow, s.done_when, s.predicates, s.completion, s.seats)
    assert "baseline_comparison@1" in e.deprecated and not s.deprecated


def test_the_census_of_seeds_follows_the_policy():
    green = dict(RED, test_auc_model=0.86, test_auc_baseline=0.83, test_seeds_ahead={"k": 5, "n": 5})
    line = "The new churn model is ahead of the baseline on all test seeds."
    assert filed(line, green, profile="scientific@2", **PIN) == []
    assert filed(line, green, **PIN) == []
    assert filed(line, green, profile="scientific@2") != []          # without it, "all" on 5 of 5 is a sample


def test_the_result_check_follows_the_policy():
    undirected = {k: v for k, v in RED.items() if k != "higher_is_better"}

    def result_codes(**pin) -> list[str]:
        g = Graph(None)
        inv = investigation(g, **pin)
        who = g.author("ml-agent")
        run = who.add("run", inv, kind="external", state="succeeded", name="My evaluation run.")
        try:
            who.add("result", inv, kind="computed", outcome="negative",
                    summary="The scores of the new model and the baseline on both splits.", values=undirected,
                    links=[{"rel": "produced", "from": run["id"]}])
            return []
        except GraphError as e:
            return [p["code"] for p in e.problems]
        finally:
            g.close()

    assert "EVAL_WITHOUT_DIRECTION" in result_codes(**PIN)
    assert "EVAL_WITHOUT_DIRECTION" in result_codes(profile="evaluation@1")
    assert "EVAL_WITHOUT_DIRECTION" not in result_codes()


# ── a policy reads one kind of sentence and nothing else ──
def test_a_comparison_with_no_scores_is_refused_for_want_of_them_and_every_other_sentence_is_untouched():
    tests = {"tests_passed": {"k": 14, "n": 14}, "exit_code": 0}
    line = "The new parser is better than the old one on the cases we tried."
    # a sentence of the policy's kind, on a result that holds no score pair: it says there is nothing to hold it to
    assert filed(line, tests, **PIN) == ["WIN_WITHOUT_HELDOUT"]
    assert filed(line, tests) == []
    assert filed("14 of 14 tests passed, exit code 0.", tests, **PIN) == filed("14 of 14 tests passed, exit code 0.",
                                                                               tests)


def test_a_policy_never_stands_down_a_profiles_check():
    failing = {"tests_passed": {"k": 26, "n": 29}, "exit_code": 1}
    line = "All tests pass."
    assert filed(line, failing, profile="software@3") == filed(line, failing, profile="software@3", **PIN) != []


# ── pinning ──
def test_an_unknown_policy_is_refused_when_the_investigation_is_created():
    g = Graph(None)
    with pytest.raises(GraphError, match="unknown claim policy"):
        investigation(g, claim_policies=["baseline_comparison@9"])


def test_the_ids_are_stored_once_and_sorted():
    g = Graph(None)
    inv = investigation(g, claim_policies=["BASELINE_COMPARISON@1", "baseline_comparison@1"])
    assert g.get(inv)["body"]["claim_policies"] == ["baseline_comparison@1"]
    assert "claim_policies" not in g.get(investigation(g, claim_policies=[]))["body"]
    assert g.verify_chain()["ok"]


def test_policies_are_pinned_when_the_investigation_is_created():
    g = Graph(None)
    cur = g.author("curator")
    bare, pinned = investigation(g), investigation(g, **PIN)
    with pytest.raises(GraphError, match="pinned when the investigation is created"):
        cur.revise(bare, "Adding a policy to a live investigation.", claim_policies=["baseline_comparison@1"])
    with pytest.raises(GraphError, match="pinned when the investigation is created"):
        cur.revise(pinned, "Taking the policy off a live investigation.", claim_policies=[])
    cur.revise(pinned, "A clearer objective for the same investigation.",
               objective="Report how the new churn model compares with the baseline on held-out data.",
               claim_policies=["baseline_comparison@1"])           # the same set is no change
    assert g.get(pinned)["body"]["claim_policies"] == ["baseline_comparison@1"]


# ── listings ──
def test_the_listing_says_what_each_policy_reads_refuses_and_relaxes():
    d = profiles.describe_claim_policies()["baseline_comparison@1"]
    assert "WIN_CONTRADICTED" in d["refuses"] and d["reads"] and d["relaxes"]
    assert profiles.describe()["evaluation@1"]["deprecated"]
    assert "deprecated" not in profiles.describe()["scientific@2"]


def test_what_an_investigation_is_held_to():
    g = Graph(None)
    inv = investigation(g, profile="scientific@2", **PIN)
    s = g.snapshot()
    assert profiles.pinned(s, inv) == {"profile": "scientific@2", "claim_policies": ["baseline_comparison@1"]}
    assert "win_held_to_heldout" in profiles.held_to(s, inv)
    assert "win_held_to_heldout" not in profiles.held_to(s, investigation(g, profile="scientific@2"))
