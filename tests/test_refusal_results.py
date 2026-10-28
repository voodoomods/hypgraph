"""The refusal log treats results like claims: logged in full, fixed by the author's next honest result, replayed
through the result checks. Before this, every result code showed 0 fixed (the fix matcher keyed on a statement
results don't have), a trading claim refused by the profile replayed as "passes" (replay ran the claim checks
only), and a decision's choice replayed as if it were a claim."""
import pytest

from hypgraph import Graph, GraphError, Policy


@pytest.fixture
def trading():
    g = Graph(policy=Policy(reviewers={"risk"}))
    inv = g.create(author="lead", type="investigation", fields={"title": "Test the crossover.", "profile": "trading@2",
                   "objective": "Find out whether the crossover beats buy and hold after costs."})["id"]
    return g, inv


def _codes(e: GraphError) -> set[str]:
    return {p["code"] for p in e.problems}


def test_a_refused_result_is_logged_in_full_and_fixed_by_the_honest_one(trading):
    g, inv = trading
    quant = g.author("quant")
    with pytest.raises(GraphError) as e:
        quant.add("result", inv, kind="computed", summary="The crossover out of sample.",
                  values={"oos_return": -0.19, "oos_trades": 31})
    assert "BACKTEST_WITHOUT_COSTS" in _codes(e.value)
    row = g.refusals(inv)[0]
    assert row["statement"] == "The crossover out of sample." and row["fixed_by"] is None
    ok = quant.add("result", inv, kind="computed", summary="The crossover out of sample, after 10 bps per trade.",
                   values={"oos_return": -0.21, "oos_trades": 31, "fees": 0.001})
    assert ok["fixes_refusals"] == [row["id"]]
    rep = g.refusal_report(inv)
    assert rep["refused"] == 1 and rep["fixed"] == 1
    assert g.refusals(inv)[0]["fixed_by"]["code"] == ok["code"]


def test_a_result_that_carries_the_refused_keys_again_fixes_it_whatever_its_summary_says(trading):
    g, inv = trading
    quant = g.author("quant")
    with pytest.raises(GraphError):
        quant.add("result", inv, kind="computed", summary="Grid best.", values={"best_oos_return": -0.18,
                  "worst_oos_return": -0.31, "n_settings": 20})
    ok = quant.add("result", inv, kind="computed", summary="Twenty settings, out of sample, costs charged.",
                   values={"best_oos_return": -0.19, "worst_oos_return": -0.33, "n_settings": 20, "fees": 0.001})
    assert ok.get("fixes_refusals")
    other = g.author("risk").add("result", inv, kind="computed", summary="Buy and hold over the window.",
                                 values={"buy_hold_oos_return": -0.027})
    assert "fixes_refusals" not in other                    # another author's result fixes nothing of the quant's


def test_replay_runs_results_through_the_result_checks_and_claims_through_the_profile_s(trading):
    g, inv = trading
    quant = g.author("quant")
    with pytest.raises(GraphError):
        quant.add("result", inv, kind="computed", summary="The crossover out of sample.", values={"oos_return": -0.19})
    with pytest.raises(GraphError):
        quant.add("result", inv, kind="computed", summary="A label in a count's clothes.",
                  values={"best": {"k": "40/50", "n": "rank 1 of 20"}, "fees": 0.001})
    r = quant.add("result", inv, kind="computed", summary="After costs.",
                  values={"oos_return": -0.21, "fees": 0.001, "oos_trades": 31})["id"]
    with pytest.raises(GraphError) as e:
        quant.add("claim", inv, statement="The crossover has an edge over buy and hold.",
                  scope="prices.csv, 2000 daily closes.", links=[{"rel": "derived_from", "to": r}])
    assert "EDGE_WITHOUT_TRIALS" in _codes(e.value)
    rep = g.replay_refusals(inv)
    rows = {x["statement"]: x for x in rep["rows"]}
    assert rows["The crossover out of sample."]["type"] == "result"
    assert rows["The crossover out of sample."]["verdict"] == "same"
    assert "VALUE_NOT_A_NUMBER" in rows["A label in a count's clothes."]["now"]
    assert rows["The crossover has an edge over buy and hold."]["type"] == "claim"
    assert "EDGE_WITHOUT_TRIALS" in rows["The crossover has an edge over buy and hold."]["now"]
    assert rep["replayed"] == 3 and rep["verdicts"] == {"same": 3}


def test_restated_results_and_typed_nodes_are_skipped_not_replayed_as_claims():
    g = Graph(policy=Policy(reviewers={"critic"}))
    lead = g.author("lead")
    inv = lead.investigation("Counts", "Count the rows and keep the count once.")["id"]
    a = g.author("analyst")
    a.add("result", inv, summary="607 of 821 rows pass.", values={"pass": {"k": 607, "n": 821}})
    with pytest.raises(GraphError) as e:
        a.add("result", inv, summary="Counted again: 607 of 821 rows pass.", values={"pass": {"k": 607, "n": 821}})
    assert "RESULT_RESTATES" in _codes(e.value)
    row = g.refusals(inv)[0]
    assert row["statement"] == "Counted again: 607 of 821 rows pass."      # logged like any result, in full
    rep = g.replay_refusals(inv)
    assert rep["replayed"] == 0 and rep["skipped"] == {"RESULT_RESTATES": 1}
