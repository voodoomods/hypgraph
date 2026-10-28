"""The record's own bookkeeping decision isn't a position. `accept_work` settles an order with a decision whose text
quotes the order's objective and that rests on the claims that met its predicates; under trading, a kind-less decision
with position words in its text and `based_on` links was taken for a position and refused for want of a stop
(POSITION_WITHOUT_STOP), and the whole run crashed at the moment it settled (studies T2, budget-fit baseline)."""
from hypgraph import Graph, Policy

H = "harness"


def _trading():
    g = Graph(policy=Policy(reviewers={"risk"}, extra_reserved={H}))
    inv = g.create(author=H, type="investigation", fields={"title": "The crossover.", "profile": "trading@2",
                   "objective": "Decide whether the desk trades the crossover."})["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q3",
                 fields={"text": "Should the desk take a paper position on the crossover, or decline?"})["id"]
    return g, inv, q


def _decline(g, inv, q):
    """A checked-in answer: a run with its code, a result with the backtest's numbers, a claim bound to them."""
    run = g.create(author="quant", type="run", inv=inv, fields={"kind": "agent", "name": "bt", "state": "succeeded",
                   "config": {"source": "print('oos_return', -0.19)"}})
    rs = g.create(author="quant", type="result", inv=inv, fields={"summary": "Backtest out of sample after costs.",
                  "values": {"oos_return": {"value": -0.19}, "bh_return": {"value": -0.03}, "fees": {"value": 0.024},
                             "trials": {"value": 20}}, "outcome": "negative"},
                  links=[{"rel": "produced", "from": run["id"]}])["id"]
    return g.create(author="quant", type="claim", inv=inv, fields={
        "statement": "The desk should decline the crossover: out of sample after costs the rule returns -0.19 against "
                     "buy and hold's -0.03.",
        "scope": "prices.csv, the held-out days, at 10 bps per position change.",
        "measurements": [{"name": "rule", "key": "oos_return", "result": rs}, {"name": "bh", "key": "bh_return", "result": rs}]},
        links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]


def test_settling_an_order_about_a_position_is_not_a_position():
    g, inv, q = _trading()
    o = g.issue_work(author=H, inv=inv, target=q, assignee="quant", role="worker", done_when=[{"p": "claim_made"}],
                     objective="Q3 is at stage 'claimed': should the desk take a paper position on the crossover, or decline?")
    _decline(g, inv, q)
    g.return_work(author="quant", order=o["order"], note="The claim is written: the desk should decline the crossover.")
    settled = g.settle(author=H, inv=inv)                        # raised POSITION_WITHOUT_STOP
    assert settled and settled[0]["order"] == g.get(o["order"])["code"]
    d = g.get(g.resolve(settled[0]["decision"], inv))
    assert d["body"]["kind"] == "accepted" and d["body"]["choice"].startswith("Accept ")
    assert g.stage(q)["gates"][-2]["gate"] == "positioned" and not g.stage(q)["gates"][-2]["met"]   # still no position


def test_a_real_position_still_needs_its_stop():
    import pytest
    from hypgraph import GraphError
    g, inv, q = _trading()
    c = _decline(g, inv, q)
    with pytest.raises(GraphError, match="POSITION_WITHOUT_STOP"):
        g.create(author="lead", type="decision", inv=inv, fields={"choice": "Take a small paper position on the crossover.",
                 "reasons": "It beats buy and hold out of sample."}, links=[{"rel": "based_on", "to": c}])
