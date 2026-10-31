# HypGraph — the plan

> **Don't believe the hype. Test the hyp.**
> hypgraph.com

HypGraph is a small, dependency-free Python library for keeping a research record that **can't flatter itself**.
You write down questions, hypotheses, experiments, runs, results, claims, sources, reviews and decisions as typed
nodes joined by typed links. The library never lets anyone *set* how well something is known. It works that out
every time you read: whether a claim was reviewed and on which version, whether something it rests on has fallen,
how many independent lines of evidence it has, and how strong the best one is. Every write is an event in a
SHA-256 hash chain, so a record can't be backdated or quietly changed.

It started as the research graph inside PegasusDMZ, where a team of AI agents does long investigations. It was
built after real mistakes: a validation that was blind to the answer, a null that broke the system's own rules,
numbers in a summary that matched no result, "never" written about something that happened once in a thousand
trials. The library turns each of those mistakes into a rule that is enforced when the record is written.

## Who it is for

Refocused 2026-10-24: agents first, and the people who deploy them.

| Who | What they get |
|---|---|
| **AI agents** | An MCP server and an Agent Skill. Claims are checked before they enter the record, an agent can't review its own work, and every refusal says what to fix. |
| **AI/ML engineers** | One dependency-free package to wire in: roles as policy (reviewers, the job runner as instrument), tool wrappers, the JSON API, the Atlas, spend per investigation. |
| **Scientists running agents** | Eval reports and findings whose numbers are bound to the runs that produced them, with premise chains and reviews kept honest by the record. |
| **Reviewers and auditors** | One bundle to verify with SHA-256, in any language or in the browser. |
| **Tool builders** | An open record format (`hypgraph/1`), a JSON-over-HTTP API, and a framework-free Atlas to embed. |

## Principles (the record's rules)

1. **Standing is derived, never asserted.** No field says "confirmed". Review state, risk, support and evidence
   strength are computed on read from the record itself.
2. **Append-only, hash-chained.** Revisions add versions; withdrawals and retractions are new rows. `verify()`
   recomputes the chain and checks every stored body against the event that wrote it.
3. **Reviews pin versions.** A revised claim is no longer "checked". Its old review stays on record, marked stale.
4. **Claims carry their numbers.** Each number in a claim's statement must be accounted for by a measurement bound
   to a result field, by the scope, or by a declared constant. Absolute words ("never", "all") need k of n with
   k = 0 or k = n. An exclusion needs a search shown able to find a planted answer.
5. **Independence is counted, not assumed.** Support lines that share a run, a data artifact or a source count once.
   Lines with no recorded provenance count once between them.
6. **Instruments speak for themselves.** Only an instrument author (the lab runner) files `kind=lab` runs and what
   they produced. An agent's or person's report of a run is labelled as a report.
7. **Nobody reviews their own work.** Only a reviewer's verdict counts. Everyone else's goes on record as a comment.
8. **Fixed history stays fixed.** A published investigation is closed to new evidence. You build on it in a
   follow-up, and reviews and comments are still welcome.

## Shape of the repository

```
HypGraph/
  src/hypgraph/
    schema.py      the vocabulary: node types, relations, verdicts, evidence ranks (hypgraph/1)
    policy.py      who is a reviewer, an instrument, a curator — the host's trust decisions, not hardcoded
    store.py       SQLite append-only store, triggers, the event hash chain, verify()
    derive.py      standing on read: lifecycle, review, fallen, at_risk, profile, independent lines, sentence
    checks.py      claim checks (numbers, absolutes, exclusions, conventions)
    graph.py       Graph: create / revise / link / retract / withdraw / review / lease + every read
    plan.py        next experiments, work map, duplicates, digest, report
    bundle.py      export / import / verify a portable bundle (string-exact, verifiable without Python)
    server.py      JSON API + the Atlas UI (stdlib http.server; no framework)
    mcp.py         FastMCP server — `hypgraph mcp`
    cli.py         `hypgraph init | add | link | review | show | why | impact | report | verify | export | serve | mcp | demo`
    demos/         teaching investigations (Broad Street, 1854)
    ui/            Atlas: framework-free ES module + CSS + vendored Cytoscape (MIT), offline-first
  tests/           pytest; the Pegasus regression suite ported, plus bundle, server, MCP, CLI
  site/            hypgraph.com — static; forks at the door: "I'm a human" / "I'm an agent"
  docs/            spec (hypgraph/1), how-tos, this plan
  AGENTS.md, llms.txt   the agent entrypoint
```

**Core has no dependencies.** `pip install hypgraph` gives you the engine, the CLI, the HTTP server and the Atlas.
`pip install "hypgraph[mcp]"` adds FastMCP. That matters for schools and locked-down lab machines, and it lets the
engine run in the browser through Pyodide, which the website uses for its live playground.

## The bundle: verifiable without trusting us

`hypgraph export INV > bundle.json` writes one investigation and the event chain behind it. Every event and every
version body is stored as the **exact canonical string that was hashed**, so a verifier only has to run SHA-256 over
strings and compare. The site does this in your browser with WebCrypto. Nothing has to reimplement our JSON
canonicalisation. A paper can ship its bundle, and a reader can check that the record wasn't edited and see each
claim's derived standing.

## Pegasus becomes the first customer

- The proxy's `research_graph.py` becomes a thin shim over `hypgraph.Graph`, with Pegasus's `Policy` (review board,
  `lab` as the instrument, `operator` / `importer` as curators). Spend (`cost()`) stays in Pegasus as a hook: the
  library knows nothing about ledgers.
- The broker routes, graph tools and every existing test keep working, since the shim keeps the module API.
- Atlas on `:8000/atlas` is built from `hypgraph.ui`. The agent image installs the wheel and serves the package's
  static files. Pegasus adds only its operator link and its spend card.
- `egress-check`, backups (`verify(path=…)`) and lab sync are unchanged.

## Phases

| | What | Done when |
|---|---|---|
| **P0** | Plan (this file) | — |
| **P1** | Core library: schema, policy, store, derive, checks, graph, plan, report | The ported Pegasus suite passes against `hypgraph` |
| **P2** | Bundle export / import / verify; CLI | Round trip; a tampered bundle fails `verify` |
| **P3** | HTTP server + Atlas UI kit (HTTP source and bundle source) | `hypgraph serve` shows the demo in the Atlas |
| **P4** | FastMCP server | An MCP client lists the tools and adds a hypothesis and a refused claim |
| **P5** | Website: door, human path, agent path, live demo, verify-in-browser, Pyodide playground | Every page renders in light and dark at phone width; the in-browser verifier passes the demo bundle |
| **P6** | Pegasus rewired onto hypgraph | Pegasus tests pass; Atlas on `:8000` runs on the package's UI |
| **P7** | Release (operator's call): GitHub repo, PyPI, domain | Repo public, wheel on PyPI, site deployed |

## Out of scope for 0.1

Multi-writer sync between graphs (bundles cover sharing), authentication (the host's job; the HTTP server binds to
loopback and is read-only unless started with `--writable`), and a hosted service.

## Status at 0.7.12 (2026-10-31)

All seven phases are done: the library, bundles, the server and UI, the MCP server, the website, Pegasus running on
the package, and releases to PyPI from tags with trusted publishing. What came after the plan, by release, is in
[CHANGELOG.md](../CHANGELOG.md); the main additions were profiles and their workflows (0.5), the coordination layer
of work orders (0.4), pinned references between records (0.7.8) and blind work orders (0.7.9–0.7.11).

Two lines above have moved:

- **Authentication** is no longer only the host's job. `hypgraph serve` binds writes to bearer tokens
  (`--token SECRET=authors`), refuses writes from other origins, and keeps reserved and reviewer names for tokens that
  name them. Reads stay open; see [SECURITY.md](../SECURITY.md).
- **Anchoring** has a verifier: `hypgraph verify --head` checks a record against a head published elsewhere
  ([verification.md](verification.md)).

Still out of scope: sync between records (bundles and pinned references cover sharing), a hosted service, and any
judgement by a model. The rules stay deterministic.

## Where HypGraph ends

HypGraph is useful on its own, with nothing else from the family installed:

| | Responsibility |
|---|---|
| **HypGraph** | The record: evidence, its rules, derived standing, coordination through work orders, verification. |
| **HypSwarm** | Running a team of agents on a record: the scheduler, seats, budgets, telemetry. |
| **HypMesh** | A public mesh of records, one per open question: identities, agent tokens, standing across organisations. |
| **HypDMZ** | Running a swarm in a locked pod: governed egress, the vaulted key, an audit chain. |

A feature belongs in HypGraph only if a single user with one record needs it.
