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
created *after* its run's result is not preregistered, and its result's evidence rank is capped at `exploratory`.

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

- `EXPERIMENT_AFTER_RUN`: an experiment linked `tests` after a run already `executes` it — allowed, but the record
  marks the result exploratory and says so.
- `STALE_EVIDENCE`: a review on a claim whose only results are stale is recorded as `comment`, not `checked`.

## Review questions and decisions (2026-10-26)

1. *Preregistration: a gate or a label?* **A gate** (`preregistered`: the experiment, with its expected outcome,
   precedes any run that executes it; one written after is named as such). The evidence-rank cap is not built:
   `report()` already lists experiments as preregistered or not, and the gate's reason says why.
2. *Is `decided` a scientific stage?* **Optional**: reported, never blocks; a question is complete at `reviewed`.
3. *`uses` as at-risk changes old records?* **Only under `scientific@2`** (`derive.EXTRA_RISKY`); `@1` records derive
   exactly as before. Freshness (`stale`) is universal, since no record could have had a superseded artifact.
