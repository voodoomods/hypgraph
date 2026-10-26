# Workflow: `software`

## The method it is taken from

Continuous integration and code review as practised in professional engineering: a change is a reviewable unit
against a known base; the tests that count are the ones a machine ran on **that** change; nothing merges without
them; and a later change re-opens the question. Fowler's continuous integration ("every commit is built and
tested"), the pull-request review norm (author ≠ approver), and the DORA practice of trunk-based delivery where a
release is a decision on evidence the pipeline produced. The requirement plays the role of the question; the
instrument plays the role of CI.

## Stages

| # | stage | holds | gate out of it | who |
|---|---|---|---|---|
| 1 | specified | question = the requirement or the bug, with acceptance stated | the question has an acceptance criterion in its text or `success_criteria` **new** on a linked experiment (the test plan) | lead |
| 2 | implemented | artifact `kind=diff` registered: `base_sha`, `head_sha`, `files`, `sha256` of the patch | `diff_registered` **new**: a diff artifact `part_of` the question, newer than the last one | implementer |
| 3 | verified | run `kind=lab` that `uses` the diff artifact; result `tests` with `passed k of n`, `exit_code` | `tests_pass` **on that head**: the instrument's run `uses` the diff whose `head_sha` is current | tester, instrument |
| 4 | claimed | claim "requirement met" with measurements bound to the lab result | `claim_made`; validator `PASS_WITHOUT_INSTRUMENT_RUN` (today) | tester |
| 5 | reviewed | review by a reviewer who is not the diff's author | `reviewed` | reviewer |
| 6 | released | decision `based_on` the claim: merge / ship / hold, with the head_sha it releases | `decided` **new** | lead |

## Invalidation

- A **new diff artifact** on the same question (a newer `head_sha`) `supersedes` the old one. Every lab run that
  `uses` the old diff is STALE; its results, the claims on them, and the release decision go AT RISK. This is the
  gate a prompt cannot keep: the model that ran the tests at 14:02 does not know about the commit at 14:10.
- `uses`, `derived_from`, `based_on`, `rests_on` as at-risk relations (as scientific), plus **`supersedes` on
  artifacts** (today supersedes is for claims and decisions only).

## Freshness

A test result is fresh only if the diff its run `uses` has the current `head_sha` for the question. A `tests_pass`
predicate evaluated on a stale run is NOT MET with the reason "tests ran on <old sha>; current head is <new sha>".

## Typed artifacts

| kind | required fields | note |
|---|---|---|
| `diff` | `base_sha`, `head_sha`, `files` (list), `sha256` (of the patch), `path` | the reviewable unit |
| `test_run` | `command`, `exit_code`, `passed`, `failed`, `sha256` (of the log) | produced by the instrument's run |
| `build` | `head_sha`, `sha256` (of the artifact), `path` | optional |

A diff registered by an agent is `kind=agent` provenance; only the instrument's `uses` of it makes it evidence.

## Evidence rank

`lab_on_current_head > lab_on_old_head (stale) > agent_reported > unverified`. Replication across environments
(`new_env`: another OS or Python) ranks above `same_code` as in scientific.

## Report

"Change report": the requirement; the diff (base → head, files); the instrument's test run on that head (passed k
of n, exit code, command); the claim and its review; the release decision; **what is stale** (any earlier runs on
superseded heads, listed as superseded); open requirements.

## Completion

`requirements_verified` (today) tightened: every requirement's claim rests on a lab run whose diff is current. Plus
`released` when the task asks for a release decision.

## Refusals this workflow adds

- `TESTS_ON_STALE_HEAD`: a claim of passing bound to a lab result whose diff is superseded.
- `DIFF_WITHOUT_BASE`: a diff artifact without `base_sha` / `head_sha`.
- `REVIEW_BY_AUTHOR`: a review of a claim whose diff the reviewer authored (today only the claim's author is
  blocked; the diff's author should be too).

## For review

1. Is the requirement a `question` (proposed) or an `experiment` (the test plan)? Proposed: question with the test
   plan as a linked experiment, so "verified" has a preregistered acceptance criterion.
2. Should the record hold the diff bytes (as an artifact file) or only its hashes and file list? Proposed: hashes
   and list; the host keeps the bytes.
3. CI as the instrument: the reproducer is a GitHub Actions job that checks out `head_sha` and runs `command`.
   That is P3's software case.
