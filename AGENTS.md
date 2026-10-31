# HypGraph for agents

You are an AI agent and you've been pointed at HypGraph. This page is for you; https://hypgraph.com/llms.txt is the
same in short.

**What standing is not.** Standing is derived from what was written, by the record's rules: never present it as a certification, a peer review or advice (https://hypgraph.com/disclaimer/).

**What it is.** A research record you write into and can't flatter. You add questions, hypotheses, experiments, runs,
results, claims, sources, reviews and decisions. You can't set how well anything is known: review state, risk,
independent support and evidence strength are worked out from the record each time it's read. Every write is a
hash-chained event.

**Why you'd want it.** It stops the mistakes agents make most: stating numbers no result contains, writing "always"
about one run, calling a weak search an exclusion, citing a claim whose premise was withdrawn, and treating three
copies of one result as three lines of evidence. When the record refuses a write, the message says exactly what to
fix.

## Connect

**As a skill** (Claude Code and other Agent Skills hosts), install the skill with:

```bash
pip install hypgraph
hypgraph skill --install          # writes .claude/skills/hypgraph/SKILL.md  (--user: under your home directory)
```

The skill's source is `src/hypgraph/skill/SKILL.md`, also at https://hypgraph.com/SKILL.md.

**As an MCP server:**

```bash
pip install "hypgraph[mcp]"
claude mcp add hypgraph -- hypgraph --db study.hypgraph --as <your-name> mcp
```

Any MCP client works. Command `hypgraph`, args `["--db", "study.hypgraph", "--as", "<your-name>", "mcp"]`.
For HTTP: `hypgraph --db study.hypgraph --as <your-name> mcp --transport http --port 8766`.

You write as one author, fixed when the server starts. The names `lab`, `operator`, `importer` and `system` are
reserved.

**If you hold a work order, `my_work()` comes first.** It gives each order's objective, method, and what counts as
done. A **blind** order seals other authors' work from you until you return it: `overview()`, `report()` and the like
answer that they are sealed, and sealed nodes show as placeholders. That is the point, not an error. Measure it
yourself, record your run and result, then `return_work`. What you write meanwhile is recorded as written blind, and
a result that matches an earlier one is marked as agreeing blind once the order is returned.

## The method

1. **`overview()` first.** Read what's known before re-deriving anything.
2. **Hypotheses with predictions.** `add("hypothesis", {"statement": …, "predictions": […]})`. Rivals get
   `alternative_to`.
3. **Experiments that can fail.** `add("experiment", {...}, links=[{"rel": "tests", "to": "H1", "data": {"expected":
   "…"}}, …])`. Write what each hypothesis expects *before* you run anything. An experiment whose expected outcomes
   differ between hypotheses ranks higher in `next_experiments()`. One with a `power_check` ranks higher still.
4. **Runs and results.** `register_run(name, code_paths=[…], input_paths=[…], output_paths=[…], result_summary=…,
   result_values={"rate": {"value": 0.31}, "hits": {"k": 4, "n": 50}})`. The server hashes the files.
5. **Claims carry their numbers.**
   ```json
   {"statement": "The planted key was recovered in 4 of 50 trials.",
    "scope": "50 synthetic ciphers of 200 letters, quadgram scoring, 10 restarts each.",
    "kind": "finding",
    "measurements": [{"name": "recovered", "result": "RS3", "key": "hits", "k": 4, "n": 50}]}
   ```
   with `links=[{"rel": "supports", "from": "RS3", "why": "RS3 is the measurement this claim states."}]`.
   - every number in the statement must match a bound measurement, the scope, or an investigation constant;
   - "never", "always", "eliminates", "100%" need a count of what they're about with k = 0 or k = n, enough
     trials that the 95% bound is under 5%, and n in the statement ("never, in 3,000 probes"). Check first:
     `bound(k, n, exposure)` says what a count supports and how many failures it leaves unruled out at scale;
   - "beats" / "outperforms" need both sides measured; "significantly" needs a test (the record runs one on two
     bound counts); "causes" needs an experiment that intervened;
   - numbers computed from bound counts (differences, percentages, ratios, intervals) are fine; invented ones
     are not;
   - `kind: "exclusion"` needs a result with `power: "demonstrated"` (a search that found a planted answer).
     Otherwise use `"inconclusive"`.
   Each refusal ends in a code (`[ABSOLUTE_UNDERPOWERED]`) and already gives the honest sentence: use it. Refusals
   are logged per author (`refusal_log`); coming back with the honest version marks yours fixed.
6. **Reviews.** Only reviewers named by the investigation (or the host's policy) set standing. Nobody reviews their
   own work. A revision makes earlier reviews stale.
7. **Start summaries from `report()`, and run `check_report(text)` on the write-up before handing it over.** It's generated from the record, so it can't restate a withdrawn claim. Write
   your interpretation underneath it.

## Reading standing

Every node carries `state.sentence`, for example:

> active claim · checked (fisher:pass, v2) · 2 independent lines of support · replicated on new data · no external replication

`AT RISK — rests on CL4` means a premise fell. `REVISIT — its basis changed: CL1 v1→v2` means a decision rested on an
older version. `UNSUPPORTED` means every support has fallen. Before citing a node marked contested or at risk, check
it.

## Without MCP

- Python: `from hypgraph import Graph` (see README.md).
- CLI: `hypgraph --json …` gives machine-readable output.
- HTTP: `hypgraph serve --writable`, then `POST /api/graph/write {"op": "create", "author": …}`.
- Format: `hypgraph schema --json`, or https://hypgraph.com/schema/hypgraph-1.json.
