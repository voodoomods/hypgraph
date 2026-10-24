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
8. **Check the write-up before you hand it over.** `hypgraph check summary.md` (MCP: `check_report`) reads it
   against the record and flags:
   - numbers no result contains;
   - claims you call "established" that the record has as unchecked, contested or withdrawn;
   - codes that don't exist;
   - "never" / "no effect" / "significantly" with nothing cited behind them.

   Fix every error. Keep a warning only if you can say why. It exits 1 on errors, so it can gate CI.

## Refusals and their fixes

Every refused claim lists one line per problem, ending in a code like `[ABSOLUTE_UNDERPOWERED]`. With the Python
API, `GraphError.problems` holds the same as dicts: `code`, `message`, `fix`, `words`. The message has already done
the arithmetic. Use it.

| Code | What it means | Do this |
|---|---|---|
| `UNBOUND_NUMBER` | A number with no source. Differences, ratios, percentages and intervals computed from bound counts are fine. | Bind it to a result field. Never drop the number to get past. |
| `ABSOLUTE_WITHOUT_COUNT` | never / always / eliminates / 100% with nothing counted. | Say what was seen: "in k of n". |
| `ABSOLUTE_UNDERPOWERED` | 0 of n, but n is too small: the rate could still be above 5%. | Use the honest sentence the refusal gives ("no occurrences in n trials (95% upper bound X)"), or run the trials it says you need. |
| `ABSOLUTE_HIDES_DENOMINATOR` | 0 of n is enough, but the statement hides n. | Put n in the statement: "never, in 3,000 probes". |
| `ABSOLUTE_UNRELATED_COUNT` | The 0 of n counts something else. | Name the measurement after what it counts, or bind the right count. |
| `COMPARATIVE_WITHOUT_COMPARISON` | beats / outperforms / higher than with fewer than two sides measured. | Bind both sides (k/n or value each). |
| `SIGNIFICANCE_WITHOUT_TEST` / `SIGNIFICANCE_NOT_SHOWN` | "significantly" with no test, or a test that fails at 0.05. The record tests two bound counts itself. | Bind both sides as k/n, or a p-value. If it isn't significant, say the difference and that it isn't. |
| `CAUSAL_WITHOUT_INTERVENTION` | causes / leads to with no experiment that intervened. | Say "is associated with", or run the experiment and support the claim with its result. |
| `EXCLUSION_WITHOUT_POWER` | "no effect" / "rules out" without a search shown to find a planted effect. The refusal says the smallest effect your sample could have seen. | Show power (`power=demonstrated`), or file it as `kind=inconclusive` and say "no detectable effect". |
| `SCOPE_MISSING` / `EVIDENCE_MISSING` | No conditions, or nothing supports it. | Name the data, method and sample. Link the result with `supports`. |

**Before writing never or always, run `hypgraph bound K N --exposure USERS`** (MCP tool `bound`). It tells you what
the count supports and how many failures are not ruled out at the scale the claim will be used. Set `exposure` (and
`exposure_unit`) on the claim, so its standing carries that number.

Other refusals: `tests …: give data.expected` (say what each hypothesis predicts), `you can't review your own work`
(ask a named reviewer), `… is published — its record is fixed` (open a follow-up investigation).

**Your refusals are logged.** `hypgraph refusals --author <you>` (MCP: `refusal_log`) shows what you tried to
say, what the record said back, and whether you came back with the honest version. Open refusals are claims you
abandoned. Revisit them.

**When you withdraw or contest a node,** the reply lists what now rests on something that fell, e.g.
`2 nodes rest on CL1: 1 decision (D1); 1 claim (CL2)`. Tell whoever owns those nodes.

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

`hypgraph check summary.md` · `hypgraph refusals` · `hypgraph bound K N [--exposure X]` · `hypgraph show NODE [--why|--impact|--history]` · `hypgraph work` · `hypgraph next` · `hypgraph revise NODE k=v --reason "…"`
· `hypgraph withdraw NODE --why "…"` · `hypgraph export -o bundle.json` · `hypgraph verify [bundle.json]` ·
`hypgraph serve` (the Atlas explorer) · `hypgraph schema` (every type and relation).
