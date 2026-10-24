---
name: hypgraph
description: Keep a research record that can't flatter itself — hypotheses with predictions, experiments with expected outcomes written before running, hashed runs, results, and claims whose every number is bound to a result. Use when investigating a question with evidence (science, data analysis, debugging a hypothesis, literature claims, ML evaluation), when asked to record findings, cite what is established, plan the next experiment, or write a summary that must not overclaim. Works through the `hypgraph` CLI or its MCP server.
---

# HypGraph — test the hyp

HypGraph is an append-only, hash-chained research record. You write nodes (question, hypothesis, experiment, run,
result, claim, source, decision) and typed links. **You cannot set how well anything is known.** Review state, risk,
independent support and evidence strength are derived on every read. When the record refuses a write, the message
says exactly what to fix: fix that, don't route around it.

Prefer the MCP tools if a `hypgraph` server is connected (`overview`, `find`, `show`, `add`, `link`, `review`,
`register_run`, `next_experiments`, `work_queue`, `report`, `verify`). Otherwise use the CLI below, adding `--json`
when you need to parse the output. Install it with `pip install hypgraph`.

## Setup (CLI)

```bash
export HYPGRAPH_DB=study.hypgraph HYPGRAPH_AUTHOR=<your-name>      # or --db / --as on every command
hypgraph ls                                                         # what investigations exist
hypgraph init "Title" --objective "What you want to find out, in a sentence." --reviewers <reviewer-names>
```

The names `lab`, `operator`, `importer` and `system` are reserved. Never write as someone else.

## The method

1. **Read first.** Run `hypgraph ls`, `hypgraph ls --type claim`, `hypgraph show CL3 --why` and `hypgraph work`
   before re-deriving anything. Don't cite a node whose sentence says CONTESTED, AT RISK or UNSUPPORTED without
   checking it.
2. **Hypotheses with predictions.** Name rival hypotheses too.
   ```bash
   hypgraph add hypothesis statement="Caching causes the latency spike." predictions='["Spike disappears with cache off."]'
   hypgraph link H2 alternative_to H1
   ```
3. **Experiments that can fail.** Write the expected outcome per hypothesis **before** running:
   ```bash
   hypgraph add experiment aim="Toggle the cache under fixed load." protocol="10 runs each, cache on/off, same load script." \
     success_criteria="Median p99 differs by more than run-to-run spread." power_check="Inject a known 50 ms delay; confirm it is detected."
   hypgraph link X1 tests H1 expected="p99 drops with cache off"
   hypgraph link X1 tests H2 expected="no change with cache off"
   ```
   `hypgraph next` ranks experiments by how many hypotheses they separate, whether they can show their own power,
   and their cost.
4. **Runs and results.** Hash what you ran: `hypgraph.file_sha256(path)` or MCP `register_run`. Results carry values
   as `{name: {value}}` or `{name: {k, n}}`:
   ```bash
   hypgraph add result summary="p99 fell from 840 ms to 210 ms with the cache off." \
     values='{"p99_on_ms": {"value": 840}, "p99_off_ms": {"value": 210}, "runs": {"value": 10}}' outcome=positive
   ```
5. **Claims carry their numbers.**
   ```bash
   hypgraph add claim statement="With the cache off, p99 fell from 840 ms to 210 ms." \
     scope="Staging, fixed load script, 10 runs per condition, build 4f2a." \
     measurements='[{"name":"on","result":"RS1","key":"p99_on_ms","value":840},{"name":"off","result":"RS1","key":"p99_off_ms","value":210}]' \
     --link "supports:from:RS1:RS1 is the measurement this claim states"
   ```
6. **Ask for review.** Only the investigation's reviewers set standing, never on their own work. Revising a claim
   makes earlier reviews stale and flags decisions based on it.
7. **Summaries start from the record.** `hypgraph report -o facts.md` generates the facts, which can't restate a
   withdrawn claim or override a verdict. Write your interpretation underneath.

## Refusals and their fixes

| The record says | Do this |
|---|---|
| `numbers in the statement that no bound measurement … account for: 30` | Add a measurement binding that number to a result field, or put design constants in the scope. Don't delete the number to sneak past. |
| `'always' is absolute` | Back it with k of n where k = 0 or n, or say "in k of n" / "rarely". |
| `an exclusion needs a search that recovered a planted answer` | Run a power check (plant a known answer and recover it) and set `power=demonstrated` on the result, or file the claim as `kind=inconclusive`. |
| `scope: say under which conditions this holds` | Name the data, method and sample. |
| `link the evidence` | Add a `supports` link from the result, with a reason. |
| `tests …: give data.expected` | Say what the experiment should show if that hypothesis is true. |
| `you can't review your own work` | Ask a named reviewer. |
| `… is published — its record is fixed` | Open a follow-up investigation and link to what you build on. |

## Reading standing

`active claim · checked (fisher:pass, v2) · 2 independent lines of support · replicated on new data · no external replication`

- **review** — `unchecked`, `checked`, `contested`, or `review stale` (vN not yet re-checked).
- **independent lines** — results sharing a run, data file or source count once.
- **evidence** — the strongest line: unverified report < agent-reported run < lab-recorded run < reproduced in
  project < separate implementation < replicated on new data < external source.
- **AT RISK** — a premise fell. **REVISIT** — a decision's basis changed. **UNSUPPORTED** — every support fell.

Report standing as the record states it. Don't upgrade "unchecked" to "shown", or "1 line, agent-reported" to
"established".

## Useful commands

`hypgraph show NODE [--why|--impact|--history]` · `hypgraph work` · `hypgraph next` · `hypgraph revise NODE k=v --reason "…"`
· `hypgraph withdraw NODE --why "…"` · `hypgraph export -o bundle.json` · `hypgraph verify [bundle.json]` ·
`hypgraph serve` (the Atlas explorer) · `hypgraph schema` (every type and relation).
