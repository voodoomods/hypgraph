# Changelog

## 0.4.2 — 2026-10-25

- **A question is not an assertion.** `language.interrogative` / `asserted` return nothing for a sentence that ends
  with a question mark, and the report check skips the language and number rules on a sentence that asks or that
  quotes one of the investigation's own questions (citations are still checked). Found in the first real HypSwarm
  mixed-swarm run: the lead headed a section "Q2 — Is A significantly more accurate than B…?" and lost its report
  to `REPORT_SIGNIFICANCE_UNBACKED` three times.

## 0.4.1 — 2026-10-25

Three rules the hypswarm examples exposed, each with a test:
- A claim's numbers that appear in a cited source's passage, citation or title are accounted for (a knowledge claim
  "signed on 24 October 1648" citing the passage that says so is no longer `UNBOUND_NUMBER`).
- A rework's predicates count evidence written since the **first** order of its chain (`coord.chain_root`): a
  `tests_pass` met by the instrument's re-run under the original order stays met under the rework.
- `PASS_WITHOUT_INSTRUMENT_RUN` accepts a claim resting on the author's result when a live lab run `replicates`
  the run that produced it and the re-run's result is positive (`profiles._instrument_backed`).

## 0.4.0 — 2026-10-25: the coordination layer

Held until the harmony study had exercised every path (pilots 1–4, a 142-run confirmatory, two follow-up rounds). Governance profiles, token-bound authors, work orders with predicates, order text that carries the target, instrument reproduction, replayable refusals.

### Identity and arithmetic (2026-10-25)
- `hypgraph serve --token SECRET[=authors]` binds writes to bearer tokens (401 without one, 403 for an author the token isn't bound to; a reserved name needs a token that names it). `--token-file`, `$HYPGRAPH_TOKEN`. Without tokens: unchanged. `Policy.extra_reserved` lets a host reserve its own names (hypswarm reserves `harness`). ADR-001.
- **Governance profiles** (`hypgraph.profiles`, ADR-002): `scientific@1` (the default), `software@1`, `trading@1`, `knowledge@1`, `optimization@1` — each a versioned set of default predicates per target, domain predicates (`tests_pass`, `backtested_oos`, `sourced`, `feasible_bounded`), write-time refusals (`PASS_WITHOUT_INSTRUMENT_RUN`, `EDGE_WITHOUT_OOS_COSTS`, `BACKTEST_WITHOUT_COSTS`, `CLAIM_WITHOUT_SOURCE`, `OPTIMAL_WITHOUT_BOUND`, `OBJECTIVE_WITHOUT_FEASIBILITY`) and completion criteria. Pinned on the investigation (`fields.profile`); `Graph.completion(inv)`, `GET /api/graph/completion|profiles`, MCP `completion`; the briefing names the profile and its criteria. A cited source counts as a claim's evidence.
- The order text carries the target's own content (a claim's statement, scope, measurements and the values of the results it rests on; a result's values; a question's text; an experiment's protocol), and names a replication of the author's run when one exists — the harmony confirmatory showed 11–16 `show` calls a run reading back what the reply had said.
- `cancel_work` releases the target's lease when the order was still open, so the target can be issued to someone else at once (a resumed hypswarm run with a replaced seat found it blocked).
- `stats.two_proportions` / `detectable` no longer divide by zero on an empty arm (undefined, p = 1, the whole range). `tests/test_stats_values.py` pins Wilson, rule-of-three, Newcombe and the z-test to reference values.


- **Honest negations pass.** A word counts only when its sentence asserts it (`language.asserted`): "A is not
  significantly better", "no evidence that it ever fails", "we cannot conclude that…" are accepted; the unnegated
  overclaim is refused as before. New code `SIGNIFICANCE_CONTRADICTED`: "not significant" when the bound counts
  are (p < 0.05). Found by the harmony pilot, where the checker refused the honest sentence its own message asked
  for.
- **The record binds the numbers it already holds.** A claim's loose numbers are bound to the author's own results
  in the investigation (linked results first) before any refusal; a `derived_from` link is added to the result
  they came from, and the reply says what was bound. Small integers (≤ 12) bind only to counts. In the pilot,
  61 of 106 refused numbers were already in a result.
- **The done signal.** After every write by an assignee, the reply carries its open orders with each predicate
  MET / NOT MET, and "return_work now" when all are (`coord.done_lines`; `orders` on create / revise / review
  results; shown by the MCP tools). In the pilot 8 of 9 sub-agents worked to their turn cap past done.
- **Orders meetable by construction.** `done_when` accepts `predicate` / `name` / a bare string as spellings of
  `p`, and a bad predicate's refusal shows the valid form. Each predicate in an order carries how to meet it with
  the assignee's tools. `result_exists` and `run_registered` count what the assignee wrote while holding the
  order, so no link vocabulary stands between an honest result and a met predicate. A third rework of an order
  whose predicate hasn't moved is refused, with the choices spelled out.
- **The question board.** The briefing's unit is the question: settled (a checked claim answers it), contested,
  answered (unchecked), in progress, open; the frontier is driven by it, and one review settles a question
  (`question_board`). `settle` / MCP `settle_work` accepts every returned order whose predicates are all met.
  Standing in the briefing is now exceptions only (contested, at risk, fallen).
- **Absolutes over an enumerated set pass.** "A trails B in every subset: math −2.6, code −2.2, reading −0.4",
  "all three subsets", "over all 818 items" quantify over what the sentence lists; they are not
  generalisations and are no longer refused. "below zero" is a number, not "never".
- **Replay.** Refusals are logged with the whole claim body and its support, and `hypgraph replay-refusals`
  (`Graph.replay_refusals`) runs every logged refusal through the checker as it is now: same, changed, passes.
  A rule change is judged on the corpus of what agents wrote before it ships.
- **A result written twice is written once.** The same author re-registering the same numbers (the multiset of
  a result's values, rounded, keys ignored) is refused with `RESULT_RESTATES`; a declared rerun (a run that
  `replicates`) is kept and marked; another author's restatement is kept and its standing says `RESTATES RSn`.
  Restated results are collapsed in work-order text.

- **Coordinating a team through the record** (`coord.py`). All of it is deterministic and makes no model calls.
  - `briefing(inv)`: the orchestrator's context compiled from the record (mission, rules, roster, standing,
    frontier, orders in flight and returned with their predicates checked, budget, what changed since the last
    one), with a hash.
  - Work orders are `task` nodes: `issue_work` (the target is leased to the assignee; a duplicate is refused),
    `order_text`, `return_work`, `check_work` (each predicate MET / NOT MET with the nodes that satisfy it),
    `accept_work` (a decision based on the evidence, only when every predicate is met), `rework`, `cancel_work`
    and `cancel_moot`.
  - An order's status is derived, never set: open, returned, overdue, accepted, reworked, cancelled or moot.
    Only evidence written after the order was issued counts toward it.
- **Schema.**
  - `task` gains optional `objective`, `assignee`, `role`, `prediction`, `method`, `done_when`, `budget` and
    `note`; `kanban_id` is no longer required.
  - New relations `rests_on` (an order's pinned premises) and `settles` (a decision accepting an order).
  - `works_on` and `rests_on` join the at-risk relations, so the blast radius of a withdrawal now lists the work
    orders it makes moot.
- **Surfaces.** MCP tools `briefing`, `issue_work`, `my_work`, `check_work`, `return_work`, `accept_work`,
  `rework`, `cancel_work` and `cancel_moot`; CLI `hypgraph brief` and `hypgraph orders`.

## 0.3.0 — 2026-10-24

- **The refusal log.** Every refused claim is logged: author, statement, codes, messages. A later accepted claim by
  the same author that says the same thing (same node, or ≥ 30% shared content words within 24 hours) marks the
  refusal fixed. Append-only, with its own hash chain (`verify_refusals()`); the record's chain is untouched.
  - API: `refusals()`, `refusal_report()`.
  - CLI: `hypgraph refusals [--author …]`. MCP: `refusal_log`. HTTP: `GET /api/graph/refusals`.
  - Atlas: an "Overclaims caught" card in the Work view.
- **`hypgraph check report.md`** lints a write-up against the record (`Graph.check_text`; MCP `check_report`; HTTP
  `POST /api/graph/check`). Exits 1 on errors (`--strict`: warnings too).
  - Errors: citations of withdrawn nodes, settled language about unchecked, contested or at-risk work, unknown
    codes, and unbacked never / no effect / significantly.
  - Warnings: numbers no result contains or implies, omitted disputes, superseded citations, uncited causal
    language.
  - Calibrated on 24 real PegasusDMZ write-ups against its live record. That fixed negations ("cannot be proven"),
    quoted passages under correction, instructions ("never use the eval set"), p-values given in the sentence, and
    "results in" as a noun phrase.
- An absolute whose statement gives its n ("no leaks in 50 prompts", "nothing in 50 of 50") is scoped to what was
  seen and accepted; its standing still carries the bound. Without n it is refused, as before.
- Spec draft 3 (§8 refusal log, §9 checking a write-up).

## 0.2.0 — 2026-10-24

**Refusal, remastered.** The claim checks now do the arithmetic the writer skipped, and every refusal says what the
count actually supports and offers the honest sentence.

- **The arithmetic of never.** "Never" / "always" / "eliminates" / "100%" need a count of what they're about with
  k = 0 or n (`ABSOLUTE_WITHOUT_COUNT`, `ABSOLUTE_UNRELATED_COUNT`). That count needs a 95% bound under 5%
  (`ABSOLUTE_UNDERPOWERED`: "0 of 3 only rules out more than 63%"), and the statement has to show its denominator
  (`ABSOLUTE_HIDES_DENOMINATOR`). The bounds are exact at k = 0 (1 − 0.05^(1/n), the rule of three) and Wilson
  otherwise.
- **Exposure.** A claim can say how many uses, users or units it applies to (`exposure`, `exposure_unit`). Refusals
  and the claim's standing then state how many failures the bound leaves unruled out: "up to 58,155 of 1,000,000".
- **New rules:** `COMPARATIVE_WITHOUT_COMPARISON`, `SIGNIFICANCE_WITHOUT_TEST`, `SIGNIFICANCE_NOT_SHOWN` (the
  record runs a two-proportion test on bound counts itself), `CAUSAL_WITHOUT_INTERVENTION`, and
  `EXCLUSION_WITHOUT_POWER` for "no effect" however it is filed, with the smallest effect the sample could have
  detected.
- **True numbers pass.** Differences, ratios, percentages and relative changes computed from bound measurements are
  accepted ("2.8 points", "81.2% vs 78.4%", "+3.6%"). Statistical quantities must be written to one decimal place, so
  "5 points" can't borrow an interval's end.
- **Refusals agents can act on:** a stable code on every line, and `GraphError.problems` with `code`, `message`,
  `fix` and `words`.
- **Blast radius.** `withdraw()`, and a review that makes a node fall, return `blast_radius`: what rests on it, by
  type, with claims and decisions named (and spend, if metered). The CLI and MCP print it.
- **`hypgraph bound K N --exposure X`** and the MCP tool `bound`: what a count supports, before anyone writes "never".
- A claim's standing carries `bounds`, and `test` for "significantly" claims. Spec draft 2 (§7 rewritten).
- Credits: made by Nicolas Houghtaling at VoodooMods LLC (README, NOTICE, CITATION.cff, package metadata, site).

## 0.1.0 — 2026-10-24

First release on PyPI.

- **Writes cost what they touch.** A write no longer copies the whole in-memory snapshot. Tables are shallow
  copies, and a node's list is copied only when the write appends to it. Derived standing is kept for every node the
  write can't affect (`derive.affected_by`), so the first full read after a write no longer re-derives the graph.
  At 10,000 nodes: building the graph took 77 s instead of 133 s, a full read after a write 0.02 s instead of
  0.17 s, and a write at 5,000 nodes 5.8 ms instead of 12 ms. A randomized suite checks the carried standing
  against a full rebuild after every kind of write.
- New indexes for display codes and the rate limit (`nodes(inv, type)`, `nodes(inv, code)`, `events(actor, kind,
  at)`). Created on open; existing records just gain them.
- Positioning: the evidence layer for AI research agents. README and site lead with the MCP server and the Agent
  Skill; a new engineering guide (`/engineers/`) replaces the human guide; the eval-report example replaces the
  classroom one.

### Extracted from PegasusDMZ

Extracted from the PegasusDMZ research graph and verified against it: on a copy of Pegasus's live
graph (1,357 events, 790 nodes in 5 investigations), the library reproduces the same chain head, every node's
standing, the work queues and the next-experiment rankings.

- **Engine** (stdlib only): typed nodes and edges, append-only SQLite with a SHA-256 event chain and `verify()`,
  standing derived on read, claim checks on write, review pinned to versions, independence and evidence profile,
  leases, next experiments, work map, digest, report.
- **Policy**: reviewers, instrument, operator, importer and system are the host's to set (they were hardcoded in
  Pegasus). Optional `spend` hook for cost. Injectable `clock`; only the importer may set a write's time.
- **Bundles** (`hypgraph/1-bundle`): every event and body as the exact hashed string, so they can be verified in any
  language. Scoped exports redact events outside the investigation and say so. A complete bundle replays row for row.
- **CLI**: `init`, `add`, `link`, `review`, `revise`, `withdraw`, `ls`, `show --why/--impact/--history`, `next`, `work`,
  `report`, `export`, `import`, `verify`, `demo`, `schema`, `serve`, `mcp`, `skill`.
- **MCP server** (FastMCP, `hypgraph[mcp]`): 17 tools, 4 resources, a `method` prompt. Writes as one fixed author.
- **Agent skill**: `SKILL.md` ships in the package; `hypgraph skill --install`.
- **Atlas**: the framework-free explorer, with an HTTP source and a bundle source (it verifies the chain in the
  browser). Cytoscape is vendored.
- **Demo**: Broad Street, 1854 — a teaching reconstruction with three refusals built into the story.
- Fixed while extracting it: a report listed stale-reviewed claims under the wrong key; claim measurements now accept
  result codes (RS3) and store ids.
