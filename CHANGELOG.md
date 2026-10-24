# Changelog

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
