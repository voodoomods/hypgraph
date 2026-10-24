# Deviations from the locked preregistration

Every change made after `PREREG-LOCK.json` (2026-10-24T21:42:08Z) is listed here, with its reason, the evidence
behind it and whether it has been applied. Pilot data never enters the confirmatory analysis (PREREG §3).

## Pilot 1: what it found (2026-10-24)

F1 and F7, seeds 900–901, all four conditions: 16 runs, **$0.3677 metered** (cap $5). Model:
DeepSeek-V4.1-Flash. Frozen analysis output: `runs/pilot/results.md`.

| condition | correct runs | mean fraction | $ total | calls | trap hits | ended without a report |
|---|---|---|---|---|---|---|
| A chat | 3 / 4 | 0.875 | 0.0320 | 66 | 2 | 0 (2 never called submit, but the final message scored) |
| B Pegasus today | 4 / 4 | 1.00 | 0.0490 | 105 | 0 | 0 |
| C record | 1 / 4 | 0.25 | 0.1603 | 464 | 0 | 3 (2 out of lead turns, 1 hit the 150-call cap) |
| D record, no gates | 2 / 4 | 0.50 | 0.1264 | 358 | 1 | 2 |

What the numbers say, read plainly:
1. **C as locked can't be judged.** Three of its four runs ended with no report: the lead ran out of its 14
   turns, or the run hit 150 calls. In F1-901-C the lead had accepted six of seven orders and pulled the report
   facts when its turns ran out. **The cap applies per unit, and for the lead the unit is the whole run.** That
   penalises the condition that needs the most orchestrator turns, so it's a design flaw, not a finding.
2. **Most of C's extra calls go to formatting retries, not judgement.** The record refused 91 claims and 79 came
   back honest. The codes:
   - `UNBOUND_NUMBER` 63, `MEASUREMENT_UNKNOWN_FIELD` 26, `MEASUREMENT_MALFORMED` 12. The `graph_add` tool
     description barely explains binding numbers to results.
   - `SIGNIFICANCE_WITHOUT_TEST` 23, `ABSOLUTE_WITHOUT_COUNT` 18, `COMPARATIVE_WITHOUT_COMPARISON` 10. These are the
     gates working as designed.
3. **Where the gates showed:** C refused "significant" on F1-900 where A and D let it through. A built answers on
   the stale file after the F7 notice; B and C didn't.
4. **B is strong.** It was right every time, at about 1.5× A's cost. A fair outcome might be that structured
   hand-offs do most of the work and the record adds overclaim protection at a price. If so, we report that.
5. **Sample-size rule** (on pilot-1 C/A log ratios): 3 instances per family. It's computed from C runs that mostly
   failed for the reason in (1), so it is recomputed after pilot 2 (D-5).

## Applied (approved by the operator, 2026-10-24)

| # | Change | Why | Applies to |
|---|---|---|---|
| D-1 | The orchestrator gets no per-unit turn cap; it is bounded only by the run's 150-call budget. Sub-agents keep 14 turns per unit. | Pilot finding 1: the lead's cap was a whole-run cap, and it falls hardest on the condition with the most coordination steps | all conditions |
| D-2 | When a run has used 85 % of its call budget, the orchestrator's next tool result says: "You have N calls left: submit the report now." | Budget exhaustion produced reports-that-never-were; the instruction is the same everywhere and changes nothing else | all conditions |
| D-3 | `graph_add`'s description gains one worked example of binding a number (`register_run` → `RS1` with values `{"rate": {"k": 812, "n": 1000}}` → a claim with `measurements: [{"name": …, "result": "RS1", "key": "rate", "k": 812, "n": 1000}]`, `derived_from` RS1, `answers` Q1). | Pilot finding 2: binding-format refusals were the main cost driver. B gets Pegasus's mature hand-off text, so C deserves an equally clear tool text | C, D |
| D-4 | The F7 waste metric counts a unit as stale only if it used `site_b.csv` **and not** `site_b_fixed.csv` after the notice. | The pilot critic re-read the stale file only to verify the factor of 10, which is good practice, not waste | analysis |
| D-5 | **Pilot 2** on fresh seeds 902–903 (F1, F7, all conditions, cap $5) with D-1 to D-4 applied, then the sample-size rule recomputed from pilot 2 only. | Confirms C can finish inside the budget before any confirmatory money is spent | procedure |

Applied in `dev/study_runner.py` (D-1, D-2, D-3), `dev/study_host.py` (`pilot --out`, for D-5) and
`analysis.py` (D-4). `lock.py --deviation` recorded the new hashes beside the originals in `PREREG-LOCK.json`;
`lock.py --check` now compares against the original lock overlaid with its deviations.

## D-6: a robustness slice on a stronger model (added 2026-10-24, before any confirmatory data)

The operator asked for this. It is specified here before the confirmatory run, so it is preregistered, not
chosen after seeing results.

- **Question:** does the effect (or its absence) hold on a stronger, reasoning model, or is it an artefact of a
  cheap one?
- **Model:** `deepinfra:deepseek-ai/DeepSeek-V4-Pro@medium` (thinking at medium effort), every seat, every
  condition. Metered at $1.30 / $0.10 cached / $2.60 per million tokens, plus reasoning tokens.
- **Runs:** families F1 and F7 × the first three confirmatory instances (seeds 100–102) × conditions A, B and C:
  18 runs, on the **same instances** as the confirmatory runs, so each is paired with its Flash counterpart.
  Same caps, harness, order rule and scoring.
- **When:** after the confirmatory run is complete and analysed, so it can't influence the main study.
- **Analysis:** secondary. The same contrasts (C vs A, C vs B) on this slice, plus the model × condition
  interaction on correctness and on cost (paired by instance). It is reported whichever way it comes out, and it
  is never pooled into the primary hypotheses.
- **Budget:** estimated $3–10, with the same guard: a run starts only if spend so far plus a reserve fits under
  the approved cap. **Approved by the operator on 2026-10-24: up to $10.** This approval covers D-6 only, not the
  confirmatory run.

## D-7: a conditions option for the D-6 slice (tooling only)

`study_host.py pilot --conditions ABC`. The default stays ABCD, so the shuffled order of every other run is
unchanged.

## The operator's conditional pre-approval (2026-10-24, recorded while pilot 2 was running, before any of its C runs had finished)

> "if pilot 2 shows the record condition finishing within its call budget in most runs, run the confirmatory study
> (sample size from the rule, cap $15), analyse it, then run D-6 (cap $10). If pilot 2 doesn't show that, stop
> and report."

The test, fixed now: in pilot 2's **C** runs, at least **3 of 4** submitted a report (`submitted: true`) without
hitting the 150-call cap. If it passes:
1. Confirmatory: all ten families, seeds 100 … 100 + k − 1, where k comes from the sample-size rule applied to
   pilot 2 only. Every condition runs in the preregistered shuffled order (seed 20261024), output to
   `runs/confirmatory/`, with a $15 guard.
2. The frozen analysis on `runs/confirmatory/`.
3. D-6 (`--families F1,F7 --seeds 100,101,102 --conditions ABC`, output `runs/d6/`, $10 guard), then its
   analysis.

If the test fails, nothing more is spent and pilot 2 is reported.

## Pilot 2 result and the go decision (2026-10-24)

16 runs, **$0.3360** metered. Test: C submitted 4 of 4, with 0 cap hits → **passes** (needed 3 of 4).
Sample-size rule on pilot 2 (C/A log-ratio SD 0.197, 4 pairs) → 7 pairs needed → **k = 3 instances per family**
(the floor), not underpowered for cost.

| condition | correct runs | mean fraction | $ total | calls | trap hits |
|---|---|---|---|---|---|
| A chat | 4 / 4 | 1.00 | 0.0321 | 68 | 2 ("significant" ×2) |
| B Pegasus today | 3 / 4 | 0.81 | 0.0398 | 97 | 1 (stale file after the F7 notice) |
| C record | 4 / 4 | 1.00 | 0.1526 | 426 | 0 |
| D record, no gates | 4 / 4 | 1.00 | 0.1115 | 328 | 1 ("significant") |

Under the pre-approval: the confirmatory run starts now (all ten families × seeds 100–102 × ABCD = 120 runs,
$15 guard), then its analysis, then D-6.

## The confirmatory run was stopped by the operator (2026-10-24)

The operator said "no need on the confirmatory study. lets stop that", and it was stopped. By then the chain had
already halted on its own after 2 runs: F4-100 B completed ($0.0184), F2-101 D produced no output, and staging
the third run failed (`podman cp` exited 0xC0000142 on the host). Those runs sit in `runs/confirmatory/`. They are
**not** analysed or reported as confirmatory results: the study is incomplete. D-6 did not run.

Spend for the whole study: smoke $0.0001 + pilot 1 $0.3677 + pilot 2 $0.3360 + confirmatory $0.0184 ≈ **$0.72**.

Harness note for any restart: copies staged with `podman cp` into `/root/harmony-code-*` arrive without owner
write permission, so the runner's cleanup failed silently and 84 copies piled up (code only, no keys). They were
removed by hand (`chmod -R u+rwX`, then `rm`). The host's cleanup needs that chmod before the confirmatory run
restarts.

## D-8: engine fixes from the pilot records, before any further run (2026-10-24)

Approved by the operator ("fix the engine first"). Changes in HypGraph (`src/hypgraph`), all deterministic, with
tests (`tests/test_engine_fixes.py`):
1. **Negation-aware checks.** A word counts only when its sentence asserts it. Pilot evidence: the checker refused
   "A is not significantly more accurate than B" with the same code as the overclaim; an analyst's honest trap
   check was refused three times (F1-903-C). New code `SIGNIFICANCE_CONTRADICTED` for "not significant" when the
   bound counts are.
2. **Auto-binding.** A claim's loose numbers are bound to the author's own results before any refusal, with a
   `supports` link added. Pilot evidence: 61 of 106 numbers refused as unbound in pilot 2's C runs already sat in
   a result of the same record.
3. **The done signal.** Every write by an assignee returns its open orders with predicates MET / NOT MET and
   "return_work now" when all are. Pilot evidence: 8 of 9 sub-agent units in F1-902-C ran to the turn cap.
4. **Result deduplication.** The same author re-registering the same numbers is refused (`RESULT_RESTATES`); a
   declared rerun or another author's restatement is kept and marked. Pilot evidence: RS4 / RS7 / RS9 / RS14 /
   RS16 in F1-902-C all carried the same subset numbers.

Runner: `dev/study_runner.py`'s record tools now show the record's notes and the done signal to the agent (the
tool outputs only; no change to prompts or caps). The lock now hashes the whole engine (`hypgraph/src`), since
the checks are part of condition C; before D-8 it covered only `coord.py` and `schema.py`.

These change condition C (and D, through auto-binding and the done signal) and nothing in A or B. Pilots 1 and 2
were run without them and are reported as such; any later pilot or confirmatory run is on the D-8 engine.
