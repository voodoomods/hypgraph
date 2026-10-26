# Workflow: `trading`

## The method it is taken from

Quantitative strategy research as the sceptical part of the field describes it: a thesis is a hypothesis; its
test is a backtest whose window, costs and rules are fixed **before** it runs (the trading analogue of
preregistration); only an **out-of-sample, after-cost** result speaks to an edge; and a result has a shelf life.
Bailey, Borwein, López de Prado and Zhu on backtest overfitting ("the probability of backtest overfitting" — the
more configurations tried, the less an in-sample result means); the deflated Sharpe ratio; walk-forward
validation; and the risk-management norm that a position is a sized decision with a stop and a review date, taken
by someone other than the analyst. No live-order path exists anywhere in this workflow.

## Stages

| # | stage | holds | gate out of it | who |
|---|---|---|---|---|
| 1 | asked | question: the market question | stated | lead |
| 2 | thesised | hypothesis with `predictions` = the move, the horizon, the universe | `hypothesis_stated` **new** | quant |
| 3 | preregistered | experiment: `protocol` names the in-sample and out-of-sample windows, the costs (fees, slippage), the rules, the number of configurations to be tried; `expected` on the `tests` link | `preregistered` **new**: the experiment exists **before** the run that `executes` it, with windows and costs in the protocol | quant |
| 4 | backtested | run `executes` the experiment, `uses` the data artifact; result with `oos_*` and cost values, `trials` (configurations tried) | `backtested_oos` (today) + **`trials_declared`** new: the result states how many configurations were tried | quant, instrument |
| 5 | claimed | claim about the edge or its absence, bound to the oos result | `claim_made`; validators `EDGE_WITHOUT_OOS_COSTS`, `BACKTEST_WITHOUT_COSTS` (today), **`EDGE_WITHOUT_TRIALS`** new | quant |
| 6 | risk-reviewed | review by the risk seat (never the quant) | `reviewed` | risk |
| 7 | positioned | decision `based_on` the claim: `size`, `stop`, `review_date`, `paper: true` | `position_recorded` (today's completion criterion becomes a gate) | lead |
| 8 | monitored | later results on the same hypothesis with newer data; notices | `still_valid` **new**: a result newer than the position's `review_date` or a regime check on the hypothesis | quant, risk |

## Invalidation

- **Expiry.** A backtest result carries `valid_until` (default: the decision's `review_date`). Past it the result is
  STALE and the position AT RISK until a newer result on the same hypothesis exists.
- **Regime notice.** A host notice ("regime changed: rates / volatility / venue") withdraws the data artifact's
  claim to represent the present; every position whose claim rests on results `uses`-ing it goes AT RISK.
- `uses`, `derived_from`, `based_on`, `rests_on` as at-risk relations.

## Freshness

Fresh = `now ≤ valid_until` and the data artifact the run `uses` is live. A claim of an edge on a stale result is
reported as "edge as of <window>, not re-tested since".

## Typed artifacts and decisions

| kind | required fields | note |
|---|---|---|
| artifact `prices` | `sha256`, `path`, `from`, `to`, `frequency` | the data window |
| artifact `backtest` | `sha256` (of the code), `path`, `trials` | the code and how many configurations it tried |
| decision `position` | `size`, `stop`, `review_date`, `paper` (must be true), `based_on` → claim | the only kind of position the record accepts |

## Evidence rank

`oos_after_costs_new_data > oos_after_costs > in_sample > unverified`. A result whose `trials` is large relative to
its window is flagged (the overfitting warning), not refused.

## Report

"Desk note": the thesis; the preregistered protocol (windows, costs, trials); the out-of-sample result after costs
with the trade count; the risk review; the position (size, stop, review date, paper); what is stale or past review;
open theses.

## Completion

`questions_settled` + `position_recorded` (today) + **`nothing_past_review`**: no position whose `review_date` has
passed without a newer result.

## Refusals this workflow adds

- `EDGE_WITHOUT_TRIALS`: "edge" on a result that does not state how many configurations were tried.
- `POSITION_WITHOUT_STOP`: a position decision missing `size`, `stop` or `review_date`.
- `LIVE_ORDER`: any decision or artifact kind that names a venue order; there is no path, and the refusal says so.
- `BACKTEST_AFTER_PROTOCOL_EDIT`: an experiment revised after its run (a changed window) — allowed, but the result
  is re-ranked `in_sample`.

## For review

1. Is `trials` (configurations tried) something agents will report honestly? Proposed: the instrument counts the
   parameter grid in the registered code where it can, and the agent's number is checked against it.
2. `review_date` default: 30 days? Proposed: required, no default.
3. Should the regime notice be a host action only (as now) or can the quant raise it? Proposed: host or risk seat,
   never the quant who holds the thesis.
