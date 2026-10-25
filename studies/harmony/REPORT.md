# Harmony study — internal report (P5)

**Status: internal. Not for publication, the site, or a README.** 2026-10-25.
Preregistration: `PREREG.md`, locked in `PREREG-LOCK.json`; every departure is in `DEVIATIONS.md` (D-1 … D-19b).
Data: `runs/confirmatory/` (A–E), `runs/d19/` (E′), `runs/d19b/` (E″); analysis `analysis.py`, `compare_e.py`,
`compare_e3.py`, all frozen before the runs they score.

## 1. The question

Does an agent team coordinated **through the record** (compiled briefs, work orders with predicates, cascade
containment) answer more correctly and cost less than one coordinated through **prose** (a single agent, or
Pegasus's delegation) on decomposable research tasks with planted traps?

Conditions: **A** one agent with a notebook · **B** Pegasus delegation as it ships · **C** record-coordinated with
claim gates · **D** record-coordinated without gates · **E** hypswarm (the record's own scheduler; added post-lock,
D-13). Ten task families F1–F10, instances by seed, one model for every seat (`DeepSeek-V4.1-Flash`, non-thinking),
150-call cap per run, the answer key never in the container.

## 2. What was run

| phase | runs | $ | note |
|---|---|---|---|
| pilots 1–4 | 4 × (2–10 families × 4–5 conditions) | ≈ $2 | instrumentation, stall rule (D-16), prefix-cache hang → nonce (D-17) |
| confirmatory | 142 of 150 (A–E on seeds 100–102) | $3.04 | ten parallel family lanes (D-18); stopped by the operator at 142 to analyse |
| E′ | 30 | $0.74 | D-19: instrument reproduction + one-call result/claim |
| E″ | 29 | $0.70 | D-19b: corrected three-way reproduction verdicts |

The eight unrun confirmatory instances are F8/F9 (mostly B). The analysis reports pairs that exist; nothing is
imputed.

## 3. Results against the preregistered hypotheses

| | prediction | measured (paired, 95 % CI, Holm on primaries) | verdict |
|---|---|---|---|
| H1 | C costs less than A | cost ratio C/A **3.96 [3.40, 4.59]** | **fails** |
| H2 | C ≥ 20 points more correct than A | Δ correct **−0.185 [−0.333, −0.037]**; A correct on 28/28 | **fails** |
| H3 | C no less correct than B, and cheaper | Δ −0.120 [−0.240, 0.000]; cost ratio 3.11 [2.68, 3.59] | **fails** both halves |
| H4 | C spends less on stale work after the F7 notice | no condition read the stale file after the notice in any kept F7 run | **null** at k = 3 |
| H5 | C's reports hit fewer traps than A's | 6 discordant pairs, 5 : 1 in C's favour; A's hits all on *correct* numbers | direction right, **not significant** |

Secondary: **D vs C** 0.75 [0.62, 0.92] on cost, no less correct — the claim gates cost calls and bought no
correctness here. **B vs A** 1.27× cost, identical correctness. **E** (26 runs): 24 correct, 75 calls/run,
$0.022/run, 1 trap, 1 cap; vs A 2.57× cost, traps 1 vs 5; vs C 0.62× cost, +0.08 correct. E is the best of the
record family on every axis and still 2.6× A.

Every C miss is a 150-call cap hit with no report (F1-100, F2-100, F6-101, F8-102, F9-102), not a wrong answer.

## 4. The two follow-up rounds (D-19, D-19b)

Built from where the calls went in C/D/E (the critic re-deriving every answer; `show` reading back the reply; two
writes per result+claim): reproduction by the instrument, one-call result+claim, the target's content carried in
the order. Predictions were written before each run and both failed.

| | E | E′ | E″ |
|---|---|---|---|
| calls / run | 72.5 | 72.9 | 71.1 |
| critic calls | 29.3 | 32.0 | 26.2 |
| paired cost vs E | — | 1.18 [1.09, 1.28] | 1.13 [1.01, 1.26] |
| correct / traps / caps (of 25) | 24 / 1 / 0 | 24 / 2 / 0 | 24 / 1 / 1 |

What the rounds established: the reviewer verifies by reading whatever it is given, and a model given more
context uses more calls, not fewer. Mechanical reproduction itself is sound: in E″ the instrument re-ran 216
author runs, confirmed 1,059 registered values, found 13 unprinted and **27 contradicted (2.5 %)** — real catches a
reviewer could act on, at the cost of a sandbox call, not a model call.

## 5. What the data say, plainly

On tasks of this size — an afternoon's work, 2–5 sub-questions, at most one notice — **a single agent with a
notebook answers everything correctly for a quarter of the record's cost.** The coordination layer's measured
advantages are in *how* answers are stated and *what survives a change*, not in calls or dollars:

1. **Fewer overclaims.** A's trap hits are correct numbers under overclaimed sentences; the record refuses those
   sentences at the write (H5, 5 : 1).
2. **Stale-premise immunity.** No record condition ever built on the withdrawn file; Pegasus's prose delegation
   did once (pilot 4, F7-907). The confirmatory's F7 instances were too easy to separate the conditions (H4 null).
3. **Mechanical reproduction catches contradictions** (2.5 % of values) without a reviewer.

Where the cost goes is structural, not mechanical: a second agent that checks must read, and reading costs calls.
Two rounds of targeted fixes moved E by −2 % calls and +13 % dollars.

## 6. What this does and does not support

- Supports: the record as an **evidence layer** — refusals, standing, reproduction, blast radius — on top of
  whatever coordination a team uses. These are the strengths the public material leads with.
- Does not support: "coordinate through the record and it costs less", on afternoon-sized tasks. That claim is
  withdrawn from the positioning (PLAN §8, row 2 at best: "more right per dollar" is also not shown here, since A
  is right on everything).
- Untested: long-horizon, many-agent work where re-reading and stale branches dominate — the case the plan's §1
  ledger figures came from. The task families don't represent it; a suite that does is the precondition for any
  further cost claim (see §8).

## 7. Known defects and open items

- **Lost reports (hypswarm).** 3 of 29 E″ runs (and 1 E, 2 E′) ended with no report and zero refusals: the lead
  never called `submit_report`. Lead tool calls are now logged; diagnosis needs ~$0.10 of runs. Until it is fixed,
  E's correctness is a lower bound by 7–10 %.
- **H4 is null, not negative.** The F7 notice arrived after the stale work was already done in every kept run.
  A family where the notice lands mid-work is needed to test cascade containment at all.
- **Provider.** DeepInfra hung on a repeated request prefix (system message + tool schemas); a per-run nonce (D-17)
  removed it. Stalls are per-run retries (D-16), excluded from cost.
- Eight confirmatory instances unrun (≈ $0.20); the report is complete without them for every contrast.

## 8. Recommendations

1. **Ship 0.4 with the coordination layer as an evidence feature**, not a cost feature: profiles, token-bound
   authors, order text with content, instrument reproduction. The study has exercised every path.
2. **Keep this result internal** until a long-horizon suite exists (operator's rule, 2026-10-25). Nothing from §3
   or §4 goes on a site or README.
3. **Build the long-horizon suite per profile** (software: multi-file fix with regressions; trading: a season of
   paper decisions; knowledge: a brief with contested sources; optimization: a model that is revised), with
   notices that land mid-work, before any new cost hypothesis is preregistered.
4. **Fix the lost-report defect first** in hypswarm; nothing else about E is interpretable while reports vanish
   silently.
5. P6 (showcase, preprint) stays closed. If it reopens, the honest version is PLAN §8 row 3: publish the negative
   result with the three measured strengths.
