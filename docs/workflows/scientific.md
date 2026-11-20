# Workflow: `scientific`

## The method it is taken from

The hypothetico-deductive method as practised in empirical science, with the modern discipline of
**preregistration**: state the hypothesis and the analysis before seeing the outcome, so the test cannot be bent
to the result. Popper's criterion that a scientific statement must be falsifiable; the Center for Open Science's
preregistration practice (hypothesis, design, analysis plan fixed before data); and the replication norm that a
finding stands on independent lines of evidence, not repeated copies of one. HypGraph's kernel was built from this
workflow, so this spec mostly names what the kernel already does and marks the two things it doesn't.

## Stages

| # | stage | holds | gate out of it | who |
|---|---|---|---|---|
| 1 | asked | question | the question is stated (`question` node with `text`) | lead |
| 2 | conjectured | hypothesis with `predictions` | `hypothesis_stated` **new**: a hypothesis `answers` the question with at least one checkable prediction | lead / worker |
| 3 | preregistered | experiment with `aim`, `protocol`, `success_criteria`, `tests` → hypothesis with `expected` | `preregistered` **new**: an experiment `tests` the hypothesis with an expected outcome stated **before** any run `executes` it (created_at order) | worker |
| 4 | run | run (`agent` or `lab`), artifacts it `uses` | `run_registered` | worker, instrument |
| 5 | evidenced | result `produced` by the run, values | `result_exists`; the instrument's replicate when code was registered | worker, instrument |
| 6 | claimed | claim with measurements, `answers` the question | `claim_made` | worker |
| 7 | reviewed | review by a policy reviewer, not the author | `reviewed` | reviewer |
| 8 | decided | decision `based_on` the claim | `decided` **new** (optional stage; required only when the task asks for a decision) | lead |

A question is **settled** at stage 7 (today's rule). Stage 3's gate is what preregistration adds: an experiment
written *after* a run that executes it is not preregistered, and the gate says so (the evidence-rank cap this spec
first proposed was not built; see decision 1).

## Invalidation (at-risk relations)

Today's set, unchanged: `requires`, `derived_from`, `based_on`, `works_on`, `rests_on`. Plus **`uses`**: a run
that `uses` an artifact which is later withdrawn (a corrected data file) puts its results, their claims and the
decisions on them AT RISK — the F7 case. Today this works only through `derived_from` chains that happen to pass
through the artifact; it should be the relation itself.

## Freshness

A result is fresh while every artifact its run `uses` is the live version (same sha). A result on a withdrawn or
superseded artifact is STALE; a claim resting only on stale results needs a rerun before a review counts.

## Typed artifacts

| kind | required fields | note |
|---|---|---|
| `data` | `sha256`, `path`, `size` | what the run read; registered by the task or the host |
| `protocol` | `sha256`, `path` | the analysis code or plan, when it is a file |
| `figure` | `sha256`, `path`, `format` | produced by a run |

## Evidence rank (unchanged)

`external > new_data > separate_implementation > same_code > unverified`, from `replicates` links and their
`differs` field; an unprovenanced line counts once.

## Report

"Facts from the record" as today: claims with standing and verdicts, results and whether a claim carries them,
hypotheses, experiments (preregistered or not), open items, spend; interpretation underneath; linted.

## Completion

`questions_settled` (today). Optional: `decisions_recorded` when the task asked for a decision.

## Refusals this workflow adds

None of its own. A late experiment and a check of stale evidence are written, and the gates don't count them:

- An experiment written after a run already `executes` it goes in; `preregistered` is not met, and its reason names
  both: *"X1 was written after RUN1 executed it — not preregistered; the experiment (protocol, expected outcome)
  comes before the run"*.
- A review of a claim whose only results are stale is recorded as given; `reviewed` is not met: *"CL1 is checked but
  its evidence is stale: artifact A1 is superseded — rerun before the check counts"*.
- Not caught under `scientific@2`: an experiment *revised* after its run (a changed protocol) still meets
  `preregistered`, which reads when the experiment was first written, not when its protocol last changed; nor does
  it see a hypothesis linked to the experiment after the run. `scientific@3` catches both (below).

## `scientific@3` (2026-11-20): preregistration per hypothesis

`scientific@2`'s `preregistered` reads one time per experiment, when it was first written, against its first run.
Two things went through. A hypothesis written after the run's outcome and linked `tests` to the experiment that ran
counted as preregistered, because the experiment was. A protocol changed after the run counted, because the
experiment's first version came first. `scientific@3` is `scientific@2` with the gate judging each link;
`scientific@1` and `@2` are unchanged, and a record keeps the version it was pinned with.

- A hypothesis is preregistered through a `tests` link written, with its expected outcome, before the first run that
  executes the experiment, while the experiment was itself written before that run and its `protocol` and
  `success_criteria` are still the ones that ran. Another field (the aim) may change.
- The question's gate is met when some hypothesis on it is preregistered and none is tested only after the fact. One
  that is holds the question, and the reason names it:
  - *"H2 is tested only through X1, linked after RUN1 executed it — a hypothesis written after its run's outcome is
    not preregistered; test it with a new experiment, written before its run"*
  - *"H1 is tested only through X1, linked after RUN1 executed it — H1 was written before the run, but the link's
    expected outcome after it; test it with a new experiment, written before its run"*: the expected outcome is on
    the link, so a link written after the run holds the question even when the hypothesis came first.
  - *"X1's protocol was changed after RUN1 executed it (version 2) — the test that ran is not the one on the record;
    write the new protocol as a new experiment, before its run"*
  - an experiment written after its run, with the reason above, now also when another hypothesis on the question was
    preregistered.
- What the reason asks for meets the gate: a new experiment that tests the hypothesis, written before its run. A
  withdrawn hypothesis or a retracted link no longer holds the question. A claim linked after the run doesn't hold
  the question (an order on that claim reads it), and nor does a hypothesis that answers only another question.
- An order on one hypothesis or claim reads only that target's links.

Measured before it was released:
- every question in the existing records pinned to a workflow (7,526 in 3,070 records) gets the same verdicts from
  the frozen versions before and after this change.
- under the new versions (`scientific@3`, `trading@4`, `optimization@4`), 14 of the 960 questions with an experiment
  move, all from met to not met, all in HypSwarm seats' records. 11 had an experiment written after its run beside a
  preregistered one, 3 a hypothesis linked after the run to an experiment preregistered for another; in 13 of the 14
  the hypothesis was written after its run's result, seconds to minutes later. 17 of the 1,413 orders given with
  `preregistered` move the same way; 3 of them had been accepted.

## Review questions and decisions (2026-10-26)

1. *Preregistration: a gate or a label?* **A gate** (`preregistered`: the experiment, with its expected outcome,
   precedes any run that executes it; one written after is named as such). The evidence-rank cap is not built:
   `report()` already lists experiments as preregistered or not, and the gate's reason says why.
2. *Is `decided` a scientific stage?* **Optional**: reported, never blocks; a question is complete at `reviewed`.
3. *`uses` as at-risk changes old records?* **Only under `scientific@2`** (`derive.EXTRA_RISKY`); `@1` records derive
   exactly as before. Freshness (`stale`) is universal, since no record could have had a superseded artifact.
