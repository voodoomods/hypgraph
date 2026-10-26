# Workflow: `optimization`

## The method it is taken from

Operations-research practice: a problem is modelled (objective, decision variables, constraints) before it is
solved; a solution is only a solution if it is feasible; "optimal" is a statement about a **bound**, not about
effort; and a solver's answer is verified against the constraints by someone other than the modeller. The
mixed-integer programming convention that an incumbent is reported with its optimality gap (the gap between the
best solution and the best bound); the sensitivity-analysis norm that a recommendation says how it changes when
the data does; and the modelling-lifecycle view (Williams, *Model Building in Mathematical Programming*) that the
model is a hypothesis about the problem and can be wrong independently of the solver.

## Stages

| # | stage | holds | gate out of it | who |
|---|---|---|---|---|
| 1 | posed | question: what to minimise or maximise, under which constraints; the instance as an artifact | `instance_registered` **new**: an artifact `kind=instance` with its sha | lead |
| 2 | modelled | hypothesis = the modelling choice (variables, objective, constraints as stated); `predictions` = what the solution should look like | `hypothesis_stated` **new** | modeller |
| 3 | configured | experiment = the solve configuration: solver, time limit, tolerances, `tests` the hypothesis | `preregistered` **new** (the configuration precedes the solve) | solver |
| 4 | solved | run `executes` the experiment, `uses` the instance; result with `objective`, `feasible`, `bound`, `gap`, `runtime_s`, `solution` artifact | `feasible_bounded` (today) | solver, instrument |
| 5 | verified | review by the verifier: the solution satisfies the constraints of the **instance artifact** (recomputed, not trusted) | `reviewed` with method naming the check | verifier |
| 6 | claimed | claim "best found, gap g" or "optimal" with the bound; `OPTIMAL_WITHOUT_BOUND` (today) | `claim_made` | solver |
| 7 | checked | the verifier checks the claim's wording against the result (a question settles on a checked claim) | `reviewed` | verifier |
| 8 | recommended | decision `based_on` the claim: the incumbent to use, with the sensitivity note | `decided` **new** (optional) | lead |

Infeasibility is a settled outcome: a result with `feasible: false` and a claim of `kind=exclusion` ("no feasible
assignment exists: total capacity 7 < 8 customers") settles the question. Today that path trips
`ABSOLUTE_WITHOUT_COUNT`; the workflow makes "no feasible X" bind to the result's `feasible` value.

## Invalidation

- **A changed instance** (new sha) `supersedes` the old instance artifact; every run that `uses` it is STALE, its
  results, claims and the recommendation AT RISK. Same mechanism as software's new head.
- A revised model (new hypothesis version) marks solves of the old model as "of the old model".
- `uses`, `derived_from`, `based_on`, `rests_on`.

## Freshness

Fresh = the run's instance artifact is the live one and the model hypothesis is at its reviewed version.

## Typed artifacts

| kind | required fields | note |
|---|---|---|
| `instance` | `sha256`, `path`, `size` | the data the model is solved on |
| `solution` | `sha256`, `path`, `objective`, `feasible` | the assignment / schedule / plan |
| `model` | `sha256`, `path` (the formulation file), `solver` | optional; when the model is a file |

## Evidence rank

`proven_optimal (gap 0 or bound = objective) > bounded (gap stated) > feasible_only > infeasible_claimed >
unverified`. A `bound` that comes from enumeration counts as a proof for the instance size it names.

## Report

"Solution report": the problem; the model (variables, objective, constraints); the configuration; the incumbent
with objective, feasibility, bound and gap; the verifier's check; the recommendation and its sensitivity; what is
stale (solves on superseded instances or models).

## Completion

`questions_settled` + `incumbent_feasible` (today) + **`verified`**: the incumbent has a verifier's review that
recomputed feasibility.

## Refusals this workflow adds

- `SOLVED_WITHOUT_INSTANCE`: a run with no `uses` → instance artifact.
- `VERIFIED_BY_SOLVER`: a review of a solution by its own author.
- `OPTIMAL_ON_STALE_INSTANCE`: "optimal" bound to a solve whose instance is superseded.

## Review questions and decisions (2026-10-26)

1. *The model: hypothesis or experiment?* **Hypothesis** (`modelled`, gate `hypothesis_stated`): it can be wrong
   independently of the solve and is revisable with its own version.
2. *Mechanical feasibility recomputation?* **P3** (`check_solution` reproducer). Built now: `result_reviewed` —
   the verifier's check on the result, by someone who is not its author — and `incumbent_verified` needs it on the
   current instance.
3. *Sensitivity?* **An optional `sensitivity` field on the decision.**

Also decided: `SOLVED_WITHOUT_INSTANCE` refuses a solve result with no producing run as well as one whose run uses
no instance — otherwise the gate is dodged by not linking the run.
