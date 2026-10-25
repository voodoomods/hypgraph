# ADR-001 — Writes over HTTP are bound to tokens, and hosts can reserve their own names

**Date** 2026-10-25 · **Status** accepted · **Where** `server.py`, `policy.py`, `cli.py`

## Context

`hypgraph serve --writable` took `author` from the request body and authenticated nobody. The MCP server fixes
its author at start (`--as`), so an agent on MCP can't impersonate; over HTTP anyone who could reach the port
could write as any non-reserved author. For hypswarm that included **`harness`** — the orchestrator that owns
every order, may cancel and rework them, and settles accepted work — because `Policy.reserved` knew only the
engine's four names (instrument, operator, importer, system).

The principle at stake: the record is the authority, and authority starts with knowing who is writing.

## Decision

1. **`Policy.extra_reserved`**: a host may add names to the reserved set (hypswarm adds `harness`). Everything
   that consults `policy.reserved` — the HTTP write path, the MCP `--as` check, the rate limiter, the fixed-record
   guard — sees them. Default empty: existing policies are unchanged.
2. **Bearer tokens on the write route.** `serve --token SECRET=a,b` binds a token to authors; `SECRET=*` (or a
   bare secret) means any *non-reserved* author; `--token-file` and `$HYPGRAPH_TOKEN` are the same thing in other
   places. With any token configured, a write without a known token is **401** (`WWW-Authenticate: Bearer`), a
   write as an author the token isn't bound to is **403**, and a reserved name is accepted only from a token that
   names it explicitly. Secrets are compared with `hmac.compare_digest`; a secret under 16 characters is refused
   at parse time. Reads stay open (the Atlas needs them; a server exposed beyond localhost still belongs behind a
   reverse proxy for reads).
3. **No tokens → exactly today's behaviour**: reserved names refused, everyone else taken at their word.

## Alternatives considered

- Make `harness` one of the engine's fixed roles: it is a hypswarm concept; the engine shouldn't know it.
  `extra_reserved` lets any host reserve what it needs.
- Per-request signatures (HMAC over the body): stronger against replay, but every client would need the
  signing code, and the threat here is identity, not tampering on a localhost link. Tokens over TLS (or a
  reverse proxy) cover the exposure the server is documented for.
- Authenticating reads too: left to the proxy layer for now; a `--private` flag is an easy follow-up.

## Consequences

- hypswarm's `HttpRecord(token=…)` sends the bearer; its one client writes as the harness and every seat, so its
  token is bound to all of them (`SECRET=harness,analyst,…`). An outside seat (a person on MCP, another agent)
  gets a token bound to its own name and cannot issue, cancel or settle orders.
- `AuthError` (hypswarm) distinguishes a refused identity from a refused write.
- Tests: `tests/test_server_auth.py` (401 / 403 / reserved / case folding / no-token path unchanged / parsing);
  hypswarm `tests/test_auth.py` (a swarm runs on its token; outsider can't be the harness).
- The hypgraph suite grew from 91 to 108 tests; wall time 11.4 s → 14.6 s (the new tests start real servers).
