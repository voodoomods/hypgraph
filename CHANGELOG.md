# Changelog

## 0.5.2 — 2026-10-26: freshness for sources, stale evidence in the report

For P3 (the change suite and the instruments in HypSwarm), the record had to know when a *page* moved, not only a
file:
- **A source is fresh while its page still says it.** A host that re-fetches a source's page registers an
  `excerpt` artifact (`derived_from` the source; `meta.contains_passage`, `meta.fetched`). The source is STALE when
  every excerpt of it was superseded, or the live one says the page no longer contains its passage — an edit
  elsewhere on the page keeps it fresh. A source never re-fetched is not stale: nothing says it moved.
- **A claim is stale when every result and every cited source behind it is.** The knowledge gates
  (`source_quoted`, `sourced`) take only fresh sources, so a changed page reopens the question at *sourced*.
- **The report marks it.** Claims and results on stale evidence read `checked · STALE` in the facts tables, a new
  open item lists them, the workflow section lists stale sources too, and the report check treats calling a stale
  claim settled as `REPORT_OVERSTATES_STANDING`.
- **Gates count only what still speaks for the question.** `result_exists`, `backtested` and `solved` take only
  fresh results (their message says which went stale and why); `result_reviewed` doesn't count a check of a stale
  result; a decision is stale when everything it was based on is, and `positioned` / `decided` take only fresh ones
  — a position taken on a backtest the vendor later corrected has to be decided again.
- **The report check reads the answers block.** A fenced ```answers block (the part of a report a harness scores and a
  reader copies) was skipped like any code block, so a report could carry an answer only stale evidence gave and pass.
  Now each answer has to be one a current claim on its question makes — live, not stale — at the precision written and
  with its sign: `REPORT_ANSWER_STALE` when only old claims or stale results give it (or a current claim binds the
  same field to another value), `REPORT_ANSWER_UNBACKED` when no claim does or the question has no claim,
  `REPORT_ANSWERS_UNREADABLE` for invalid JSON. Results count through the claims that bind them, and a count k of n
  backs its rate; a number a claim names only as a superseded figure doesn't back an answer; URLs, paths and hashes
  are provenance. Keys are question codes in any case, or a flat object checked against the investigation. Found by
  HypSwarm's change suite.
- **The report check skips the record's own facts.** A line inside a "Facts from the research graph" block is not
  linted when it is exactly a line the record generates now (a hypothesis that says "significantly" is a conjecture
  the record lists, not the author's assertion). Anything else written under that heading is checked as usual.
  Found when a report was refused for the hypothesis line the record itself had written.

## 0.5.1 — 2026-10-26

What wiring HypSwarm's scheduler to the stages (P2) found the workflows had no honest ending or no right answer for:
- **Declining a thesis is a decision.** A decision `kind=no_position` based on the claim meets `positioned` and
  `position_sized` ("1 declined"); only `kind=position` needs size, stop, review date and `paper=true`.
- **An honest "it can't be answered" settles a question whatever its stage.** A checked claim of kind
  `inconclusive` or `exclusion` that answers the question (no source says it; too few trades; infeasible) completes
  it; `stage()` reports `settled_by` and `settled_how`. The claim still needs its evidence — the search's own
  result ("read 3 of 3 pages; 0 mention it") is what it derives from.
- **A verified failure settles a software requirement.** A checked claim resting on an instrument-recorded
  *negative* result ("1 of 2 checks pass", re-run by the instrument) completes the question; `tests_pass_current`
  stays unmet and `requirements_verified_current` says so.
- **The same bytes, registered again, are one node that learns.** A second `create` of an artifact with the same
  sha adds the links given now (`part_of` a question, `supersedes`) and, when the node was untyped, its `kind` /
  `meta` / `path` as a new version. Before, the task's own file silently swallowed the diff registered on it.
- **A decision that settles a work order is the harness's, not the question's** (`decided` ignores it).
- **optimization gains a `checked` stage** (the verifier checks the claim after the result): a question settles on a
  checked claim, so the workflow had to ask for one.
- A review order's target predates the order; `reviewed` / `result_reviewed` now ask that the *review* be new.
- `report()` names experiments by aim and decisions by choice.

## 0.5.0 — 2026-10-26: profiles carry their discipline's workflow

Each discipline's method, as the record enforces it — one page each in `docs/workflows/`, taken from the method
itself (hypothetico-deductive with preregistration; continuous integration and code review; preregistered
backtesting and risk management; source criticism and fact-checking; operations-research practice). The `@1`
profiles are frozen as they were; `scientific@2` … `optimization@2` add the workflow. No profile → unchanged.

- **The stage is derived, never set.** `Graph.stage(question)` / `stages(inv)`, `GET /stage/{id}` / `/stages`, MCP
  `stage`: a question is in the first stage whose gate the record does not meet, every gate MET / NOT MET with what
  would meet it. `Profile.workflow` (`Workflow`, `Stage`) holds the stages, gates, invalidation, typed shapes.
- **Gates double as order predicates**: `hypothesis_stated`, `preregistered` (the experiment, with its expected
  outcome, precedes any run that executes it), `decided`, `diff_registered`, `tests_pass_current`,
  `instance_registered`, `source_quoted`, `search_recorded`, `backtested` (out of sample, after costs, trials
  declared), `positioned`, `still_valid`, `solved`, `result_reviewed`. The `@2` profiles' `done_when` use them.
- **A workflow widens what counts as resting on.** `uses` (scientific, software, trading, optimization) and `cites`
  (knowledge) join `schema.RISKY` for that profile only (`derive.EXTRA_RISKY`): a corrected data file, a superseded
  diff or instance, a withdrawn source puts what rested on it AT RISK. Records under `@1` keep exactly the standing
  they had.
- **Freshness** (`derive.stale`, in every standing): a result whose run used an artifact that is now superseded or
  withdrawn, or whose new `valid_until` has passed, is STALE; a claim is stale when every result behind it is. A
  check on stale evidence doesn't meet `reviewed`; `requirements_verified_current` and `incumbent_verified` need
  fresh instrument runs.
- **Typed shapes.** `artifact.kind` + `artifact.meta` with required fields per workflow (`diff`: base_sha,
  head_sha, files; `instance`; `prices`; `solution`: objective, feasible …) → `ARTIFACT_MISSING_FIELDS`;
  `source.kind` primary / secondary / tertiary and `reliability`; `decision.kind` with `size`, `stop`,
  `review_date`, `paper`, `sensitivity`. `supersedes` now joins artifacts; `corrects` joins sources.
- **The disciplines' refusals**: `TESTS_ON_STALE_HEAD`, `REVIEW_BY_AUTHOR` (the diff's author can't check the
  claim), `EDGE_WITHOUT_TRIALS`, `POSITION_WITHOUT_STOP`, `LIVE_ORDER` (no such path exists), `PASSAGE_MISSING`,
  `SOLVED_WITHOUT_INSTANCE`, `OPTIMAL_ON_STALE_INSTANCE`.
- **Report**: under an `@2` profile, `report()` adds the workflow's section — each question's stage and next gate,
  and the evidence that has gone stale.
- Schema additions are fields and relation endpoints only; no migration. Deferred to later phases, and said so in
  the specs: per-workflow evidence rank (documented, not derived), the knowledge re-fetch check and
  `NUMBER_NOT_IN_PASSAGE`, CI as the software instrument, mechanical feasibility recomputation.

## 0.4.3 — 2026-10-26

Five vocabulary-friction fixes from the HypSwarm discovery study, where 110 of 118 refusals were binding, naming
and shape errors rather than overclaims — and one correct answer was refused fifteen times.
- **A named p-value backs "significantly".** A bound field named `p`, `p_value` or `p_<test>` (an exact McNemar
  `p_exact`), or such a field on a supporting result, satisfies the significance check; below 0.05 the word is
  accepted, above it `SIGNIFICANCE_NOT_SHOWN` quotes it. The record's own two-proportion test stays the fallback.
- **A bound measurement's result supports the claim.** A claim written with `measurements` that name a result gets
  a `supports` edge from that result, so its standing counts the line of support the writer already bound.
- **A wrong relation names the right one.** `executes can't join run → question … — a run joins a question with
  part_of, motivated_by; the other way round, a question joins a run with …`.
- **Enum synonyms** (`schema.SYNONYMS`): `outcome=success` → `positive`, `kind=fact` → `finding`,
  `state=done` → `succeeded`, and more; the stored value is canonical.
- **Small integers bind to a value the sentence names.** "produced 0 trades" binds to `oos_trades`,
  "capacity is 7" to `capacity_total`; an unnamed small integer still binds only to a count.

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
