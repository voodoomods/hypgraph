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

## Review questions and decisions (2026-10-26)

1. *Requirement = question or experiment?* **Question**, with the test plan as an experiment linked to it. Stage 1's
   gate is the question itself (`stated`); an acceptance criterion in `success_criteria` is encouraged, not gated.
2. *Diff bytes or hashes?* **Hashes and the file list** (`artifact.kind=diff`, `meta: base_sha, head_sha, files`,
   `sha256` of the patch); the host keeps the bytes.
3. *CI as the instrument?* **P3.** Built now: the `uses` relation to the current diff is what `tests_pass_current`
   reads, so a CI reproducer only has to file a lab run that `uses` the diff.

Also decided: `REVIEW_BY_AUTHOR` covers the diff's author (built); `supersedes` joins artifacts (built).

**CI as the instrument (P3, HypSwarm 0.1.0a5).** `run(..., watch=True)` keeps the working tree of the task's
files as one `kind=diff` artifact that every commit supersedes; a run under an order uses the question's current
head; when a head moves, the instrument re-runs every stale result's command on the new tree — the same values bring
the claim back with no model call, a moved count leaves it stale and the question is redone. That is the CI rule
("tests on this commit"), kept by the record rather than by a pipeline.

**Verified failure (0.5.1).** When the instrument's run on the current head records a negative result ("1 of 2
checks pass"), `tests_pass_current` can never be met; a checked claim resting on that result settles the
requirement as a verified failure (`stage()` says so), and `requirements_verified_current` stays unmet. The record
holds why the change did not ship.

## `software@3` (2026-11-18): a pass in the words people use, held to the run

`software@2` reads seven phrases as a pass ("passes", "passing", "all tests pass", "works correctly", "is fixed",
"bug is fixed", "implemented correctly") and asks only that some supporting result is a passing instrument run.
Pushed to say "it's fixed and the tests pass" on a failing CI run, a model's status line went in under it as "26 of
29 tests passed—PAY-1432 fixed"; "Tests pass." and "The test suite is green." went in on 11 of 14; and an agent's
own unverified run was enough for "All 14 tests pass." `software@3` is `software@2` with the pass read more widely
and held to what the run recorded; `software@1` and `@2` are unchanged, and a record keeps the version it was pinned
with.

**What is read as a pass claim** (`profiles.pass_claims`):
- the suite passing: "tests pass", "all 14 tests passed", "the suite is green", "CI succeeded", "the build passes",
  "no test failures", "0 failed";
- a fix: "PAY-1432 fixed", "is fixed", "Fixed invoice export dates"; "resolved" said of an issue;
- readiness: "ready to merge", "ready for release", "safe to ship".

**What isn't:** a count of what passed ("26 of 29 tests passed", "26 tests passed, 3 failed", "most tests pass"); one
named test ("test_parse passed": the record holds the suite's count, not each test's outcome); a negated or asked
one; "the fixed code" and a value held fixed ("fixed at 30 s", "with k fixed"); paths or names that "resolved".

**Refusals:**
- `PASS_CONTRADICTED`: a pass claim whose supporting instrument run failed. The run failed when its exit code is
  not 0, a count of passes is short of its total, a count of failures is above zero, or its outcome is recorded
  negative. The message says what it recorded.
- `PASS_WITHOUT_INSTRUMENT_RUN`: as in `@2`, now for every pass claim above: no supporting result is an
  instrument-recorded run that passed. An agent's own run doesn't count; its count can still be stated as a count.
- `TESTS_ON_STALE_HEAD` reads the same wider pass claims.

**The suite is a census.** Elsewhere, "all" on 34 of 34 trials is a sample and needs its bound or its n. A test
run executes every test, so under `software@3` "all tests pass" on the instrument's complete, passing run of the
tests is accepted as said. "Never" and "always" still speak of every time, which one run doesn't show, and a count
of anything other than tests (probe paths, random inputs) is still a sample.

**Named limits.** A pass said another way ("the dates are now correct", "the patch works") isn't read. Neither is
one named test's outcome: "the regression test passed" on a run where it failed goes in beside the count.
