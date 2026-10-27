"""Measuring returns isn't trading them, and a confidence interval that leaves out zero isn't an exclusion. A real-model
trading run (studies T3, a mean-reversion edge) lost eight writes to BACKTEST_WITHOUT_COSTS on a lag-1
autocorrelation, because the result also counted its returns (`n_returns`), and three claims to
EXCLUSION_WITHOUT_POWER for "the bootstrap 95% CI excludes zero" — which says the effect is there."""
import pytest

from hypgraph import Graph, GraphError, Policy
from hypgraph import language as L

H = "harness"


def _trading():
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={H}))
    inv = g.create(author=H, type="investigation", fields={"title": "Reversal.", "profile": "trading@1",
                   "objective": "Measure the reversal before backtesting it."})["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q1",
                 fields={"text": "Is the lag-1 autocorrelation of daily returns distinguishable from zero?"})["id"]
    return g, inv, q


def _result(g, inv, values, summary="Lag-1 autocorrelation of daily returns, in sample."):
    run = g.create(author="quant", type="run", inv=inv, fields={"kind": "agent", "name": "acf", "state": "succeeded"})
    return g.create(author="quant", type="result", inv=inv, fields={"summary": summary, "values": values,
                    "outcome": "positive"}, links=[{"rel": "produced", "from": run["id"]}])["id"]


@pytest.mark.parametrize("values", [
    {"acf1_insample": {"value": -0.09995, "unit": "correlation"}, "insample_n_returns": {"value": 1499, "unit": "returns"}},
    {"autocorr_lag1": {"value": -0.1008, "unit": "correlation"}, "n_return_obs_in": {"value": 1500, "unit": "returns"}},
    {"acf1": {"value": -0.100, "unit": "acf"}, "N_returns_in_sample": {"value": 1500, "unit": "returns"},
     "return_t_stat": {"value": -3.87}, "return_p_value": {"value": 0.0001}},
])
def test_a_statistic_and_a_count_of_returns_need_no_costs(values):
    g, inv, _q = _trading()
    _result(g, inv, values)


def test_a_return_earned_still_needs_costs():
    g, inv, _q = _trading()
    with pytest.raises(GraphError, match="BACKTEST_WITHOUT_COSTS"):
        _result(g, inv, {"oos_return": {"value": 0.756}, "n_trades": {"value": 795, "unit": "trades"}},
                summary="Out-of-sample return of the reversal rule.")


@pytest.mark.parametrize("text", ["the bootstrap 95% CI excludes zero", "the interval excludes 0.0",
                                  "the odds ratio's CI excludes 1", "a shuffle test rules out chance"])
def test_leaving_out_the_null_is_not_an_exclusion(text):
    assert L.asserted(L.EXCLUSION, text) == []


@pytest.mark.parametrize("text", ["the trial rules out an effect", "the data exclude a benefit", "there is no effect"])
def test_real_exclusions_still_count(text):
    assert L.asserted(L.EXCLUSION, text)


def test_a_claim_that_the_interval_excludes_zero_is_written():
    g, inv, q = _trading()
    rs = _result(g, inv, {"acf1": {"value": -0.100}, "boot_ci_lo": {"value": -0.144}, "boot_ci_hi": {"value": -0.048}})
    g.create(author="quant", type="claim", inv=inv, fields={
        "statement": "The lag-1 autocorrelation is -0.100 and its bootstrap 95% CI [-0.144, -0.048] excludes zero.",
        "scope": "bars.csv, days 0-1499.",
        "measurements": [{"name": "acf1", "key": "acf1", "result": rs}, {"name": "lo", "key": "boot_ci_lo", "result": rs},
                         {"name": "hi", "key": "boot_ci_hi", "result": rs}]},
        links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])
