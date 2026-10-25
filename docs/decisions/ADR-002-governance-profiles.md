# ADR-002 — Governance profiles: what a domain means by evidence, acceptance and done, pinned and versioned

**Date** 2026-10-25 · **Status** accepted · **Where** `profiles.py`, hooks in `schema`, `coord`, `graph`, `server`, `mcp`

## Context

The engine's rules — claims bound to measured results, k/n for absolutes, a reviewer's verdict to settle a question
— are the scientific case written as code. A software team needs "it passes" to mean *the instrument ran the
tests*; a trading desk needs "edge" to mean *out of sample, after costs*; a research assistant needs every factual
claim to cite what was read; an optimisation run needs "optimal" to come with a bound. Each is a different answer to
the same three questions: what counts as evidence for a claim, when is an order's work accepted, and when is the
investigation done. Those answers belong in the record, not in prompts (the harmony study measured that rules in
prompts are followed inconsistently; rules the record enforces are followed always).

## Decision

A **profile** is a named, versioned, frozen set of: vocabulary (shown, not enforced); default predicates per target
type; domain predicates the record can check (`tests_pass`, `backtested_oos`, `sourced`, `feasible_bounded`);
write-time validators on claims and results (`PASS_WITHOUT_INSTRUMENT_RUN`, `EDGE_WITHOUT_OOS_COSTS`,
`BACKTEST_WITHOUT_COSTS`, `CLAIM_WITHOUT_SOURCE`, `OPTIMAL_WITHOUT_BOUND`, `OBJECTIVE_WITHOUT_FEASIBILITY`);
completion criteria derived from the record (`questions_settled`, `requirements_verified`, `position_recorded`,
`all_sourced`, `incumbent_feasible`); and suggested seat templates. Five ship: `scientific@1` (the default — an
investigation with no profile behaves exactly as before), `software@1`, `trading@1`, `knowledge@1`,
`optimization@1`.

An investigation **pins** its profile (`fields.profile = "software@1"`; an unknown id is refused at creation).
Rules never change under a version — a changed rule is `@2` — so a record written under `trading@1` means the same
thing in a year. `issue_work` takes the profile's default predicates; `check_work` evaluates the domain predicates
with the same lease-window rule as the built-ins; `create` adds the profile's refusals to the claim checks and
refuses results the profile rejects (curators excepted, as for claim checks); `completion(inv)` reports the
criteria; the briefing's MISSION names the profile and the criteria's state; the server has `/completion` and
`/profiles`; the MCP server has `completion`. A cited source now counts as a claim's evidence (knowledge profile).

## Alternatives considered

- Per-host subclasses of `Graph`: rules would live in code outside the record and couldn't be pinned or read back.
- Prompts per domain only: the measured failure mode (see context).
- One mutable profile per name: a record written under last month's rules would silently mean something else.

## Consequences

- Tests (`tests/test_profiles.py`): unknown profile refused; no profile = today's predicates and criteria; software —
  the tester's own "positive" result does not meet `tests_pass`, the instrument's replicating lab run does, "passes"
  is refused without it, completion needs instrument evidence; trading — a costless backtest result is refused, an
  in-sample edge is refused, out-of-sample + fees + a reviewed claim + a sized decision completes; optimisation —
  objective without feasibility refused, "optimal" without a bound refused; knowledge — unsourced claim refused,
  cited claim accepted and completes; server routes. 119 tests pass.
- hypswarm binds rosters and toolkits to these ids (hypswarm ADR-008).
- Open: a `@2` of any profile needs a migration note in CHANGELOG; validators use the same clause-level negation
  as the claim checks (`language.asserted`), so "no edge was found" is not refused.
