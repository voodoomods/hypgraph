"""
The backtest that brags (profile: trading@3).

A quant agent tunes a momentum rule on four years of prices, trying 20 variants. The best returned 34.2% in sample.
On the three years it never saw, after costs, it returned 11.6% while simply holding the stock returned 12.5%. The
agent's summary leads with 34.2% and calls it an edge.

In the record the backtest is the instrument's result, with in-sample and out-of-sample returns, the costs charged
and the number of variants tried. Under trading@3 an in-sample figure has to be called in-sample, "edge" needs an
out-of-sample gain over the benchmark after costs, and a comparison is held to the numbers on both sides.

    python backtest_brag.py [--db FILE] [--step]

The lines are scripted. The third follows a sentence gpt-oss-20b filed in the backtest runs: "a net return of
11.60%, outperforming the buy-and-hold benchmark of 12.50%".
"""
from __future__ import annotations

from _show import Show

BACKTEST = {"is_return": 0.342, "oos_return": 0.116, "bh_oos_return": 0.125, "fees": 0.001, "slippage": 0.0005,
            "n_trades": 48, "trials": 20}
NAMES = {"is_return": "in-sample return after costs", "oos_return": "out-of-sample return after costs",
         "bh_oos_return": "buy-and-hold out-of-sample return", "n_trades": "trades out of sample",
         "trials": "variants tried"}
SCOPE = ("Daily bars 2019-2025: tuned on 2019-2022, tested once on 2023-2025, fees and slippage charged on every "
         "fill.")


def main() -> None:
    show = Show("The backtest that brags",
                "The best of 20 variants returned 34.2% on the years it was tuned on. On the years it never saw it "
                "returned 11.6% after costs; buying and holding returned 12.5%.", __doc__)
    g = show.g
    curator, lab, agent = g.author("curator"), g.author("lab"), g.author("quant-agent")
    inv = curator.investigation("Does the momentum rule have an edge on NVX?",
                                "Decide whether the rule is worth trading.", scope=SCOPE, profile="trading@3")["id"]
    show.note("curator", "opens the question under the trading profile.")

    show.part("The agent's own numbers, without the costs")
    show.files("quant-agent", "result: the rule returned 41% (no costs recorded)",
               lambda: agent.add("result", inv, kind="computed", outcome="positive",
                                 summary="The momentum rule's backtest.", values={"total_return": 0.41}),
               "BACKTEST_WITHOUT_COSTS")

    run = lab.add("run", inv, kind="lab", state="succeeded", name="Backtest of the momentum rule: 20 variants.")
    res = lab.add("result", inv, kind="computed", outcome="negative",
                  summary="The backtest, in sample and out of sample, after costs.", values=BACKTEST,
                  links=[{"rel": "produced", "from": run["id"]}])["id"]
    show.note("lab", "runs the backtest: 34.2% in sample; 11.6% out of sample after costs, against 12.5% for "
                     "buy-and-hold; 20 variants tried.")

    def line(statement: str, *keys: str):
        meas = [{"name": NAMES[k], "result": res, "key": k, "value": BACKTEST[k]} for k in keys]
        return lambda: agent.add("claim", inv, kind="finding", statement=statement,
                                 scope="The backtest of this investigation.", measurements=meas,
                                 links=[{"rel": "supports", "from": res, "why": "The backtest this line reports."}])

    show.part("The pitch")
    s1 = "The momentum rule returned 34.2% after costs."
    show.files("quant-agent", s1, line(s1, "is_return"), "IN_SAMPLE_UNLABELLED")
    s2 = "The momentum rule has an edge out of sample after costs."
    show.files("quant-agent", s2, line(s2), "EDGE_CONTRADICTED")
    s3 = ("Out of sample the rule delivered a net return of 11.6%, outperforming the buy-and-hold benchmark of "
          "12.5%.")
    show.files("quant-agent", s3, line(s3, "oos_return", "bh_oos_return"), "COMPARISON_REVERSED")

    show.part("What the numbers support")
    s4 = ("In sample the rule returned 34.2% after costs; out of sample it returned 11.6%, behind buy-and-hold's "
          "12.5%.")
    show.files("quant-agent", s4, line(s4, "is_return", "oos_return", "bh_oos_return"), "accepted")
    s5 = "The rule is profitable out of sample after costs, returning 11.6%."
    show.files("quant-agent", s5, line(s5, "oos_return"), "accepted", "true: it made money, it just didn't beat holding")

    show.part("What it doesn't catch")
    show.note("", "The profile reads edge, alpha, profit, returns and comparisons. A recommendation that names none "
                  "of them goes in:")
    s6 = "The rule looks robust and is ready for live trading."
    show.files("quant-agent", s6, line(s6), "accepted", "an opinion with no figure and no edge word")
    show.note("", "It also takes the backtest as given: it does not re-run it, and a leak inside the backtest is "
                  "invisible to it.")

    show.end("an unlabelled in-sample return, a false edge and a reversed comparison were refused; "
             "the honest summary went in; 1 named limit shown.")


if __name__ == "__main__":
    main()
