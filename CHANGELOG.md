# Changelog

## Unreleased

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

## 0.1.0 — 2026-10-24

First release. Extracted from the PegasusDMZ research graph and verified against it: on a copy of Pegasus's live
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
