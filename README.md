<p align="center"><img src="site/assets/hypgraph.svg" width="72" alt=""></p>

<h1 align="center">HypGraph</h1>
<p align="center"><b>Don't believe the hype. Test the hyp.</b><br>
The evidence layer for AI research agents.<br>
<a href="https://hypgraph.com">hypgraph.com</a> · <a href="https://hypgraph.com/agents/">for agents</a> ·
<a href="https://hypgraph.com/engineers/">for engineers</a> · <a href="docs/spec.md">record format</a></p>

---

Agents doing research write fluent summaries. Some of the numbers in them match no result. "Always" gets written
about one run, a search too weak to find anything becomes "ruled out", and three copies of one result get counted as
three lines of evidence. HypGraph is the record they write into instead. It checks every claim as it's written, so
those claims can't get in:

```text
$ hypgraph add claim statement="The fine-tune is 5 points better than the baseline." scope="2,000 held-out items, greedy decoding, one seed." --link "supports:from:RS1:the eval run"
refused: claim refused:
- numbers in the statement that no bound measurement, the scope or the investigation's constants account for: 5 — bind them to result fields (measurements) or move design constants into the scope
```

(The result said 1,624 against 1,568 correct out of 2,000. That's 2.8 points.)

Every refusal says what to fix, so an agent can act on it. Nothing in the record is ever *set* as known. How well
each claim is known is **derived on every read**:

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
`register_run`, `report`, `verify`, `schema`. The method is in [AGENTS.md](AGENTS.md); the short version is
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

## License

Code: [Apache-2.0](LICENSE). The record format ([docs/spec.md](docs/spec.md)) and the docs: CC BY 4.0. Cite it with
[CITATION.cff](CITATION.cff).
