# Preregistration: coordinating agent teams through the record

*Status: **LOCKED.** `PREREG-LOCK.json` holds the sha256 of this file, the analysis script, the task suite, the runner, the host script and HypGraph's coordination layer, and the commits of both repositories; `python studies/harmony/lock.py --check` says whether they still match. Every change after the lock goes in `DEVIATIONS.md`, with its reason.*

Authors: Nicolas Houghtaling (VoodooMods LLC), with Claude.
Plan and rationale: [PLAN.md](PLAN.md).

---

## 1. Question

Teams of LLM agents are working research tasks whose answers are known. Does a team that coordinates through a
shared evidence record get more answers right, for less money, than the same agents coordinating in prose? The
record does three jobs: it compiles each agent's context, it accepts work against predicates, and it cancels work
whose premises fell.

## 2. Conditions

All conditions use the same subject model, the same five seats and the same data tools. The seats are an
orchestrator plus an analyst, a statistician, an engineer and a critic. The data tools run python as an
unprivileged user in the run's own folder, and list and read files. All conditions share the same caps (§6) and
the same final-answer format. Sub-agents run one at a time in every condition. The implementation is
`Pegasus/pod/dev/study_runner.py`, at the commit and sha256 recorded in the lock.

| | Condition | Coordination |
|---|---|---|
| **A** | Chat | The orchestrator `ask`s a teammate. The teammate sees the whole team transcript and replies in prose. No checks. |
| **B** | Pegasus today | `delegate` with 1–4 done-when criteria. Returns use Pegasus's CRITERIA / OPEN QUESTIONS / NOT DONE / SUMMARY format (`delegation.handoff_block`), and every return gets Pegasus's focused check (`checks.SYSTEM` / `checks.QUESTIONS`, one model call). The orchestrator must accept or reopen each return (reopen at most twice) before it may submit. There's a war room. |
| **C** | Record-coordinated | A per-run HypGraph record (the coordination layer at the locked commit). The orchestrator starts from `briefing` and issues work orders on the question nodes or on planning nodes it adds. Teammates return writes to the record, and claims are checked as they are written. `accept_work` only works when every predicate is met. `cancel_moot` cancels orders whose premises fell. The report must pass `check_text`. |
| **D** | Record without gates | As C, except claims aren't checked (non-strict investigation), the orchestrator accepts on its own judgement, and the report isn't checked. |

**Notices.** Family F7 has a notice. It's delivered after the first sub-agent returns: its files are added, and
its text reaches the orchestrator with the next tool result. The team also gets it through the condition's own
shared channel: A's transcript, B's war room, and in C/D the record, where the stale file's artifact is withdrawn.

## 3. Tasks

There are ten generated families (`studies/harmony/suite/families.py`). Each instance plants an answer and one
trap, and its answer key stays on the host. A reference solution computed from the files alone matches the key for
every family on seeds 0–5. The task-suite tests check this, along with determinism, leak-freedom and trap
detection.

| | Family | Trap |
|---|---|---|
| F1 | paired eval comparison | calling A significantly better when the paired test says it isn't |
| F2 | rare failure, 0–1 leaks in 40–120 attacks | "never leaks" |
| F3 | leaky validation split | the inflated accuracy reported as held-out |
| F4 | confounded uplift | a causal claim |
| F5 | underpowered A/B null | "no effect" |
| F6 | disguised duplicate sub-question | doing the same computation twice |
| F7 | data file declared corrupt mid-run | answers or work built on the stale file |
| F8 | Vigenère cipher, known key | — (objective break) |
| F9 | synthetic whistles in noise | measuring a louder harmonic |
| F10 | two sources, one station in °F | averaging the units |

**Seeds.** Dry run: seed 0. Pilot: families **F1** (core statistics claim checks) and **F7** (the mid-run notice
and cascade), seeds 900–901, all four conditions: 16 runs. Confirmatory: seeds 100 … 100 + k − 1 per family,
where k comes from the sample-size rule (§7). Seeds are never reused across phases, and pilot data never enters
the confirmatory analysis.

## 4. Outcomes

- **Primary 1, correctness.** `run_correct`: every core sub-question is right, scored by `suite/score.py` against
  the sealed key. The secondary measure is `fraction`, the share of core sub-questions right.
- **Primary 2, cost.** Metered dollars per run, read from the proxy ledger, with every call labelled
  `study-<run>`. The secondary measure is dollars per correct run.
- **Secondary:**
  - trap hits in the final report;
  - waste dollars by kind (analysis.py `waste()`):
    - F7 calls after the notice in units that read the stale file;
    - F6 calls in Q2/Q4 units after the first such unit;
    - reopened hand-offs and reworked orders;
  - calls; input / cached / output tokens; cap hits; errors.

## 5. Hypotheses and what counts as failure

| | Prediction | Fails if |
|---|---|---|
| H1 | C costs less per run than A | the bootstrap 95 % CI of the paired cost ratio C/A includes 1 |
| H2 | C is at least 20 points more often correct than A | the 95 % CI lower bound of the paired difference is below +0.20 |
| H3 | C is no less correct than B (margin 10 points) **and** C costs less than B | either the CI lower bound of C − B correctness is below −0.10, or the cost-ratio CI includes 1 |
| H4 | On F7, C spends less on post-notice stale work than A and than B | a paired difference CI includes 0 |
| H5 | C's final reports contain fewer trap hits than A's | the CI of the paired difference includes 0 |

Every hypothesis is reported, whichever way it comes out. If C wins on dollars per correct answer but not on
dollars per run, that is what we claim.

## 6. Procedure

- **Subject model.** One model for every seat in every condition: **`deepinfra:deepseek-ai/DeepSeek-V4.1-Flash`**,
  without reasoning effort (non-thinking), chosen by the operator on 2026-10-24 and recorded in
  PREREG-LOCK.json. Same temperature and limits as Pegasus's inference policy at the lock. Metered at
  $0.20 / $0.006 cached / $0.60 per million tokens (`proxy-config/pricing.json`).
- **Caps per run.** 150 model calls (the focused checks count), 14 turns per agent per unit, 3,600 s wall time.
  Hitting a cap ends the run, and the run counts with whatever report exists, often none.
- **Order.** The list of (instance, condition) pairs is shuffled with seed 20261024 and run in that order,
  interleaved, so provider load and time of day fall on every condition alike.
- **Isolation.** One run at a time.
  - Each run gets a fresh folder, a fresh record and no memory, company search or awareness.
  - The answer key never enters the container.
  - Run outputs are root-only (0700) inside the container and copied out at the end of the run.
- **Exclusions.** There are none for outcomes. Cap hits, wrong formats and refusals all count. The only reruns:
  - a run that crashes from a **harness defect** (a traceback in the runner, not a model or tool error) is rerun
    once after the fix, and the fix is logged in DEVIATIONS.md;
  - a run that fails from a **provider outage** (5xx / 429 after the fallback model) is rerun once. A second
    failure counts as a failed run.
- **Spend.** The pilot is capped at $5. `study_host.py pilot` starts a run only if the metered spend so far
  plus a reserve (1.5 × the costliest run so far, at least $0.50) fits under the cap; otherwise it stops and the
  pilot is reported as incomplete. The confirmatory run needs a budget the operator approves before it
  starts. The host script refuses a real model without `--i-have-approval`.

## 7. Analysis

`studies/harmony/analysis.py`, frozen by the lock:

- **Pairing:** by instance. Bootstrap over instances: 10,000 resamples, seed 20261024.
- **Correctness:** paired difference of `run_correct`, with a CI and a two-sided bootstrap p.
- **Cost:** paired log ratio, with a CI and p; reported as a ratio.
- **Holm correction** across the primary contrasts (C vs A, C vs B), separately for correctness and for cost.
  D vs C and B vs A are secondary.
- **Sample-size rule (pilot):** k instances per family so that a paired test on log cost detects a 20 % difference
  with 80 % power at 5 %, using the pilot's SD of C/A log ratios, bounded to [3, 6]. If more than 6 per family
  would be needed, the study runs 6 and states it is underpowered for cost.
- **Power for correctness, stated now:** at 30–60 paired instances, roughly a 40 → 80 % difference is detectable,
  but not 60 → 75 %. We'll only claim what the study is powered for.
- **Human review** (secondary): a random 20 % of final reports, with node codes and condition-revealing tool names
  stripped, rated against the trap list by the operator, who won't know the condition. Unblinding risk remains
  and is stated as a limitation.

## 8. What is not claimed

- The study shows nothing about tasks unlike these families, about other models, or about parallel sub-agents.
- The record is never the judge of its own success: scoring uses the sealed keys only.
- Nothing from the unpublished D'Agapeyeff work is used.
