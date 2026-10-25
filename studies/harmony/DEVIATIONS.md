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

## D-9: pilot 3 on the D-8 engine (2026-10-24, approved by the operator)

F1 and F7, seeds 904–905, all four conditions, $5 guard, output `runs/pilot3/`. Same model, caps and order rule
as pilot 2. Its purpose: does the record condition finish, how many calls does it take, and what does it cost, on
the D-8 engine, compared with pilot 2 on the pre-D-8 engine. Still a pilot: not confirmatory data.

## Pilot 3 result (2026-10-24): the record condition did not finish faster

16 runs, **$0.3468** metered. Full comparison: `python compare_pilots.py runs/pilot2 runs/pilot3`.

| condition | pilot 2 → pilot 3 | correct runs | calls / run | $ / run | traps |
|---|---|---|---|---|---|
| A chat | | 4 → 3 | 17 → 16 | 0.008 → 0.008 | 2 → 1 |
| B Pegasus today | | 3 → 3 | 24 → 27 | 0.010 → 0.012 | 1 → 1 |
| C record | | 4 → 3 (one hit the 150-call cap) | 107 → 124 | 0.038 → 0.039 | 0 → 0 |
| D record, no gates | | 4 → 4 | 82 → 78 | 0.028 → 0.028 | 1 → 0 |

What D-8 did, measured on C's refusal mix: `SIGNIFICANCE_NOT_SHOWN` 28 → 1 (the negation fix), `UNBOUND_NUMBER`
54 → 30 (auto-binding), `RESULT_RESTATES` 0 → 12 (dedup catching re-registration; each one is still a spent
call). Sub-agent units that returned on their own: 14 of 29 → 19 of 36. Calls per unit 12.9 → 11.7.

What it did not do: cut the run. The lead's own calls grew. Lead tool errors in C runs went from 3 to 17: a
malformed `done_when` (`{"predicate": …}` instead of `{"p": …}`, 4 calls), orders on nodes that don't exist,
and duplicate-order refusals; reworks went from 4 to 9, five of them chasing `result_exists` on a hypothesis,
which the assignee's tools could not satisfy (a result has no link to a hypothesis unless the agent adds
`supports` by hand). `ABSOLUTE_WITHOUT_COUNT` rose 10 → 22, mostly on honest enumerations ("A trails B in every
subset: math −2.6, code −2.2, reading −0.4"). Wall time per call rose in every condition (A 3.2 → 4.4 s), so the
longer runs are provider latency, not the engine.

Reading: on this engine the record's cost is coordination friction at the lead (unmeetable predicates, rework
loops, error retries), not the claim gates. D, with the same engine and no gates, finished every run in 78 calls.
Sample-size rule on pilot 3: 3 instances per family, as before.

## D-10 (proposed, not applied): orders meetable by construction, and a replay corpus

1. `done_when` accepts `predicate` / `name` as spellings of `p`; every refusal shows the valid call.
2. `result_exists` counts a live result written by the assignee under the order's lease; claims still need their
   structural link (`answers` / `supports`).
3. Each predicate in an order carries how to meet it with the assignee's tools.
4. A third rework of an order whose failing predicate hasn't moved is refused, with the choice spelled out.
5. Absolutes over an enumerated set the statement lists or binds ("every subset: …", "all three") are not
   generalisations and pass.
6. `hypgraph replay-refusals`: replay every logged refusal (statement + the bindings available then) through the
   current checker and report what would now pass, so rule changes like (5) are made against the real corpus.
7. The briefing becomes a question board with a sufficiency rule; fully met orders accept automatically.

## D-10 applied (2026-10-24): orders meetable by construction, enumeration, the question board, replay

Approved by the operator; built with tests (`tests/test_d10.py`), no model spend. In HypGraph:
1. `done_when` accepts `predicate` / `name` / a bare string; a bad predicate's refusal shows `{"p": "claim_made"}`;
   a missing target's refusal says what a target is.
2. `result_exists` / `run_registered` count what the assignee wrote while holding the order (the lease window),
   as well as structurally linked work. Claims still need `answers` / `supports` / `challenges`.
3. Every predicate in an order carries how to meet it with the assignee's tools (`coord.RECIPES`).
4. A third rework of an order whose predicate hasn't moved is refused unless `done_when` changes.
5. Absolutes over a set the sentence enumerates ("every subset: math −2.6, code −2.2, reading −0.4", "all 818
   items") pass; "below zero" is a number.
6. Refusals now log the whole claim body and its support; `hypgraph replay-refusals` replays them.
7. The briefing's unit is the question (`question_board`: settled / contested / answered / in progress / open,
   with the sufficiency rule in RULES); standing shows exceptions only; `settle` / `settle_work` accepts every
   returned order whose predicates are all met.

**Replay of the three pilots' 263 logged refusals** (`replay-baseline-d8.md` → `replay-after-d10.md`; 139 are
binding-dependent and undecidable because pilots 1–3 logged statements only):
- `ABSOLUTE_WITHOUT_COUNT` (50): would pass 1 → 16. Every flipped statement read: "over all 818 items …",
  "in every subset: …" — enumerations, as intended. 13 unchanged, 21 refused for other reasons.
- `SIGNIFICANCE_WITHOUT_TEST` (71): would pass 39 (D-8's negation fix, measured on the corpus).
- `COMPARATIVE_WITHOUT_COMPARISON` (10): unchanged, correctly.

Not yet in the study runner: `settle` after each return and the `settle_work` tool. That change goes in with the
next pilot's deviation, so the runner stays as pilot 3 ran it until then.

## D-11 (2026-10-24, approved by the operator): the runner settles, and pilot 4

`dev/study_runner.py`, condition C only: after every order returns (issue_work and rework), the record accepts
every returned order whose predicates are all met (`settle`), and the result is appended to the lead's tool
output; the lead also gets `settle_work`. Its prompt says the record accepts met orders and it reworks or cancels
the rest. Condition D keeps acceptance by the lead's judgement, which is the ablation. A and B are untouched.

Pilot 4: F1 and F7, seeds 906–907, all four conditions, $5 guard, `runs/pilot4/`, on the D-10 engine. The
question: does the record condition finish, in how many calls, at what cost, against pilots 2 and 3. Still a
pilot.

**D-10 engine checked against Pegasus's live record** (2026-10-24, while pilot 4 ran): a copy of `proxy-data/graph.db`
(790 nodes, 1,357 events) derived under the proxy's installed 0.3.0 engine and under the D-10 source gives the same
chain head and identical standing on every node in every dimension (lifecycle, review, evidence, independent lines,
at-risk, fallen, bounds, test, sentence); no node acquires `restates`. The live refusal log has no rows yet.

**Pilot 4 note (recorded while it ran):** the provider stalled the lead's long calls for the full 600 s timeout
during the first run (ledger calls ten minutes apart; small calls answered in 4 s). The operator chose to let it
run. Wall time is excluded from pilot 4's comparison; calls and metered cost are unaffected, since a timed-out
call is not billed.

## D-12 (2026-10-24): lifecycle follows a chain of replacements

Found while building hypswarm on the D-10 engine: `lifecycle` called a node superseded only when its direct
replacement was live, so in a rework chain T1 → T2 → T3 the first order read as live again once T2 was itself
replaced, and the scheduler escalated it twice. A node is now superseded when its replacement is live or itself
superseded (the chain ends in a live node); a withdrawn replacement still replaces nothing. Test in
`tests/test_d10.py`. Pegasus's live record derives identically before and after (790 nodes, same chain head).

**Pilot 4 stopped (2026-10-24, by the operator).** Its first run (F7-906, B) reached 55 metered calls in 48
minutes against the 22–34 a B run takes, because the provider stalled long calls past the 600 s client timeout
and then completed them anyway: the proxy meters the completed request, and the client's retry bills a second
copy. So the stalls inflated metered calls and cost, not only wall time — contrary to the note above, which was
written before the ledger showed it. Nothing from the run is kept (the partial folder was deleted; the ledger rows
remain under `study-F7-906-B-20261024202041` and are excluded). Pilot 4 is rerun as specified under D-11 when
the provider answers long calls normally; `runs/pilot4/` is reused. Spend on the stopped run: $0.0169.

Harness note for the rerun: a stalled call that the provider later completes is billed. The runner's timeout
and retry policy should be recorded with each pilot, and a run whose metered calls exceed its counted calls by
more than a few is flagged as stall-affected in the analysis.

## D-13 (preregistered 2026-10-24, before any run): hypswarm as condition E

**Condition E, "record-scheduled swarm".** The hypswarm alpha (`voodoomods/hypswarm`, commit recorded in the
lock) runs the task: four worker seats (analyst, stats, engineer, and a fourth general worker), one reviewer
(critic), and a lead called only at exceptions (an order NOT MET after two reworks, a contested claim, or an
empty frontier with questions open) and for the report's interpretation. The scheduler issues orders from the
question board to idle seats, settles every returned order whose predicates are met, reworks the rest at most
twice, and cancels what a fallen premise made moot; workers run in parallel under leases. Same subject model
for every seat (DeepSeek-V4.1-Flash, non-thinking), same sandboxed python tool, same caps (150 calls per run,
14 turns per order, 40 calls per order), same final-answer format, same scoring against the sealed key. The F7
notice is delivered after the first order returns, as in A–D: the corrected file is added to the working
folder, the stale artifact is withdrawn in the record with the notice as the reason, and the notice text is
prepended to every order issued afterwards and to the lead's prompts.

**Instances.** The pilot-4 instances, F1 and F7 at seeds 906–907, so E is paired with A–D on the same data
(output into `runs/pilot4/`, condition `E`). $5 guard. Still a pilot.

**Predictions, written before the run** (from DESIGN.md §5 and the one unpreregistered plumbing run on seed 0):
- E finishes every run (no cap hits) and answers at least as many sub-questions as C.
- Calls per run near D's (≈ 80) and below C's; lead calls per run under 10.
- Trap hits: none, as C.
- Reworks per run ≤ 1 on average.
- Wall time below C's on F1 (parallel sub-questions); no prediction on F7, whose cascade is sequential.

**What counts as failure:** a cap hit, or calls per run not below C's on the same instances, or a trap hit.

**Not changed:** A–D, the engine, the task suite, the scorer, the caps.

**Pilot 4 rerun stopped again (2026-10-24 evening).** A long-call probe (three 14k-token calls, < 1 s each) passed,
the rerun started, and its first run stalled within ten calls. The proxy's own audit log shows the cause is
upstream: one inference request completed with `latency_ms` 1,800,105 (thirty minutes), long after the client
that sent it had timed out, and the proxy metered it on completion. A second probe found no difference between
streaming and non-streaming tool calls (first uncached 10k-token call ≈ 25 s, then ≈ 1 s), so it is not the
runner's call path; the provider is intermittently hanging requests tonight. The hypswarm plumbing run of 59
calls at the same time happened not to hit one. The partial run is discarded; the rerun waits for a day when
the provider holds up across a whole run, which the long-call probe cannot guarantee. Spend on the stopped
rerun: under $0.01.

**D-13 harness ready (2026-10-24):** `dev/study_e.py` + `study_host.py --condition E` run a suite instance through
hypswarm with the same spec in and the same `run.json` / `score.json` / `ledger.json` out. Stub dry runs on F1 and
F7 pass (62 scripted calls each, report parsed, $0); on F7 the notice is delivered after the first return, the
stale artifact is withdrawn, and 24 of 36 later tool calls are marked after-notice. The lock now also hashes
`dev/study_e.py` and hypswarm's `src/` (`hypswarm/src`). Condition E has not run on a model.

## D-14 (2026-10-24): MCP `my_work` lists only orders still to be worked

Found by hypswarm's external-seat test: a returned order stayed in `my_work`, so an agent polling it worked the
same order twice. Returned orders are now noted as awaiting acceptance, not listed as work. The MCP surface is on
no study condition's path (A–D use the runner's tools, E hypswarm's in-process tools); recorded so the lock
stays exact.

## D-15 (2026-10-24): coordination routes on the HTTP server

`server.py` gains the coordination write ops and reads so hypswarm's workers can use a served record. No study
condition goes over HTTP (E runs hypswarm's in-process record); recorded for the lock.

**Pilot 4 rerun, third attempt, stopped by the stall watch (2026-10-25 03:41–03:51Z).** Before launch the provider
looked healthy: 100 study-shaped calls (8 KB prompt, a tool schema, 300 tokens out; six concurrent, half streamed)
all returned in 0.5–2.7 s, median 1.36 s, and nothing over 60 s had completed since 02:45Z. The rerun was started
under a stall watch (`dev/study_stallwatch.py`: it kills the pilot and the container runner when a DeepInfra call
completes after more than 120 s, or when no call completes for 150 s while a pilot is alive — a hanging call has
no audit row yet). Two runs completed normally — F7-906 B (23 calls, $0.0093, score 1.00) and F1-906 C (127
calls, $0.0454, score 1.00, no traps). The third, F7-907 B, made 14 calls in 40 s and then went silent at
03:48:46Z; the watch stopped everything at 03:51:23Z (157 s of silence). After the client was killed the proxy
still held an upstream connection to 38.101.151.20 (DeepInfra), consistent with a request hanging server-side.
So a 100-call clean burst does not predict a clean pilot: the hang rate is low (one in ~165 calls here, 8 in
~270 on the previous attempt) and the hangs last up to 30 minutes, which is exactly the shape that distorts
calls and cost. The partial run is discarded (14 metered calls, $0.0050, ledger rows under
`study-F7-907-B-20261024224806`, excluded); the two completed runs stay in `runs/pilot4/` and the resume rule
keeps them. Total spend this attempt $0.0597. Condition E did not start (the chain aborts after a stop).

Decision for the next attempt: keep the stall watch, and treat a stall as a *skip and retry of that run*, not a
stop of the pilot — the stalled call's metered rows are excluded by run id, and the run is repeated on the same
instance with a fresh run id, at most twice. That keeps a stall from ending a pilot while the metered calls and
cost of every kept run stay honest. To be implemented in `study_host.py` before the next rerun and recorded here
when done.
