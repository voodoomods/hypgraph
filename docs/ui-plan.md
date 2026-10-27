# HypGraph UI — plan (Atlas → HypGraph)

*Status (2026-10-26): P1–P4 built and released in hypgraph 0.6.0; P5 (the Pegasus pod) waits for a rebuild. The
decisions in §6 were taken as proposed: plain "HypGraph", light by default, OpenTelemetry as an optional extra with
prompts and outputs off. The prototype the plan refers to (`dev/ui-prototype/`, with screenshots) lives on the
proposal's branch, `ui-hypgraph` (PR #10), not on main.*

## 1. Where it stands

The explorer shipped as **Atlas** (`src/hypgraph/ui/atlas.js`, `hypgraph serve`, the site's `/atlas/`). It predates the
profiles-as-workflows release (0.5) and was never updated for it:

- **It knows only the scientific method.** Its six views (Graph, Hypotheses, Claims, Provenance, Work, Timeline) are
  built around hypotheses and claims. Nothing in it reads a profile, a workflow, a stage or a gate. A software
  record shows "hypotheses" where the team wrote designs; a trading record has no place for positions; a knowledge
  record's sources and excerpts are just nodes.
- **It has no notion of a running swarm.** It polls the record's events, so writes appear, but who holds which work
  order, which model call is in flight, what it costs, and whether the run is stuck are not visible.
- **It looks like a demo.** It has a dark neon theme, one dense canvas and a single investigation at a time.

## 2. What it becomes

**One product name: HypGraph.** "Atlas" goes everywhere: the page title, `hypgraph serve`'s banner, the site and the
docs. For one release, `HypAtlas` stays as a global alias and `/atlas/` redirects, so embeds don't break.

**It speaks each profile's language.** Every profile gains `labels`, a short noun per node type: a software
`question` is a **Requirement**, a trading `hypothesis` is a **Thesis**, an optimization `result` is a **Solution**.
Every view uses them, and the stages, gates and report name come from the profile's workflow. A record with no
profile falls back to the kernel's words.

**Information architecture.** These are the prototype's eight views, all driven by data the engine already derives:

| view | what it answers |
|---|---|
| **Overview** | Is this done, and is it sound? KPI tiles (settled, checked, stale, contested, work orders, spend), the completion criteria, each question's stage, recent activity |
| **Live** | What is the swarm doing right now? (§3) |
| **Pipeline** | Where is each question in the workflow, and what would move it? A swimlane of the profile's stages with each gate MET / NOT MET, its evidence and what would meet it |
| **Graph** | What rests on what? The graph, with profile labels, checked and stale rings, and click-through to the node |
| **Evidence** | Every claim, result, source and decision, with its derived standing: checked, stale, contested, at risk, re-run by the instrument |
| **Work orders** | What was each seat asked to do, its predicates for done, and how it ended |
| **Audit log** | The append-only event log, with the hash chain re-verified on read (the badge in the top bar) |
| **Report** | The profile's report (Change report, Desk note, Sourced brief, …), with PDF and bundle export |

**Enterprise properties.**
- **Look:** light theme first, with dark available. Dense, tabular and calm. One accent colour (the brand blue);
  status colour only for status.
- **Every screen is a URL:** `#view=pipeline&inv=software@2&q=Q1&at=40`.
- **Trust is visible:** a "chain verified · N events" badge, derived standing everywhere, nothing settable by hand.
- **Search:** ⌘K across nodes, questions and orders.
- **Keyboard and accessibility:** keyboard navigation, WCAG-AA contrast in both themes.
- **Export:** CSV for tables, PNG and JSON for the graph, PDF for the report, a verifiable bundle for the record.
- **Read-only by default:** the UI never writes. Approvals and human review, when they come, go through the
  record's own API with an author, like every other write.
- **No build step, no network:** vanilla ES modules plus the vendored Cytoscape, served by `hypgraph serve` or
  opened from a static site.
- **The CLI is unchanged.**

## 3. Live observability for a running swarm

The goal is everything a run does, from start to end, visible as it happens and auditable afterwards.

**Two streams, one timeline.**
1. **The record** (truth): every write, review, refusal, lease, supersession and stage change. It is already
   hash-chained. `hypgraph serve` gains `GET /api/graph/stream?inv=` (Server-Sent Events) so the UI is pushed each
   event instead of polling.
2. **Swarm telemetry** (observation, never trusted for standing): what the record can't see. HypSwarm emits
   structured events:
   - **Run:** start, stop, why it stopped, budget and its warning line.
   - **Seats:** each seat's lifecycle, what it holds and what it is doing now.
   - **Model calls:** model id, tokens in, cached and out, $, latency, retries, errors.
   - **Tool calls:** name, a scrubbed summary of the arguments, duration, ok or error.
   - **Scheduler decisions:** dispatch, rework, escalation, re-verification, refresh, world changes, and report
     assembled or lost.

   Each event carries `run_id`, `inv`, `seat`, `order`, `span_id` and `parent_span_id`.

**Where telemetry goes** (`run(..., telemetry=…)`):
- **JSONL sidecar** (default, local): `<record>.telemetry.jsonl`. `hypgraph serve` tails it and merges it into the
  stream.
- **OpenTelemetry** (optional extra `hypswarm[otel]`): traces as run → order → model call / tool call spans; metrics
  for tokens, $, calls and latency per seat and model; logs for the rest. This feeds Datadog, Grafana, Honeycomb and
  Splunk without any HypGraph-specific code.
- **Scrubbing:** secrets and arguments are scrubbed before they leave the process. Prompts and outputs are off by
  default and can be switched on per run.

**The Live view.** The prototype shows its shape on replayed real event logs:
- **Run header:** running / settled / stopped, elapsed time, events per minute, budget burn ($ and calls against
  the cap, warning line), and play / pause / scrub for replay of finished runs.
- **Seats:** each seat with its current work order and, with telemetry, its in-flight model or tool call (spinner,
  model, elapsed), writes, cost and errors.
- **The record, growing:** nodes appear as they're written, with stale rings appearing as files change.
- **Event stream:** record and telemetry merged, filterable by seat, kind and order.
- **Alerts:** a seat holding an order past its lease, the same tool failing repeatedly, a loop of identical calls,
  the budget warning line, a refusal burst, stale evidence, a lost report.
- **Trace:** a waterfall per work order: the order's span with each model and tool call inside, tokens and $ per
  span, and where the time went.

A finished run's Live view is the same screen fed from the record plus its telemetry sidecar, so every run can be
replayed exactly.

## 4. The site: a working example per profile

Each `@2` profile gets an interactive page, `/examples/<profile>/`, running the new UI read-only on a real record.
The records come from HypSwarm's five scripted examples: 01 scientific, 02 software, 03 trading, 04 knowledge,
05 optimization. Each page opens on the **Live replay** of that run, so a visitor watches the swarm work, then can
explore the Pipeline, Graph, Evidence and Report.

This needs the bundle to carry what the UI shows. `derived` gains `profile` (labels, stages, report name), `stages`,
`completion`, `board`, `orders` and the `report` markdown, plus the telemetry sidecar when one exists. As now, the
bundle's hash chain is re-verified in the browser, and its derived views are shown as derived and never trusted.

## 5. Phases

| phase | what | verified by |
|---|---|---|
| **P0** | this plan and the prototype (real data, eight views, deep links, light and dark) | screenshots in `dev/ui-prototype/shots/` |
| **P1 · engine** | `Profile.labels` for the five profiles; the bundle's `derived` gains profile, stages, completion, board, orders and report; `GET /api/graph/stream` (SSE); "Atlas" renamed in server, CLI and docs | tests; a bundle round-trip; `hypgraph serve` streaming a write |
| **P2 · UI** | `src/hypgraph/ui/` rebuilt as the HypGraph app (ES modules, no build), all eight views, ⌘K, exports, accessibility; `HypAtlas` alias and `/atlas` redirect | headless screenshots of every view × profile × theme in CI; keyboard and contrast checks |
| **P3 · telemetry** | HypSwarm's event schema, JSONL sink and optional OTLP exporter; serve merges telemetry into the stream; Live view on a real running swarm, with alerts and the trace waterfall | an end-to-end test: a scripted swarm against a served record, with the UI updating as it runs |
| **P4 · site** | five profile example pages with Live replay; the site's Atlas page replaced; docs | the pages load offline from the bundle; the chain verifies in the browser |
| **P5 · pod** | Pegasus's `/atlas` moves to the new UI (needs a pod rebuild: your go-ahead) | the pod's UI smoke check |

## 6. Decisions (taken as proposed)

1. **Name in the UI:** "HypGraph" as the plain product name (prototype), or a qualifier ("HypGraph Console" /
   "HypGraph Explorer")?
2. **Theme:** light by default for enterprise (prototype), with dark one click away?
3. **Telemetry:** OpenTelemetry as an optional extra (proposed), and prompts/outputs off by default?
