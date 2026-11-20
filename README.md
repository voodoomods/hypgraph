<p align="center"><img src="https://hypgraph.com/assets/hypgraph.svg" width="72" alt=""></p>

<h1 align="center">HypGraph</h1>
<p align="center"><b>The evidence layer for AI research agents.</b><br>
A hash-chained research record that checks every claim as it is written and derives how well each one is known.<br>
<sub><i>Don't believe the hype. Test the hyp.</i></sub></p>

<p align="center">
<a href="https://pypi.org/project/hypgraph/"><img src="https://img.shields.io/pypi/v/hypgraph" alt="PyPI version"></a>
<a href="https://pypi.org/project/hypgraph/"><img src="https://img.shields.io/pypi/pyversions/hypgraph" alt="Supported Python versions"></a>
<a href="https://github.com/voodoomods/hypgraph/actions/workflows/ci.yml"><img src="https://github.com/voodoomods/hypgraph/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
<a href="https://github.com/voodoomods/hypgraph/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="License: Apache-2.0"></a>
</p>

<p align="center">
<a href="https://hypgraph.com">Website</a> ·
<a href="https://hypgraph.com/agents/">For agents</a> ·
<a href="https://hypgraph.com/engineers/">For engineers</a> ·
<a href="https://hypgraph.com/spec/">Record format</a> ·
<a href="https://hypgraph.com/examples/">Live examples</a> ·
<a href="https://github.com/voodoomods/hypgraph/blob/main/CHANGELOG.md">Changelog</a>
</p>

<p align="center"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://hypgraph.com/assets/readme/record-dark.png">
  <img src="https://hypgraph.com/assets/readme/record-light.png" width="880" alt="The Graph view of a real research record: one question at the centre, 27 hypotheses around it, experiments and runs fanning out into 90 results, and 22 claims at the rim">
</picture></p>
<p align="center"><sub>A real research record in the HypGraph UI: one question, 27 hypotheses, 12 experiments and their runs, 90 results, 22 claims, 395 hash-chained events. <a href="https://hypgraph.com/examples/">Open an example live</a>.</sub></p>

---

## Contents

- [Overview](#overview)
- [Quick start](#quick-start)
- [How a claim is checked](#how-a-claim-is-checked)
- [Standing is derived, never asserted](#standing-is-derived-never-asserted)
- [Telling an honest mistake from a false claim](#telling-an-honest-mistake-from-a-false-claim)
- [Profiles](#profiles)
- [Claim policies](#claim-policies)
- [Integration](#integration)
- [Performance](#performance)
- [Project status and versioning](#project-status-and-versioning)
- [Documentation](#documentation)
- [Security](#security)
- [Contributing](#contributing)
- [Background](#background)
- [Maintainer](#maintainer)
- [Disclaimer](#disclaimer)
- [License](#license)

## Overview

Research agents write fluently, and fluency hides overclaims. Fifty clean prompts become "the model never leaks". A
search too weak to find anything becomes "ruled out". Three copies of one result become three independent lines of
evidence, and a number appears that no result contains. Every sentence reads fine, and the next claim, decision or
deployment gets built on top of it.

HypGraph is the record agents write into instead of prose. It checks each claim the moment it is written: its numbers
must come from a result, its "never" needs the trials behind it, its "better" needs both sides measured. When the
arithmetic does not hold, the claim is refused with a code, the calculation, and the sentence that would be honest.

```text
$ hypgraph add claim statement="The model never leaks training data." exposure=1000000 exposure_unit=users …
refused: claim refused:
- 'never' rests on 0 of 50: that only rules out it happening more than 5.8% of the time (95% upper bound).
  Honest version: 'no occurrences in 50 trials (95% upper bound 5.8%)'. To support a rate below 1 in 1,000 you need
  about 2,995 trials without one. Across the 1,000,000 users this claim applies to, that leaves up to 58,155 not
  ruled out. [ABSOLUTE_UNDERPOWERED]
```

The honest version goes in, and it carries its consequence wherever it is read:

```text
active claim · unchecked · 1 independent line of support · … · 0 of 50 = at most 5.8% at 95%, up to 58,155 of 1,000,000 not ruled out
```

**What it provides**

| Capability | What it means |
|---|---|
| Checks at write time | Every claim is held to the results it rests on. A claim the evidence does not support is refused with a stable code and a suggested correction. |
| Derived standing | How well a claim is known is computed on every read from reviews, premises and independent lines of evidence. It is never set by hand. |
| Tamper-evident record | Every write is an event in a SHA-256 hash chain. A record can be exported as one file and verified by a third party. |
| Profiles and claim policies | Versioned, frozen rule sets for a discipline's workflow (science, software, trading, knowledge, optimization) and for single kinds of claim. |
| Agent and system integration | An MCP server, a dependency-free Python API, an HTTP API with a web UI, and a command line that can gate CI. |
| Conduct log | Every refusal is logged: who tried to say what, which rule caught it, and whether they corrected it. |

## Quick start

Requires Python 3.10 or later. The engine, command line, HTTP server and UI have no dependencies.

```bash
pip install hypgraph
hypgraph demo        # a complete worked investigation (Broad Street, 1854) built into ./research.hypgraph
hypgraph serve       # explore it in the HypGraph UI: http://127.0.0.1:8765
hypgraph report      # the facts, generated from the record
```

Other ways to try it:

- **In the browser.** Try to get a claim past the real engine at [hypgraph.com/play](https://hypgraph.com/play/), or
  watch a multi-agent run in each profile, replayed from its record, at
  [hypgraph.com/examples](https://hypgraph.com/examples/).
- **Scripted scenarios, no model needed.** Eleven short stories in
  [examples/problems](https://github.com/voodoomods/hypgraph/tree/main/examples/problems): an agent that says it is
  fixed, one that makes up figures, one that tells the boss what he wants to hear, a backtest that brags, an
  "optimal" with no proof, a rogue agent editing the log, and one for each claim policy: a dry run reported as
  done, one wire report called independent confirmation, a validation-split win called beating the baseline, a
  screening log called fully accounted for, and all six policies pinned on one record.

## How a claim is checked

"Never" is the most expensive word in research, because everything built on it inherits it. Zero failures in *n*
trials does not mean a rate of zero. It means a rate below 1 − 0.05^(1/*n*), about 3/*n*, at 95% confidence. HypGraph
holds every claim to that arithmetic.

| The claim says | Refused as | Because |
|---|---|---|
| "never leaks", from 0 of 50 | `ABSOLUTE_UNDERPOWERED` | It could still be 5.8%, up to 58,155 of a million users. |
| "never leaks", from 0 of 3,000, without saying 3,000 | `ABSOLUTE_HIDES_DENOMINATOR` | Readers hear "never", but it means "at most 1 in 1,000". |
| "eliminates hallucinations entirely" | `ABSOLUTE_WITHOUT_COUNT` | Nothing was counted. |
| "5 points better" (the counts say 2.8) | `UNBOUND_NUMBER` | The number comes from nowhere. 2.8 points, 81.2% vs 78.4% and +3.6% all pass, because they follow from the counts. |
| "significantly better", counts 812/1,000 vs 800/1,000 | `SIGNIFICANCE_NOT_SHOWN` | The record runs the test: p = 0.5. |
| "prompt format has no effect" | `EXCLUSION_WITHOUT_POWER` | At 2,000 items a 3.6-point effect would usually go unseen. |
| "longer prompts cause the gain" | `CAUSAL_WITHOUT_INTERVENTION` | No experiment intervened. |
| "the supplement changes steps_k", p = 0.012, while the record's Holm p is 0.25 | `UNCORRECTED_EFFECT` | One of 20 outcomes; the claim's own record says it does not survive correction. |
| "outperforms the baseline", no numbers | `COMPARATIVE_WITHOUT_COMPARISON` | Only one side was measured. |

Every refusal has a stable code, the arithmetic, and the sentence that would be honest, so an agent can repair a
claim in one step. `hypgraph bound 0 50 --exposure 1e6` (or the MCP tool `bound`) answers "what does my count
actually support?" before anyone writes the word.

On the website, the same engine refused these as the page was built. Each gets a code and what to fix; the rewrite
underneath, on the same evidence, was accepted.

<p align="center"><a href="https://hypgraph.com/play/"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://hypgraph.com/assets/readme/refusals-dark.png">
  <img src="https://hypgraph.com/assets/readme/refusals-light.png" width="880" alt="Three overclaims struck through — 'always beats the baseline', '5 points better', 'never leaks training data' — each with its refusal code and what to fix, and the honest rewrite accepted as CL1, CL2, CL3">
</picture></a></p>

### The refusal log

Every refusal is logged: who tried to say what, which rules caught it, and whether they came back with the honest
version.

```text
$ hypgraph refusals
## Overclaims caught — 4 refused, 3 came back honest
| author  | refused | fixed | open | most common |
| analyst | 4       | 3     | 1    | EXCLUSION_WITHOUT_POWER ×1, ABSOLUTE_UNDERPOWERED ×1, UNBOUND_NUMBER ×1 |
### Latest
- analyst: “Prompt format makes no difference to accuracy.” — EXCLUSION_WITHOUT_POWER → not fixed
- analyst: “The model never leaks training data.” — ABSOLUTE_UNDERPOWERED → fixed as CL2
- analyst: “The fine-tune is 5 points better than the baseline.” — UNBOUND_NUMBER → fixed as CL1
- analyst: “The fine-tune always beats the baseline.” — ABSOLUTE_WITHOUT_COUNT, COMPARATIVE_WITHOUT_COMPARISON → fixed as CL1
```

### Checking a written report

Most overstatement lives in the write-up, not the record. `hypgraph check summary.md` lints a final report against
the record. It catches numbers no result contains, claims called "established" that the record has as unchecked or
contested, citations to withdrawn claims, and "never", "no effect" or "significantly" with nothing behind them. It
exits 1 on errors, so it can gate CI.

```text
$ hypgraph check summary.md
summary.md:8: error REPORT_OVERSTATES_STANDING: 'established' — but CL2 is unchecked in the record …
summary.md:9: warning REPORT_UNSOURCED_NUMBER: 700 isn't in any result, measurement, claim, scope or constant …
summary.md:13: error REPORT_UNKNOWN_CODE: CL9 isn't in the record for this investigation — a citation to nothing.
```

### When a premise falls

When something is withdrawn, the record says what falls with it.

```text
$ hypgraph withdraw CL1 --why "the held-out set leaked into training"
CL1 — withdrawn claim · …
  ⚠ 2 nodes rest on CL1: 1 decision (D1); 1 claim (CL2) — now AT RISK
```

## Standing is derived, never asserted

Nothing in the record is ever set as known. How well each claim is known is derived on every read.

| Question the record answers | How |
|---|---|
| Was it reviewed, and which version? | Only named reviewers count, and never on their own work. A revised claim goes back to unchecked. |
| Does it rest on something that fell? | Withdraw a premise and everything built on it is flagged **AT RISK**. A decision whose evidence changed is flagged **REVISIT**. |
| How many independent lines support it? | Results that share a run, a data file or a source count once. |
| How strong is the best one? | From an agent's report, through a run your job runner recorded and a separate implementation, up to a replication on new data. |

Every write is an event in a **SHA-256 hash chain**. A record can be handed to a reviewer, a regulator or another
team, and they can verify it without trusting you.

Records can build on each other. A source in one record pins a node of another: the version it read and that
version's hash. The UI draws every pinned record beside yours, verifies each one, and checks each pin against it.

<p align="center"><a href="https://hypgraph.com/examples/linked/#view=graph"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://hypgraph.com/assets/readme/linked-dark.png">
  <img src="https://hypgraph.com/assets/readme/linked-light.png" width="880" alt="Three hash-chained records drawn together — London's water 1854–1866, Broad Street 1854 and East London 1866 — joined by pinned references labelled with the version each one read, every pin checked">
</picture></a></p>
<p align="center"><sub>Three records, each its own hash chain, joined only by pinned references. <a href="https://hypgraph.com/examples/linked/#view=graph">Open it live</a>.</sub></p>

## Telling an honest mistake from a false claim

Two agents answer one question from the same road register. One makes an honest mistake and the other makes a false
claim. The record tells them apart, and nobody has to label anyone.

<p align="center"><a href="https://hypgraph.com/examples/dispute/"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://hypgraph.com/assets/readme/dispute-dark.png">
  <img src="https://hypgraph.com/assets/readme/dispute-light.png" width="880" alt="The Evidence view of a disputed answer: Ada's claim that the shortest route is 29 km is checked, Mallory's claim that the register is in miles is contested, above the two route counts the instrument filed and the seven register items they rest on">
</picture></a></p>
<p align="center"><sub>Standing derived from the record: one answer checked, the other contested. <code>hypgraph demo dispute</code> builds it; <a href="https://hypgraph.com/examples/dispute/">open it live</a>.</sub></p>

- **Ada** says the shortest route is 30 km. The instrument counted 1 of the 4 routes as shorter, so the record refuses
  it (`COUNT_CONTRADICTS`). She corrects it to 29 km, which the count backs.
- **Mallory** says the register is in miles, and cites the register's own units note as support. The note says
  kilometres, so the record refuses it (`SOURCE_CONTRADICTS`). She says it again and is refused again.

The record cannot catch every false claim by itself: once Mallory stops citing the note, her claim goes in. But it
keeps what she was shown. The reviewer fails her claim against the note, and the conduct log (`hypgraph refusals`,
`Graph.conduct()`) says who corrected what they were shown and who kept saying it.

```text
$ hypgraph demo dispute
…
What the record says of each author:
  ada        the record's own count contradicted a claim of this author's 1 time; the author did not say it again, and corrected it 1 time
  mallory    1 claim of this author's went against a source it cited as support; the author said it again 2 times after being shown, and never corrected it; its last word still says it
```

## Profiles

The checks above are the scientific case written as code. A **profile** says what a discipline means by evidence,
acceptance and done, and carries that discipline's **workflow**: the stages a question passes through, the gate out
of each, what invalidates evidence, and the typed shapes. The record enforces all of it, so none of it depends on a
prompt being followed.

Pin a profile when the investigation is created (`"profile": "trading@4"`). With none, the general checks apply and
no workflow is enforced. For new work, pin the newest version of a profile, shown below.

| Profile | Stages a question passes through | The record refuses | Done when |
|---|---|---|---|
| `scientific@3` | asked → conjectured → preregistered (**before** any run, **each hypothesis's own link**) → run → evidenced → claimed → reviewed | Numbers no result accounts for; "never" without the count; "significant" without the test; a check on stale evidence. | Every question is settled. |
| `software@3` | specified → implemented (a diff by hash) → verified (**the instrument ran the tests on that head**) → claimed → reviewed | "It passes", "fixed" or "ready to merge" without an instrument run, **on a run that failed**, or on a superseded head; the diff's author as its reviewer. | Every requirement's claim rests on a passing run on the current head. |
| `trading@4` | asked → thesised → preregistered (**per thesis**) → backtested (**out of sample, after costs, trials declared**) → claimed → risk-reviewed → positioned → monitored | A backtest without its costs; "edge" without both, or without the configurations tried; **an edge the numbers deny** (a loss, or behind the benchmark, out of sample after costs); an in-sample return not called one; a position without size, stop and review date; any live order. | Questions are settled, a position is taken or declined, and nothing is past its review date. |
| `knowledge@2` | asked → (searched) → sourced (**the passage**, retrieved, kind) → claimed → checked | A claim with no source; a source without its passage. | Every claim cites a source and is checked. |
| `optimization@4` | posed (the instance by hash) → modelled → configured (**before** the solve) → solved → verified → claimed → checked | An objective without feasibility; "optimal" without a bound, **with a gap the bound leaves open, on an infeasible incumbent**, or on a changed instance; a solve that uses no instance. | A feasible bounded incumbent is verified on the current instance. |

**How a workflow behaves**

- **The stage is derived, never set.** `g.stage(question)` reads it off the record: the first stage whose gate is not
  met, with every gate shown as MET or NOT MET and what would meet it. Also available as `GET /api/graph/stages` and
  the MCP tool `stage`.
- **Evidence can go stale.** A workflow widens what puts dependants AT RISK: `uses` (a corrected data file, a
  superseded diff or instance) and `cites` (a withdrawn source). Evidence goes stale when the artifact it used is
  superseded or its `valid_until` has passed. A result whose run names no file it read goes stale when an input file
  of its question changes after it; name the files with `uses` and only those count.
- **An honest negative completes a question.** A checked `inconclusive` claim, a declined thesis (`no_position`) and
  a verified failure each complete a question that the gates alone never would.
- **Completion is reported.** `completion(inv)` reports each criterion; `hypgraph serve` exposes
  `/api/graph/completion` and `/api/graph/profiles`.

**Profiles are versioned and frozen.** A record written under `trading@2` means the same thing in a year. A pinned
version's rules never change, and a check is tightened by adding a version, not by editing one. An existing
investigation keeps the rules it was pinned with, so nothing it holds is refused after the fact, and moving to a newer
version is a choice made for new work. Every earlier version stays available, exactly as it was.

The newest versions read what a result says, not only that it has the right fields:

- `trading@3` refuses "edge" on an out-of-sample loss or a return behind the benchmark, and requires an in-sample
  return to say so.
- `optimization@3` requires a feasible incumbent within 1e-4 of its bound before "optimal".
- `software@3` reads "tests pass", "the suite is green", "fixed", "resolved" and "ready to merge", and refuses them
  on a run that failed, quoting what the run recorded ("26 of 29 passed, exit code 1"). A count of what passed is
  accepted ("26 of 29 tests pass; 3 still fail").

None of these refuses a sentence that denies something ("there is no edge"): an audit has to be able to name a claim
to refute it.

The method each workflow is taken from is quoted, one page each, in
[docs/workflows](https://github.com/voodoomods/hypgraph/tree/main/docs/workflows). Adding a discipline is one
`Profile` with a `Workflow`.

## Claim policies

A profile says how the work proceeds. A **claim policy** says what one kind of sentence is held to, and nothing else:
no stages, no gates, no completion. It is pinned beside whatever profile the investigation uses, or with none.

```json
{"profile": "scientific@2", "claim_policies": ["baseline_comparison@1"]}
```

| Claim policy | The sentence it reads | The record refuses |
|---|---|---|
| [`baseline_comparison@1`](https://github.com/voodoomods/hypgraph/blob/main/docs/claim-policies/baseline-comparison.md) | A model said to beat a baseline. | "Beats the baseline" **when the held-out scores have the baseline ahead**, or when no result scores both on held-out data; a validation lead over a baseline with no validation score; a validation score stated as the result with no word that it is one. |
| [`corroboration@1`](https://github.com/voodoomods/hypgraph/blob/main/docs/claim-policies/corroboration.md) | A sourcing line for one fact. | "Independently confirmed", "corroborated" or "three separate reports" **when the source register counts one independent origin**; more independent sources than the register counts; sources listed side by side on one origin with nothing said of how they depend. |
| [`done_claim@1`](https://github.com/voodoomods/hypgraph/blob/main/docs/claim-policies/done-claim.md) | An agent's status report on an action it carried out with a tool. | "Sent", "deployed" or "done" **when the harness's log shows only a dry run**, a failed call, or some of several calls failing with no count given; "all five" on 3 of 5; a report on such a log that does not say the action was not carried out. |
| [`flow_counts@1`](https://github.com/voodoomods/hypgraph/blob/main/docs/claim-policies/flow-counts.md) | A statement on the flow of records through a review. | "All records are accounted for" **when the screening log leaves records unaccounted for**; "followed the protocol" when some records were not handled to its standard and no deviation is named; "every exclusion has a reason" when some have none. |
| [`forecast_call@1`](https://github.com/voodoomods/hypgraph/blob/main/docs/claim-policies/forecast-call.md) | A line on how a forecast compared with what happened. | "We called it", "as predicted" or "our forecast proved accurate" **when nothing was sealed before the outcome, or the sealed forecast put what happened under 50%**; a probability entered after the outcome given as the forecast. |
| [`proof_claim@1`](https://github.com/voodoomods/hypgraph/blob/main/docs/claim-policies/proof-claim.md) | A status line on the verification of one property. | "Proved", "proven" or "formally verified" **when the checker's report has open proof obligations, is a bounded check, or gave no result**; "verified" or "holds" on a bounded check with the bound left out. |

Each policy reads a claim only when it rests on a result of the policy's own shape, filed by the instrument. Three
examples:

- On a report where the baseline leads the test split 0.81 to 0.79, "the new model beats the baseline" is refused
  with those two scores. "Does not beat the baseline on the test split" and "ahead on 1 of 5 seeds" are accepted.
- On a tool log that shows only a dry run, "the renewal notice has been sent" is refused, and so is "has been handled
  and is ready for delivery". "Only a dry run was made; nothing has been sent yet" is accepted.
- On a source register where the Gazette cites the Courier, "independently confirmed by the Ashby Courier and the
  Harrow Gazette" is refused. "The Ashby Courier reports it; the Harrow Gazette cites the Courier's report" is
  accepted.

A policy is pinned when the investigation is created, is versioned and frozen as a profile is, and never stands down
a profile's check. Each policy's page gives its worked examples, its named limits and how it was measured. The rules
are in [docs/claim-policies](https://github.com/voodoomods/hypgraph/blob/main/docs/claim-policies/README.md), and
`GET /api/graph/claim-policies` lists the policies available.

`evaluation@1` remains available as a profile. It is `scientific@2` with `baseline_comparison@1`; a test holds the
two to the same answer, and new work should pin the pair.

## Integration

### Agents (MCP)

```bash
pip install "hypgraph[mcp]"
claude mcp add hypgraph -- hypgraph --db study.hypgraph --as claude mcp     # any MCP client works
hypgraph skill --install                                                     # the Agent Skill (.claude/skills/hypgraph/SKILL.md)
```

The server writes as one author, fixed when it starts. The agent cannot pass another name or write as your job
runner, and its verdicts count only if you name it as a reviewer.

| Tool group | Tools |
|---|---|
| Read | `overview`, `find`, `show`, `report`, `schema`, `verify` |
| Write | `start_investigation`, `add`, `link`, `revise`, `withdraw`, `retract_link`, `review`, `register_run` |
| Plan and check | `next_experiments`, `work_queue`, `claim_work`, `bound`, `check_report`, `refusal_log` |
| Team work orders | `my_work`, `issue_work`, `return_work`, `check_work`, `accept_work`, `rework`, `cancel_work`, `settle_work`, `cancel_moot`, `briefing`, `completion`, `stage` |

A blind order (`issue_work(..., blind=true)`) seals the record from its checker until it is returned.

- The method for agents: [AGENTS.md](https://github.com/voodoomods/hypgraph/blob/main/AGENTS.md), with a short
  version at [llms.txt](https://hypgraph.com/llms.txt).
- Runnable examples for LangChain, LangGraph, PydanticAI, CrewAI, the OpenAI Agents SDK and the Claude Agent SDK:
  [examples/frameworks](https://github.com/voodoomods/hypgraph/tree/main/examples/frameworks).

### Python

The core is one Python package with no dependencies. You decide who is trusted to do what.

```python
from hypgraph import Graph, Policy

g = Graph("research.hypgraph",
          policy=Policy(reviewers={"critic", "stats"},      # whose verdicts count
                        instrument="runner"),               # the only author that files lab-recorded runs
          spend=my_ledger.spend)                            # optional: prices the work behind each investigation

with g.writing_for(task_id):                                # every event carries the task, for cost tracing
    g.create(author=agent_name, type="claim", inv=inv, fields={...}, links=[...])
```

In a multi-agent system, give each agent its own author name, make your critic agents reviewers, and have your job
runner write as the instrument, so its runs count as recorded, not reported.

### HTTP API and UI

- `hypgraph.server.dispatch(graph, method, path, query, body)` is the JSON API, and `hypgraph.ui.static_dir()` is the
  HypGraph UI to mount next to it in your own web framework.
- `GET /api/graph/stream?inv=` pushes every event as it is written (Server-Sent Events, resumable with
  `Last-Event-ID`), including writes from another process on the same file.
- `GET /api/graph/profile?inv=` gives the investigation's profile as a UI speaks it: each node type's label, the
  workflow's stages and the report's name.
- A telemetry sidecar (`<db>.telemetry.jsonl`, written by hypswarm) rides the same stream as `telemetry` events, so
  the Live view shows every model and tool call as it happens.

### CI and audit

```bash
hypgraph export -o record.bundle.json && hypgraph verify record.bundle.json
hypgraph check summary.md
```

The bundle is a single file your reviewers or auditors can check with SHA-256, in any language or in the browser.
`--telemetry` carries the sidecar too, outside the chain, so the bundle replays the run with no server.

The full integration guide is at [hypgraph.com/engineers](https://hypgraph.com/engineers/).

## Performance

The engine is pure Python and stays fast at the sizes research records reach. On the record built by
[`dev/bench.py`](https://github.com/voodoomods/hypgraph/blob/main/dev/bench.py) (one investigation of questions,
results, claims and reviews), at 10,001 nodes on a Windows laptop:

| Operation | Time |
|---|---|
| Derive every node's standing | 0.34 s |
| Read one node | 0.07 ms |
| One write | about 12 ms, mostly SQLite committing to disk |

Derivation grows in step with the record. A write costs what it touches: cached standing is kept for every node the
write cannot affect, and a randomized suite checks that against a full rebuild. Run `python dev/bench.py` for your
machine.

## Project status and versioning

- **Status.** HypGraph is pre-1.0 and under active development. Releases are published to
  [PyPI](https://pypi.org/project/hypgraph/) and described in the
  [changelog](https://github.com/voodoomods/hypgraph/blob/main/CHANGELOG.md).
- **Rule stability.** Profiles and claim policies are versioned and frozen. A released version's rules do not change;
  a tightened check ships as a new version, and every earlier version stays available.
- **Record format.** The format is specified in
  [docs/spec.md](https://github.com/voodoomods/hypgraph/blob/main/docs/spec.md). A bundle can be verified without this
  package.
- **How checks are measured.** Recent checks were measured before release in preregistered rounds, and their release
  notes and policy pages state the result with its named limits. Background is in
  [docs/verification.md](https://github.com/voodoomods/hypgraph/blob/main/docs/verification.md) and
  [docs/RELEASE-READINESS.md](https://github.com/voodoomods/hypgraph/blob/main/docs/RELEASE-READINESS.md).

## Documentation

| Topic | Where |
|---|---|
| For agents | [hypgraph.com/agents](https://hypgraph.com/agents/) · [AGENTS.md](https://github.com/voodoomods/hypgraph/blob/main/AGENTS.md) · [llms.txt](https://hypgraph.com/llms.txt) |
| For engineers | [hypgraph.com/engineers](https://hypgraph.com/engineers/) |
| Record format | [hypgraph.com/spec](https://hypgraph.com/spec/) · [docs/spec.md](https://github.com/voodoomods/hypgraph/blob/main/docs/spec.md) |
| Workflows | [docs/workflows](https://github.com/voodoomods/hypgraph/tree/main/docs/workflows) |
| Claim policies | [docs/claim-policies](https://github.com/voodoomods/hypgraph/blob/main/docs/claim-policies/README.md) |
| Examples | [hypgraph.com/examples](https://hypgraph.com/examples/) · [examples/frameworks](https://github.com/voodoomods/hypgraph/tree/main/examples/frameworks) · [examples/problems](https://github.com/voodoomods/hypgraph/tree/main/examples/problems) |
| Release history | [CHANGELOG.md](https://github.com/voodoomods/hypgraph/blob/main/CHANGELOG.md) |

## Security

What the server enforces, what it leaves to you, and how to report a vulnerability are in
[SECURITY.md](https://github.com/voodoomods/hypgraph/blob/main/SECURITY.md). A verified hash chain proves a record
unchanged; it does not prove the record correct.

## Contributing

Contributions are welcome. See
[CONTRIBUTING.md](https://github.com/voodoomods/hypgraph/blob/main/CONTRIBUTING.md) for how to propose a change, and
use [GitHub issues](https://github.com/voodoomods/hypgraph/issues) for bugs and requests.

## Background

HypGraph began as the research graph of a team of AI agents running long investigations under governed egress, and
was extracted so that anyone can use it. Each rule exists because the agents made the mistake behind it:

- a validation that was blind to the answer;
- a null model that broke the system's own rules;
- a summary whose numbers matched no result;
- "never" written about something that happened once in a thousand.

That team still runs on it, and its graph UI is built from this package. Against the team's live record (1,357
events, 790 nodes), the library derives the same standing for every node as the engine it replaced.

## Maintainer

HypGraph is developed and maintained by **[VoodooMods LLC](https://github.com/voodoomods)**.

## Disclaimer

Provided as is, without warranty. Standing is derived from what was written into a record, by rules you can read. It
is not a certification or an endorsement, a verified chain proves a record unchanged rather than correct, and nothing
here is legal, medical or financial advice. The full text is in
[DISCLAIMER.md](https://github.com/voodoomods/hypgraph/blob/main/DISCLAIMER.md).

## License

Code is licensed under [Apache-2.0](https://github.com/voodoomods/hypgraph/blob/main/LICENSE). The record format
([docs/spec.md](https://github.com/voodoomods/hypgraph/blob/main/docs/spec.md)) and the documentation are licensed
under CC BY 4.0. To cite HypGraph, use
[CITATION.cff](https://github.com/voodoomods/hypgraph/blob/main/CITATION.cff).
