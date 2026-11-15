"""A comparison the bound measurements reverse: "A's 81% is higher than B's 84%".

Found in the backtest-bragging showcase (2026-11-15): "a net return of 11.6% …, outperforming the buy-and-hold
benchmark of 12.5%", both figures bound to the backtest's fields, was accepted from the pitching seat and from the
honest one. COMPARATIVE_WITHOUT_COMPARISON counted the measured sides and never read their order."""
import pytest

from hypgraph import Graph, GraphError

VALUES = {"accuracy_a": 0.81, "accuracy_b": 0.84, "error_a": 0.19, "error_b": 0.16, "oos_return": 0.064,
          "bh_oos_return": 0.125, "loss_return": -0.031, "bh_small": 0.012, "n_trades": 52, "trades_b": 48,
          "days": 300, "acc_a_k": {"k": 81, "n": 100}, "acc_b_k": {"k": 84, "n": 100}, "p_min": 0.0134, "n_sig": 1,
          "rotas": 2790, "best": 112, "items": 30,
          "time_limit_s": 60}


def _codes(statement, keys):
    g = Graph()
    cur = g.author("curator")
    inv = cur.investigation("Comparisons", "Which of the two does better on the run?")["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="The instrument's run.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="What the instrument measured.",
                values=VALUES, links=[{"rel": "produced", "from": run["id"]}])["id"]
    meas = [{"name": k.replace("_", " "), "result": r, "key": k,
             **(VALUES[k] if isinstance(VALUES[k], dict) else {"value": VALUES[k]})} for k in keys]
    try:
        g.author("seat").add("claim", inv, statement=statement, scope="The instrument's run.", measurements=meas,
                             links=[{"rel": "supports", "from": r, "why": "The instrument's run."}])
    except GraphError as e:
        return [p["code"] for p in e.problems]
    return []


ACC = ["accuracy_a", "accuracy_b"]
ERR = ["error_a", "error_b"]
RET = ["oos_return", "bh_oos_return"]


@pytest.mark.parametrize("statement, keys", [
    ("Model A's accuracy of 81% is higher than model B's accuracy of 84%.", ACC),
    ("Model A's accuracy of 81% exceeds model B's 84%.", ACC),
    ("Model B's accuracy of 84% is lower than model A's 81%.", ACC),
    ("Model A, at 81% accuracy, outperforms model B at 84%.", ACC),
    ("The strategy returned 6.4% out of sample after costs, outperforming buy-and-hold at 12.5%.", RET),
    ("A net return of 6.4% (after costs), beating the buy-and-hold benchmark of 12.5%.", RET),
    # an error is better lower: 19% beating 16% is the wrong way round
    ("Model A, with an error of 19%, outperforms model B at 16%.", ERR),
    # a loss is a negative figure: -3.1% is not above 1.2%
    ("The strategy's return of -3.1% is higher than buy-and-hold's 1.2%.", ["loss_return", "bh_small"]),
])
def test_reversed(statement, keys):
    assert "COMPARISON_REVERSED" in _codes(statement, keys)


@pytest.mark.parametrize("statement, keys", [
    ("Model B's accuracy of 84% is higher than model A's accuracy of 81%.", ACC),
    ("Model B's error of 16% is lower than model A's error of 19%.", ERR),
    ("Model B, with an error of 16%, outperforms model A at 19%.", ERR),
    ("Buy-and-hold's 1.2% is higher than the strategy's -3.1%.", ["loss_return", "bh_small"]),
    ("Buy-and-hold returned 12.5%, outperforming the strategy's 6.4%.", RET),
    # left alone: a difference before the word, a threshold, a negation, a multiple, figures after the word only
    ("Model B's accuracy is 3% higher than model A's 81%.", ["accuracy_a"]),
    ("Accuracy rose from 84% to more than 81%.", ACC),
    ("Model A's 81% does not exceed model B's 84%.", ACC),
    ("Model A's 81% is not higher than model B's 84%.", ACC),
    ("Model B outperforms model A: 84% against 81%.", ACC),
    # a figure of another kind before the word is not a side: 300 days, then 6.4% against 12.5%
    ("Over 300 days buy-and-hold returned 12.5%, more than the strategy's 6.4%.", RET + ["days"]),
    # a figure without its minus sign against a negative value: the size of a loss, or a fall — left alone
    # (backtest-bragging diagnostic: "a net loss of 4.66% is far less than the buy-and-hold loss of 56.73%")
    ("The strategy's net loss of 3.1% is less than buy-and-hold's loss of 12.5%.", ["loss_return", "bh_oos_return"]),
    ("The strategy returned 1.2%, outperforming a buy-and-hold that fell 3.1%.", ["bh_small", "loss_return"]),
    # from HypSwarm challenge records, all honest: a fraction's parts are not sides, nor is a hyphenated label, nor a
    # threshold inside an absolute, nor a figure named as a difference after the word
    ("Model B's accuracy (84/100 = 0.84) exceeds model A's (81/100 = 0.81).", ["acc_a_k", "acc_b_k"]),
    ("The smallest p is 0.0134, which exceeds the Holm step-1 threshold 0.0025.", ["p_min", "n_sig"]),
    ("None of those 2790 rotas costs less than 112 hours.", ["rotas", "best"]),
    ("Model A's error is 0.19, a gap smaller than 0.16 percentage points over model B.", ERR),
    # a negation by "without", and two figures that count different things (Exp6 diagnostic, the selling seat)
    ("With 30 parcels selected, the plan fills the van without exceeding the time limit of 60 seconds.",
     ["items", "time_limit_s"]),
    ("The plan uses 30 parcels, more than the 60 seconds the solver had.", ["items", "time_limit_s"]),
    # merit words need both keys to say which way is better: trades don't
    ("The strategy made 48 trades, beating buy-and-hold's 52.", ["n_trades", "trades_b"]),
])
def test_not_reversed(statement, keys):
    assert "COMPARISON_REVERSED" not in _codes(statement, keys)


def test_size_words_read_the_values_whatever_the_metric():
    # "more trades" is a size, not a merit: 48 is not more than 52
    assert "COMPARISON_REVERSED" in _codes("The strategy's 48 trades are more than buy-and-hold's 52.",
                                           ["n_trades", "trades_b"])
