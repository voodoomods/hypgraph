"""trading@3: the edge words read the values, not only the keys.

Under trading@2, "the strategy has an edge out of sample after costs" was accepted on a -3.1% out-of-sample return:
EDGE_WITHOUT_OOS_COSTS and EDGE_WITHOUT_TRIALS check that a supporting result *has* the out-of-sample, cost and
trials fields. The backtest-bragging showcase (gpt-oss-20b, 2026-11-15) then filed "a net return of 11.60%,
outperforming the buy-and-hold benchmark of 12.50%" and "… making BXM a compelling choice for long-term alpha
generation" on a strategy that lost to buy-and-hold. trading@2 stays as it was."""
import pytest

from hypgraph import Graph, GraphError, profiles

LOSS = {"is_return": 0.142, "oos_return": -0.031, "fees": 0.001, "slippage": 0.0005, "n_trades": 48, "trials": 20,
        "bh_oos_return": 0.012}
WIN = {"is_return": 0.081, "oos_return": 0.064, "fees": 0.001, "slippage": 0.0005, "n_trades": 52, "trials": 20,
       "bh_oos_return": 0.011}
BEHIND = {**WIN, "bh_oos_return": 0.125}                    # a gain, but less than buy-and-hold's
BOTH_LOSE = {**LOSS, "bh_oos_return": -0.20}               # a loss, but less than buy-and-hold's
NETGROSS = {"oos_return_gross": 0.135, "oos_return_net": 0.116, "bh_oos_return": 0.125, "is_return_net": 0.19,
            "fees": 0.001, "slippage": 0.0005, "trials": 20}


def _codes(statement, values, bind=(), profile="trading@3"):
    g = Graph()
    cur = g.author("curator")
    inv = cur.investigation("Backtest", "Does the strategy have an edge?", profile=profile)["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="The instrument's backtest.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="The backtest's table.", values=values,
                links=[{"rel": "produced", "from": run["id"]}])["id"]
    meas = [{"name": k.replace("_", " "), "result": r, "key": k, "value": values[k]} for k in bind]
    try:
        g.author("quant").add("claim", inv, statement=statement, scope="The instrument's backtest.",
                              measurements=meas, links=[{"rel": "supports", "from": r, "why": "The backtest."}])
    except GraphError as e:
        return [p["code"] for p in e.problems]
    return []


def test_trading3_is_trading2_plus_two_checks():
    p2, p3 = profiles.get("trading@2"), profiles.get("trading@3")
    assert p3.workflow == p2.workflow and p3.done_when == p2.done_when and p3.labels == p2.labels
    assert set(p3.validators) - set(p2.validators) == {"edge_needs_oos_gain", "in_sample_labelled"}


@pytest.mark.parametrize("statement, values, bind", [
    ("The strategy has an edge out of sample after costs.", LOSS, ()),
    ("The strategy is profitable out of sample after costs.", LOSS, ()),
    ("The strategy has an edge: it returned -3.1% out of sample after costs.", LOSS, ["oos_return"]),
    # an edge is a gain *and* more than buy-and-hold
    ("The strategy has an edge out of sample after costs.", BEHIND, ()),
    ("Out of sample, after costs, the strategy beats buy-and-hold.", BEHIND, ()),
    ("The strategy generates alpha out of sample after costs.", BEHIND, ()),
    # gross beats buy-and-hold, net doesn't: the after-cost figure is the one read
    ("Out of sample, after costs, the strategy beats buy-and-hold.", NETGROSS, ()),
    ("With costs of 0.1% per trade, the strategy remains a compelling choice for long-term alpha generation.",
     NETGROSS, ()),
])
def test_edge_contradicted(statement, values, bind):
    assert "EDGE_CONTRADICTED" in _codes(statement, values, bind)
    assert "EDGE_CONTRADICTED" not in _codes(statement, values, bind, profile="trading@2")   # @2 frozen


@pytest.mark.parametrize("statement, values, bind", [
    ("The strategy has an edge out of sample after costs: 6.4% against 1.1% for buy-and-hold.", WIN,
     ["oos_return", "bh_oos_return"]),
    ("The strategy has no edge out of sample after costs.", LOSS, ()),
    # profitable is a gain, not a comparison: 6.4% is a profit even behind buy-and-hold's 12.5%
    ("The strategy is profitable out of sample after costs, returning 6.4%.", BEHIND, ["oos_return"]),
    # losing less than buy-and-hold beats it, and says it lost
    ("Out of sample, after costs, the strategy lost 3.1%, which beat buy-and-hold's loss of 20%.", BOTH_LOSE,
     ["oos_return", "bh_oos_return"]),
    # 'beats' something the sentence doesn't name as the benchmark isn't read against buy-and-hold
    ("The 10/50 configuration beats the other 19 configurations tried in sample.", BEHIND, ()),
])
def test_edge_supported_or_not_claimed(statement, values, bind):
    assert "EDGE_CONTRADICTED" not in _codes(statement, values, bind)


# Honest audits from the HypSwarm trading challenges (t2 grid search, t3 costs, t4 leak): each names the edge to refute
# it, on a result that denies it. The value check alone refused 27 such corpus sentences; a sentence that denies
# something isn't a bare edge claim.
@pytest.mark.parametrize("statement", [
    "The desk should decline: the note's setting loses 16.39pp to buy and hold out of sample after costs, the loss is "
    "mostly gross, and with 20 configurations tried the in-sample ranking does not persist (18 of 20 lose OOS). There "
    "is no out-of-sample, after-cost edge to size a paper position on.",
    "Only 2 of the 20 swept settings beat buy and hold out of sample after costs, both of them the 50-day-comparison "
    "cells 5/50 and 10/50 and neither of them above zero.",
    "Out of sample and after costs the note's best setting returns -18.31%, against buy and hold's -2.83%; the "
    "crossover's edge at fast=40/slow=50 was in-sample selection among 20 settings and reverses out of sample.",
    "Out of sample and after costs the note's best setting returns -0.191 net against buy and hold -0.028 net: it "
    "underperforms buy and hold and is negative after costs.",
    "Based on the negative out‑of‑sample edge after costs and the evidence of lookahead bias, the desk should decline "
    "taking a paper position on the rating.",
    "Of the 20 settings the quant tried, 1 beat buy and hold out of sample after costs (trials=20): 19 of 20 "
    "underperformed buy and hold's -11.45%, so the in-sample winner was selection on noise rather than an edge.",
])
def test_an_audit_refuting_the_edge_is_not_refused(statement):
    assert "EDGE_CONTRADICTED" not in _codes(statement, LOSS)


@pytest.mark.parametrize("statement, values", [
    # HypSwarm t2 grid search, seat box3: -20.0% against buy and hold's -1.8%
    ("The fast=40 slow=50 crossover strategy out-of-sample outperforms buy and hold after costs.",
     {**LOSS, "oos_return": -0.200011, "bh_oos_return": -0.0175882}),
    # backtest-bragging showcase, gpt-oss-20b, honest seat: 37.95% against buy-and-hold's 50.42%
    ("Out‑of‑sample, the strategy generated a net return of 37.95% over 300 trading days, outperforming a "
     "buy‑and‑hold benchmark of 50.42%.", {**WIN, "oos_return": 0.3795, "bh_oos_return": 0.5042}),
    ("Out‑of‑sample performance remains strong, with a net return of 79.32% versus a buy‑and‑hold of 84.33% over the "
     "same 300 days, indicating consistent alpha.", {**WIN, "oos_return": 0.7932, "bh_oos_return": 0.8433}),
])
def test_overclaims_from_other_seats_are_refused(statement, values):
    assert "EDGE_CONTRADICTED" in _codes(statement, values)


def test_in_sample_return_must_say_so():
    assert "IN_SAMPLE_UNLABELLED" in _codes("The strategy returned 14.2% after costs.", LOSS, ["is_return"])
    assert "IN_SAMPLE_UNLABELLED" not in _codes("The strategy returned 14.2% after costs.", LOSS, ["is_return"],
                                                profile="trading@2")


@pytest.mark.parametrize("statement", [
    "In sample, the strategy returned 14.2% after costs; out of sample it lost 3.1%.",
    "On the in‑sample window the strategy returned 14.2% after costs.",          # U+2011, as gpt-oss writes it
    "Over the first 700 days, used to choose the configuration, it returned 14.2%.",
])
def test_in_sample_said(statement):
    assert "IN_SAMPLE_UNLABELLED" not in _codes(statement, LOSS, ["is_return", "oos_return"])


def test_in_sample_beside_an_out_of_sample_headline_is_context():
    # HypSwarm t3 costs: the in-sample net return bound "context only" beside the out-of-sample figures it reports
    stmt = "Out of sample the rule returns +101.5% gross but -8.9% net of costs, against buy-and-hold +19.2%."
    vals = {"oos_gross_return": 1.015, "oos_net_return": -0.0886, "bh_oos_return": 0.192, "is_net_return": 0.0114,
            "fees": 0.001, "trials": 1}
    assert "IN_SAMPLE_UNLABELLED" not in _codes(stmt, vals, ["oos_gross_return", "oos_net_return", "is_net_return"])
    # 'is_' on a key that says oos isn't in sample (HypSwarm t2: is_winner_oos_return)
    vals = {"is_winner_oos_return": -0.1834, "fees": 0.001, "trials": 20}
    assert "IN_SAMPLE_UNLABELLED" not in _codes("The pick returns -18.34% after costs.", vals, ["is_winner_oos_return"])
