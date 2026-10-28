# Changelog

## Unreleased

- **Honest sentences the rules were refusing.** Read off every refusal logged in 96 records of the challenge studies
  (846 refusals; each fix replayed on all of them):
  - absolutes over a set the sentence counts ("cases 1-7 all pass", "none of these 49 rows", "all other 19
    outcomes"), "almost all", an interval "entirely below zero", "distinguishable from zero", "cannot be used /
    asserted / ruled out", and "proven" beside a bound gap or bound, are not generalisations and pass;
  - "no difference remains significant after correction" denies a test, it is not an exclusion that needs power;
    "the interval excludes zero" is interval language;
  - a p-value is found by its key's tokens (`welch_two_sided_p`, `raw_p_steps_k`, `steps_k_p`), not only by a `p_`
    prefix, so "significant" beside such a field is tested rather than refused;
  - a key written beside its value ("n_sig_holm = 0 of 20") is not `KEY_FOR_NUMBER`; "two-sided" and a date are not
    unbound numbers;
  - the instrument's re-execution of a run (what the code printed) is not asked for `feasible` beside an objective
    or fees beside a return — the original result was; a benchmark's return (buy-and-hold, flat) is not a return
    the strategy earned, and `BACKTEST_WITHOUT_COSTS` now names the fields it took as returns.
- **`UNCORRECTED_EFFECT` reads its qualifier beside the effect word.** "Uncorrected" counts within 20 words of
  "changes" / "differs", in the same sentence — not anywhere in it. A 70-word finding "The supplement changes
  steps_k … while dropping its uncorrected p < 0.05 claim" had passed on the word's presence alone.
- **A nominal effect can't hide its correction in the scope.** New code `UNCORRECTED_EFFECT`: a finding that says an
  outcome changed, differs or is significant, while a live result in the same investigation holds that outcome's
  corrected p-value (Holm, Bonferroni, FDR, …) at or above 0.05 or a count of 0 outcomes surviving correction, is
  refused unless the sentence says the test is uncorrected ("differs at uncorrected p < 0.05"), or it binds a
  corrected value and names the correction — or it is filed as a lead. The
  refusal quotes the result and field. "Not significant after Holm correction (Holm p = 0.25)" beside a bound
  nominal p of 0.012 is read against the corrected p, not refused as `SIGNIFICANCE_CONTRADICTED`. Found in a
  20-outcome trial study, where two of twelve runs settled "the supplement changes steps_k" as a checked finding,
  hedged only in the scope field, while the same record said nothing survived correction.
- **The record's own bookkeeping decision isn't a position.** `accept_work` settles an order with a decision
  whose text quotes the order's objective and that rests on the claims that met its predicates. Under trading, a
  kind-less decision with position words in its text and `based_on` links counted as a position, so settling an
  order on "should the desk take a paper position?" was refused for want of a stop (POSITION_WITHOUT_STOP) and the
  run crashed as it settled. The decision now carries `kind: accepted`; a real position still needs its stop.

## 0.7.1 — 2026-10-27: a computed answer needs its code, and opposed answers keep a question open

- **A computation nobody can re-run doesn't settle a computational question.** The optimization workflow's
  `solved`, trading's `backtested` and the scientific workflow's evidenced stage (`result_exists` under a
  scientific profile) count only results something can re-run: the run that produced them carries its code, or
  it is the instrument's (`kind=lab`). Through the hypswarm CLI, with no tool that executes code, the seats wrote
  "exact DP over capacity" and "brute force over 2^21" as prose; the verifier passed a wrong optimum (757 for
  656) and the question settled. The gate now says which results report a computation with no code behind it.
  `workflow.rerunnable(snap, result)`.
- **A question settles only when every live answer to it is checked.** A checked answer beside a live unchecked one
  used to settle the question, and the two may disagree: in a real-model trading run a reviewer re-ran the numbers
  behind "no look-ahead" and checked it while "it is look-ahead" stood unchecked on the same question. The board row
  now says `answered` with the unchecked answers named (`unchecked`), the reviewed gate names them, and completion
  waits. An answer nobody may review (its author is the only reviewer) doesn't block; the row lists it under
  `unreviewable`. `derive.unchecked_answers` / `unreviewable_answers`.
- **Measuring returns isn't trading them.** Trading's BACKTEST_WITHOUT_COSTS no longer fires on a result that counts
  its returns (`n_returns`, `insample_n_returns`, a value in units of returns, days, bars or trades) or reports a
  statistic of them (an autocorrelation, its t, p, standard error or CI). A return, P&L or Sharpe still needs its
  costs. A real-model run lost eight writes measuring a lag-1 autocorrelation.
- **A confidence interval that excludes zero isn't an exclusion.** "Excludes zero", "excludes 1" (a ratio's
  null) and "rules out chance" say an effect is there, so they no longer need a power check
  (EXCLUSION_WITHOUT_POWER). "Rules out an effect" and "no effect" still do.

## 0.7.0 — 2026-10-27: measure questions, and claim checks that know a version from a figure

- **Measure questions.** A question may say `asks: "measure"`, and its workflow's `measure_skips` gates then don't
  apply to it, in `Graph.stage()` and as order predicates. Until now every question met every gate of its profile:
  a timing question was reworked for a diff, a count for a preregistered hypothesis, a look-ahead check for a
  backtest. Real-model runs lost most of their calls to those reworks. `profiles.view()` lists the skipped gates.
- **Claim checks:** dotted versions, inline code and labels (case 8, cases 9–12, #3) aren't figures; a measurement's
  key written in place of its number is refused (KEY_FOR_NUMBER); a statement that says nothing ("Placeholder.")
  is refused (STATEMENT_EMPTY).
- **A rework's predicates are checked like an order's:** an unknown predicate is refused, naming every predicate the
  target can take. A lead had reworked an order with an invented one (`claim_answers_q3`) that could never be met.
- **Trading: a statistic about returns isn't a return earned.** Correlations, hit rates and other diagnostics of
  returns no longer need fees and slippage (BACKTEST_WITHOUT_COSTS); a return, P&L or Sharpe still does.
- **hypgraph.com in the app's design system.** One stylesheet on the HypGraph app's tokens and components, light by
  default, restyles every page. The new homepage:
  - opens on the live app, which can switch between the five workflows, Broad Street and the page's own record;
  - offers the agent and engineer paths, then the facts, what the record refuses, the eight rules and the
    arithmetic of never;
  - ends with the workflows, the deployment options, the page's record and what the record shows and doesn't claim.
- **The homepage proves its figures with its own HypGraph record** (`dev/site_record.py`, now run at every deploy):
  - The instrument measures each figure: tests passing, runtime dependencies, the example records' chains, the bound
    behind the arithmetic of never, and the refused overclaims.
  - A reviewer re-measures each one another way.
  - The page's text is checked against the record with `hypgraph check`, and a copy error fails the deploy.
- **The report check no longer flags "not ruled out" as an absence claim.** Exclusion words that the sentence negates
  are skipped, as absolutes already were. "Up to 58,155 … are not ruled out" and "a leak cannot be ruled out" are
  hedges; the engine's own bound note says it in those words.

- **Derivation scales with the record.** Working out which earlier results a result repeats (`derive.restates`) took a
  pass over the whole graph for every result, recomputing each one's numbers, so deriving a record grew with the
  square of its results. It now reads a per-snapshot index of each investigation's results by the numbers they carry,
  and a result's numbers are computed once per version, shared across snapshots. On `dev/bench.py`'s record: 10,001
  nodes derive in 0.34 s (was 20.35 s), 4,001 in 0.11 s (was 3.65 s). The write-time duplicate check uses the same
  index.
- **Two fixes to carried standing.** Both were found by the test at scale.
  - Results written in the same second were ordered by id, so a result written later could count as "earlier" and
    change what an older result repeats, after the older one's standing had been derived and carried forward. Ties now
    go by write order.
  - Revising or withdrawing a result now re-derives the results that repeat its numbers. They reach it through no
    edge, so they used to keep their old standing.

  The randomized incremental suite now gives results numbers, by several authors, and revises them. It fails on the
  old code (5 of 6 seeds) and passes now.
- `dev/bench.py`: reads, writes and derivation at a given record size, on your machine. The README's performance
  figures come from it.

## 0.6.0 — 2026-10-26: the HypGraph UI, live swarm observability, an example per profile

The Atlas becomes **HypGraph**: one app for every profile, in each profile's own words, that watches a swarm
work as it happens and replays any finished run. The design record is `docs/ui-plan.md`. Nothing in the record
format changes; bundles gain optional fields that sit outside the hash chain.

**The HypGraph UI**, which replaces the Atlas:
- **Eight views in each profile's own words:** Overview, Live, Pipeline, Graph, Evidence, Work orders, Audit log and
  Report. A software investigation shows Requirements and Verifications; a trading one shows Theses and Positions.
- **Overview** has KPI tiles, the completion criteria, each question's stage, a "needs attention" list and recent
  activity. Attention covers stale evidence, contested claims, premises that fell, leases held past their time,
  returned orders, overclaims refused and a broken chain.
- **Pipeline** is a swimlane of the profile's stages, with each gate met or not, its evidence, and what would meet it.
- **Live** shows seats, the record growing and the event stream. It follows `/api/graph/stream` and falls back to
  polling on hosts without it. Any run plays back with play, pause, scrub and speed controls.
- **Drawers:** a node's drawer gives its standing, fields, links both ways, provenance and what would be at risk if
  it fell. A question's drawer gives its stage and gates.
- **Enterprise:**
  - light by default, with dark one key away;
  - WCAG AA text contrast in both themes, checked by a test;
  - every screen is a URL, and Back and Forward work;
  - ⌘K search over views, investigations and nodes, plus keys 1–8, `/`, `t` and Esc;
  - CSV export for tables, PNG and JSON for the graph, Markdown and print-to-PDF for the report, and the bundle;
  - the hash-chain badge, read-only, with no build step.
- **Compatibility for one release:** `atlas.js` and `atlas.css` load the new app, `HypAtlas` is an alias of
  `HypGraph`, and the `--hg-*` theme tokens still apply. Routes a host doesn't serve are hidden rather than failing,
  so PegasusDMZ's older API still works.
- `dev/ui_smoke.py` renders every view of five profile fixtures in both themes, plus an Atlas-style page, in headless
  Chrome. CI runs it.

**Live observability for a running swarm** (with hypswarm ≥ 0.1.0a7's telemetry):
- **`hypgraph serve` streams a swarm's telemetry.** hypswarm writes `<record>.telemetry.jsonl` beside the record: every
  model call, tool call, work order and scheduler decision, as spans. The server serves it at `GET /api/graph/telemetry`
  (paged by byte offset) and tails it into `/api/graph/stream` as `telemetry` events. Ids become `<seq>:<offset>` so a
  reconnect resumes both. A sidecar that appears after the server starts is picked up, and `--telemetry FILE` /
  `--no-telemetry` override the default. Telemetry is shown, never trusted for standing.
- **The Live view shows the swarm working:**
  - each seat's call in flight (the model it's calling or the tool it's running, with seconds elapsed), and its calls,
    tokens, cost and errors;
  - KPI tiles for model calls, tokens in → out and cached, spend, tool calls, errors, and budget used against the run's cap;
  - an event stream merging the record and telemetry, with a filter;
  - a trace for any work order, showing each model and tool call on a timeline;
  - alerts: a tool failing three times in a row, a seat repeating an identical tool call, failed model calls, the
    budget passing 80 %;
  - status from the run's own start and end ("Run ended · settled").

  A record opened before its swarm starts picks the investigation up when it begins. Replay scopes telemetry to the
  replay position. Overview's spend falls back to telemetry when the ledger isn't metered.
- `dev/ui-fixtures/swarm.*` holds a real scripted swarm's bundle and telemetry, and the smoke check requires its trace.

**What the UI needs from the engine:**
- **Each profile speaks its own words.** `Profile.labels` gives the short noun a screen shows for each node type: a
  software question is a **Requirement**, a trading hypothesis a **Thesis**, a decision a **Position**, an
  optimization result a **Solution**. `profiles.view(pid)` returns what a UI needs: the labels for every node type
  (the kernel's word where the profile has none), the meaning of each type, and the workflow's stages, gates and
  report name. The `@1` profiles are frozen and keep the kernel's words. The labels are display only.
- **A bundle carries the workflow views.** Each investigation's `derived` now has `profile`, `stages`, `completion`,
  `board` and `orders` beside the report, so a viewer shows stages and gates without the engine. As before, derived
  views are outside the hash chain and never trusted.
- **Watch a record live.** `GET /api/graph/stream?inv=&after=` pushes every event as it is written, as Server-Sent
  Events. It includes writes from another process on the same file, so a swarm running against the record is
  watched as it works. Ids are event seqs, so a client resumes with `Last-Event-ID`. A comment line every 15 s keeps
  proxies open, and `max_seconds` bounds a read.
- `GET /api/graph/profile?inv=` gives the investigation's profile as a UI speaks it.
- "Atlas" is now the HypGraph UI in the server, the CLI, the README and the skill.

**A live example per profile on hypgraph.com:**
- **Five live examples.** `/examples/` has one page per `@2` profile: scientific, software, trading, knowledge and
  optimization. Each is a HypSwarm run on a real record that opens on its live replay. You see the seats take work
  orders, model and tool calls in flight, writes refused and rewritten, and reviews landing, then you can explore the
  pipeline, graph, evidence and report. The pages load offline from their bundles and re-verify each hash chain in
  the browser. `dev/site_examples.py` rebuilds them from HypSwarm's scripted examples, pacing each reply 0.35–1.4 s,
  and every page says so.
- **A bundle can carry the run's telemetry.** `export(inv, telemetry=path)` and `hypgraph export --telemetry [FILE]`
  (default `<db>.telemetry.jsonl`) add a swarm's sidecar for replay. It is outside the hash chain:
  `verify_bundle` and `from_bundle` ignore it, and the UI labels it "not hash-chained". It is off unless asked for,
  because a sidecar names a run's models, seats and spend.
- **`play` opens on the replay.** The `play` mount option, or `#view=live&play=1`, opens the Live view and plays the
  run from its first event. With reduced motion requested, it shows the finished run with Play one click away.
- **A refused write is not an error.** In the Live view, a tool call the record refused counts as "refused by the
  record", with its reason: amber on the seat, in the stream and in the trace. Errors count real failures only.
- **The site's Atlas page is replaced.** The UI is served from `/app/`, `/explore/` opens any bundle full screen, and
  `/atlas/` forwards there (keeping `?bundle=`, the hand-over from `/verify/` and the fragment). The home page embeds
  the app directly. `/verify/` says when a bundle carries telemetry and opens bundles in HypGraph.
- **A narrow layout.** Below 760 px of its own width (a phone, or a narrow frame), the app's sidebar becomes a strip of
  tabs and the top bar wraps. It uses a container query, so an embed sizes it, not the window.
- The smoke check also renders the site: each example opens replaying with its chain verified, plus the home page,
  the explorer, the `/atlas/` forward and the gallery (106 pages).

## 0.5.3 — 2026-10-26: results that name no file can go stale

- **A result that names no file it read can go stale.** Under a workflow (`@2` profiles), a result whose run has no
  `uses` link was fresh forever, however the files changed. It now goes STALE once an input file of its
  investigation is replaced or withdrawn after the result was written ("it names no file it read, and A1 changed
  after it was written"), and claims resting only on it with it. A file registered on another question only
  (`part_of`) doesn't count against it; run outputs and page excerpts never do; a result written after the change
  is fresh; a result that names its files keeps the usual rule (only those files count). Ordered by the event log,
  not timestamps. Records without a workflow are unchanged. Measured on 851 results in HypSwarm's stored study
  records: none changes standing.

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
