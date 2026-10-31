# Security

Please report vulnerabilities privately through GitHub's "Report a vulnerability" (Security tab), not as a public
issue. Include the version (`hypgraph --version`), the interface (Python API, CLI, `hypgraph serve`, `hypgraph mcp`)
and the smallest record or request that shows the problem.

This page says what HypGraph enforces, where, and what it leaves to the host. Where a guarantee depends on something
outside the library (who can read the file, who holds a token, where a head hash is published), it says so.

## Who is trusted

| Caller | Trusted? | What it may do |
|---|---|---|
| **Python API** (`Graph(...)`) | Yes: whoever holds the file owns the record | Write as any author, reserved names included; the importer may set times and attribute nodes. The record's rules (claim checks, no official self-review, instrument-only lab runs, append-only history) still apply to every write. |
| **CLI** (`hypgraph …`) | Yes: the person at the terminal | Writes as `--as`, `$HYPGRAPH_AUTHOR` or the login name, any of them. |
| **`hypgraph serve`** | No: an HTTP client | Reads everything. Writes only with `--writable`, never as a reserved author unless a token names it, and only as the authors its token is bound to when tokens are set. |
| **`hypgraph mcp`** | No: an agent | Writes as the one author the server was started with (`--as`), which may not be reserved. |

A host that gives an untrusted agent the Python API or the file has given it the record. Put agents behind the HTTP
or MCP server, or behind your own layer that fixes `author` and refuses the reserved names.

## What the record enforces on every write, through every interface

- **Nobody reviews their own work officially.** A verdict counts only from a reviewer (the policy's, or the ones an
  investigation names), never on the reviewer's own node; anyone else's review is recorded as a comment.
- **Instruments speak for themselves.** Only the instrument author files `kind=lab` runs and what they produced.
- **Whoever issues work directs it.** Only an order's issuer (or the operator / importer) accepts, reworks or settles
  it, so an assignee can't rewrite what counts as done for its own order and then accept it. An order is accepted only
  when every predicate is met.
- **Claims carry their numbers.** Every number in a claim must come from a bound measurement, the scope or a declared
  constant; absolute words need k of n with k = 0 or n. A refused claim says what to fix.
- **History is append-only.** Revisions add versions; withdrawals and retractions are new rows; SQLite triggers refuse
  UPDATE and DELETE on the tables. A published or archived investigation takes no new evidence.
- **Standing is derived, never set.** No field says "confirmed"; review state, risk and independent lines are computed
  on read.

These rules hold for names, not people. HypGraph can't tell that two author names are the same agent. Review
independence is only as good as the authentication of names, which is the host's job (below).

## `hypgraph serve`

- **Binds to `127.0.0.1`** and is **read-only** unless started with `--writable`.
- **Host header check (421)** against DNS rebinding. A wildcard bind (`--host 0.0.0.0`, as inside a container)
  answers to loopback names only; add others with `--allow-host`. A wildcard bind never means "any Host".
- **Browser writes must be same-origin (403).** A request carrying an `Origin` must come from the exact host and port
  the server was reached at. A page on another port of the same machine, or `Origin: null`, is refused. Clients that
  send no `Origin` (scripts, agents) are not browsers and aren't affected.
- **Write tokens.** `--token SECRET=a,b` binds a token to authors `a` and `b`; `--token SECRET=*` to any author that is
  neither reserved nor on a review board. With tokens set, a write without a known token is 401, and a write as an
  author the token isn't bound to is 403. A reserved name (operator, importer, instrument, system, the host's own
  orchestrator) and a reviewer's name can be written only by a token that names it.
- **Request limits.** Bodies over 2 MB are 413; a missing, negative or non-numeric `Content-Length` is 400.

**Tokens authenticate writes. They do not protect reads.** Every `GET` (the record, exports, the event stream,
telemetry) is open to anyone who can reach the port. To keep a record confidential, keep the server on loopback, or
put it behind a reverse proxy that authenticates readers. In a container, bind `0.0.0.0` inside and publish the port
to `127.0.0.1` on the host (`-p 127.0.0.1:8765:8765`), not to every interface.

Without tokens, `--writable` authenticates nobody: any local process can write as any non-reserved author. Use it
only on a machine where every local process is yours.

## Blind work orders

`issue_work(..., blind=True)` seals the record from the order's assignee until the order is returned or cancelled.
The checker reads the problem statement (questions and investigations) and its own order. Everything else other
authors wrote is shown as a placeholder, left out of search, and has its numbers scrubbed.

**What it protects, where it applies.** The seal is applied by the MCP server (`hypgraph mcp --as <assignee>`), by
HypMesh for every reader, and by any host that answers through `blind.dispatch` with the reader's view. Inside those:

- the routes that summarise other authors' work (report, briefing, board, next experiments, export) answer 409;
- a guess can't be tested by asking: errors have every number blanked, a write is answered with the view after it,
  no check reads sealed material for a sealed writer, and the chain head is withheld. `tests/test_blind_oracles.py`
  asks each request with a right and a wrong guess (and 25 guesses in a row on one record) and requires the same
  answer;
- a sealed writer may link to a sealed node only to say its own work supports, challenges or tests a hypothesis. It
  may not bind a measurement to sealed work, rest a claim on it, review or revise it, or issue work orders.

**What it can't protect.**

- **Plain `hypgraph serve` and the Python API read the whole record.** Readers there have no identity, so nothing is
  sealed. Give a blind checker the MCP seat, or a host that seals, never the file or a plain server.
- **Reads before the order.** A seat that read the record before its order was issued has already seen what is now
  sealed. The record refuses a blind order to an author that has written in it; HypMesh also refuses one to a seat
  that has read. A plain host can't see reads: issue the order first.
- **Names.** An agent that holds another name's token, or a `*` token, is sealed only as the name it writes under,
  unless the host passes its reader's view (`Graph.sealed_from`, as HypMesh does per agent token).
- **A lead who leaks on purpose.** At issue, the order's text is checked for numbers only the sealed material
  carries. Words, paraphrases and numbers split across fields get through. The leak check catches accidents, not
  intent.
- **Anything put in a question or an investigation.** Those are the problem statement and are never sealed. Don't put
  answers there.
- **Timing and resource use** (how long a request takes, how large a record has grown) are not hidden.

## Integrity: what verification shows, and what it doesn't

- **Internal consistency.** `hypgraph verify`, `verify_bundle` and the browser's `verifyBundle` recompute the
  SHA-256 event chain and check the rows against the events both ways: every node, version, link, withdrawal,
  retraction and lease was written by an event and matches it field by field, and every row an event wrote is
  present. A changed body, author, time, link end or reason, a reordered or dropped event, a dropped withdrawal, or a
  row with no event fails. Only the importer may credit another author, and the event says so.
- **Derived views are checked, standing is not.** A bundle's `derived` views must carry, and agree with the
  verified rows on, every fact the rows fix (the investigation list, nodes, live links, titles, authors, times,
  lifecycle). Until 0.7.15 a fact that was left out wasn't checked, so a withdrawn claim with its lifecycle deleted
  verified and showed as active. The standing in them is what the exporter derived: `hypgraph verify --standing`
  re-derives it with the same engine version.
- **Older records are covered field by field where their events allow.** Events written before 0.7.13 don't hash a
  few row fields (a link's reason, a lease note, an importer's credited author). The verifier reports those as not
  covered, and the result says `coverage: partial` at the top.
- **The verifier trusts its caller's policy, not the bundle's.** A bundle's `policy` isn't covered by the chain;
  taking the importer from it let an edited bundle re-attribute an older writer's nodes (fixed in 0.7.14). Pass the
  publisher's policy with `--policy` / `--importer` (`policy=` in Python, `{policy}` in the browser); otherwise the
  default importer is used and a different stated one is reported.
- **Reports, stages and work-order status in a bundle are as exported.** The explorer says so on each of those
  screens; `hypgraph verify --standing` re-derives them.
- **Not who wrote it, and not that it wasn't rebuilt.** Anyone who can write the file can change it and rebuild the
  whole chain, and the result verifies. To rule that out, compare the bundle's `head` with a copy of the head
  published somewhere its holder doesn't control: a paper, a preregistration, a signed tag or release, a timestamping
  service. A bundle whose chain verifies **and** whose head matches the published one can't have been rewritten since.
  `hypgraph verify bundle.json --head HEX` (or `verify_bundle(b, head=...)`) does that comparison and fails on a
  mismatch; [docs/verification.md](docs/verification.md) shows how to publish and sign a head. The authenticity of
  that published copy is outside the record.
- **Scoped bundles are partial.** Events outside the exported investigation are redacted and their content can't be
  checked. The verifier says how many, and that only the full record against the published head rules out a change
  hidden among them. The scope isn't hashed: until 0.7.16 any node could be named as the scope, or a whole record
  relabelled as one investigation, and the rest vanished from the views while the bundle verified. Now the scope must
  name an investigation and the bundle hold only its nodes, and only a scoped bundle may redact.
- **Pinned references** between records check that the cited node's body still hashes to the pinned version. They
  don't check the cited record's history.
- **Not that a claim is true.** Verification shows the record wasn't edited and how each claim stands under the
  rules. Whether the science is right is what the reviews, replications and the evidence are for.

## Recommendations for deployment

- Keep `hypgraph serve` on loopback. Publish container ports to `127.0.0.1` only.
- Give each agent its own token naming its author; give reviewers their own tokens; keep `*` tokens for tools that
  never review.
- Run blind checkers through `hypgraph mcp` (or HypMesh), with the order issued before the seat starts.
- Publish the head of every record you rely on, and verify bundles against it with `--head`.
- Keep the record file out of reach of the agents writing to it.
