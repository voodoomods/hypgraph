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

An experiment written after its run is not refused: `preregistered` is not met, and its reason says the experiment
was written after the run. Not caught under `trading@2` and `@3`: an experiment *revised* after its run (a changed
window) still meets `preregistered`, which reads when the experiment was first written, and a thesis linked to the
backtest after it ran, or one whose predictions changed after it, counts as preregistered. `trading@4` catches all
three (below).

## `trading@3` (2026-11-15): the values behind the edge words

`trading@2` checks that a supporting result *has* an out-of-sample, after-cost return and a trials count before
"edge" is said; it doesn't read what the return is. Under it, "the strategy has an edge out of sample after costs"
was accepted on a −3.1% out-of-sample return, and an in-sample return could be the unlabelled headline. `trading@3`
is `trading@2` with two more claim checks; `trading@1` and `@2` are unchanged, and a record keeps the version it
was pinned with.

- `EDGE_CONTRADICTED`: an asserted edge word the supporting results' values deny. *profitable* and *edge* need the
  out-of-sample return to be a gain; *edge*, *alpha* and *excess return* need it above the benchmark's when the
  result records one; *beats* / *outperforms* need that only when the sentence names the benchmark (buy-and-hold,
  the index, the market). The after-cost figure is read first (`net`, `after_cost`), then one that says neither, then
  the gross one (costs only lower a return); statistics of returns, counts and two candidates in one tier read as
  nothing. Refused only when every supporting result that says something denies it, and never in a sentence that
  denies something itself (no, not, loses, trails, underperforms, *k of n*): an audit names the edge to refute it
  ("there is no out-of-sample, after-cost edge", "only 2 of the 20 settings beat buy and hold"). That costs recall
  — an overclaim with a "not" in it goes through — and buys precision.
- `IN_SAMPLE_UNLABELLED`: the claim's only bound returns are in sample (`is_*`, `in_sample_*`, `train_*`, not one
  that also says `oos`) and the sentence doesn't say in sample, training, fitted or tuned. An in-sample figure bound
  beside an out-of-sample headline is context.

Measured before it was released, on material written by other seats:
- every live claim in the existing records pinned `trading@1` / `@2` (1,084), checked as if pinned `@3`: 7 refused,
  all overclaims — "outperforming the buy-and-hold benchmark of 50.42%" on 37.95%, "consistent alpha" on 79.32%
  against 84.33%, a HypSwarm seat's "outperforms buy and hold after costs" on −20.0% against −1.8%. The first draft,
  without the denial rule, gave 37 refusals, 30 of them on honest audits (27 edge, 3 in-sample); those are now tests.
- every logged sentence of the backtest-bragging showcase (gpt-oss-20b) re-filed under `@3`: 9 of 367 move, all on
  trials whose truth is no edge, and no true edge.

## `trading@4` (2026-11-20): preregistration per thesis

`trading@4` is `trading@3` with `preregistered` judging each `tests` link, as `scientific@3` does (see
[scientific.md](scientific.md#scientific3-2026-11-20-preregistration-per-hypothesis)): a thesis linked to the
backtest after it ran, a protocol (windows, costs, configurations) changed after the run, or a thesis whose
statement or predictions changed after it, holds the question until a new experiment tests it before its run and that
run is on the record. `trading@1` to `@3` are unchanged. In the existing records, 5 of the 15 questions that move are
trading questions; in two of them the lead wrote a second thesis five to six minutes after the quant's backtest ran
and linked it to that backtest.

## Review questions and decisions (2026-10-26)

1. *Will agents report `trials` honestly?* **Required, and checked like any value**: `backtested` and
   `EDGE_WITHOUT_TRIALS` need it, and the instrument's re-run confirms or contradicts the printed `trials` as it does
   every registered value. Counting a parameter grid statically from arbitrary code was not built (P3): it can't be
   done reliably, and a wrong count would be worse than the confirmed one.
2. *`review_date` default?* **Required, no default** (`POSITION_WITHOUT_STOP` names what is missing).
3. *Who raises a regime notice?* **The host or the risk seat**: it is a withdrawal (or supersession) of the data
   artifact, which only they write; `uses` then carries it to every position.

Also decided: `still_valid` counts a result as newer only if written after both the review date and the position
(the evidence a position was taken on doesn't renew it). A separate refusal for a protocol edited after its run was
not built: `preregistered` already names an experiment written after its run (and from `trading@4` one revised
after it).
