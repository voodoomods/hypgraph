<p align="center"><img src="site/assets/hypgraph.svg" width="72" alt=""></p>

<h1 align="center">HypGraph</h1>
<p align="center"><b>Don't believe the hype. Test the hyp.</b><br>
A research record that can't flatter itself — for students, scientists and AI agents.<br>
<a href="https://hypgraph.com">hypgraph.com</a> · <a href="https://hypgraph.com/humans/">for humans</a> ·
<a href="https://hypgraph.com/agents/">for agents</a> · <a href="docs/spec.md">the record format</a></p>

---

HypGraph keeps the questions, hypotheses, experiments, runs, results, claims, sources, reviews and decisions of an
investigation as **typed nodes joined by typed links**, in one SQLite file. What it never lets anyone do is *set* how
well something is known. That is **derived on every read** from the record itself:

- **was it reviewed, and which version?** A revised claim isn't "checked" any more. Its old review stays on record,
  marked stale.
- **does it rest on something that fell?** Withdraw a premise and everything built on it is flagged **AT RISK**.
- **how many independent lines of evidence?** Lines that share a run, a data file or a source count **once**.
- **how strong is the best one?** From an unverified report, through a lab-recorded run and a separate
  implementation, up to a replication on new data or an external source.

Every write is an event in a **SHA-256 hash chain**. History can't be rewritten quietly, and a published record can
be checked by anyone, in any language, even in a browser.

And it **refuses** the claims that hype is made of:

```text
$ hypgraph add claim statement="Blue light always grows cress taller." --link supports:from:RS1:the tray heights
refused: claim refused:
- scope: say under which conditions this holds (the data, method, sample) — at least a sentence
- 'always' is absolute: back it with a k/n measurement where k is 0 or n, and keep the scope to the trials actually run — or say 'rarely' / 'in k of n'
```

Every number in a claim must be bound to a result field. "Rules out" needs a search shown to recover a planted
answer. Nobody reviews their own work.

## Install

```bash
pip install hypgraph            # the engine, CLI, HTTP server and Atlas explorer: no dependencies
pip install "hypgraph[mcp]"     # + the MCP server for agents (FastMCP)
```

Python 3.10+. Windows, macOS, Linux.

## Five minutes

```bash
hypgraph demo                   # build "How does cholera spread? Broad Street, 1854" into ./research.hypgraph
hypgraph serve                  # explore it in the Atlas: http://127.0.0.1:8765
hypgraph report                 # the facts, generated from the record (nobody can edit them)
```

Start your own:

```bash
hypgraph init "Cress and light" --objective "Find out whether light colour changes how fast cress grows." --reviewers ada
hypgraph add hypothesis statement="Blue light grows cress faster than red light." predictions='["Blue trays are taller after 7 days."]'
hypgraph add result summary="Blue trays averaged 41 mm, red 33 mm after 7 days." values='{"blue_mm": {"value": 41}, "red_mm": {"value": 33}}'
hypgraph link RS1 supports H1 --why "The blue trays grew taller, as H1 predicts."
hypgraph --as ada review H1 pass --method "Re-measured the trays." --notes "41 and 33 hold."
hypgraph show H1 --why
```

## In Python

```python
from hypgraph import Graph, Policy

g = Graph("cress.hypgraph", policy=Policy(reviewers={"ada"}))
sam = g.author("sam")
inv = sam.investigation("Cress and light", "Find out whether light colour changes how fast cress grows.")["id"]
r = sam.add("result", inv, summary="Blue trays averaged 41 mm, red trays 33 mm after 7 days.",
            values={"blue_mm": {"value": 41}, "red_mm": {"value": 33}})
c = sam.add("claim", inv, statement="Blue-lit cress averaged 41 mm against 33 mm under red light.",
            scope="Two trays each, one week, a windowless room.",
            measurements=[{"name": "blue", "result": r["id"], "key": "blue_mm", "value": 41},
                          {"name": "red", "result": r["id"], "key": "red_mm", "value": 33}],
            links=[{"rel": "supports", "from": r["id"], "why": "The tray heights are the measurement."}])
print(c["state"]["sentence"])
# active claim · unchecked · 1 independent line of support · unverified report · no external replication
```

## For agents (MCP + skill)

```bash
claude mcp add hypgraph -- hypgraph --db study.hypgraph --as claude mcp
hypgraph skill --install          # the agent skill: .claude/skills/hypgraph/SKILL.md
```

The server writes as **one** author, fixed at start. Its claims are checked like anyone's, its verdicts count only
if the investigation names it as a reviewer, and a refusal comes back as a tool error that says what to fix. Tools:
`overview`, `find`, `show`, `start_investigation`, `add`, `link`, `revise`, `withdraw`, `retract_link`, `review`,
`next_experiments`, `work_queue`, `claim_work`, `register_run`, `report`, `verify`, `schema`. See
[AGENTS.md](AGENTS.md).

## Share a record anyone can check

```bash
hypgraph export -o study.bundle.json        # the whole record, every event as the exact string that was hashed
hypgraph verify study.bundle.json
# ✓ study.bundle.json: 59 events verified — chain intact, every row matches the event that wrote it.
```

A bundle can be checked without trusting us or our code: SHA-256 over strings and a few lookups.
[hypgraph.com/verify](https://hypgraph.com/verify/) does it in your browser, then opens the record in the Atlas.

## Embed the Atlas

```html
<link rel="stylesheet" href="atlas.css">
<script src="vendor/cytoscape.min.js"></script>
<script src="atlas.js"></script>
<div id="atlas" style="height:80vh"></div>
<script>
  HypAtlas.mount(document.getElementById('atlas'), { source: HypAtlas.BundleSource(bundle) });  // or HttpSource('/api/graph')
</script>
```

The files ship in the package (`hypgraph.ui.static_dir()`), with Cytoscape vendored, so it works offline.

## Where it came from

HypGraph is the research graph of PegasusDMZ, a governed team of AI agents doing long investigations, pulled out so everyone can use it. Each rule exists because a
real mistake was made without it: a validation that was blind to the answer, a null that broke the system's own
rules, a summary whose numbers matched no result, "never" written about something that happened once in a
thousand. PegasusDMZ's Atlas is built from this package.

## License

Code: [Apache-2.0](LICENSE). The record format ([docs/spec.md](docs/spec.md)) and the docs: CC BY 4.0. Cite it with
[CITATION.cff](CITATION.cff).
