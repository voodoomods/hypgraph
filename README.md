<p align="center"><img src="https://hypgraph.com/assets/hypgraph.svg" width="72" alt=""></p>

<h1 align="center">HypGraph</h1>
<p align="center"><b>Don't believe the hype. Test the hyp.</b><br>
The evidence layer for AI research agents.<br>
<a href="https://hypgraph.com">hypgraph.com</a> · <a href="https://hypgraph.com/agents/">for agents</a> ·
<a href="https://hypgraph.com/engineers/">for engineers</a> · <a href="https://hypgraph.com/spec/">record format</a></p>

---

Agents doing research write fluent summaries. Some of the numbers in them match no result. A clean red-team run of
50 prompts becomes "the model never leaks". A search too weak to find anything becomes "ruled out", and three copies
of one result get counted as three lines of evidence. Then other claims, decisions and deployments get built on top.
HypGraph is the record agents write into instead. It checks every claim as it's written, does the arithmetic the
writer skipped, and refuses:

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
| "outperforms the baseline", no numbers | `COMPARATIVE_WITHOUT_COMPARISON` | only one side was measured |

Every refusal has a stable code, the arithmetic, and the sentence that *would* be honest, so an agent can repair a
claim in one step. `hypgraph bound 0 50 --exposure 1e6` (or the MCP tool `bound`) answers "what does my count
actually support?" before anyone writes the word.

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

## Connect your agent

```bash
pip install "hypgraph[mcp]"
claude mcp add hypgraph -- hypgraph --db study.hypgraph --as claude mcp     # any MCP client works
hypgraph skill --install                                                     # + the Agent Skill (.claude/skills/hypgraph/SKILL.md)
```

The server writes as one author, fixed when it starts. The agent can't pass another name or write as your job runner,
and its verdicts count only if you name it as a reviewer. Tools: `overview`, `find`, `show`, `start_investigation`,
`add`, `link`, `revise`, `withdraw`, `retract_link`, `review`, `next_experiments`, `work_queue`, `claim_work`,
`register_run`, `bound`, `report`, `verify`, `schema`. The method is in [AGENTS.md](https://github.com/voodoomods/hypgraph/blob/main/AGENTS.md); the short version is
[llms.txt](https://hypgraph.com/llms.txt).

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
  `hypgraph.ui.static_dir()` is the Atlas explorer to mount next to it.
- **CI:** `hypgraph export -o record.bundle.json && hypgraph verify record.bundle.json`. The bundle is a single file
  your reviewers or auditors can check with SHA-256, in any language or in the browser.

The full guide is at [hypgraph.com/engineers](https://hypgraph.com/engineers/).

## Try it

```bash
pip install hypgraph
hypgraph demo        # a complete worked investigation (Broad Street, 1854) built into ./research.hypgraph
hypgraph serve       # explore it in the Atlas: http://127.0.0.1:8765
hypgraph report      # the facts, generated from the record
```

Or try to get a claim past the real engine in your browser: [hypgraph.com/play](https://hypgraph.com/play/).

## Where it came from

HypGraph is the research graph of PegasusDMZ, where a team of AI agents runs long investigations under governed
egress, pulled out so anyone can use it. Each rule exists because the agents made the mistake behind it:
- a validation that was blind to the answer;
- a null model that broke the system's own rules;
- a summary whose numbers matched no result;
- "never" written about something that happened once in a thousand.

PegasusDMZ is the reference deployment, and its Atlas is built from this package. Against PegasusDMZ's live record
(1,357 events, 790 nodes), the library derives the same standing for every node as the engine it replaced.

## Performance

The engine is pure Python and stays fast at the sizes research records reach. At 10,000 nodes, deriving every node's
standing takes 0.09 s, reading one node 0.3 ms, and a write about 10 ms, mostly SQLite committing to disk. A write
costs what it touches: cached standing is kept for every node the write can't affect, and a randomized suite checks
that against a full rebuild.

## Made by

HypGraph is made by **Nicolas Houghtaling** at **[VoodooMods LLC](https://github.com/voodoomods)**.

## License

Code: [Apache-2.0](https://github.com/voodoomods/hypgraph/blob/main/LICENSE). The record format ([docs/spec.md](https://github.com/voodoomods/hypgraph/blob/main/docs/spec.md)) and the docs: CC BY 4.0. Cite it with
[CITATION.cff](https://github.com/voodoomods/hypgraph/blob/main/CITATION.cff).
