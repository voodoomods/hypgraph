<p align="center"><img src="https://hypgraph.com/assets/hypgraph.svg" width="72" alt=""></p>

<h1 align="center">HypGraph</h1>
<p align="center"><b>Don't believe the hype. Test the hyp.</b><br>
The evidence layer for AI research agents.<br>
<a href="https://hypgraph.com">hypgraph.com</a> · <a href="https://hypgraph.com/agents/">for agents</a> ·
<a href="https://hypgraph.com/engineers/">for engineers</a> · <a href="https://hypgraph.com/spec/">record format</a></p>

<p align="center"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://hypgraph.com/assets/readme/record-dark.png">
  <img src="https://hypgraph.com/assets/readme/record-light.png" width="880" alt="The Graph view of a real research record: one question at the centre, 27 hypotheses around it, experiments and runs fanning out into 90 results, and 22 claims at the rim">
</picture></p>
<p align="center"><sub>A real research record in the HypGraph UI: one question, 27 hypotheses, 12 experiments and their runs, 90 results, 22 claims, 395 hash-chained events. <a href="https://hypgraph.com/examples/">Open an example live</a>.</sub></p>

---

Research agents write fluently, and fluency hides overclaims. Fifty clean prompts become "the model never leaks". A
search too weak to find anything becomes "ruled out". Three copies of one result become three independent lines of
evidence, and a number appears that no result contains. Every sentence reads fine, and the next claim, decision or
deployment gets built on top of it.

HypGraph is the record agents write into instead of prose. It checks each claim the moment it's written: its numbers
must come from a result, its "never" needs the trials behind it, its "better" needs both sides measured. When the
arithmetic doesn't hold, the claim is refused, with a code, the math, and the sentence that would be honest:

```text
$ hypgraph add claim statement="The model never leaks training data." exposure=1000000 exposure_unit=users …
refused: claim refused:
- 'never' rests on 0 of 50: that only rules out it happening more than 5.8% of the time (95% upper bound).
  Honest version: 'no occurrences in 50 trials (95% upper bound 5.8%)'. To support a rate below 1 in 1,000 you need
  about 2,995 trials without one. Across the 1,000,000 users this claim applies to, that leaves up to 58,155 not
  ruled out. [ABSOLUTE_UNDERPOWERED]
```

The honest version goes in, and it carries its consequence wherever it's read:

```text
active claim · unchecked · 1 independent line of support · … · 0 of 50 = at most 5.8% at 95%, up to 58,155 of 1,000,000 not ruled out
```

On the website, the same engine refused these as the page was built. Each gets a code and what to fix; the
rewrite underneath, on the same evidence, got in:

<p align="center"><a href="https://hypgraph.com/play/"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://hypgraph.com/assets/readme/refusals-dark.png">
  <img src="https://hypgraph.com/assets/readme/refusals-light.png" width="880" alt="Three overclaims struck through — 'always beats the baseline', '5 points better', 'never leaks training data' — each with its refusal code and what to fix, and the honest rewrite accepted as CL1, CL2, CL3">
</picture></a></p>
<p align="center"><sub>Try to get a claim past it yourself: <a href="https://hypgraph.com/play/">hypgraph.com/play</a>.</sub></p>

## The arithmetic of never

"Never" is the most expensive word in research, because everything built on it inherits it. Zero failures in *n*
trials doesn't mean a rate of zero. It means a rate below 1 − 0.05^(1/*n*), about 3/*n*, at 95% confidence. HypGraph
holds every claim to that:

| The claim says | Refused as | Because |
|---|---|---|
| "never leaks", from 0 of 50 | `ABSOLUTE_UNDERPOWERED` | it could still be 5.8%, up to 58,155 of a million users |
| "never leaks", from 0 of 3,000, without saying 3,000 | `ABSOLUTE_HIDES_DENOMINATOR` | readers hear "never", but it means "at most 1 in 1,000" |
| "eliminates hallucinations entirely" | `ABSOLUTE_WITHOUT_COUNT` | nothing was counted |
| "5 points better" (the counts say 2.8) | `UNBOUND_NUMBER` | the number comes from nowhere. 2.8 points, 81.2% vs 78.4% and +3.6% all pass, because they follow from the counts. |
| "significantly better", counts 812/1,000 vs 800/1,000 | `SIGNIFICANCE_NOT_SHOWN` | the record runs the test: p = 0.5 |
| "prompt format has no effect" | `EXCLUSION_WITHOUT_POWER` | at 2,000 items a 3.6-point effect would usually go unseen |
| "longer prompts cause the gain" | `CAUSAL_WITHOUT_INTERVENTION` | no experiment intervened |
| "the supplement changes steps_k", p = 0.012, while the record's Holm p is 0.25 | `UNCORRECTED_EFFECT` | one of 20 outcomes; the claim's own record says it doesn't survive correction |
| "outperforms the baseline", no numbers | `COMPARATIVE_WITHOUT_COMPARISON` | only one side was measured |

Every refusal has a stable code, the arithmetic, and the sentence that *would* be honest, so an agent can repair a
claim in one step. `hypgraph bound 0 50 --exposure 1e6` (or the MCP tool `bound`) answers "what does my count
actually support?" before anyone writes the word.

Every refusal is also **logged**: who tried to say what, which rules caught it, and whether they came back with
the honest version.

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

And because most hype lives in the write-up, not the record, **`hypgraph check summary.md`** lints the final report
against the record. It catches numbers no result contains, claims called "established" that the record has as
unchecked or contested, citations to withdrawn claims, and "never" / "no effect" / "significantly" with nothing
behind them. It exits 1 on errors, so it can gate CI:

```text
$ hypgraph check summary.md
summary.md:8: error REPORT_OVERSTATES_STANDING: 'established' — but CL2 is unchecked in the record …
summary.md:9: warning REPORT_UNSOURCED_NUMBER: 700 isn't in any result, measurement, claim, scope or constant …
summary.md:13: error REPORT_UNKNOWN_CODE: CL9 isn't in the record for this investigation — a citation to nothing.
```

And when something does fall, the record says what falls with it:

```text
$ hypgraph withdraw CL1 --why "the held-out set leaked into training"
CL1 — withdrawn claim · …
  ⚠ 2 nodes rest on CL1: 1 decision (D1); 1 claim (CL2) — now AT RISK
```

## Derived, never asserted

Nothing in the record is ever *set* as known. How well each claim is known is **derived on every read**:

- **reviewed, and which version?** Only named reviewers count, and never on their own work. A revised claim goes back
  to unchecked.
- **does it rest on something that fell?** Withdraw a premise and everything built on it is flagged **AT RISK**. A
  decision whose evidence changed is flagged **REVISIT**.
- **how many independent lines?** Results that share a run, a data file or a source count **once**.
- **how strong is the best one?** From an agent's report, through a run your job runner recorded and a separate
  implementation, up to a replication on new data.

Every write is an event in a **SHA-256 hash chain**. A record can be handed to a reviewer, a regulator or another
team, and they can verify it without trusting you.

Records can build on each other. A source in one record pins a node of another: the version it read and that
version's hash. The UI draws every pinned record beside yours, verifies each one, and checks each pin against it.

<p align="center"><a href="https://hypgraph.com/examples/linked/#view=graph"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://hypgraph.com/assets/readme/linked-dark.png">
  <img src="https://hypgraph.com/assets/readme/linked-light.png" width="880" alt="Three hash-chained records drawn together — London's water 1854–1866, Broad Street 1854 and East London 1866 — joined by pinned references labelled with the version each one read, every pin checked">
</picture></a></p>
<p align="center"><sub>Three records, each its own hash chain, joined only by pinned references. <a href="https://hypgraph.com/examples/linked/#view=graph">Open it live</a>.</sub></p>

## One record, five disciplines

The rules above are the scientific case written as code. A **profile** says what a domain means by evidence,
acceptance and done — and, from 0.5, carries the discipline's own **workflow**: the stages a question passes
through, the gate out of each, what invalidates evidence, the typed shapes. The record enforces all of it, so none
of it depends on a prompt being followed. Pin one on the investigation (`"profile": "software@2"`); without one, the
record behaves exactly as before.

| profile | the stages a question passes through | the record refuses | done when |
|---|---|---|---|
| `scientific@2` | asked → conjectured → preregistered (**before** any run) → run → evidenced → claimed → reviewed | numbers no result accounts for, "never" without the count, "significant" without the test, a check on stale evidence | every question settled |
| `software@2` | specified → implemented (a diff by hash) → verified (**the instrument ran the tests on that head**) → claimed → reviewed | *"it passes"* without an instrument run, or on a superseded head; the diff's author as its reviewer | every requirement's claim rests on a passing run on the current head |
| `trading@2` | asked → thesised → preregistered → backtested (**out of sample, after costs, trials declared**) → claimed → risk-reviewed → positioned → monitored | a backtest without its costs; *"edge"* without both, or without the configurations tried; a position without size, stop, review date; any live order | questions settled, a position taken or declined, nothing past its review date |
| `knowledge@2` | asked → (searched) → sourced (**the passage**, retrieved, kind) → claimed → checked | a claim with no source; a source without its passage | every claim cites a source and is checked |
| `optimization@2` | posed (the instance by hash) → modelled → configured → solved → verified → claimed → checked | an objective without feasibility; *"optimal"* without a bound, or on a changed instance; a solve that uses no instance | a feasible bounded incumbent, verified on the current instance |

**The stage is derived, never set**: `g.stage(question)` reads it off the record (the first stage whose gate is not
met, every gate MET / NOT MET with what would meet it); `GET /api/graph/stages`; MCP tool `stage`. A workflow
widens what puts dependants AT RISK — `uses` (a corrected data file, a superseded diff or instance), `cites` (a
withdrawn source) — and evidence goes **stale** when the artifact it used is superseded or its `valid_until` has
passed. A result whose run names no file it read goes stale when an input file of its question changes after it:
nothing shows it read the new version (name the files with `uses` and only those count). An honest "it can't be answered" (a checked `inconclusive` claim), a declined thesis (`no_position`) and a
verified failure each complete a question the gates alone never would.

Profiles are versioned and frozen: a record written under `trading@1` means the same thing in a year, and the `@1`
profiles stay exactly as they were. `completion(inv)` reports each criterion; `hypgraph serve` exposes
`/api/graph/completion` and `/api/graph/profiles`. The method each workflow is taken from is quoted, one page each,
in [docs/workflows/](docs/workflows/). Adding a discipline is one `Profile` with a `Workflow`.

## Connect your agent

```bash
pip install "hypgraph[mcp]"
claude mcp add hypgraph -- hypgraph --db study.hypgraph --as claude mcp     # any MCP client works
hypgraph skill --install                                                     # + the Agent Skill (.claude/skills/hypgraph/SKILL.md)
```

The server writes as one author, fixed when it starts. The agent can't pass another name or write as your job runner,
and its verdicts count only if you name it as a reviewer. Tools: `overview`, `find`, `show`, `start_investigation`,
`add`, `link`, `revise`, `withdraw`, `retract_link`, `review`, `next_experiments`, `work_queue`, `claim_work`,
`register_run`, `bound`, `check_report`, `refusal_log`, `report`, `verify`, `schema`; and for a team working through
work orders, `my_work`, `issue_work`, `return_work`, `check_work`, `accept_work`, `rework`, `cancel_work`,
`settle_work`, `cancel_moot`, `briefing`, `completion`, `stage`. A blind order (`issue_work(..., blind=true)`) seals
the record from its checker until it is returned. The method is in [AGENTS.md](https://github.com/voodoomods/hypgraph/blob/main/AGENTS.md); the short version is
[llms.txt](https://hypgraph.com/llms.txt). What the server enforces, and what it leaves to you, is in
[SECURITY.md](https://github.com/voodoomods/hypgraph/blob/main/SECURITY.md).

Runnable examples for LangChain, LangGraph, PydanticAI, CrewAI, the OpenAI Agents SDK and the Claude Agent SDK, each
the same story wired a different way, are in
[examples/frameworks](https://github.com/voodoomods/hypgraph/tree/main/examples/frameworks).

## Wire it into your system

The core is one Python package with no dependencies. You decide who is trusted to do what:

```python
from hypgraph import Graph, Policy

g = Graph("research.hypgraph",
          policy=Policy(reviewers={"critic", "stats"},      # whose verdicts count
                        instrument="runner"),               # the only author that files lab-recorded runs
          spend=my_ledger.spend)                            # optional: prices the work behind each investigation

with g.writing_for(task_id):                                # every event carries the task, for cost tracing
    g.create(author=agent_name, type="claim", inv=inv, fields={...}, links=[...])
```

- **Multi-agent:** give each agent its own author name. Make your critic agents reviewers. Have your job runner
  write as the instrument, so its runs count as recorded, not reported.
- **Your web framework:** `hypgraph.server.dispatch(graph, method, path, query, body)` is the JSON API, and
  `hypgraph.ui.static_dir()` is the HypGraph UI to mount next to it.
- **Watching it live:** `GET /api/graph/stream?inv=` pushes every event as it is written (Server-Sent Events,
  resumable with `Last-Event-ID`), including writes from another process on the same file, such as a swarm running
  against the record. `GET /api/graph/profile?inv=` gives the investigation's profile as a UI speaks it: each node
  type's label ("Requirement", "Thesis"), the workflow's stages and the report's name. A swarm's telemetry sidecar
  (`<db>.telemetry.jsonl`, written by hypswarm) rides the same stream as `telemetry` events, so the Live view shows every
  model and tool call as it happens.
- **CI:** `hypgraph export -o record.bundle.json && hypgraph verify record.bundle.json`. The bundle is a single file
  your reviewers or auditors can check with SHA-256, in any language or in the browser. `--telemetry` carries the
  swarm's sidecar too, outside the chain, so the bundle replays the run with no server.

The full guide is at [hypgraph.com/engineers](https://hypgraph.com/engineers/).

## Try it

```bash
pip install hypgraph
hypgraph demo        # a complete worked investigation (Broad Street, 1854) built into ./research.hypgraph
hypgraph serve       # explore it in the HypGraph UI: http://127.0.0.1:8765
hypgraph report      # the facts, generated from the record
```

Or watch a swarm work in each profile, replayed live from its record:
[hypgraph.com/examples](https://hypgraph.com/examples/). Or try to get a claim past the real engine in your browser:
[hypgraph.com/play](https://hypgraph.com/play/).

## Where it came from

HypGraph began as the research graph of a team of AI agents running long investigations under governed egress, and
was pulled out so anyone can use it. Each rule exists because the agents made the mistake behind it:
- a validation that was blind to the answer;
- a null model that broke the system's own rules;
- a summary whose numbers matched no result;
- "never" written about something that happened once in a thousand.

That team still runs on it, and its graph UI is built from this package. Against the team's live record (1,357 events,
790 nodes), the library derives the same standing for every node as the engine it replaced.

## Performance

The engine is pure Python and stays fast at the sizes research records reach. On `dev/bench.py`'s record (one
investigation of questions, results, claims and reviews), at 10,001 nodes deriving every node's standing takes 0.34 s
on a Windows laptop, reading one node 0.07 ms, and a write about 12 ms, mostly SQLite committing to disk; derivation
grows in step with the record. A write costs what it touches: cached standing is kept for every node the write can't
affect, and a randomized suite checks that against a full rebuild. Run `python dev/bench.py` for your machine.

## Made by

HypGraph is made by **Nicolas Houghtaling** at **[VoodooMods LLC](https://github.com/voodoomods)**.

## Disclaimer

Provided as is, without warranty. Standing is derived from what was written into a record, by rules you can
read; it is not a certification or an endorsement, a verified chain proves a record unchanged rather than correct, and
nothing here is legal, medical or financial advice. The full text: [DISCLAIMER.md](https://github.com/voodoomods/hypgraph/blob/main/DISCLAIMER.md).

## License

Code: [Apache-2.0](https://github.com/voodoomods/hypgraph/blob/main/LICENSE). The record format ([docs/spec.md](https://github.com/voodoomods/hypgraph/blob/main/docs/spec.md)) and the docs: CC BY 4.0. Cite it with
[CITATION.cff](https://github.com/voodoomods/hypgraph/blob/main/CITATION.cff).
